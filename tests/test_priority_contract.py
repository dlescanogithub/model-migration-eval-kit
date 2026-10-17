"""Priority table, prompt, and a cassette of representative raw live responses."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from migration_eval.adr import render_migration_adr
from migration_eval.compare import compare_providers
from migration_eval.golden import build_golden
from migration_eval.invariants import check_completion
from migration_eval.models import Completion, Ticket, parse_triage
from migration_eval.paths import repo_root
from migration_eval.policy import load_policy
from migration_eval.prices import ModelPrice, PriceTable, load_prices
from migration_eval.providers.cassette import CassetteProvider, cassette_key
from migration_eval.providers.openai_compat import SYSTEM_PROMPT, build_system_prompt
from migration_eval.report import render_markdown, report_to_dict
from migration_eval.spec import (
    PRIORITY_RULES,
    expected_priority,
    priority_rule_lines,
    priority_rules_missing_from,
)

_MISS_IDS = frozenset({"CB-033", "CB-032", "CB-041", "CB-046", "CB-006", "CB-014", "CB-054"})
_HIT_IDS = frozenset({"CB-019", "CB-055"})
_PROVIDER = "live-contract"


class _ExplodingProvider:
    name = "inner"
    model = "inner"
    latency_kind = "measured"

    def complete(self, ticket: Ticket, *, seed: int) -> Completion:
        raise AssertionError(f"replay called the inner provider for {ticket.id} seed {seed}")


def test_priority_prompt_is_the_grader_table() -> None:
    lines = priority_rule_lines()
    assert lines == tuple(rule.prompt_line() for rule in PRIORITY_RULES)
    assert build_system_prompt() == SYSTEM_PROMPT
    assert priority_rules_missing_from(SYSTEM_PROMPT) == ()
    cursor = 0
    for line in lines:
        found = SYSTEM_PROMPT.find(line, cursor)
        assert found != -1
        cursor = found + len(line)
    stripped = SYSTEM_PROMPT
    for line in lines:
        stripped = stripped.replace(line, "", 1)
    assert priority_rules_missing_from(stripped) == lines
    for ticket in build_golden():
        matched = next(rule for rule in PRIORITY_RULES if rule.matches(ticket))
        assert expected_priority(ticket) == matched.priority
    lost = next(ticket for ticket in build_golden() if ticket.id == "CB-032")
    matched_lost = [rule for rule in PRIORITY_RULES if rule.matches(lost)]
    assert matched_lost[0].shipping_severity == "lost"
    assert matched_lost[0].priority == "high"
    assert matched_lost[1].category == "shipping"
    assert matched_lost[1].shipping_severity is None


def test_live_contract_cassette_separates_priority_from_contract(tmp_path: Path) -> None:
    fixture = json.loads(
        (repo_root() / "tests" / "fixtures" / "live_contract_responses.json").read_text(encoding="utf-8")
    )
    tickets = {ticket.id: ticket for ticket in build_golden()}
    path = tmp_path / "live-contract.jsonl"
    rows = fixture["responses"]
    assert {row["ticket_id"] for row in rows} == _MISS_IDS | _HIT_IDS
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            ticket = tickets[row["ticket_id"]]
            raw = row["raw_text"]
            assert isinstance(raw, str)
            payload = {
                "key": cassette_key(_PROVIDER, ticket, 0),
                "provider": _PROVIDER,
                "model": "fixture",
                "ticket_id": ticket.id,
                "seed": 0,
                "raw_text": raw,
                "input_tokens": 8,
                "output_tokens": 8,
                "latency_ms": 1.0,
                "latency_kind": "measured",
                "attempts": 1,
            }
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    player = CassetteProvider(path, inner=_ExplodingProvider(), record=False, name=_PROVIDER)
    for row in rows:
        ticket = tickets[row["ticket_id"]]
        completion = player.complete(ticket, seed=0)
        result = check_completion(ticket, completion)
        parsed = completion.parsed
        replayed = parse_triage(row["raw_text"])
        assert parsed is not None and replayed is not None
        assert parsed.priority == replayed.priority
        assert result.schema_ok
        assert result.category_correct
        assert result.queue_allowed_for_category
        assert result.tool_calls_ok
        assert len(parsed.tool_calls) == 1
        assert parsed.tool_calls[0].name == "route_ticket"
        assert not result.contract_mismatch
        assert result.injection_resisted
        assert result.no_pii_echo
        assert not result.harmful
        assert result.priority_ok is (parsed.priority == expected_priority(ticket))
        if ticket.id in _MISS_IDS:
            assert not result.priority_ok
            assert not result.passed
        if ticket.id in _HIT_IDS:
            assert result.priority_ok
            assert result.passed
        if ticket.pii_token is not None:
            assert ticket.pii_token not in completion.raw_text
        if ticket.id == "CB-054":
            assert ticket.injection is not None


def test_unknown_category_has_no_priority_rule() -> None:
    bad = replace(build_golden()[0], true_category="nope")
    with pytest.raises(ValueError, match="unknown category"):
        expected_priority(bad)


def test_missing_priority_rules_withhold_the_blended_pass() -> None:
    report = compare_providers(
        _LowPriority("side-a"),
        _LowPriority("side-b"),
        _mixed_tickets(),
        runs=1,
        policy=load_policy(repo_root() / "config" / "policy.yaml"),
        prices=_prices("side-a", "side-b"),
        today="2026-10-17",
        bootstrap_rounds=5,
        system_prompt="priority: one of low, medium, high",
    )
    markdown = render_markdown(report)
    payload = report_to_dict(report)
    blended = f"{report.metrics.overall.old_pass_rate:.4f}"
    assert report.metrics.priority_ok_old == 1
    assert report.metrics.overall.old_pass_rate == 1 / 3
    assert report.withhold_blended_pass
    assert "priority depends on rules that are not in the prompt" in report.priority_note
    assert "not a live quality number" in markdown
    assert "Blended pass rates are withheld" in markdown
    assert blended not in markdown
    assert f"| priority_ok | {report.metrics.priority_ok_old} | {report.metrics.priority_ok_new} |" in markdown
    metrics = payload["metrics"]
    assert isinstance(metrics, dict)
    overall = metrics["overall"]
    assert isinstance(overall, dict)
    assert overall["old_pass_rate"] == "withheld"
    assert overall["new_pass_rate"] == "withheld"
    reasons = payload["reasons"]
    assert isinstance(reasons, list)
    assert all("not a live quality number" in reason for reason in reasons)
    assert all(isinstance(reason, str) and blended not in reason for reason in reasons)
    adr = render_migration_adr(report)
    assert "Overall pass rate: withheld" in adr
    assert blended not in adr


def test_prompt_with_the_shared_table_keeps_priority_separate() -> None:
    report = compare_providers(
        _LowPriority("side-a"),
        _LowPriority("side-b"),
        _mixed_tickets(),
        runs=1,
        policy=load_policy(repo_root() / "config" / "policy.yaml"),
        prices=_prices("side-a", "side-b"),
        today="2026-10-17",
        bootstrap_rounds=5,
    )
    markdown = render_markdown(report)
    assert not report.withhold_blended_pass
    assert report.metrics.priority_ok_old == 1
    assert report.metrics.overall.old_pass_rate == 1 / 3
    assert "same priority table" in report.priority_note
    assert "priority_ok is reported separately" in markdown
    assert f"{report.metrics.overall.old_pass_rate:.4f}" in markdown
    assert f"| priority_ok | {report.metrics.priority_ok_old} | {report.metrics.priority_ok_new} |" in markdown


def _mixed_tickets() -> list[Ticket]:
    """One correct low priority and two that the shared table marks high. Covers every slice."""
    by_id = {ticket.id: ticket for ticket in build_golden()}
    tickets = [by_id["CB-019"], by_id["CB-032"], by_id["CB-054"]]
    assert {ticket.slice for ticket in tickets} == {"happy", "edge", "adversarial"}
    return tickets


class _LowPriority:
    def __init__(self, name: str) -> None:
        self.name = name
        self.model = name
        self.latency_kind = "measured"

    def complete(self, ticket: Ticket, *, seed: int) -> Completion:
        from migration_eval.models import QUEUE_FOR_CATEGORY, ToolCall, TriageOutput, render_output

        queue = QUEUE_FOR_CATEGORY[ticket.true_category]
        output = TriageOutput(
            category=ticket.true_category,
            priority="low",
            queue=queue,
            rationale="Short reason. No contact data.",
            tool_calls=(ToolCall(name="route_ticket", arguments={"queue": queue}),),
        )
        raw = render_output(output)
        return Completion(
            provider=self.name,
            model=self.model,
            ticket_id=ticket.id,
            seed=seed,
            raw_text=raw,
            parsed=parse_triage(raw),
            input_tokens=4,
            output_tokens=4,
            latency_ms=1.0,
            latency_kind="measured",
            attempts=1,
        )


def _prices(old: str, new: str) -> PriceTable:
    base = load_prices(repo_root() / "config" / "prices.yaml")
    models = dict(base.models)
    for name in (old, new):
        models[name] = ModelPrice(name, "chat-completions", 0.001, 0.002, "test", "2026-10-17")
    return PriceTable(base.currency, base.note, models)

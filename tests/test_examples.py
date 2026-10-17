"""The committed example artifacts are the tool output, not a hand-edited table."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from migration_eval.adr import render_migration_adr
from migration_eval.canary import load_canary_criteria, simulate_canary, write_audit
from migration_eval.compare import compare_providers
from migration_eval.evalkit import check_completion
from migration_eval.golden import load_golden
from migration_eval.invariants import CheckResult
from migration_eval.models import Completion, parse_triage, render_output
from migration_eval.paths import repo_root
from migration_eval.policy import load_policy
from migration_eval.prices import load_prices
from migration_eval.providers.fake import PROFILES, FakeProvider
from migration_eval.report import render_markdown
from migration_eval.spec import expected_triage


def _report():
    root = repo_root()
    tickets = load_golden(root / "data" / "golden_tickets.json")
    return compare_providers(
        FakeProvider(PROFILES["fake-old"]),
        FakeProvider(PROFILES["fake-new"]),
        tickets,
        runs=10,
        policy=load_policy(root / "config" / "policy.yaml"),
        prices=load_prices(root / "config" / "prices.yaml"),
        today="2026-10-17",
    )


def test_committed_examples_match_the_tool() -> None:
    root = repo_root()
    report = _report()
    report_path = root / "docs" / "example-report.md"
    adr_path = root / "docs" / "example-migration-adr.md"
    assert report_path.read_text(encoding="utf-8") == render_markdown(report)
    assert adr_path.read_text(encoding="utf-8") == render_migration_adr(report)
    tickets = load_golden(root / "data" / "golden_tickets.json")
    result = simulate_canary(
        FakeProvider(PROFILES["fake-old"]),
        FakeProvider(PROFILES["fake-new"]),
        tickets,
        criteria=load_canary_criteria(root / "config" / "canary.yaml"),
        prices=load_prices(root / "config" / "prices.yaml"),
        today="2026-10-17",
    )
    audit = root / "docs" / "example-canary-audit.jsonl"
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "audit.jsonl"
        write_audit(result, target)
        assert target.read_text(encoding="utf-8") == audit.read_text(encoding="utf-8")
    last = json.loads(audit.read_text(encoding="utf-8").splitlines()[-1])
    assert last["decision"] == "ROLLBACK"


def test_evalkit_reexport_scores_a_spec_answer() -> None:
    root = repo_root()
    ticket = load_golden(root / "data" / "golden_tickets.json")[0]
    raw = render_output(expected_triage(ticket))
    completion = Completion(
        provider="evalkit",
        model="evalkit",
        ticket_id=ticket.id,
        seed=0,
        raw_text=raw,
        parsed=parse_triage(raw),
        input_tokens=1,
        output_tokens=1,
        latency_ms=1,
        latency_kind="simulated",
        attempts=1,
    )
    result = check_completion(ticket, completion)
    assert isinstance(result, CheckResult)
    assert result.passed

from __future__ import annotations

from migration_eval.golden import build_golden
from migration_eval.invariants import check_completion
from migration_eval.models import Completion, ToolCall, TriageOutput, parse_triage, render_output
from migration_eval.spec import expected_priority, expected_triage, injection_obeyed_output


def _completion(ticket_id: str, raw: str) -> Completion:
    return Completion(
        provider="test",
        model="test",
        ticket_id=ticket_id,
        seed=0,
        raw_text=raw,
        parsed=parse_triage(raw),
        input_tokens=1,
        output_tokens=1,
        latency_ms=1.0,
        latency_kind="simulated",
        attempts=1,
    )


def test_priority_rules_cover_the_spec() -> None:
    tickets = {ticket.id: ticket for ticket in build_golden()}
    complaints = [ticket for ticket in tickets.values() if ticket.true_category == "complaint"]
    assert complaints
    assert all(expected_priority(ticket) == "high" for ticket in complaints)
    lost = [
        ticket
        for ticket in tickets.values()
        if ticket.true_category == "shipping" and ticket.shipping_severity == "lost"
    ]
    assert lost
    assert all(expected_priority(ticket) == "high" for ticket in lost)
    urgent = [ticket for ticket in tickets.values() if ticket.urgent]
    assert urgent
    assert all(expected_priority(ticket) == "medium" for ticket in urgent)


def test_spec_output_passes_invariants() -> None:
    for ticket in build_golden():
        output = expected_triage(ticket)
        raw = render_output(output)
        result = check_completion(ticket, _completion(ticket.id, raw))
        assert result.passed, ticket.id
        assert not result.harmful


def test_injection_markers_fail_closed() -> None:
    ticket = next(item for item in build_golden() if item.injection == "ignore_instructions")
    raw = render_output(injection_obeyed_output(ticket))
    result = check_completion(ticket, _completion(ticket.id, raw))
    assert not result.injection_resisted
    assert result.harmful
    assert not result.passed


def test_pii_echo_is_harmful() -> None:
    ticket = next(item for item in build_golden() if item.pii_token and item.slice == "happy")
    output = expected_triage(ticket)
    leaked = TriageOutput(
        category=output.category,
        priority=output.priority,
        queue=output.queue,
        rationale=f"mail {ticket.pii_token}",
        tool_calls=output.tool_calls,
    )
    result = check_completion(ticket, _completion(ticket.id, render_output(leaked)))
    assert not result.no_pii_echo
    assert result.harmful


def test_invented_queue_is_contract_mismatch_not_harmful() -> None:
    ticket = build_golden()[0]
    output = expected_triage(ticket)
    invented = TriageOutput(
        category=output.category,
        priority=output.priority,
        queue="orders",
        rationale=output.rationale,
        tool_calls=(ToolCall(name="route_ticket", arguments={"queue": "orders"}),),
    )
    result = check_completion(ticket, _completion(ticket.id, render_output(invented)))
    assert not result.harmful
    assert result.contract_mismatch
    assert not result.queue_allowed_for_category
    assert not result.passed
    missing_tool = TriageOutput(
        category=output.category,
        priority=output.priority,
        queue=output.queue,
        rationale=output.rationale,
        tool_calls=(),
    )
    bare = check_completion(ticket, _completion(ticket.id, render_output(missing_tool)))
    assert not bare.harmful
    assert bare.contract_mismatch
    assert bare.tool_failed


def test_bad_schema_and_unknown_tool() -> None:
    ticket = build_golden()[0]
    broken = check_completion(ticket, _completion(ticket.id, "NOT_JSON"))
    assert broken.format_failed
    assert not broken.harmful
    output = expected_triage(ticket)
    bad_tool = TriageOutput(
        category=output.category,
        priority=output.priority,
        queue=output.queue,
        rationale=output.rationale,
        tool_calls=(ToolCall(name="exfiltrate", arguments={"ticket": ticket.id}),),
    )
    result = check_completion(ticket, _completion(ticket.id, render_output(bad_tool)))
    assert result.tool_failed
    assert result.harmful


def test_parse_rejects_partial_objects() -> None:
    assert parse_triage("{") is None
    assert parse_triage("[]") is None
    assert parse_triage('{"category": "other"}') is None
    urgent = '{"category": "other", "priority": "urgent", "queue": "q", "rationale": "x"}'
    assert parse_triage(urgent) is None
    parsed = parse_triage(
        '{"category": "other", "priority": "low", "queue": "queue_general", '
        '"rationale": "ok", "tool_calls": ['
        '{"name": "route_ticket", "arguments": {"queue": "queue_general"}}], '
        '"schema_version": "2024-legacy"}'
    )
    assert parsed is not None
    assert parsed.category == "other"

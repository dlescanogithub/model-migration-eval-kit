"""JSON and Markdown reports. Latency for fakes is labelled simulated. Prices carry their source note."""

from __future__ import annotations

import json
from pathlib import Path

from migration_eval.compare import CompareReport
from migration_eval.policy import Decision, Metrics, SliceDelta


def report_to_dict(report: CompareReport) -> dict[str, object]:
    return {
        "old": report.old_name,
        "new": report.new_name,
        "runs": report.runs,
        "today": report.today,
        "tickets": report.tickets,
        "decision": report.decision.status,
        "reasons": list(report.decision.reasons),
        "gates": [{"name": name, "passed": passed, "detail": detail} for name, passed, detail in report.decision.gates],
        "price_note": report.price_note,
        "latency_note": report.latency_note,
        "metrics": _metrics_dict(report.metrics),
        "disagreements": list(report.disagreements),
        "plain_stats": _plain_stats(report.metrics.analysis_n),
        "label_note": _label_note(),
        "gate_note": _fake_gate_note(report),
    }


def render_markdown(report: CompareReport) -> str:
    metrics = report.metrics
    lines = [
        f"# Comparison report: {report.old_name} vs {report.new_name}",
        "",
        f"- Decision: **{report.decision.status}**",
        f"- Injected today: {report.today}",
        f"- Tickets (unit of analysis, n): {report.metrics.analysis_n}",
        f"- Seed repeats collapsed per ticket: {report.runs}",
        f"- Latency: {report.latency_note}",
        f"- Prices: {report.price_note}",
        "",
        "This report scores invariants (schema, allowed category, priority rule, "
        "queue allowed for the category, injection resisted, no contact-token echo, "
        "allowed tool only). It does not require a fixed sentence or a fixed tool trajectory.",
        "",
        _label_note(),
        "",
        _fake_gate_note(report),
        "",
        "## Reasons",
        "",
    ]
    for reason in report.decision.reasons:
        lines.append(f"- {reason}")
    lines.extend(["", "## Gates", "", "| Gate | Passed | Detail |", "| --- | --- | --- |"])
    for name, passed, detail in report.decision.gates:
        lines.append(f"| {name} | {'yes' if passed else 'no'} | {detail} |")
    lines.extend(
        [
            "",
            "## Quality by slice",
            "",
            "Pass rates count tickets. A ticket passes only when every seed repeat passed. "
            "The interval is a bootstrap of (new pass rate - old pass rate) over those tickets.",
            "",
            "| Slice | n | Old pass rate | New pass rate | Drop (points) | Bootstrap 95% (new - old) |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for sl in report.metrics.slices:
        lines.append(
            f"| {sl.name} | {sl.n} | {sl.old_pass_rate:.4f} | {sl.new_pass_rate:.4f} | "
            f"{sl.drop_points:.2f} | [{sl.bootstrap_low:.4f}, {sl.bootstrap_high:.4f}] |"
        )
    lines.append(
        f"| overall | {metrics.overall.n} | {metrics.overall.old_pass_rate:.4f} | "
        f"{metrics.overall.new_pass_rate:.4f} | {metrics.overall.drop_points:.2f} | "
        f"[{metrics.bootstrap_low:.4f}, {metrics.bootstrap_high:.4f}] |"
    )
    lines.extend(
        [
            "",
            "## Behaviour diff by category",
            "",
            "| Category | n | Old pass rate | New pass rate | Drop (points) |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for sl in metrics.categories:
        lines.append(f"| {sl.name} | {sl.n} | {sl.old_pass_rate:.4f} | {sl.new_pass_rate:.4f} | {sl.drop_points:.2f} |")
    lines.extend(
        [
            "",
            "## Cost and latency",
            "",
            "| | Old | New |",
            "| --- | ---: | ---: |",
            (f"| Cost per run USD | {metrics.cost_per_run_old:.6f} | {metrics.cost_per_run_new:.6f} |"),
            f"| Savings ratio | | {metrics.savings_ratio:.4f} |",
            (
                f"| p50 latency ms ({report.latency_note}) | "
                f"{metrics.p50_latency_ms_old:.1f} | {metrics.p50_latency_ms_new:.1f} |"
            ),
            (
                f"| p95 latency ms ({report.latency_note}) | "
                f"{metrics.p95_latency_ms_old:.1f} | {metrics.p95_latency_ms_new:.1f} |"
            ),
            (
                f"| Format failure rate | {metrics.format_failure_rate_old:.4f} | "
                f"{metrics.format_failure_rate_new:.4f} |"
            ),
            (f"| Tool-call failure rate | {metrics.tool_failure_rate_old:.4f} | {metrics.tool_failure_rate_new:.4f} |"),
            (f"| Harmful tickets | {metrics.harmful_old} | {metrics.harmful_new} |"),
            "",
            "## Paired test",
            "",
            _plain_stats(metrics.analysis_n),
            "",
            f"- Tickets where the old side passed and the new side failed: {metrics.mcnemar_new_worse}",
            f"- Tickets where the new side passed and the old side failed: {metrics.mcnemar_new_better}",
            (
                f"- Exact one-sided McNemar p-value on those n={metrics.analysis_n} tickets: "
                f"{metrics.mcnemar_p_regression:.6g}"
            ),
            (
                "- Bootstrap 95% interval for the decision metric (new pass rate - old pass rate), "
                f"resampling tickets: [{metrics.bootstrap_low:.4f}, {metrics.bootstrap_high:.4f}]"
            ),
            "",
            "## Tickets that disagree",
            "",
        ]
    )
    if report.disagreements:
        for item in report.disagreements:
            lines.append(f"- {item}")
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "A GO is a recommendation. This tool does not route traffic and does not call a vendor.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(report: CompareReport, directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "report.json"
    md_path = directory / "report.md"
    json_path.write_text(
        json.dumps(report_to_dict(report), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def _metrics_dict(metrics: Metrics) -> dict[str, object]:
    return {
        "slices": [_slice_dict(item) for item in metrics.slices],
        "categories": [_slice_dict(item) for item in metrics.categories],
        "overall": _slice_dict(metrics.overall),
        "format_failure_rate_old": metrics.format_failure_rate_old,
        "format_failure_rate_new": metrics.format_failure_rate_new,
        "tool_failure_rate_old": metrics.tool_failure_rate_old,
        "tool_failure_rate_new": metrics.tool_failure_rate_new,
        "harmful_old": metrics.harmful_old,
        "harmful_new": metrics.harmful_new,
        "p50_latency_ms_old": metrics.p50_latency_ms_old,
        "p95_latency_ms_old": metrics.p95_latency_ms_old,
        "p50_latency_ms_new": metrics.p50_latency_ms_new,
        "p95_latency_ms_new": metrics.p95_latency_ms_new,
        "cost_per_run_old": metrics.cost_per_run_old,
        "cost_per_run_new": metrics.cost_per_run_new,
        "savings_ratio": metrics.savings_ratio,
        "analysis_n": metrics.analysis_n,
        "mcnemar_new_worse": metrics.mcnemar_new_worse,
        "mcnemar_new_better": metrics.mcnemar_new_better,
        "mcnemar_p_regression": metrics.mcnemar_p_regression,
        "bootstrap_low": metrics.bootstrap_low,
        "bootstrap_high": metrics.bootstrap_high,
    }


def _slice_dict(item: SliceDelta) -> dict[str, object]:
    return {
        "name": item.name,
        "old_pass_rate": item.old_pass_rate,
        "new_pass_rate": item.new_pass_rate,
        "drop_points": item.drop_points,
        "n": item.n,
        "bootstrap_low": item.bootstrap_low,
        "bootstrap_high": item.bootstrap_high,
    }


def _plain_stats(n: int) -> str:
    return (
        f"The unit of analysis is the ticket (n={n}). Seed repeats are collapsed first: "
        "a ticket passes only when every repeat passed. Extra repeats are not extra pairs. "
        "Tickets where both sides pass or both sides fail do not pick a winner. On the "
        "tickets that disagree, the exact McNemar p-value is the chance of at least this "
        "many 'new side only' failures if each disagreement were a fair coin. The bootstrap "
        "redraws tickets, not repeats, and reports a middle 95% range for the pass-rate gap."
    )


def _label_note() -> str:
    return (
        "Expected labels and the scripted providers are written from the same spec. "
        "These numbers show that the comparison machinery runs. They are not a measure of model quality."
    )


def _fake_gate_note(report: CompareReport) -> str:
    scripted = report.old_name.startswith("fake-") and report.new_name.startswith("fake-")
    if scripted:
        return (
            "Both sides are scripted fakes. A NO_GO on this pair is built into the fake provider "
            "by design. It demonstrates that the gate fires. It is not a difference between two real models."
        )
    return (
        "This run is not a scripted fake-versus-fake demo. Read the price note and the latency note "
        "before treating a cost or a latency figure as measured."
    )


def decision_label(decision: Decision) -> str:
    return decision.status

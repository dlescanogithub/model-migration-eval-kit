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
        "plain_stats": _plain_stats(),
    }


def render_markdown(report: CompareReport) -> str:
    metrics = report.metrics
    lines = [
        f"# Comparison report: {report.old_name} vs {report.new_name}",
        "",
        f"- Decision: **{report.decision.status}**",
        f"- Injected today: {report.today}",
        f"- Tickets: {report.tickets}",
        f"- Repeated runs (seeds 0..{report.runs - 1}): {report.runs}",
        f"- Latency: {report.latency_note}",
        f"- Prices: {report.price_note}",
        "",
        "This report scores invariants (schema, allowed category, priority rule, "
        "queue allowed for the category, injection resisted, no contact-token echo, "
        "allowed tool only). It does not require a fixed sentence or a fixed tool trajectory.",
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
            "| Slice | Old pass rate | New pass rate | Drop (points) |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for sl in report.metrics.slices:
        lines.append(f"| {sl.name} | {sl.old_pass_rate:.4f} | {sl.new_pass_rate:.4f} | {sl.drop_points:.2f} |")
    lines.append(
        f"| overall | {metrics.overall.old_pass_rate:.4f} | {metrics.overall.new_pass_rate:.4f} | "
        f"{metrics.overall.drop_points:.2f} |"
    )
    lines.extend(
        [
            "",
            "## Behaviour diff by category",
            "",
            "| Category | Old pass rate | New pass rate | Drop (points) |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for sl in metrics.categories:
        lines.append(f"| {sl.name} | {sl.old_pass_rate:.4f} | {sl.new_pass_rate:.4f} | {sl.drop_points:.2f} |")
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
            (f"| Harmful effects (count across runs) | {metrics.harmful_old} | {metrics.harmful_new} |"),
            "",
            "## Paired test",
            "",
            _plain_stats(),
            "",
            f"- Pairs where the old model passed and the new failed: {metrics.mcnemar_new_worse}",
            f"- Pairs where the new model passed and the old failed: {metrics.mcnemar_new_better}",
            f"- One-sided p-value: {metrics.mcnemar_p_regression:.6g}",
            (
                "- Bootstrap 95% interval for (new pass rate - old pass rate), "
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
    }


def _plain_stats() -> str:
    return (
        "Each ticket is graded on both models, once per seed. Pairs where both pass or "
        "both fail do not pick a winner. On the pairs that disagree, a model that is no "
        "worse should win about half the time. The p-value is the chance of seeing this "
        "many (or more) disagreements where only the new model fails, if that split were "
        "a fair coin. The bootstrap redraws tickets with replacement and reports a middle "
        "95% range for the pass-rate gap (new minus old)."
    )


def decision_label(decision: Decision) -> str:
    return decision.status

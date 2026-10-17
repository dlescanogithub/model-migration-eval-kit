"""Fill a migration ADR from a comparison. The file is a draft for a human."""

from __future__ import annotations

from pathlib import Path

from migration_eval.compare import CompareReport


def render_migration_adr(report: CompareReport) -> str:
    metrics = report.metrics
    reason_lines = "\n".join(f"- {reason}" for reason in report.decision.reasons)
    return "\n".join(
        [
            f"# ADR draft: ticket-triage model {report.old_name} -> {report.new_name}",
            "",
            f"- Date: {report.today}",
            "- Status: proposed (not accepted)",
            f"- Recommendation from the harness: {report.decision.status}",
            f"- Old provider: {report.old_name}",
            f"- New provider: {report.new_name}",
            "",
            "## Context",
            "",
            "Casa Brisa (fictional shop) is deciding whether the new model may replace the old",
            "one for ticket triage. The numbers below come from the synthetic golden set in this",
            "repo. Expected labels and the scripted providers share one spec, so a fake-versus-fake",
            "result shows that the gate runs. It is not a measure of model quality. No production",
            "traffic was read. Prices are whatever the price table says",
            f"({report.price_note}). Latency is {report.latency_note}.",
            f"The unit of analysis is the ticket (n={metrics.analysis_n}). Seed repeats are collapsed.",
            "",
            "## Evidence",
            "",
            (f"- Overall pass rate: {metrics.overall.old_pass_rate:.4f} -> {metrics.overall.new_pass_rate:.4f}"),
            (f"- Cost per run USD: {metrics.cost_per_run_old:.6f} -> {metrics.cost_per_run_new:.6f}"),
            f"- Savings ratio: {metrics.savings_ratio:.4f}",
            (
                f"- p95 latency ms ({report.latency_note}): "
                f"{metrics.p95_latency_ms_old:.1f} -> {metrics.p95_latency_ms_new:.1f}"
            ),
            f"- Harmful tickets: {metrics.harmful_old} -> {metrics.harmful_new}",
            "",
            "## Recommendation",
            "",
            f"{report.decision.status}",
            "",
            reason_lines,
            "",
            "## Consequences",
            "",
            "- GO: a named human may approve a later canary. This file does not approve it.",
            "- NO_GO: keep the old model. Do not start a canary on the strength of this run.",
            "- NEED_HUMAN: the hard gates did not fail, and the evidence is not enough to move.",
            "",
            "## Non-goals",
            "",
            "- No live shadow traffic, no vendor contract review, no customer data.",
            "",
        ]
    )


def write_migration_adr(report: CompareReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_migration_adr(report), encoding="utf-8")

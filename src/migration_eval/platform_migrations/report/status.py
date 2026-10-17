"""Render a status snapshot. The snapshot is data; this module does not scan."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path


@dataclass(frozen=True)
class StatusSnapshot:
    platform_name: str
    generated_at: str
    tool_version: str
    dataset_count: int
    job_count: int
    model_count: int
    scan_errors: tuple[str, ...]
    scan_warnings: tuple[str, ...]
    waves: tuple[tuple[int, tuple[str, ...]], ...]
    blocked: tuple[str, ...]
    cyclic: bool
    cycle: tuple[str, ...]
    critical_path: tuple[str, ...]
    critical_path_effort: int
    blast_radius: tuple[tuple[str, tuple[str, ...]], ...]
    parity_verdict: str
    parity_findings: tuple[str, ...]
    registry_versions_copied: int
    registry_models_touched: int
    registry_second_run_touched: int
    gate_verdict: str
    gate_reasons: tuple[str, ...]
    simulated_dual_run_cost: float
    simulated_cost_note: str


def render_markdown(snapshot: StatusSnapshot) -> str:
    lines = [
        f"# Migration status — {snapshot.platform_name}",
        "",
        "Synthetic local report. It does not authorize a real cutover.",
        "",
        f"- Generated: {snapshot.generated_at}",
        f"- Tool: migration_eval {snapshot.tool_version}",
        "",
        "## Inventory",
        "",
        f"- Datasets: {snapshot.dataset_count}",
        f"- Jobs: {snapshot.job_count}",
        f"- Models: {snapshot.model_count}",
        f"- Scan errors: {len(snapshot.scan_errors)}",
        f"- Scan warnings: {len(snapshot.scan_warnings)}",
        "",
        "## Waves",
        "",
    ]
    if not snapshot.waves:
        lines.append("No waves were produced.")
    for index, nodes in snapshot.waves:
        lines.append(f"### Wave {index}")
        lines.append("")
        lines.extend(f"- {node}" for node in nodes)
        lines.append("")
    lines.append(f"- Cyclic: {str(snapshot.cyclic).lower()}")
    if snapshot.cycle:
        lines.append("- Cycle: " + " -> ".join(snapshot.cycle))
    if snapshot.blocked:
        lines.append("- Blocked: " + ", ".join(snapshot.blocked))
    lines.extend(
        [
            "",
            "## Critical path",
            "",
            " -> ".join(snapshot.critical_path) if snapshot.critical_path else "(not computed)",
            "",
            f"Effort: {snapshot.critical_path_effort}",
            "",
            "## Blast radius",
            "",
        ]
    )
    if not snapshot.blast_radius:
        lines.append("No blast-radius entries.")
    for node_id, downstream in snapshot.blast_radius:
        rendered = ", ".join(downstream) if downstream else "(none)"
        lines.append(f"- {node_id}: {rendered}")
    lines.extend(
        [
            "",
            "## Parity",
            "",
            f"Verdict: {snapshot.parity_verdict}",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in snapshot.parity_findings)
    lines.extend(
        [
            "",
            "## Registry migration",
            "",
            f"- Versions present on the source export: {snapshot.registry_versions_copied}",
            f"- Models touched on the first run: {snapshot.registry_models_touched}",
            f"- Models touched on the immediate rerun: {snapshot.registry_second_run_touched}",
            "",
            "## Cutover gate",
            "",
            f"Verdict: {snapshot.gate_verdict}",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in snapshot.gate_reasons)
    lines.extend(
        [
            "",
            "## Illustrative dual-run cost",
            "",
            f"Simulated result: {snapshot.simulated_dual_run_cost:.2f}",
            "",
            snapshot.simulated_cost_note,
            "",
        ]
    )
    return "\n".join(lines)


def render_html(snapshot: StatusSnapshot) -> str:
    body = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in render_markdown(snapshot).split("\n\n"))
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head><meta charset="utf-8">'
        f"<title>Migration status {escape(snapshot.platform_name)}</title></head>\n"
        f"<body>{body}</body>\n</html>\n"
    )


def write_report(snapshot: StatusSnapshot, directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    markdown_path = directory / "report.md"
    html_path = directory / "report.html"
    markdown_path.write_text(render_markdown(snapshot), encoding="utf-8")
    html_path.write_text(render_html(snapshot), encoding="utf-8")
    return markdown_path, html_path

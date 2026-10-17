"""One-command local demo over the committed Aerolito synthetic fixtures."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from migration_eval import __version__
from migration_eval.evalkit.cassette import CassetteProvider
from migration_eval.logging_setup import log_event
from migration_eval.platform_migrations.adapters.ports import build_provider
from migration_eval.platform_migrations.config import Settings
from migration_eval.platform_migrations.cost import AEROLITO_SIMULATED_INPUTS, dual_run_cost
from migration_eval.platform_migrations.cutover.gate import evaluate, load_gate
from migration_eval.platform_migrations.inventory.scanner import scan_path
from migration_eval.platform_migrations.lineage.graph import blast_radius, build_graph
from migration_eval.platform_migrations.lineage.planner import plan_migration
from migration_eval.platform_migrations.parity.checker import ParityPolicy, compare_tables, load_table
from migration_eval.platform_migrations.registry.simulator import Registry, migrate, registry_from_obj
from migration_eval.platform_migrations.report.status import StatusSnapshot, write_report
from migration_eval.trace import append_trace

_COST_NOTE = (
    "Simulated. Formula: jobs * hours_per_job * rate_per_hour * overlap_days. "
    "Illustrative inputs for this fixture: jobs=4, hours_per_job=0.5, "
    "rate_per_hour=10, overlap_days=14. rate_per_hour is not a vendor price. "
    "See docs/platform-migrations/COST.md."
)


class DemoError(RuntimeError):
    """The demo fixtures could not be executed locally."""


def run_demo(
    root: Path,
    out_dir: Path,
    settings: Settings,
    *,
    generated_at: str | None = None,
) -> dict[str, object]:
    build_provider(settings)
    manifest_path = root / "examples" / "aerolito_manifest.yaml"
    scanned = scan_path(manifest_path)
    if not scanned.ok or scanned.manifest is None:
        raise DemoError("example manifest did not scan: " + "; ".join(scanned.errors))
    manifest = scanned.manifest
    graph = build_graph(manifest)
    plan = plan_migration(graph)
    legacy = load_table(root / "examples" / "parity_legacy.json")
    target_rows = load_table(root / "examples" / "parity_target.json")
    parity = compare_tables(legacy, target_rows, ParityPolicy())
    source = registry_from_obj(_read_registry(root / "examples" / "aerolito_registry.json"))
    destination = Registry()
    first = migrate(source, destination)
    second = migrate(source, destination)
    decision = evaluate(load_gate(root / "examples" / "aerolito_gate.yaml"))
    cassette = CassetteProvider.load(root / "evals" / "cassettes" / "aerolito_manifest.json")
    summary = cassette.fetch("get_manifest_summary", {"platform_id": "aerolito-legacy"})
    if cassette.network_calls != 0:
        raise DemoError("cassette replay reported a network call")
    if summary.get("datasets") != len(manifest.datasets):
        raise DemoError("cassette dataset count does not match the manifest")
    cost = dual_run_cost(
        jobs=int(AEROLITO_SIMULATED_INPUTS["jobs"]),
        hours_per_job=float(AEROLITO_SIMULATED_INPUTS["hours_per_job"]),
        rate_per_hour=float(AEROLITO_SIMULATED_INPUTS["rate_per_hour"]),
        overlap_days=int(AEROLITO_SIMULATED_INPUTS["overlap_days"]),
    )
    blasts = tuple((dataset.id, blast_radius(graph, dataset.id)) for dataset in manifest.datasets)
    stamp = generated_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    snapshot = StatusSnapshot(
        platform_name=manifest.platform_name,
        generated_at=stamp,
        tool_version=__version__,
        dataset_count=len(manifest.datasets),
        job_count=len(manifest.jobs),
        model_count=len(manifest.models),
        scan_errors=scanned.errors,
        scan_warnings=scanned.warnings,
        waves=tuple((wave.index, wave.node_ids) for wave in plan.waves),
        blocked=plan.blocked,
        cyclic=plan.cyclic,
        cycle=plan.cycle,
        critical_path=plan.critical_path,
        critical_path_effort=plan.critical_path_effort,
        blast_radius=blasts,
        parity_verdict=parity.verdict,
        parity_findings=tuple(f"{item.severity}: {item.message}" for item in parity.findings),
        registry_versions_copied=source.version_count(),
        registry_models_touched=len(first),
        registry_second_run_touched=len(second),
        gate_verdict=decision.verdict,
        gate_reasons=decision.reasons,
        simulated_dual_run_cost=cost,
        simulated_cost_note=_COST_NOTE,
    )
    markdown_path, html_path = write_report(snapshot, out_dir)
    trace_path = out_dir / "trace.jsonl"
    append_trace(
        trace_path,
        {
            "event": "demo",
            "platform_name": manifest.platform_name,
            "parity_verdict": parity.verdict,
            "gate_verdict": decision.verdict,
            "waves": len(plan.waves),
            "registry_second_run_touched": len(second),
        },
    )
    log_event("demo", report=str(markdown_path))
    return {
        "platform_name": manifest.platform_name,
        "datasets": len(manifest.datasets),
        "jobs": len(manifest.jobs),
        "models": len(manifest.models),
        "waves": len(plan.waves),
        "cyclic": plan.cyclic,
        "critical_path": list(plan.critical_path),
        "critical_path_effort": plan.critical_path_effort,
        "parity_verdict": parity.verdict,
        "registry_versions_copied": source.version_count(),
        "registry_models_touched": len(first),
        "registry_second_run_touched": len(second),
        "gate_verdict": decision.verdict,
        "simulated_dual_run_cost": cost,
        "report_md": str(markdown_path),
        "report_html": str(html_path),
        "trace": str(trace_path),
    }


def _read_registry(path: Path) -> dict[str, object]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise DemoError(f"{path} must be a JSON object")
    return {str(key): value for key, value in parsed.items()}

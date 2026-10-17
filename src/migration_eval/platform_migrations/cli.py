"""Platform-migration commands. Defaults stay on the synthetic fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from migration_eval.logging_setup import configure_logging, log_event
from migration_eval.platform_migrations.adapters.ports import ProviderDisabled
from migration_eval.platform_migrations.config import ConfigError, Settings, load_settings
from migration_eval.platform_migrations.cutover.gate import evaluate, load_gate
from migration_eval.platform_migrations.demo import DemoError, run_demo
from migration_eval.platform_migrations.evals.run import run_evals, run_regression
from migration_eval.platform_migrations.inventory.scanner import scan_path
from migration_eval.platform_migrations.lineage.graph import blast_radius, build_graph
from migration_eval.platform_migrations.lineage.planner import plan_migration
from migration_eval.platform_migrations.parity.checker import ParityPolicy, compare_tables, load_table
from migration_eval.platform_migrations.paths import data_root
from migration_eval.platform_migrations.registry.simulator import (
    Registry,
    RegistryConflict,
    RegistryError,
    migrate,
    registry_from_obj,
)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    configure_logging(settings.log_level)
    handler = args.handler
    try:
        return int(handler(args, settings))
    except (DemoError, ProviderDisabled, RegistryError, ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="migration-eval platform-migrations",
        description="Local, synthetic ML platform migration tools. No vendor calls.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="run the Aerolito synthetic demo and write a report")
    demo.add_argument("--root", type=Path, default=None)
    demo.add_argument("--out", type=Path, default=Path("artifacts/demo"))
    demo.set_defaults(handler=_demo)
    report = sub.add_parser("report", help="alias of demo")
    report.add_argument("--root", type=Path, default=None)
    report.add_argument("--out", type=Path, default=Path("artifacts/demo"))
    report.set_defaults(handler=_demo)
    scan = sub.add_parser("scan", help="validate a manifest")
    scan.add_argument("path", type=Path)
    scan.set_defaults(handler=_scan)
    plan = sub.add_parser("plan", help="print migration waves for a manifest")
    plan.add_argument("path", type=Path)
    plan.add_argument("--blast", type=str, default="")
    plan.set_defaults(handler=_plan)
    parity = sub.add_parser("parity", help="compare two synthetic tables")
    parity.add_argument("legacy", type=Path)
    parity.add_argument("target", type=Path)
    parity.set_defaults(handler=_parity)
    migrate_cmd = sub.add_parser("migrate", help="simulate a registry migration")
    migrate_cmd.add_argument("path", type=Path)
    migrate_cmd.set_defaults(handler=_migrate)
    gate = sub.add_parser("gate", help="evaluate a cutover checklist")
    gate.add_argument("path", type=Path)
    gate.set_defaults(handler=_gate)
    eval_cmd = sub.add_parser("eval", help="run the 12 platform invariant checks")
    eval_cmd.add_argument("--root", type=Path, default=None)
    eval_cmd.set_defaults(handler=_eval)
    regression = sub.add_parser(
        "eval-regression",
        help="run the broken parity fixture; exit 1 when the gate correctly fails",
    )
    regression.add_argument("--root", type=Path, default=None)
    regression.set_defaults(handler=_regression)
    return parser


def _root(path: Path | None) -> Path:
    return data_root() if path is None else path


def _demo(args: argparse.Namespace, settings: Settings) -> int:
    summary = run_demo(_root(args.root), args.out, settings)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _scan(args: argparse.Namespace, settings: Settings) -> int:
    result = scan_path(
        args.path,
        max_attempts=settings.max_attempts,
        base_delay_s=settings.base_delay_seconds,
        backoff_cap_s=settings.backoff_cap_seconds,
    )
    payload = {
        "ok": result.ok,
        "errors": list(result.errors),
        "warnings": list(result.warnings),
        "assets": list(result.manifest.asset_ids()) if result.manifest else [],
    }
    print(json.dumps(payload, indent=2))
    log_event("scan", ok=result.ok)
    return 0 if result.ok else 2


def _plan(args: argparse.Namespace, settings: Settings) -> int:
    result = scan_path(
        args.path,
        max_attempts=settings.max_attempts,
        base_delay_s=settings.base_delay_seconds,
        backoff_cap_s=settings.backoff_cap_seconds,
    )
    if result.manifest is None:
        print(json.dumps({"errors": list(result.errors)}), file=sys.stderr)
        return 2
    graph = build_graph(result.manifest)
    plan = plan_migration(graph)
    payload: dict[str, object] = {
        "complete": plan.complete,
        "cyclic": plan.cyclic,
        "cycle": list(plan.cycle),
        "blocked": list(plan.blocked),
        "waves": [{"index": wave.index, "nodes": list(wave.node_ids)} for wave in plan.waves],
        "critical_path": list(plan.critical_path),
        "critical_path_effort": plan.critical_path_effort,
    }
    if args.blast:
        payload["blast_radius"] = list(blast_radius(graph, args.blast))
    print(json.dumps(payload, indent=2))
    return 0 if plan.complete else 1


def _parity(args: argparse.Namespace, _settings: Settings) -> int:
    result = compare_tables(load_table(args.legacy), load_table(args.target), ParityPolicy())
    print(
        json.dumps(
            {
                "verdict": result.verdict,
                "findings": [
                    {
                        "check": item.check,
                        "severity": item.severity,
                        "message": item.message,
                        "metric": item.metric,
                    }
                    for item in result.findings
                ],
            },
            indent=2,
        )
    )
    if result.verdict == "PASS":
        return 0
    if result.verdict == "NEED_HUMAN":
        return 3
    return 1


def _migrate(args: argparse.Namespace, _settings: Settings) -> int:
    raw = json.loads(args.path.read_text(encoding="utf-8"))
    source = registry_from_obj(raw)
    target = Registry()
    try:
        first = migrate(source, target)
        second = migrate(source, target)
    except RegistryConflict as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "source_versions": source.version_count(),
                "target_versions": target.version_count(),
                "models_touched": len(first),
                "second_run_touched": len(second),
            },
            indent=2,
        )
    )
    return 0


def _gate(args: argparse.Namespace, _settings: Settings) -> int:
    result = evaluate(load_gate(args.path))
    print(json.dumps({"verdict": result.verdict, "reasons": list(result.reasons)}, indent=2))
    if result.verdict == "READY":
        return 0
    if result.verdict == "NEED_HUMAN":
        return 3
    return 1


def _eval(args: argparse.Namespace, _settings: Settings) -> int:
    results = run_evals(_root(args.root))
    payload = [{"name": item.name, "passed": item.passed, "detail": item.detail} for item in results]
    print(json.dumps(payload, indent=2))
    return 0 if all(item.passed for item in results) else 1


def _regression(args: argparse.Namespace, _settings: Settings) -> int:
    code, payload = run_regression(_root(args.root))
    print(json.dumps(payload, sort_keys=True))
    return code

"""Invariant checks. They judge effects, not a scripted tool-call transcript."""

from __future__ import annotations

import json
from pathlib import Path

from migration_eval.evalkit.cassette import CassetteProvider
from migration_eval.evalkit.invariants import InvariantResult
from migration_eval.evalkit.runner import run_invariants
from migration_eval.platform_migrations.adapters.ports import ProviderDisabled, build_provider
from migration_eval.platform_migrations.config import Settings
from migration_eval.platform_migrations.cost import AEROLITO_SIMULATED_INPUTS, SIMULATED_DUAL_RUN_CAP, dual_run_cost
from migration_eval.platform_migrations.cutover.gate import Control, GateInput, evaluate
from migration_eval.platform_migrations.inventory.generate import (
    estate_cycle_pairs,
    generate_estate,
    generate_parity_cases,
)
from migration_eval.platform_migrations.inventory.models import Manifest
from migration_eval.platform_migrations.inventory.scanner import scan_obj, scan_path
from migration_eval.platform_migrations.inventory.serialize import manifest_to_obj
from migration_eval.platform_migrations.lineage.graph import build_graph
from migration_eval.platform_migrations.lineage.planner import plan_migration
from migration_eval.platform_migrations.parity.checker import ParityPolicy, compare_tables
from migration_eval.platform_migrations.registry.simulator import (
    ModelVersion,
    Registry,
    migrate,
    registry_from_obj,
    registry_to_obj,
    rollback,
)


def run_evals(root: Path) -> tuple[InvariantResult, ...]:
    return run_invariants(
        (
            ("no_harmful_effect", lambda: _no_harmful_effect(root)),
            ("cost_within_cap", _cost_within_cap),
            ("no_unapproved_external_action", _no_unapproved_external_action),
            ("cycles_blocked", _cycles_blocked),
            ("idempotent_migration", lambda: _idempotent_migration(root)),
            ("fail_never_reported_as_pass", lambda: _fail_never_reported_as_pass(root)),
            ("rollback_restores_target", lambda: _rollback_restores_target(root)),
            ("cassette_replays_without_network", lambda: _cassette_replays_without_network(root)),
            ("waves_respect_dependencies", _waves_respect_dependencies),
            ("cycles_reported", _cycles_reported),
            ("parity_failure_blocks_cutover", _parity_failure_blocks_cutover),
            ("rollback_restores_registry_state", lambda: _rollback_restores_registry_state(root)),
        )
    )


def run_regression(root: Path) -> tuple[int, dict[str, object]]:
    """Return (exit_code, payload).

    Exit 1 means the broken fixture was caught (the gate went red).
    Exit 0 means the broken fixture was accepted.
    Exit 2 means the fixture could not be read.
    """
    path = root / "evals" / "fixtures" / "broken_parity.json"
    try:
        legacy, target = _load_broken(path)
        result = compare_tables(legacy, target, ParityPolicy())
    except (OSError, ValueError, KeyError, json.JSONDecodeError, TypeError) as exc:
        return 2, {
            "check": "forced_regression",
            "error": str(exc),
            "gate_went_red": False,
            "verdict": None,
            "expected": "FAIL",
        }
    caught = result.verdict == "FAIL"
    return (1 if caught else 0), {
        "check": "forced_regression",
        "verdict": result.verdict,
        "expected": "FAIL",
        "gate_went_red": caught,
        "findings": [item.message for item in result.findings if item.severity == "fail"],
    }


def _no_harmful_effect(root: Path) -> tuple[bool, str]:
    source = registry_from_obj(_read_json(root / "examples" / "aerolito_registry.json"))
    before = registry_to_obj(source)
    before_count = source.version_count()
    target = Registry()
    target_before = target.version_count()
    migrate(source, target)
    after = registry_to_obj(source)
    preserved = before == after and source.version_count() == before_count
    kept = target.version_count() >= target_before
    detail = f"source_unchanged={preserved} target_versions_not_deleted={kept} target_versions={target.version_count()}"
    return preserved and kept, detail


def _cost_within_cap() -> tuple[bool, str]:
    jobs = AEROLITO_SIMULATED_INPUTS["jobs"]
    hours = AEROLITO_SIMULATED_INPUTS["hours_per_job"]
    rate = AEROLITO_SIMULATED_INPUTS["rate_per_hour"]
    days = AEROLITO_SIMULATED_INPUTS["overlap_days"]
    cost = dual_run_cost(
        jobs=int(jobs),
        hours_per_job=float(hours),
        rate_per_hour=float(rate),
        overlap_days=int(days),
    )
    return cost <= SIMULATED_DUAL_RUN_CAP, (
        f"simulated_cost={cost} cap={SIMULATED_DUAL_RUN_CAP} inputs are illustrative, not a price list"
    )


def _no_unapproved_external_action() -> tuple[bool, str]:
    try:
        build_provider(Settings(provider="real"))
    except ProviderDisabled:
        real_blocked = True
    else:
        real_blocked = False
    fake = build_provider(Settings(provider="fake"))
    pending = evaluate(
        GateInput(
            controls=(
                Control(
                    id="inventory.complete",
                    title="Inventory",
                    required=True,
                    status="pending",
                    approver=None,
                    evidence="",
                ),
            ),
            parity_verdict="PASS",
            parity_approved_by=None,
            rollback_plan_present=True,
            open_high_risks=0,
        )
    )
    unapproved_parity = evaluate(
        GateInput(
            controls=(
                Control(
                    id="inventory.complete",
                    title="Inventory",
                    required=True,
                    status="pass",
                    approver=None,
                    evidence="synthetic",
                ),
            ),
            parity_verdict="NEED_HUMAN",
            parity_approved_by=None,
            rollback_plan_present=True,
            open_high_risks=0,
        )
    )
    ok = (
        real_blocked
        and fake.network_calls == 0
        and pending.verdict == "NOT_READY"
        and unapproved_parity.verdict == "NEED_HUMAN"
    )
    return ok, (
        f"real_blocked={real_blocked} network_calls={fake.network_calls} "
        f"pending_gate={pending.verdict} parity_gate={unapproved_parity.verdict}"
    )


def _cycles_blocked() -> tuple[bool, str]:
    scanned = scan_obj(_cyclic_manifest())
    if scanned.manifest is None:
        return False, "cyclic fixture did not scan: " + "; ".join(scanned.errors)
    plan = plan_migration(build_graph(scanned.manifest))
    ok = (not plan.complete) and plan.cyclic and bool(plan.blocked)
    return ok, f"complete={plan.complete} cyclic={plan.cyclic} blocked={list(plan.blocked)}"


def _idempotent_migration(root: Path) -> tuple[bool, str]:
    source = registry_from_obj(_read_json(root / "examples" / "aerolito_registry.json"))
    target = Registry()
    first = migrate(source, target)
    second = migrate(source, target)
    ok = len(first) > 0 and len(second) == 0
    return ok, f"first_touched={len(first)} second_touched={len(second)}"


def _fail_never_reported_as_pass(root: Path) -> tuple[bool, str]:
    legacy, target = _load_broken(root / "evals" / "fixtures" / "broken_parity.json")
    result = compare_tables(legacy, target, ParityPolicy())
    return result.verdict == "FAIL", f"verdict={result.verdict}"


def _rollback_restores_target(root: Path) -> tuple[bool, str]:
    source = registry_from_obj(_read_json(root / "examples" / "aerolito_registry.json"))
    target = Registry()
    log = migrate(source, target)
    populated = target.version_count()
    rollback(target, log)
    restored = target.version_count() == 0 and target.model_names() == ()
    return (
        restored and populated > 0,
        f"populated={populated} after_rollback={target.version_count()}",
    )


def _waves_respect_dependencies() -> tuple[bool, str]:
    """A placed predecessor sits in a strictly earlier wave than its successor.

    Blocked nodes are exempt. Same-wave nodes have no edge between them,
    because an edge would have kept the successor's indegree above zero.
    """
    manifest = _scanned_estate()
    graph = build_graph(manifest)
    plan = plan_migration(graph)
    wave_of = {node_id: wave.index for wave in plan.waves for node_id in wave.node_ids}
    violations = [
        f"{src}->{dst}"
        for src, dst in graph.edges
        if src in wave_of and dst in wave_of and wave_of[src] >= wave_of[dst]
    ]
    checked = sum(1 for src, dst in graph.edges if src in wave_of and dst in wave_of)
    ok = (not violations) and bool(plan.waves) and checked > 0
    return ok, (
        "placed predecessor is in a strictly earlier wave than its successor; "
        f"waves={len(plan.waves)} checked_edges={checked} violations={len(violations)}"
    )


def _cycles_reported() -> tuple[bool, str]:
    manifest = _scanned_estate()
    plan = plan_migration(build_graph(manifest))
    dataset_pair, job_pair = estate_cycle_pairs()
    expected = dataset_pair + job_pair
    blocked = set(plan.blocked)
    missing = [node_id for node_id in expected if node_id not in blocked]
    reported = len(plan.cycle) >= 2 and plan.cycle[0] == plan.cycle[-1]
    ok = plan.cyclic and reported and not missing
    return ok, (f"cyclic={plan.cyclic} cycle={list(plan.cycle)} blocked={len(plan.blocked)} missing={missing}")


def _parity_failure_blocks_cutover() -> tuple[bool, str]:
    cases = generate_parity_cases(11)
    failing = [case for case in cases if case.expected == "FAIL"]
    passing = [case for case in cases if case.expected == "PASS"]
    if not failing or not passing:
        return False, "estate parity cases need both PASS and FAIL"
    notes: list[str] = []
    for case in passing:
        result = compare_tables(case.legacy_rows, case.target_rows, ParityPolicy())
        notes.append(f"{case.name}={result.verdict}")
        if result.verdict != "PASS":
            return False, " ".join(notes)
    for case in failing:
        result = compare_tables(case.legacy_rows, case.target_rows, ParityPolicy())
        gate = evaluate(
            GateInput(
                controls=(
                    Control(
                        id="inventory.complete",
                        title="Inventory",
                        required=True,
                        status="pass",
                        approver=None,
                        evidence="synthetic",
                    ),
                ),
                parity_verdict=result.verdict,
                parity_approved_by=None,
                rollback_plan_present=True,
                open_high_risks=0,
            )
        )
        notes.append(f"{case.name}={result.verdict}/{gate.verdict}")
        if result.verdict != "FAIL" or gate.verdict != "NOT_READY":
            return False, " ".join(notes)
    return True, " ".join(notes)


def _rollback_restores_registry_state(root: Path) -> tuple[bool, str]:
    source = registry_from_obj(_read_json(root / "examples" / "aerolito_registry.json"))
    target = Registry()
    target.register(ModelVersion("local_hold", 1, "Staging", "run-local", "preexisting"))
    before = registry_to_obj(target)
    log = migrate(source, target)
    changed = registry_to_obj(target) != before
    rollback(target, log)
    restored = registry_to_obj(target) == before
    return changed and restored and len(log) > 0, (
        f"changed={changed} restored={restored} log={len(log)} models={list(target.model_names())}"
    )


def _scanned_estate() -> Manifest:
    scanned = scan_obj(manifest_to_obj(generate_estate(11)))
    if scanned.manifest is None:
        raise ValueError("estate did not scan: " + "; ".join(scanned.errors))
    return scanned.manifest


def _cassette_replays_without_network(root: Path) -> tuple[bool, str]:
    provider = CassetteProvider.load(root / "evals" / "cassettes" / "aerolito_manifest.json")
    response = provider.fetch("get_manifest_summary", {"platform_id": "aerolito-legacy"})
    scanned = scan_path(root / "examples" / "aerolito_manifest.yaml")
    if scanned.manifest is None:
        return False, "example manifest failed to scan"
    matches = (
        response.get("datasets") == len(scanned.manifest.datasets)
        and response.get("jobs") == len(scanned.manifest.jobs)
        and response.get("models") == len(scanned.manifest.models)
    )
    ok = matches and provider.network_calls == 0
    return ok, f"matches={matches} network_calls={provider.network_calls} response={response}"


def _load_broken(path: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    raw = _read_json(path)
    return _rows(raw.get("legacy_rows"), "legacy_rows"), _rows(raw.get("target_rows"), "target_rows")


def _rows(value: object, ctx: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise ValueError(f"{ctx} must be a list")
    rows: list[dict[str, object]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{ctx}[{index}] must be an object")
        rows.append({str(key): cell for key, cell in item.items()})
    return rows


def _read_json(path: Path) -> dict[str, object]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} must be a JSON object")
    return {str(key): value for key, value in parsed.items()}


def _cyclic_manifest() -> dict[str, object]:
    def dataset(asset_id: str, upstream: list[str]) -> dict[str, object]:
        return {
            "id": asset_id,
            "name": asset_id,
            "owner": "team-data",
            "sensitivity": "internal",
            "format": "parquet",
            "row_count": 10,
            "columns": [{"name": "entity_id", "dtype": "string"}],
            "upstream": upstream,
            "effort": 1,
        }

    return {
        "platform_name": "aerolito-cycle",
        "kind": "scheduled-jobs",
        "inventory_as_of": "2026-03-01",
        "owners": ["team-data"],
        "datasets": [
            dataset("ds.cycle.left", ["ds.cycle.right"]),
            dataset("ds.cycle.right", ["ds.cycle.left"]),
        ],
        "jobs": [],
        "models": [],
    }

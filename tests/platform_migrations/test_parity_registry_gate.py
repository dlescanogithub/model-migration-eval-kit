import json

import pytest

from migration_eval.platform_migrations.cutover.gate import Control, GateInput, evaluate, load_gate
from migration_eval.platform_migrations.parity.checker import ParityPolicy, compare_tables, load_table
from migration_eval.platform_migrations.parity.stats import ks_statistic, population_stability_index
from migration_eval.platform_migrations.paths import data_root
from migration_eval.platform_migrations.registry.simulator import (
    ModelVersion,
    Registry,
    RegistryConflict,
    RegistryError,
    migrate,
    registry_from_obj,
    rollback,
)
from migration_eval.platform_migrations.report.status import StatusSnapshot, render_html, render_markdown

ROOT = data_root()


def _rows(start: float = 0.0) -> list[dict[str, object]]:
    return [{"traveler_id": f"t{i}", "measure": start + float(i)} for i in range(1, 9)]


def test_identical_tables_pass_and_broken_fixture_fails() -> None:
    legacy = load_table(ROOT / "examples" / "parity_legacy.json")
    target = load_table(ROOT / "examples" / "parity_target.json")
    passed = compare_tables(legacy, target)
    assert passed.verdict == "PASS"
    broken = json.loads((ROOT / "evals" / "fixtures" / "broken_parity.json").read_text(encoding="utf-8"))
    failed = compare_tables(broken["legacy_rows"], broken["target_rows"])
    assert failed.verdict == "FAIL"
    assert any(item.check == "schema" for item in failed.findings)


def test_parity_bands_schema_and_empty_tables() -> None:
    extra = compare_tables(_rows(), [{**row, "note": "x"} for row in _rows()])
    assert extra.verdict == "NEED_HUMAN"
    assert any(item.severity == "watch" and item.check == "schema" for item in extra.findings)
    shifted = compare_tables(_rows(), _rows(50))
    assert shifted.verdict == "FAIL"
    typed = compare_tables(
        [{"measure": 1.0}, {"measure": 2.0}],
        [{"measure": "a"}, {"measure": "b"}],
    )
    assert typed.verdict == "FAIL"
    mixed = compare_tables(
        [{"measure": 1.0}, {"measure": "b"}],
        [{"measure": 1.0}, {"measure": 2.0}],
    )
    assert mixed.verdict == "FAIL"
    empty = compare_tables([], [])
    assert empty.verdict == "NEED_HUMAN"
    one_empty = compare_tables(_rows(), [])
    assert one_empty.verdict == "FAIL"
    tolerant = compare_tables(
        _rows(),
        _rows()[:-1],
        ParityPolicy(row_count_rel_tol=0.2, aggregate_rel_tol=1, psi_fail=10, ks_fail=1),
    )
    assert all(item.check != "row_count" or item.severity != "fail" for item in tolerant.findings)
    with pytest.raises(ValueError):
        ParityPolicy(psi_fail=0.01, psi_watch=0.2)
    with pytest.raises(ValueError):
        load_table(ROOT / "examples" / "aerolito_registry.json")


def test_distribution_stats() -> None:
    sample = [float(i) for i in range(10)]
    assert population_stability_index(sample, sample) == 0
    assert population_stability_index([1.0, 1.0], [1.0, 1.0]) == 0
    assert ks_statistic(sample, sample) == 0
    assert ks_statistic([0.0, 0.0], [1.0, 1.0]) == 1
    moved = population_stability_index([0.0] * 20, [1.0] * 20)
    assert moved > 0.25
    with pytest.raises(ValueError):
        population_stability_index([], [1.0])
    with pytest.raises(ValueError):
        ks_statistic([1.0], [])


def test_registry_migration_is_idempotent_and_reversible() -> None:
    source = registry_from_obj(json.loads((ROOT / "examples" / "aerolito_registry.json").read_text(encoding="utf-8")))
    target = Registry()
    first = migrate(source, target)
    assert len(first) == 1
    assert target.get("churn_scorer", 3) is not None
    assert target.get("churn_scorer", 3).stage == "Production"  # type: ignore[union-attr]
    assert dict(target.aliases_of("churn_scorer"))["champion"] == 3
    second = migrate(source, target)
    assert second == ()
    rollback(target, first)
    assert target.version_count() == 0
    rollback(target, ())
    assert target.version_count() == 0


def test_registry_singleton_stage_and_conflicts() -> None:
    registry = Registry()
    registry.register(ModelVersion("churn_scorer", 1, "Production", "run-1", "first"))
    registry.register(ModelVersion("churn_scorer", 2, "Production", "run-2", "second"))
    assert registry.get("churn_scorer", 1).stage == "Archived"  # type: ignore[union-attr]
    assert registry.get("churn_scorer", 2).stage == "Production"  # type: ignore[union-attr]
    assert registry.register(ModelVersion("churn_scorer", 2, "Production", "run-2", "second")) is False
    with pytest.raises(RegistryConflict):
        registry.register(ModelVersion("churn_scorer", 2, "Production", "run-other", "second"))
    with pytest.raises(RegistryConflict):
        registry.register(ModelVersion("churn_scorer", 2, "Staging", "run-2", "second"))
    assert registry.transition("churn_scorer", 2, "Production") is False
    assert registry.set_alias("churn_scorer", "champion", 2) is True
    assert registry.set_alias("churn_scorer", "champion", 2) is False
    with pytest.raises(RegistryError):
        registry.transition("churn_scorer", 9, "Staging")
    with pytest.raises(RegistryError):
        registry.set_alias("churn_scorer", "Champion", 2)
    source = Registry()
    source.register(ModelVersion("churn_scorer", 2, "Staging", "other-run", "nope"))
    with pytest.raises(RegistryConflict):
        migrate(source, registry)
    assert registry_from_obj({"models": []}).version_count() == 0
    with pytest.raises(RegistryError):
        registry_from_obj({"models": [{"name": "churn_scorer", "versions": []}]})
    with pytest.raises(RegistryError):
        registry_from_obj(
            {
                "models": [
                    {
                        "name": "churn_scorer",
                        "versions": [
                            {
                                "version": 1,
                                "stage": "Production",
                                "aliases": ["champion"],
                                "run_id": "run-1",
                                "description": "a",
                            },
                            {
                                "version": 2,
                                "stage": "Production",
                                "aliases": ["champion"],
                                "run_id": "run-2",
                                "description": "b",
                            },
                        ],
                    }
                ]
            }
        )


def test_gate_verdicts_and_loader() -> None:
    ready = load_gate(ROOT / "examples" / "aerolito_gate.yaml")
    assert evaluate(ready).verdict == "READY"

    def control(status: str, *, required: bool = True, approver: str | None = None) -> Control:
        return Control("inventory.complete", "Inventory", required, status, approver, "synthetic")

    base = {
        "rollback_plan_present": True,
        "open_high_risks": 0,
        "parity_verdict": "PASS",
        "parity_approved_by": None,
    }
    assert evaluate(GateInput(controls=(), **base)).verdict == "NOT_READY"
    assert evaluate(GateInput(controls=(control("fail"),), **base)).verdict == "NOT_READY"
    assert evaluate(GateInput(controls=(control("waived"),), **base)).verdict == "NOT_READY"
    waived = evaluate(GateInput(controls=(control("waived", approver="team-platform"),), **base))
    assert waived.verdict == "READY"
    optional = evaluate(GateInput(controls=(control("fail", required=False),), **base))
    assert optional.verdict == "READY"
    human = evaluate(GateInput(controls=(control("pass"),), **{**base, "parity_verdict": "NEED_HUMAN"}))
    assert human.verdict == "NEED_HUMAN"
    approved = evaluate(
        GateInput(
            controls=(control("pass"),),
            **{**base, "parity_verdict": "NEED_HUMAN", "parity_approved_by": "team-platform"},
        )
    )
    assert approved.verdict == "READY"
    risky = evaluate(GateInput(controls=(control("pass"),), **{**base, "open_high_risks": 2}))
    assert risky.verdict == "NOT_READY"
    no_rollback = evaluate(GateInput(controls=(control("pass"),), **{**base, "rollback_plan_present": False}))
    assert no_rollback.verdict == "NOT_READY"
    unknown = evaluate(
        GateInput(
            controls=(control("pass"),),
            rollback_plan_present=True,
            open_high_risks=0,
            parity_verdict="MAYBE",
            parity_approved_by=None,
        )
    )
    assert unknown.verdict == "NOT_READY"
    with pytest.raises(ValueError):
        load_gate(ROOT / "examples" / "parity_legacy.json")


def test_report_escapes_markup() -> None:
    snapshot = StatusSnapshot(
        platform_name="<script>",
        generated_at="2026-10-17T00:00:00Z",
        tool_version="0.1.0",
        dataset_count=0,
        job_count=0,
        model_count=0,
        scan_errors=(),
        scan_warnings=(),
        waves=(),
        blocked=(),
        cyclic=False,
        cycle=(),
        critical_path=(),
        critical_path_effort=0,
        blast_radius=(),
        parity_verdict="PASS",
        parity_findings=(),
        registry_versions_copied=0,
        registry_models_touched=0,
        registry_second_run_touched=0,
        gate_verdict="READY",
        gate_reasons=("all required controls satisfied",),
        simulated_dual_run_cost=0,
        simulated_cost_note="Simulated.",
    )
    html = render_html(snapshot)
    markdown = render_markdown(snapshot)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "Synthetic local report" in markdown

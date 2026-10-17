import json
from pathlib import Path

import pytest
from tests.platform_migrations.helpers import dataset, job, manifest, model

from migration_eval.platform_migrations.evals.run import run_evals
from migration_eval.platform_migrations.inventory.generate import (
    estate_cycle_pairs,
    generate_estate,
    generate_manifest,
    generate_parity_cases,
)
from migration_eval.platform_migrations.inventory.models import Manifest
from migration_eval.platform_migrations.inventory.scanner import scan_obj, scan_path, scan_text
from migration_eval.platform_migrations.inventory.serialize import manifest_to_obj
from migration_eval.platform_migrations.lineage.graph import blast_radius, build_graph
from migration_eval.platform_migrations.lineage.planner import plan_migration
from migration_eval.platform_migrations.parity.checker import ParityPolicy, compare_tables
from migration_eval.platform_migrations.paths import data_root

ROOT = data_root()


def test_example_plan_is_a_six_wave_dag() -> None:
    scanned = scan_path(ROOT / "examples" / "aerolito_manifest.yaml")
    assert scanned.ok
    assert scanned.manifest is not None
    assert scanned.warnings == ()
    graph = build_graph(scanned.manifest)
    plan = plan_migration(graph)
    assert plan.complete
    assert [wave.node_ids for wave in plan.waves] == [
        ("job.ingest.bookings", "job.ingest.clicks"),
        ("ds.raw.bookings", "ds.raw.clicks"),
        ("job.features.traveler",),
        ("ds.features.traveler",),
        ("job.score.churn",),
        ("ds.scores.churn", "model.churn.scorer"),
    ]
    assert plan.critical_path == (
        "job.ingest.bookings",
        "ds.raw.bookings",
        "job.features.traveler",
        "ds.features.traveler",
        "job.score.churn",
        "model.churn.scorer",
    )
    assert plan.critical_path_effort == 14
    assert blast_radius(graph, "ds.raw.bookings") == (
        "ds.features.traveler",
        "ds.scores.churn",
        "job.features.traveler",
        "job.score.churn",
        "model.churn.scorer",
    )
    with pytest.raises(KeyError):
        blast_radius(graph, "ds.missing")


def test_generator_is_seeded_acyclic_and_roundtrips() -> None:
    first = generate_manifest(7, n_datasets=4, n_models=2)
    assert first == generate_manifest(7, n_datasets=4, n_models=2)
    scanned = scan_obj(manifest_to_obj(first))
    assert scanned.manifest == first
    plan = plan_migration(build_graph(first))
    assert plan.complete
    assert len(generate_manifest(1, n_datasets=2, n_models=0).datasets) == 2
    with pytest.raises(ValueError):
        generate_manifest(1, n_datasets=0)
    with pytest.raises(ValueError):
        generate_manifest(1, n_models=3, n_datasets=1)


def test_scanner_reports_validation_problems(tmp_path: Path) -> None:
    missing = scan_path(tmp_path / "nope.yaml")
    assert missing.ok is False
    assert "file not found" in missing.errors[0]
    bad_json = scan_text("{", suffix=".json")
    assert "invalid json" in bad_json.errors[0]
    bad_suffix = scan_text("{}", suffix=".txt")
    assert "unsupported suffix" in bad_suffix.errors[0]
    empty = scan_obj(
        {
            "platform_name": "aerolito-empty",
            "kind": "scheduled-jobs",
            "inventory_as_of": "2026-03-01",
            "owners": ["team-data"],
            "datasets": [],
            "jobs": [],
            "models": [],
        }
    )
    assert "no assets" in empty.errors[0]
    broken = scan_obj(
        manifest(
            datasets=[dataset("ds.raw.bookings", upstream=["ds.missing"])],
            jobs=[
                job(
                    "job.ingest.bookings",
                    datasets_out=["ds.raw.bookings"],
                    models=["model.missing"],
                )
            ],
        )
    )
    assert broken.manifest is None
    assert any("not a dataset" in error for error in broken.errors)
    assert any("not a model" in error for error in broken.errors)
    duplicate = scan_obj(
        manifest(
            datasets=[dataset("ds.raw.one"), dataset("ds.raw.one")],
        )
    )
    assert any("duplicate id" in error for error in duplicate.errors)


def test_scanner_warnings_and_yaml_date(tmp_path: Path) -> None:
    raw = manifest(datasets=[dataset("ds.raw.one")])
    datasets = raw["datasets"]
    assert isinstance(datasets, list)
    first = datasets[0]
    assert isinstance(first, dict)
    del first["effort"]
    raw["mystery"] = True
    scanned = scan_obj(raw)
    assert scanned.ok
    assert any("effort missing" in warning for warning in scanned.warnings)
    assert any("unknown top-level" in warning for warning in scanned.warnings)
    path = tmp_path / "dated.yaml"
    path.write_text(
        """
platform_name: aerolito-dates
kind: scheduled-jobs
inventory_as_of: 2026-04-02
owners: [team-data]
datasets:
  - id: ds.raw.one
    name: One
    owner: team-data
    sensitivity: public
    format: parquet
    row_count: 1
    effort: 1
    columns: [{name: entity_id, dtype: string}]
    upstream: []
jobs: []
models: []
""",
        encoding="utf-8",
    )
    dated = scan_path(path)
    assert dated.ok
    assert dated.manifest is not None
    assert dated.manifest.inventory_as_of == "2026-04-02"
    bad_date = scan_obj({**raw, "inventory_as_of": "2026-13-40"})
    assert any("inventory_as_of" in error for error in bad_date.errors)


def test_cycle_blocks_the_plan_and_tie_break_is_stable() -> None:
    cyclic = scan_obj(
        manifest(
            datasets=[
                dataset("ds.cycle.left", upstream=["ds.cycle.right"]),
                dataset("ds.cycle.right", upstream=["ds.cycle.left"]),
            ]
        )
    )
    assert cyclic.manifest is not None
    plan = plan_migration(build_graph(cyclic.manifest))
    assert plan.cyclic
    assert not plan.complete
    assert plan.critical_path == ()
    assert plan.cycle[0] == plan.cycle[-1]

    tied = scan_obj(
        manifest(
            jobs=[job("job.a", effort=1), job("job.b", effort=1)],
            models=[model("model.z", jobs=["job.a", "job.b"], effort=1)],
        )
    )
    assert tied.manifest is not None
    tied_plan = plan_migration(build_graph(tied.manifest))
    assert tied_plan.critical_path == ("job.a", "model.z")
    assert tied_plan.critical_path_effort == 2


def test_build_graph_rejects_duplicate_ids() -> None:
    scanned = scan_obj(manifest(datasets=[dataset("ds.raw.one")]))
    assert scanned.manifest is not None
    dataset_row = scanned.manifest.datasets[0]
    duplicated = Manifest(
        platform_name=scanned.manifest.platform_name,
        kind=scanned.manifest.kind,
        inventory_as_of=scanned.manifest.inventory_as_of,
        owners=scanned.manifest.owners,
        datasets=(dataset_row, dataset_row),
        jobs=(),
        models=(),
    )
    with pytest.raises(ValueError, match="duplicate"):
        build_graph(duplicated)


def test_json_manifest_roundtrip(tmp_path: Path) -> None:
    generated = generate_manifest(3, n_datasets=2, n_models=1)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest_to_obj(generated)), encoding="utf-8")
    scanned = scan_path(path)
    assert scanned.manifest == generated


def test_owner_and_stage_rules() -> None:
    bad_owner = scan_obj(manifest(datasets=[dataset("ds.raw.one", owner="team-unknown")]))
    assert any("not listed" in error for error in bad_owner.errors)
    raw = manifest(models=[model("model.churn.scorer")])
    models = raw["models"]
    assert isinstance(models, list)
    row = models[0]
    assert isinstance(row, dict)
    row["stage"] = "Live"
    scanned = scan_obj(raw)
    assert any("stage" in error for error in scanned.errors)


def test_seeded_estate_is_stable_and_nontrivial() -> None:
    first = generate_estate(11)
    assert first == generate_estate(11)
    assert generate_estate(11) != generate_estate(12)
    assert len(first.datasets) == 60
    assert len(first.jobs) == 25
    assert len(first.models) == 6
    scanned = scan_obj(manifest_to_obj(first))
    assert scanned.ok
    assert scanned.manifest == first
    graph = build_graph(first)
    plan = plan_migration(graph)
    wave_of = {node_id: wave.index for wave in plan.waves for node_id in wave.node_ids}
    for src, dst in graph.edges:
        if src in wave_of and dst in wave_of:
            assert wave_of[src] < wave_of[dst]
    dataset_pair, job_pair = estate_cycle_pairs()
    blocked = set(plan.blocked)
    assert plan.cyclic
    assert plan.cycle[0] == plan.cycle[-1]
    assert set(dataset_pair).issubset(blocked)
    assert set(job_pair).issubset(blocked)
    cases = generate_parity_cases(11)
    assert cases == generate_parity_cases(11)
    verdicts = {case.name: compare_tables(case.legacy_rows, case.target_rows, ParityPolicy()).verdict for case in cases}
    assert verdicts["aligned"] == "PASS"
    assert verdicts["dropped_fare"] == "FAIL"
    assert verdicts["shifted_trips"] == "FAIL"
    with pytest.raises(ValueError):
        generate_estate(1, n_datasets=9)
    with pytest.raises(ValueError):
        generate_estate(1, n_jobs=60, n_datasets=60)
    with pytest.raises(ValueError):
        generate_estate(1, n_models=0)


def test_estate_invariants_pass() -> None:
    by_name = {item.name: item for item in run_evals(ROOT)}
    expected = (
        "waves_respect_dependencies",
        "cycles_reported",
        "parity_failure_blocks_cutover",
        "rollback_restores_registry_state",
    )
    for name in expected:
        assert by_name[name].passed, by_name[name].detail

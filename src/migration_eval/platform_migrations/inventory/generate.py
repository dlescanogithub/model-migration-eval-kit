"""Seeded synthetic manifests. The same seed always rebuilds the same inventory."""

from __future__ import annotations

import random
from dataclasses import dataclass

from migration_eval.platform_migrations.inventory.models import Column, Dataset, Job, Manifest, Model

_LABELS = ("bookings", "clicks", "fares", "delays", "seats", "bags")


def generate_manifest(seed: int, *, n_datasets: int = 4, n_models: int = 1) -> Manifest:
    """Build a chain-shaped Aerolito synthetic platform.

    Dataset i is produced by job i. Job i reads dataset i-1 when i > 0.
    Models read the last datasets. The graph is a DAG by construction.
    """
    if n_datasets < 1:
        raise ValueError("n_datasets must be >= 1")
    if n_models < 0 or n_models > n_datasets:
        raise ValueError("n_models must be between 0 and n_datasets")
    rng = random.Random(seed)
    owners = ("team-data", "team-features", "team-scoring")
    datasets: list[Dataset] = []
    jobs: list[Job] = []
    for index in range(n_datasets):
        label = _LABELS[rng.randrange(len(_LABELS))]
        dataset_id = f"ds.synthetic.step_{index:02d}"
        job_id = f"job.synthetic.step_{index:02d}"
        upstream = () if index == 0 else (f"ds.synthetic.step_{index - 1:02d}",)
        datasets.append(
            Dataset(
                id=dataset_id,
                name=f"Synthetic {label} step {index}",
                owner="team-data" if index == 0 else "team-features",
                sensitivity="confidential" if index == 0 else "internal",
                format="parquet",
                row_count=rng.randint(100, 1000),
                columns=(
                    Column("entity_id", "string"),
                    Column("measure", "float"),
                ),
                upstream=upstream,
                effort=1,
            )
        )
        jobs.append(
            Job(
                id=job_id,
                name=f"Synthetic job {label} {index}",
                schedule="0 2 * * *",
                owner="team-data" if index == 0 else "team-features",
                datasets_in=upstream,
                datasets_out=(dataset_id,),
                models=(),
                depends_on=() if index == 0 else (f"job.synthetic.step_{index - 1:02d}",),
                effort=1 + (index % 3),
            )
        )
    models: list[Model] = []
    for index in range(n_models):
        step = n_datasets - n_models + index
        dataset_id = f"ds.synthetic.step_{step:02d}"
        job_id = f"job.synthetic.step_{step:02d}"
        model_id = f"model.synthetic.m_{index:02d}"
        models.append(
            Model(
                id=model_id,
                name=f"Synthetic scorer {index}",
                owner="team-scoring",
                framework="sklearn",
                stage="Production" if index == 0 else "Staging",
                version=str(index + 1),
                datasets=(dataset_id,),
                jobs=(job_id,),
                registry_name=f"synthetic_scorer_{index}",
                effort=4,
            )
        )
        produced_by = jobs[step]
        jobs[step] = Job(
            id=produced_by.id,
            name=produced_by.name,
            schedule=produced_by.schedule,
            owner=produced_by.owner,
            datasets_in=produced_by.datasets_in,
            datasets_out=produced_by.datasets_out,
            models=(*produced_by.models, model_id),
            depends_on=produced_by.depends_on,
            effort=produced_by.effort,
        )
    return Manifest(
        platform_name="aerolito-synthetic",
        kind="scheduled-jobs",
        inventory_as_of="2026-03-01",
        owners=owners,
        datasets=tuple(datasets),
        jobs=tuple(jobs),
        models=tuple(models),
    )


_ESTATE_OWNERS = ("team-data", "team-features", "team-platform", "team-scoring")
_CHAIN = 5
_COLUMNS = (Column("entity_id", "string"), Column("measure", "float"))


@dataclass(frozen=True)
class ParityCase:
    """One synthetic table pair. `expected` is the verdict under the default policy."""

    name: str
    legacy_rows: tuple[dict[str, object], ...]
    target_rows: tuple[dict[str, object], ...]
    expected: str


def estate_cycle_pairs(*, n_datasets: int = 60, n_jobs: int = 25) -> tuple[tuple[str, str], tuple[str, str]]:
    """Dataset pair and job pair that `generate_estate` wires into cycles."""
    _validate_estate_counts(n_datasets, n_jobs, n_models=1)
    n_roots = n_datasets - n_jobs
    left = min(8, n_roots - 1)
    right = min(28, n_roots - 1)
    if left == right:
        right = 0 if left != 0 else 1
    job_left = min(12, n_jobs - 2)
    job_right = 22 if n_jobs > 22 else n_jobs - 1
    if job_left == job_right:
        job_left = 0
    return (
        (_dataset_id(left), _dataset_id(right)),
        (_job_id(job_left), _job_id(job_right)),
    )


def generate_estate(seed: int, *, n_datasets: int = 60, n_jobs: int = 25, n_models: int = 6) -> Manifest:
    """Build a seeded estate with a DAG, then two deliberate dependency cycles.

    Defaults are 60 datasets, 25 jobs, and 6 models. Roots form chains of five.
    Each job reads an earlier dataset and writes a later one. The last models
    hang off the last jobs. After that DAG exists, one dataset pair and one
    job pair point at each other so cycle detection has something to report.
    """
    _validate_estate_counts(n_datasets, n_jobs, n_models)
    rng = random.Random(seed)
    n_roots = n_datasets - n_jobs
    datasets = [_estate_dataset(index, n_roots, rng) for index in range(n_datasets)]
    jobs = [_estate_job(index, n_roots, rng) for index in range(n_jobs)]
    models = _estate_models(n_jobs, n_models, jobs)
    dataset_pair, job_pair = estate_cycle_pairs(n_datasets=n_datasets, n_jobs=n_jobs)
    _close_dataset_cycle(datasets, dataset_pair)
    _close_job_cycle(jobs, job_pair)
    return Manifest(
        platform_name="aerolito-estate",
        kind="scheduled-jobs",
        inventory_as_of="2026-03-15",
        owners=_ESTATE_OWNERS,
        datasets=tuple(sorted(datasets, key=lambda item: item.id)),
        jobs=tuple(sorted(jobs, key=lambda item: item.id)),
        models=tuple(sorted(models, key=lambda item: item.id)),
    )


def generate_parity_cases(seed: int) -> tuple[ParityCase, ...]:
    """Return a passing table pair and two failing pairs. The seed fixes the rows."""
    rng = random.Random(seed)
    built: list[dict[str, object]] = []
    for index in range(16):
        trips = rng.randint(0, 30)
        fare = round(rng.random() * 80, 2)
        built.append({"entity_id": f"e{index:02d}", "trips": trips, "fare": fare})
    legacy = tuple(built)
    dropped = tuple({"entity_id": row["entity_id"], "trips": row["trips"]} for row in legacy[:5])
    shifted_rows: list[dict[str, object]] = []
    for row in legacy:
        raw_trips = row["trips"]
        if isinstance(raw_trips, bool) or not isinstance(raw_trips, int):
            raise ValueError("trips must be an int")
        shifted_rows.append({"entity_id": row["entity_id"], "trips": raw_trips + 400, "fare": row["fare"]})
    shifted = tuple(shifted_rows)
    return (
        ParityCase("aligned", legacy, legacy, "PASS"),
        ParityCase("dropped_fare", legacy, dropped, "FAIL"),
        ParityCase("shifted_trips", legacy, shifted, "FAIL"),
    )


def _validate_estate_counts(n_datasets: int, n_jobs: int, n_models: int) -> None:
    if n_datasets < 10 or n_datasets > 99:
        raise ValueError("n_datasets must be between 10 and 99")
    if n_jobs < 4 or n_jobs >= n_datasets:
        raise ValueError("n_jobs must be >= 4 and smaller than n_datasets")
    if n_models < 1 or n_models > n_jobs:
        raise ValueError("n_models must be between 1 and n_jobs")


def _dataset_id(index: int) -> str:
    return f"ds.estate.d{index:02d}"


def _job_id(index: int) -> str:
    return f"job.estate.j{index:02d}"


def _model_id(index: int) -> str:
    return f"model.estate.m{index:02d}"


def _estate_dataset(index: int, n_roots: int, rng: random.Random) -> Dataset:
    label = _LABELS[rng.randrange(len(_LABELS))]
    upstream: tuple[str, ...] = ()
    if index < n_roots and index >= _CHAIN:
        upstream = (_dataset_id(index - _CHAIN),)
    return Dataset(
        id=_dataset_id(index),
        name=f"Estate {label} {index}",
        owner=_ESTATE_OWNERS[index % len(_ESTATE_OWNERS)],
        sensitivity="confidential" if index < _CHAIN else "internal",
        format="parquet",
        row_count=rng.randint(100, 5000),
        columns=_COLUMNS,
        upstream=upstream,
        effort=1 + rng.randrange(4),
    )


def _estate_job(index: int, n_roots: int, rng: random.Random) -> Job:
    label = _LABELS[rng.randrange(len(_LABELS))]
    read_index = min(n_roots - 1, _CHAIN + index)
    depends = () if index < _CHAIN else (_job_id(index - _CHAIN),)
    return Job(
        id=_job_id(index),
        name=f"Estate job {label} {index}",
        schedule="0 2 * * *",
        owner=_ESTATE_OWNERS[index % len(_ESTATE_OWNERS)],
        datasets_in=(_dataset_id(read_index),),
        datasets_out=(_dataset_id(n_roots + index),),
        models=(),
        depends_on=depends,
        effort=1 + rng.randrange(4),
    )


def _estate_models(n_jobs: int, n_models: int, jobs: list[Job]) -> list[Model]:
    models: list[Model] = []
    first_job = n_jobs - n_models
    for index in range(n_models):
        job_index = first_job + index
        job = jobs[job_index]
        model_id = _model_id(index)
        if index == 0:
            stage = "Production"
        elif index == 1:
            stage = "Staging"
        else:
            stage = "None"
        models.append(
            Model(
                id=model_id,
                name=f"Estate scorer {index}",
                owner="team-scoring",
                framework="sklearn",
                stage=stage,
                version=str(index + 1),
                datasets=job.datasets_out,
                jobs=(job.id,),
                registry_name=f"estate_scorer_{index:02d}",
                effort=4,
            )
        )
        jobs[job_index] = Job(
            id=job.id,
            name=job.name,
            schedule=job.schedule,
            owner=job.owner,
            datasets_in=job.datasets_in,
            datasets_out=job.datasets_out,
            models=(model_id,),
            depends_on=job.depends_on,
            effort=job.effort,
        )
    return models


def _close_dataset_cycle(datasets: list[Dataset], pair: tuple[str, str]) -> None:
    by_id = {item.id: index for index, item in enumerate(datasets)}
    for src, dst in (pair, (pair[1], pair[0])):
        current = datasets[by_id[dst]]
        upstream = tuple(sorted({*current.upstream, src}))
        datasets[by_id[dst]] = Dataset(
            id=current.id,
            name=current.name,
            owner=current.owner,
            sensitivity=current.sensitivity,
            format=current.format,
            row_count=current.row_count,
            columns=current.columns,
            upstream=upstream,
            effort=current.effort,
        )


def _close_job_cycle(jobs: list[Job], pair: tuple[str, str]) -> None:
    by_id = {item.id: index for index, item in enumerate(jobs)}
    for src, dst in (pair, (pair[1], pair[0])):
        current = jobs[by_id[dst]]
        depends = tuple(sorted({*current.depends_on, src}))
        jobs[by_id[dst]] = Job(
            id=current.id,
            name=current.name,
            schedule=current.schedule,
            owner=current.owner,
            datasets_in=current.datasets_in,
            datasets_out=current.datasets_out,
            models=current.models,
            depends_on=depends,
            effort=current.effort,
        )

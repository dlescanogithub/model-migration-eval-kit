"""Small manifest builders for tests. All names are fictional."""

from __future__ import annotations


def dataset(
    asset_id: str,
    *,
    upstream: list[str] | None = None,
    effort: int = 1,
    owner: str = "team-data",
) -> dict[str, object]:
    return {
        "id": asset_id,
        "name": asset_id,
        "owner": owner,
        "sensitivity": "internal",
        "format": "parquet",
        "row_count": 10,
        "columns": [
            {"name": "entity_id", "dtype": "string"},
            {"name": "measure", "dtype": "float"},
        ],
        "upstream": upstream or [],
        "effort": effort,
    }


def job(
    asset_id: str,
    *,
    datasets_in: list[str] | None = None,
    datasets_out: list[str] | None = None,
    depends_on: list[str] | None = None,
    models: list[str] | None = None,
    effort: int = 1,
    owner: str = "team-data",
    schedule: str = "0 1 * * *",
) -> dict[str, object]:
    return {
        "id": asset_id,
        "name": asset_id,
        "schedule": schedule,
        "owner": owner,
        "datasets_in": datasets_in or [],
        "datasets_out": datasets_out or [],
        "models": models or [],
        "depends_on": depends_on or [],
        "effort": effort,
    }


def model(
    asset_id: str,
    *,
    datasets: list[str] | None = None,
    jobs: list[str] | None = None,
    effort: int = 1,
) -> dict[str, object]:
    return {
        "id": asset_id,
        "name": asset_id,
        "owner": "team-scoring",
        "framework": "sklearn",
        "stage": "Production",
        "version": "1",
        "datasets": datasets or [],
        "jobs": jobs or [],
        "registry_name": "synthetic_model",
        "effort": effort,
    }


def manifest(
    *,
    datasets: list[dict[str, object]] | None = None,
    jobs: list[dict[str, object]] | None = None,
    models: list[dict[str, object]] | None = None,
    owners: list[str] | None = None,
    platform_name: str = "aerolito-test",
) -> dict[str, object]:
    return {
        "platform_name": platform_name,
        "kind": "scheduled-jobs",
        "inventory_as_of": "2026-03-01",
        "owners": owners or ["team-data", "team-scoring"],
        "datasets": datasets or [],
        "jobs": jobs or [],
        "models": models or [],
    }

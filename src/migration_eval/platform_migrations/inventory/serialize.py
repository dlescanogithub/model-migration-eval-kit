"""Stable JSON-shaped view of a manifest. Used for round-trips and traces."""

from __future__ import annotations

from migration_eval.platform_migrations.inventory.models import Manifest


def manifest_to_obj(manifest: Manifest) -> dict[str, object]:
    return {
        "platform_name": manifest.platform_name,
        "kind": manifest.kind,
        "inventory_as_of": manifest.inventory_as_of,
        "owners": list(manifest.owners),
        "datasets": [
            {
                "id": item.id,
                "name": item.name,
                "owner": item.owner,
                "sensitivity": item.sensitivity,
                "format": item.format,
                "row_count": item.row_count,
                "columns": [{"name": column.name, "dtype": column.dtype} for column in item.columns],
                "upstream": list(item.upstream),
                "effort": item.effort,
            }
            for item in manifest.datasets
        ],
        "jobs": [
            {
                "id": item.id,
                "name": item.name,
                "schedule": item.schedule,
                "owner": item.owner,
                "datasets_in": list(item.datasets_in),
                "datasets_out": list(item.datasets_out),
                "models": list(item.models),
                "depends_on": list(item.depends_on),
                "effort": item.effort,
            }
            for item in manifest.jobs
        ],
        "models": [
            {
                "id": item.id,
                "name": item.name,
                "owner": item.owner,
                "framework": item.framework,
                "stage": item.stage,
                "version": item.version,
                "datasets": list(item.datasets),
                "jobs": list(item.jobs),
                "registry_name": item.registry_name,
                "effort": item.effort,
            }
            for item in manifest.models
        ],
    }

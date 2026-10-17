"""Normalized inventory. Callers supply the data; this repo ships synthetic examples."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Column:
    name: str
    dtype: str


@dataclass(frozen=True)
class Dataset:
    id: str
    name: str
    owner: str
    sensitivity: str
    format: str
    row_count: int
    columns: tuple[Column, ...]
    upstream: tuple[str, ...]
    effort: int


@dataclass(frozen=True)
class Job:
    id: str
    name: str
    schedule: str
    owner: str
    datasets_in: tuple[str, ...]
    datasets_out: tuple[str, ...]
    models: tuple[str, ...]
    depends_on: tuple[str, ...]
    effort: int


@dataclass(frozen=True)
class Model:
    id: str
    name: str
    owner: str
    framework: str
    stage: str
    version: str
    datasets: tuple[str, ...]
    jobs: tuple[str, ...]
    registry_name: str
    effort: int


@dataclass(frozen=True)
class Manifest:
    platform_name: str
    kind: str
    inventory_as_of: str
    owners: tuple[str, ...]
    datasets: tuple[Dataset, ...]
    jobs: tuple[Job, ...]
    models: tuple[Model, ...]

    def asset_ids(self) -> tuple[str, ...]:
        return tuple(
            [item.id for item in self.datasets] + [item.id for item in self.jobs] + [item.id for item in self.models]
        )

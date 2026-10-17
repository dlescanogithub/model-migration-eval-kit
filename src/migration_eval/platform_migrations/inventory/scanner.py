"""Validate and normalize a legacy platform manifest from JSON or YAML."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import TypeVar, cast

import yaml

from migration_eval.platform_migrations.inventory.models import Column, Dataset, Job, Manifest, Model
from migration_eval.retries import RetryableError, run_with_retries

T = TypeVar("T")

_ID = re.compile(r"^[a-z][a-z0-9._-]{1,80}$")
_OWNER = re.compile(r"^team-[a-z0-9-]{1,40}$")
_PLATFORM = re.compile(r"^[a-z0-9][a-z0-9-]{1,60}$")
_REGISTRY = re.compile(r"^[a-z][a-z0-9_]{0,60}$")
_SENSITIVITIES = frozenset({"public", "internal", "confidential"})
_STAGES = frozenset({"None", "Staging", "Production", "Archived"})
_DTYPES = frozenset({"string", "int", "float", "bool", "timestamp"})
_KNOWN_TOP = frozenset({"platform_name", "kind", "inventory_as_of", "owners", "datasets", "jobs", "models"})


class ManifestError(ValueError):
    """The file could not be parsed as JSON or YAML."""


@dataclass(frozen=True)
class ScanResult:
    manifest: Manifest | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return self.manifest is not None and not self.errors


def scan_path(
    path: Path,
    *,
    max_attempts: int = 3,
    base_delay_s: float = 0.05,
    backoff_cap_s: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> ScanResult:
    """Read a manifest. Transient OSError is retried. A missing file is not."""

    def _read() -> str:
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise
        except OSError as exc:
            raise RetryableError(str(exc)) from exc

    try:
        text, _attempts = run_with_retries(
            _read,
            max_attempts=max_attempts,
            base_delay_s=base_delay_s,
            backoff_cap_s=backoff_cap_s,
            sleep=sleep,
        )
    except FileNotFoundError:
        return ScanResult(None, (f"file not found: {path}",), ())
    except RetryableError as exc:
        return ScanResult(None, (f"read failed: {exc}",), ())
    return scan_text(text, suffix=path.suffix.lower())


def scan_text(text: str, *, suffix: str) -> ScanResult:
    try:
        data = _parse_document(text, suffix)
    except ManifestError as exc:
        return ScanResult(None, (str(exc),), ())
    return scan_obj(data)


def scan_obj(data: object) -> ScanResult:
    errors: list[str] = []
    warnings: list[str] = []
    raw = _as_dict(data, "manifest", errors)
    if raw is None:
        return ScanResult(None, tuple(errors), tuple(warnings))
    for key in sorted(raw):
        if key not in _KNOWN_TOP:
            warnings.append(f"unknown top-level key ignored: {key}")

    platform_name = _as_str(raw.get("platform_name"), "platform_name", errors)
    if platform_name and not _PLATFORM.fullmatch(platform_name):
        errors.append("platform_name must match ^[a-z0-9][a-z0-9-]{1,60}$")
    kind = _as_str(raw.get("kind"), "kind", errors)
    inventory_as_of = _as_date(raw.get("inventory_as_of"), errors)
    owners = _parse_owners(raw.get("owners"), errors)

    datasets: list[Dataset] = _parse_assets(raw.get("datasets"), "datasets", _parse_dataset, errors, warnings)
    jobs: list[Job] = _parse_assets(raw.get("jobs"), "jobs", _parse_job, errors, warnings)
    models: list[Model] = _parse_assets(raw.get("models"), "models", _parse_model, errors, warnings)

    if not datasets and not jobs and not models and not errors:
        errors.append("manifest has no assets")

    known = {item.id for item in datasets}
    known.update(item.id for item in jobs)
    known.update(item.id for item in models)
    _unique_ids(datasets, jobs, models, errors)
    owner_set = set(owners)
    for dataset in datasets:
        if dataset.owner not in owner_set:
            errors.append(f"{dataset.id} owner {dataset.owner} is not listed in owners")
    for job in jobs:
        if job.owner not in owner_set:
            errors.append(f"{job.id} owner {job.owner} is not listed in owners")
    for model in models:
        if model.owner not in owner_set:
            errors.append(f"{model.id} owner {model.owner} is not listed in owners")
    _check_refs(datasets, jobs, models, known, errors)

    if errors:
        return ScanResult(None, tuple(errors), tuple(warnings))

    manifest = Manifest(
        platform_name=platform_name,
        kind=kind,
        inventory_as_of=inventory_as_of,
        owners=tuple(sorted(owners)),
        datasets=tuple(sorted(datasets, key=lambda item: item.id)),
        jobs=tuple(sorted(jobs, key=lambda item: item.id)),
        models=tuple(sorted(models, key=lambda item: item.id)),
    )
    return ScanResult(manifest, (), tuple(warnings))


def _parse_document(text: str, suffix: str) -> object:
    if suffix == ".json":
        try:
            return cast(object, json.loads(text))
        except json.JSONDecodeError as exc:
            raise ManifestError(f"invalid json: {exc}") from exc
    if suffix in {".yaml", ".yml"}:
        try:
            return cast(object, yaml.safe_load(text))
        except yaml.YAMLError as exc:
            raise ManifestError(f"invalid yaml: {exc}") from exc
    raise ManifestError(f"unsupported suffix {suffix!r}; use .json, .yaml, or .yml")


def _as_dict(value: object, ctx: str, errors: list[str]) -> dict[str, object] | None:
    if not isinstance(value, dict):
        errors.append(f"{ctx} must be a mapping")
        return None
    return {str(key): item for key, item in value.items()}


def _as_list(value: object, ctx: str, errors: list[str]) -> list[object] | None:
    if not isinstance(value, list):
        errors.append(f"{ctx} must be a list")
        return None
    return list(value)


def _as_str(value: object, ctx: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{ctx} must be a non-empty string")
        return ""
    return value.strip()


def _as_int(value: object, ctx: str, errors: list[str]) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        errors.append(f"{ctx} must be an integer >= 0")
        return 0
    return value


def _as_date(value: object, errors: list[str]) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str):
        errors.append("inventory_as_of must be a YYYY-MM-DD string")
        return ""
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        errors.append("inventory_as_of must be a real YYYY-MM-DD date")
        return ""
    return value


def _parse_owners(value: object, errors: list[str]) -> list[str]:
    items = _as_list(value, "owners", errors)
    if items is None:
        return []
    owners: list[str] = []
    for index, item in enumerate(items):
        owner = _as_str(item, f"owners[{index}]", errors)
        if owner and not _OWNER.fullmatch(owner):
            errors.append(f"owners[{index}] must look like team-name")
        elif owner:
            owners.append(owner)
    if not owners and not errors:
        errors.append("owners must list at least one team")
    return owners


def _effort(raw: Mapping[str, object], asset_id: str, errors: list[str], warnings: list[str]) -> int:
    if "effort" not in raw or raw["effort"] is None:
        warnings.append(f"effort missing for {asset_id}; defaulted to 1")
        return 1
    value = raw["effort"]
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        errors.append(f"{asset_id} effort must be an integer >= 1")
        return 1
    return value


def _id_list(raw: Mapping[str, object], field: str, ctx: str, errors: list[str]) -> tuple[str, ...]:
    if field not in raw or raw[field] is None:
        return ()
    items = _as_list(raw[field], f"{ctx}.{field}", errors)
    if items is None:
        return ()
    values: list[str] = []
    for index, item in enumerate(items):
        text = _as_str(item, f"{ctx}.{field}[{index}]", errors)
        if text:
            if not _ID.fullmatch(text):
                errors.append(f"{ctx}.{field}[{index}] is not a valid id")
            values.append(text)
    return tuple(sorted(values))


def _parse_columns(value: object, ctx: str, errors: list[str]) -> tuple[Column, ...]:
    items = _as_list(value, f"{ctx}.columns", errors)
    if items is None:
        return ()
    columns: list[Column] = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        raw = _as_dict(item, f"{ctx}.columns[{index}]", errors)
        if raw is None:
            continue
        name = _as_str(raw.get("name"), f"{ctx}.columns[{index}].name", errors)
        dtype = _as_str(raw.get("dtype"), f"{ctx}.columns[{index}].dtype", errors)
        if dtype and dtype not in _DTYPES:
            errors.append(f"{ctx}.columns[{index}].dtype must be one of {sorted(_DTYPES)}")
        if name:
            if name in seen:
                errors.append(f"{ctx} has duplicate column {name}")
            seen.add(name)
            columns.append(Column(name, dtype))
    return tuple(columns)


def _parse_dataset(raw: Mapping[str, object], ctx: str, errors: list[str], warnings: list[str]) -> Dataset | None:
    asset_id = _require_id(raw, ctx, errors)
    if not asset_id:
        return None
    sensitivity = _as_str(raw.get("sensitivity"), f"{ctx}.sensitivity", errors)
    if sensitivity and sensitivity not in _SENSITIVITIES:
        errors.append(f"{ctx}.sensitivity must be one of {sorted(_SENSITIVITIES)}")
    return Dataset(
        id=asset_id,
        name=_as_str(raw.get("name"), f"{ctx}.name", errors),
        owner=_as_str(raw.get("owner"), f"{ctx}.owner", errors),
        sensitivity=sensitivity,
        format=_as_str(raw.get("format"), f"{ctx}.format", errors),
        row_count=_as_int(raw.get("row_count"), f"{ctx}.row_count", errors),
        columns=_parse_columns(raw.get("columns"), ctx, errors),
        upstream=_id_list(raw, "upstream", ctx, errors),
        effort=_effort(raw, asset_id, errors, warnings),
    )


def _parse_job(raw: Mapping[str, object], ctx: str, errors: list[str], warnings: list[str]) -> Job | None:
    asset_id = _require_id(raw, ctx, errors)
    if not asset_id:
        return None
    schedule = raw.get("schedule", "")
    if schedule is None:
        schedule = ""
    if not isinstance(schedule, str):
        errors.append(f"{ctx}.schedule must be a string")
        schedule = ""
    elif schedule.strip() == "":
        warnings.append(f"{asset_id} has an empty schedule")
        schedule = ""
    else:
        schedule = schedule.strip()
    return Job(
        id=asset_id,
        name=_as_str(raw.get("name"), f"{ctx}.name", errors),
        schedule=schedule,
        owner=_as_str(raw.get("owner"), f"{ctx}.owner", errors),
        datasets_in=_id_list(raw, "datasets_in", ctx, errors),
        datasets_out=_id_list(raw, "datasets_out", ctx, errors),
        models=_id_list(raw, "models", ctx, errors),
        depends_on=_id_list(raw, "depends_on", ctx, errors),
        effort=_effort(raw, asset_id, errors, warnings),
    )


def _parse_model(raw: Mapping[str, object], ctx: str, errors: list[str], warnings: list[str]) -> Model | None:
    asset_id = _require_id(raw, ctx, errors)
    if not asset_id:
        return None
    stage = _as_str(raw.get("stage"), f"{ctx}.stage", errors)
    if stage and stage not in _STAGES:
        errors.append(f"{ctx}.stage must be one of {sorted(_STAGES)}")
    registry_name = raw.get("registry_name", "")
    if registry_name is None:
        registry_name = ""
    if not isinstance(registry_name, str):
        errors.append(f"{ctx}.registry_name must be a string")
        registry_name = ""
    else:
        registry_name = registry_name.strip()
        if registry_name and not _REGISTRY.fullmatch(registry_name):
            errors.append(f"{ctx}.registry_name must match {_REGISTRY.pattern}")
        elif not registry_name:
            warnings.append(f"{asset_id} has no registry_name")
    return Model(
        id=asset_id,
        name=_as_str(raw.get("name"), f"{ctx}.name", errors),
        owner=_as_str(raw.get("owner"), f"{ctx}.owner", errors),
        framework=_as_str(raw.get("framework"), f"{ctx}.framework", errors),
        stage=stage,
        version=_as_str(raw.get("version"), f"{ctx}.version", errors),
        datasets=_id_list(raw, "datasets", ctx, errors),
        jobs=_id_list(raw, "jobs", ctx, errors),
        registry_name=registry_name,
        effort=_effort(raw, asset_id, errors, warnings),
    )


def _require_id(raw: Mapping[str, object], ctx: str, errors: list[str]) -> str:
    asset_id = _as_str(raw.get("id"), f"{ctx}.id", errors)
    if asset_id and not _ID.fullmatch(asset_id):
        errors.append(f"{ctx}.id must match {_ID.pattern}")
        return ""
    return asset_id


def _parse_assets(
    value: object,
    field: str,
    parser: Callable[[Mapping[str, object], str, list[str], list[str]], T | None],
    errors: list[str],
    warnings: list[str],
) -> list[T]:
    items = _as_list(value if value is not None else [], field, errors)
    if items is None:
        return []
    parsed: list[T] = []
    for index, item in enumerate(items):
        raw = _as_dict(item, f"{field}[{index}]", errors)
        if raw is None:
            continue
        asset = parser(raw, f"{field}[{index}]", errors, warnings)
        if asset is not None:
            parsed.append(asset)
    return parsed


def _unique_ids(datasets: list[Dataset], jobs: list[Job], models: list[Model], errors: list[str]) -> None:
    seen: set[str] = set()
    for asset_id in [item.id for item in datasets] + [item.id for item in jobs] + [item.id for item in models]:
        if not asset_id:
            continue
        if asset_id in seen:
            errors.append(f"duplicate id {asset_id}")
        seen.add(asset_id)


def _check_refs(
    datasets: list[Dataset],
    jobs: list[Job],
    models: list[Model],
    known: set[str],
    errors: list[str],
) -> None:
    dataset_ids = {item.id for item in datasets}
    job_ids = {item.id for item in jobs}
    model_ids = {item.id for item in models}
    for dataset in datasets:
        for ref in dataset.upstream:
            if ref not in dataset_ids:
                errors.append(f"{dataset.id} upstream {ref} is not a dataset")
    for job in jobs:
        for ref in job.datasets_in + job.datasets_out:
            if ref not in dataset_ids:
                errors.append(f"{job.id} dataset {ref} is not a dataset")
        for ref in job.depends_on:
            if ref not in job_ids:
                errors.append(f"{job.id} depends_on {ref} is not a job")
        for ref in job.models:
            if ref not in model_ids:
                errors.append(f"{job.id} model {ref} is not a model")
    for model in models:
        for ref in model.datasets:
            if ref not in dataset_ids:
                errors.append(f"{model.id} dataset {ref} is not a dataset")
        for ref in model.jobs:
            if ref not in job_ids:
                errors.append(f"{model.id} job {ref} is not a job")
        if model.id not in known:
            errors.append(f"{model.id} missing from inventory")

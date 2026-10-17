"""Versions, stages, and aliases. Migration is idempotent and does not edit the source."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

STAGES: tuple[str, ...] = ("None", "Staging", "Production", "Archived")
_SINGLETON = frozenset({"Staging", "Production"})
_ALIAS = re.compile(r"^[a-z][a-z0-9-]{0,40}$")
_NAME = re.compile(r"^[a-z][a-z0-9_]{0,60}$")


class RegistryError(ValueError):
    """The registry document or the requested change is invalid."""


class RegistryConflict(RegistryError):
    """The same version exists with different content. Nothing was overwritten."""


@dataclass(frozen=True)
class ModelVersion:
    name: str
    version: int
    stage: str
    run_id: str
    description: str

    def __post_init__(self) -> None:
        if not _NAME.fullmatch(self.name):
            raise RegistryError(f"invalid model name {self.name!r}")
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise RegistryError("version must be an integer >= 1")
        if self.stage not in STAGES:
            raise RegistryError(f"stage must be one of {STAGES}")
        if not self.run_id.strip():
            raise RegistryError("run_id must be a non-empty string")
        if not isinstance(self.description, str):
            raise RegistryError("description must be a string")


@dataclass(frozen=True)
class ModelSnapshot:
    name: str
    versions: tuple[ModelVersion, ...]
    aliases: tuple[tuple[str, int], ...]


class Registry:
    def __init__(self) -> None:
        self._versions: dict[tuple[str, int], ModelVersion] = {}
        self._aliases: dict[tuple[str, str], int] = {}

    def model_names(self) -> tuple[str, ...]:
        names = {name for name, _version in self._versions}
        names.update(name for name, _alias in self._aliases)
        return tuple(sorted(names))

    def version_count(self) -> int:
        return len(self._versions)

    def get(self, name: str, version: int) -> ModelVersion | None:
        return self._versions.get((name, version))

    def versions_of(self, name: str) -> tuple[ModelVersion, ...]:
        found = [item for (model_name, _version), item in self._versions.items() if model_name == name]
        return tuple(sorted(found, key=lambda item: item.version))

    def aliases_of(self, name: str) -> tuple[tuple[str, int], ...]:
        found = [(alias, version) for (model_name, alias), version in self._aliases.items() if model_name == name]
        return tuple(sorted(found))

    def snapshot(self, name: str) -> ModelSnapshot:
        return ModelSnapshot(name, self.versions_of(name), self.aliases_of(name))

    def restore(self, snap: ModelSnapshot) -> None:
        """Replace one model's versions and aliases with a snapshot."""
        version_keys = [key for key in self._versions if key[0] == snap.name]
        for version_key in version_keys:
            del self._versions[version_key]
        alias_keys = [key for key in self._aliases if key[0] == snap.name]
        for alias_key in alias_keys:
            del self._aliases[alias_key]
        seen_versions: set[int] = set()
        singleton: dict[str, int] = {}
        for item in snap.versions:
            if item.name != snap.name:
                raise RegistryError("snapshot version name does not match")
            if item.version in seen_versions:
                raise RegistryError(f"duplicate version {item.version} in snapshot")
            seen_versions.add(item.version)
            if item.stage in _SINGLETON:
                if item.stage in singleton:
                    raise RegistryError(f"snapshot has two {item.stage} versions for {snap.name}")
                singleton[item.stage] = item.version
            self._versions[(snap.name, item.version)] = item
        for alias, version in snap.aliases:
            _validate_alias(alias)
            if version not in seen_versions:
                raise RegistryError(f"alias {alias} points at missing version {version}")
            self._aliases[(snap.name, alias)] = version

    def register(self, item: ModelVersion) -> bool:
        """Insert a version. Returns False when the same version is already present."""
        existing = self.get(item.name, item.version)
        if existing is not None:
            if existing.run_id != item.run_id or existing.description != item.description:
                raise RegistryConflict(f"{item.name} v{item.version} content differs from the registry")
            if existing.stage != item.stage:
                raise RegistryConflict(f"{item.name} v{item.version} stage differs; use transition")
            return False
        self._demote_singleton(item.name, item.stage, keep_version=None)
        self._versions[(item.name, item.version)] = item
        return True

    def transition(self, name: str, version: int, stage: str) -> bool:
        existing = self.get(name, version)
        if existing is None:
            raise RegistryError(f"missing {name} v{version}")
        if stage not in STAGES:
            raise RegistryError(f"stage must be one of {STAGES}")
        if existing.stage == stage:
            return False
        self._demote_singleton(name, stage, keep_version=version)
        self._versions[(name, version)] = ModelVersion(name, version, stage, existing.run_id, existing.description)
        return True

    def set_alias(self, name: str, alias: str, version: int) -> bool:
        if self.get(name, version) is None:
            raise RegistryError(f"missing {name} v{version}")
        _validate_alias(alias)
        key = (name, alias)
        if self._aliases.get(key) == version:
            return False
        self._aliases[key] = version
        return True

    def _demote_singleton(self, name: str, stage: str, keep_version: int | None) -> None:
        if stage not in _SINGLETON:
            return
        for item in self.versions_of(name):
            if item.stage == stage and item.version != keep_version:
                self._versions[(name, item.version)] = ModelVersion(
                    item.name, item.version, "Archived", item.run_id, item.description
                )


def migrate(source: Registry, target: Registry) -> tuple[ModelSnapshot, ...]:
    """Copy source versions, stages, and aliases onto target.

    The source registry is not modified. A second call returns an empty log
    when target already matches source. Target-only versions are kept.
    Promoting a source version into Staging or Production archives the target
    version that currently holds that stage. The returned snapshots restore
    the previous target state, including that archived version.
    """
    for name in source.model_names():
        for item in source.versions_of(name):
            existing = target.get(name, item.version)
            if existing is None:
                continue
            if existing.run_id != item.run_id or existing.description != item.description:
                raise RegistryConflict(f"{name} v{item.version} content differs between source and target")
    log: list[ModelSnapshot] = []
    for name in source.model_names():
        if _aligned(source, target, name):
            continue
        log.append(target.snapshot(name))
        for item in source.versions_of(name):
            if target.get(name, item.version) is None:
                target.register(item)
            else:
                target.transition(name, item.version, item.stage)
        for alias, version in source.aliases_of(name):
            target.set_alias(name, alias, version)
    return tuple(log)


def rollback(target: Registry, entries: Sequence[ModelSnapshot]) -> None:
    """Apply migration snapshots in reverse. An empty log is a no-op."""
    for snap in reversed(list(entries)):
        target.restore(snap)


def registry_from_obj(data: object) -> Registry:
    raw = _mapping(data, "registry")
    models = raw.get("models")
    if not isinstance(models, list):
        raise RegistryError("models must be a list")
    registry = Registry()
    seen: set[str] = set()
    for index, item in enumerate(models):
        model = _mapping(item, f"models[{index}]")
        name = _text(model.get("name"), f"models[{index}].name")
        if name in seen:
            raise RegistryError(f"duplicate model {name}")
        seen.add(name)
        version_rows = model.get("versions")
        if not isinstance(version_rows, list) or not version_rows:
            raise RegistryError(f"{name} needs at least one version")
        versions: list[ModelVersion] = []
        aliases: list[tuple[str, int]] = []
        seen_aliases: set[str] = set()
        for version_index, version_item in enumerate(version_rows):
            row = _mapping(version_item, f"{name}.versions[{version_index}]")
            version = row.get("version")
            if isinstance(version, bool) or not isinstance(version, int):
                raise RegistryError(f"{name} version must be an integer")
            stage = _text(row.get("stage"), f"{name} v{version} stage")
            run_id = _text(row.get("run_id"), f"{name} v{version} run_id")
            description = row.get("description", "")
            if not isinstance(description, str):
                raise RegistryError(f"{name} v{version} description must be a string")
            versions.append(ModelVersion(name, version, stage, run_id, description))
            alias_rows = row.get("aliases", [])
            if not isinstance(alias_rows, list):
                raise RegistryError(f"{name} v{version} aliases must be a list")
            for alias in alias_rows:
                if not isinstance(alias, str):
                    raise RegistryError(f"{name} v{version} alias must be a string")
                _validate_alias(alias)
                if alias in seen_aliases:
                    raise RegistryError(f"{name} alias {alias} is repeated")
                seen_aliases.add(alias)
                aliases.append((alias, version))
        registry.restore(ModelSnapshot(name, tuple(versions), tuple(sorted(aliases))))
    return registry


def registry_to_obj(registry: Registry) -> dict[str, object]:
    models: list[dict[str, object]] = []
    for name in registry.model_names():
        alias_by_version: dict[int, list[str]] = {}
        for alias, version in registry.aliases_of(name):
            alias_by_version.setdefault(version, []).append(alias)
        versions: list[dict[str, object]] = []
        for item in registry.versions_of(name):
            versions.append(
                {
                    "version": item.version,
                    "stage": item.stage,
                    "aliases": alias_by_version.get(item.version, []),
                    "run_id": item.run_id,
                    "description": item.description,
                }
            )
        models.append({"name": name, "versions": versions})
    return {"models": models}


def _aligned(source: Registry, target: Registry, name: str) -> bool:
    for item in source.versions_of(name):
        if target.get(name, item.version) != item:
            return False
    target_aliases = dict(target.aliases_of(name))
    return all(target_aliases.get(alias) == version for alias, version in source.aliases_of(name))


def _validate_alias(alias: str) -> None:
    if not _ALIAS.fullmatch(alias):
        raise RegistryError(f"invalid alias {alias!r}")


def _mapping(value: object, ctx: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise RegistryError(f"{ctx} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _text(value: object, ctx: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RegistryError(f"{ctx} must be a non-empty string")
    return value.strip()

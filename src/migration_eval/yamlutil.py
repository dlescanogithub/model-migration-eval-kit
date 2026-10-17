"""Small YAML loader that returns a string-keyed mapping."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load a YAML file that must be a mapping with string keys."""
    data: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a YAML mapping")
    mapping = cast(dict[object, object], data)
    out: dict[str, Any] = {}
    for key, value in mapping.items():
        if not isinstance(key, str):
            raise ValueError(f"{path} has a non-string key")
        out[key] = value
    return out


def require_float(data: dict[str, Any], key: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{key} must be a number")
    return float(value)


def require_bool(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def require_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def require_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value

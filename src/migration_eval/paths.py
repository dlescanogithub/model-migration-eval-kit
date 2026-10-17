"""Locate the checkout so editable installs and Docker both find config/."""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Return the directory that holds pyproject.toml and config/policy.yaml."""
    starts = [Path.cwd(), *Path(__file__).resolve().parents]
    seen: set[Path] = set()
    for start in starts:
        for candidate in [start, *start.parents]:
            if candidate in seen:
                continue
            seen.add(candidate)
            policy = candidate / "config" / "policy.yaml"
            marker = candidate / "pyproject.toml"
            if marker.is_file() and policy.is_file():
                return candidate
    raise RuntimeError("could not find the repo root (pyproject.toml + config/policy.yaml); run from a checkout")

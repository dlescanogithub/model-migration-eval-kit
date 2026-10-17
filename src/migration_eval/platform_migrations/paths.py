"""Locate the synthetic fixtures shipped with this chapter."""

from __future__ import annotations

from pathlib import Path


def data_root() -> Path:
    """Directory that holds examples/ and evals/ for the platform chapter."""
    return Path(__file__).resolve().parent / "data"

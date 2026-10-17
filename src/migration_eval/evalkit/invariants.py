"""Result type for an invariant. The check is pass/fail plus a short detail."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InvariantResult:
    name: str
    passed: bool
    detail: str

"""Run invariant callables. A raised check becomes a failed result."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from migration_eval.evalkit.invariants import InvariantResult


def run_invariants(
    checks: Sequence[tuple[str, Callable[[], tuple[bool, str]]]],
) -> tuple[InvariantResult, ...]:
    results: list[InvariantResult] = []
    for name, check in checks:
        try:
            passed, detail = check()
        except Exception as exc:
            results.append(InvariantResult(name, False, f"{type(exc).__name__}: {exc}"))
            continue
        results.append(InvariantResult(name, bool(passed), detail))
    return tuple(results)

"""Invariant-check surface shared with the other portfolio repos.

See docs/PROVENANCE.md. This package re-exports invariant checks and JSONL
trace helpers. Scoring looks at effects, not an exact tool-call trajectory.
"""

from migration_eval.evalkit.invariants import InvariantResult
from migration_eval.evalkit.runner import run_invariants
from migration_eval.invariants import CheckResult, check_completion
from migration_eval.trace import append_trace, read_traces

__all__ = [
    "CheckResult",
    "InvariantResult",
    "append_trace",
    "check_completion",
    "read_traces",
    "run_invariants",
]

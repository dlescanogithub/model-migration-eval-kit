"""Invariant-check surface, reimplemented to the contract named in the brief.

See docs/PROVENANCE.md. The private reference tree was not readable from this
environment, so this package is a fresh implementation of the same ideas:
invariant checks rather than exact trajectories, JSONL traces, and an offline
runner. It is not a byte copy.
"""

from migration_eval.invariants import CheckResult, check_completion
from migration_eval.trace import append_trace, read_traces

__all__ = ["CheckResult", "append_trace", "check_completion", "read_traces"]

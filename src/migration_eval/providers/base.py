"""Provider protocol. Callers depend on this, not on a vendor SDK."""

from __future__ import annotations

from typing import Protocol

from migration_eval.models import Completion, Ticket


class Provider(Protocol):
    name: str
    model: str
    latency_kind: str

    def complete(self, ticket: Ticket, *, seed: int) -> Completion:
        """Return one completion. Must not perform unapproved side effects."""

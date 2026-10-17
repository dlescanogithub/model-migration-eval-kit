"""Grade one completion: invariant result plus simulated or measured cost."""

from __future__ import annotations

from dataclasses import dataclass

from migration_eval.invariants import CheckResult, check_completion
from migration_eval.models import Completion, Ticket
from migration_eval.prices import ModelPrice, cost_usd
from migration_eval.providers.base import Provider


@dataclass(frozen=True)
class Graded:
    ticket: Ticket
    seed: int
    completion: Completion
    check: CheckResult
    cost_usd: float


def grade(provider: Provider, ticket: Ticket, *, seed: int, price: ModelPrice) -> Graded:
    completion = provider.complete(ticket, seed=seed)
    return Graded(
        ticket=ticket,
        seed=seed,
        completion=completion,
        check=check_completion(ticket, completion),
        cost_usd=cost_usd(price, completion.input_tokens, completion.output_tokens),
    )

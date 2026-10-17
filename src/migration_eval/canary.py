"""Synthetic traffic-split canary. It never touches a live router.

The cohort is a stratified slice of the golden set (at least one ticket from
each slice, about `split` of each slice). Those tickets are the canary path.
The rest stay on the old provider. The stream repeats so the audit log shows
a short synthetic shift, not a single pass.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from migration_eval.grading import Graded, grade
from migration_eval.models import Ticket
from migration_eval.prices import PriceTable
from migration_eval.providers.base import Provider
from migration_eval.providers.fake import PROFILES
from migration_eval.yamlutil import load_yaml_mapping, require_bool, require_float, require_int


@dataclass(frozen=True)
class CanaryCriteria:
    split: float
    repeats: int
    max_fail_rate_delta: float
    rollback_on_harmful: bool


@dataclass(frozen=True)
class CanaryResult:
    decision: str
    reason: str
    cohort: tuple[str, ...]
    baseline_fail_rate: float
    canary_fail_rate: float
    canary_harmful: int
    events: tuple[dict[str, object], ...]


def load_canary_criteria(path: Path) -> CanaryCriteria:
    data = load_yaml_mapping(path)
    return CanaryCriteria(
        split=require_float(data, "split"),
        repeats=require_int(data, "repeats"),
        max_fail_rate_delta=require_float(data, "max_fail_rate_delta"),
        rollback_on_harmful=require_bool(data, "rollback_on_harmful"),
    )


def cohort_ids(tickets: list[Ticket], split: float) -> tuple[str, ...]:
    if split <= 0 or split > 1:
        raise ValueError("split must be in (0, 1]")
    chosen: list[str] = []
    by_slice: dict[str, list[Ticket]] = {}
    for ticket in tickets:
        by_slice.setdefault(ticket.slice, []).append(ticket)
    for name in sorted(by_slice):
        group = by_slice[name]
        k = max(1, round(split * len(group)))
        k = min(k, len(group))
        chosen.extend(ticket.id for ticket in group[:k])
    return tuple(chosen)


def simulate_canary(
    old: Provider,
    new: Provider,
    tickets: list[Ticket],
    *,
    criteria: CanaryCriteria,
    prices: PriceTable,
    today: str,
) -> CanaryResult:
    cohort = set(cohort_ids(tickets, criteria.split))
    old_price = prices.for_model(_price_key(old.name))
    new_price = prices.for_model(_price_key(new.name))
    events: list[dict[str, object]] = []
    baseline: list[Graded] = []
    canary_rows: list[Graded] = []
    first_harmful: str | None = None
    sequence = 0
    for repeat in range(criteria.repeats):
        for ticket in tickets:
            sequence += 1
            on_canary = ticket.id in cohort
            if on_canary:
                graded = grade(new, ticket, seed=repeat, price=new_price)
                canary_rows.append(graded)
                route = "new"
            else:
                graded = grade(old, ticket, seed=repeat, price=old_price)
                baseline.append(graded)
                route = "old"
            if graded.check.harmful and on_canary and first_harmful is None:
                first_harmful = ticket.id
            events.append(
                {
                    "event": "request",
                    "seq": sequence,
                    "repeat": repeat,
                    "today": today,
                    "ticket_id": ticket.id,
                    "slice": ticket.slice,
                    "route": route,
                    "passed": graded.check.passed,
                    "harmful": graded.check.harmful,
                    "provider": graded.completion.provider,
                }
            )
    baseline_fail = _fail_rate(baseline)
    canary_fail = _fail_rate(canary_rows)
    harmful = sum(1 for row in canary_rows if row.check.harmful)
    decision, reason = _decide(
        baseline_fail=baseline_fail,
        canary_fail=canary_fail,
        harmful=harmful,
        first_harmful=first_harmful,
        criteria=criteria,
    )
    events.append(
        {
            "event": "decision",
            "today": today,
            "decision": decision,
            "reason": reason,
            "cohort": sorted(cohort),
            "baseline_fail_rate": baseline_fail,
            "canary_fail_rate": canary_fail,
            "canary_harmful": harmful,
            "split": criteria.split,
        }
    )
    return CanaryResult(
        decision=decision,
        reason=reason,
        cohort=tuple(sorted(cohort)),
        baseline_fail_rate=baseline_fail,
        canary_fail_rate=canary_fail,
        canary_harmful=harmful,
        events=tuple(events),
    )


def write_audit(result: CanaryResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in result.events:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def _decide(
    *,
    baseline_fail: float,
    canary_fail: float,
    harmful: int,
    first_harmful: str | None,
    criteria: CanaryCriteria,
) -> tuple[str, str]:
    if criteria.rollback_on_harmful and harmful > 0:
        return (
            "ROLLBACK",
            f"harmful effect on canary traffic (first ticket {first_harmful})",
        )
    delta = canary_fail - baseline_fail
    if delta > criteria.max_fail_rate_delta:
        return (
            "ROLLBACK",
            f"canary fail rate {canary_fail:.4f} exceeded baseline {baseline_fail:.4f} "
            f"by more than {criteria.max_fail_rate_delta:.4f}",
        )
    return (
        "HOLD",
        f"canary fail rate {canary_fail:.4f} stayed within {criteria.max_fail_rate_delta:.4f} "
        f"of baseline {baseline_fail:.4f}",
    )


def _fail_rate(rows: list[Graded]) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if not row.check.passed) / len(rows)


def _price_key(name: str) -> str:
    profile = PROFILES.get(name)
    if profile is not None:
        return profile.price_key
    return name

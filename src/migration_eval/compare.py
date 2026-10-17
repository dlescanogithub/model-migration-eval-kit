"""Run the same golden set on two providers and score the paired result."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from migration_eval.grading import Graded, grade
from migration_eval.models import SLICES, Ticket
from migration_eval.policy import Decision, Metrics, Policy, SliceDelta, decide
from migration_eval.prices import PriceTable
from migration_eval.providers.base import Provider
from migration_eval.providers.fake import PROFILES
from migration_eval.stats import bootstrap_rate_delta, mcnemar_regression_pvalue, percentile


@dataclass(frozen=True)
class CompareReport:
    old_name: str
    new_name: str
    runs: int
    today: str
    tickets: int
    metrics: Metrics
    decision: Decision
    price_note: str
    latency_note: str
    disagreements: tuple[str, ...]


def compare_providers(
    old: Provider,
    new: Provider,
    tickets: list[Ticket],
    *,
    runs: int,
    policy: Policy,
    prices: PriceTable,
    today: str,
    bootstrap_rounds: int = 400,
    bootstrap_seed: int = 0,
) -> CompareReport:
    if runs < 1:
        raise ValueError("runs must be >= 1")
    if not tickets:
        raise ValueError("golden set is empty")
    old_price = prices.for_model(_price_key(old.name))
    new_price = prices.for_model(_price_key(new.name))
    old_rows: list[Graded] = []
    new_rows: list[Graded] = []
    for seed in range(runs):
        for ticket in tickets:
            old_rows.append(grade(old, ticket, seed=seed, price=old_price))
            new_rows.append(grade(new, ticket, seed=seed, price=new_price))
    metrics = _metrics(
        old_rows,
        new_rows,
        tickets,
        bootstrap_rounds=bootstrap_rounds,
        bootstrap_seed=bootstrap_seed,
    )
    decision = decide(metrics, policy)
    latency_kinds = {row.completion.latency_kind for row in old_rows + new_rows}
    if latency_kinds == {"simulated"}:
        latency_note = "simulated"
    elif "measured" in latency_kinds and "simulated" in latency_kinds:
        latency_note = "mixed simulated and measured"
    else:
        latency_note = "measured"
    return CompareReport(
        old_name=old.name,
        new_name=new.name,
        runs=runs,
        today=today,
        tickets=len(tickets),
        metrics=metrics,
        decision=decision,
        price_note=prices.note,
        latency_note=latency_note,
        disagreements=_disagreements(old_rows, new_rows),
    )


def _metrics(
    old_rows: list[Graded],
    new_rows: list[Graded],
    tickets: list[Ticket],
    *,
    bootstrap_rounds: int,
    bootstrap_seed: int,
) -> Metrics:
    categories = tuple(sorted({ticket.true_category for ticket in tickets}))
    slices = tuple(
        SliceDelta(
            name=name,
            old_pass_rate=_rate(old_rows, _slice_is(name)),
            new_pass_rate=_rate(new_rows, _slice_is(name)),
        )
        for name in SLICES
    )
    category_deltas = tuple(
        SliceDelta(
            name=name,
            old_pass_rate=_rate(old_rows, _category_is(name)),
            new_pass_rate=_rate(new_rows, _category_is(name)),
        )
        for name in categories
    )
    overall = SliceDelta(
        name="overall",
        old_pass_rate=_rate(old_rows, _always),
        new_pass_rate=_rate(new_rows, _always),
    )
    new_worse, new_better = _discordant(old_rows, new_rows)
    old_by_ticket = _pass_by_ticket(old_rows)
    new_by_ticket = _pass_by_ticket(new_rows)
    low, high = bootstrap_rate_delta(
        old_by_ticket,
        new_by_ticket,
        rounds=bootstrap_rounds,
        seed=bootstrap_seed,
    )
    runs = len({row.seed for row in old_rows})
    return Metrics(
        slices=slices,
        categories=category_deltas,
        overall=overall,
        format_failure_rate_old=_fraction(old_rows, lambda row: row.check.format_failed),
        format_failure_rate_new=_fraction(new_rows, lambda row: row.check.format_failed),
        tool_failure_rate_old=_fraction(old_rows, lambda row: row.check.tool_failed),
        tool_failure_rate_new=_fraction(new_rows, lambda row: row.check.tool_failed),
        harmful_old=sum(1 for row in old_rows if row.check.harmful),
        harmful_new=sum(1 for row in new_rows if row.check.harmful),
        p95_latency_ms_old=percentile([row.completion.latency_ms for row in old_rows], 95),
        p95_latency_ms_new=percentile([row.completion.latency_ms for row in new_rows], 95),
        p50_latency_ms_old=percentile([row.completion.latency_ms for row in old_rows], 50),
        p50_latency_ms_new=percentile([row.completion.latency_ms for row in new_rows], 50),
        cost_per_run_old=sum(row.cost_usd for row in old_rows) / runs,
        cost_per_run_new=sum(row.cost_usd for row in new_rows) / runs,
        mcnemar_new_worse=new_worse,
        mcnemar_new_better=new_better,
        mcnemar_p_regression=mcnemar_regression_pvalue(new_worse, new_better),
        bootstrap_low=low,
        bootstrap_high=high,
    )


def _slice_is(name: str) -> Callable[[Graded], bool]:
    def pred(row: Graded) -> bool:
        return row.ticket.slice == name

    return pred


def _category_is(name: str) -> Callable[[Graded], bool]:
    def pred(row: Graded) -> bool:
        return row.ticket.true_category == name

    return pred


def _always(_row: Graded) -> bool:
    return True


def _rate(rows: list[Graded], pred: Callable[[Graded], bool]) -> float:
    chosen = [row for row in rows if pred(row)]
    if not chosen:
        raise ValueError("slice or category has no rows")
    return sum(1 for row in chosen if row.check.passed) / len(chosen)


def _fraction(rows: list[Graded], pred: Callable[[Graded], bool]) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if pred(row)) / len(rows)


def _discordant(old_rows: list[Graded], new_rows: list[Graded]) -> tuple[int, int]:
    paired = _pair(old_rows, new_rows)
    worse = sum(1 for old, new in paired if old.check.passed and not new.check.passed)
    better = sum(1 for old, new in paired if new.check.passed and not old.check.passed)
    return worse, better


def _pass_by_ticket(rows: list[Graded]) -> dict[str, float]:
    buckets: dict[str, list[bool]] = {}
    for row in rows:
        buckets.setdefault(row.ticket.id, []).append(row.check.passed)
    return {key: sum(1 for item in values if item) / len(values) for key, values in buckets.items()}


def _pair(old_rows: list[Graded], new_rows: list[Graded]) -> list[tuple[Graded, Graded]]:
    index = {(row.ticket.id, row.seed): row for row in new_rows}
    return [(row, index[(row.ticket.id, row.seed)]) for row in old_rows]


def _disagreements(old_rows: list[Graded], new_rows: list[Graded]) -> tuple[str, ...]:
    seen: list[str] = []
    for old, new in _pair(old_rows, new_rows):
        if old.check.passed == new.check.passed:
            continue
        direction = "new_failed" if old.check.passed else "new_passed"
        label = f"{old.ticket.id} {old.ticket.slice} {old.ticket.true_category} {direction}"
        if label not in seen:
            seen.append(label)
    return tuple(seen)


def _price_key(name: str) -> str:
    profile = PROFILES.get(name)
    if profile is not None:
        return profile.price_key
    return name

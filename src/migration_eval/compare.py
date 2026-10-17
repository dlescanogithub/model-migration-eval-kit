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

CONTRACT_SANITY_WARNING = "posible desajuste prompt/grader, no es calidad del modelo"


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
    contract_warning: str = ""


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
    stop_on_live_error: bool = False,
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
            try:
                old_rows.append(grade(old, ticket, seed=seed, price=old_price))
                new_rows.append(grade(new, ticket, seed=seed, price=new_price))
            except Exception as exc:
                if not stop_on_live_error or not _is_live_stop(exc):
                    raise
                raise IncompleteLiveRun(str(exc), old_rows, new_rows, ticket.id) from exc
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
        contract_warning=_contract_warning(metrics, old.name, new.name),
    )


def _metrics(
    old_rows: list[Graded],
    new_rows: list[Graded],
    tickets: list[Ticket],
    *,
    bootstrap_rounds: int,
    bootstrap_seed: int,
) -> Metrics:
    """Score each ticket once. Seed repeats collapse before any rate, test, or interval."""
    old_pass = _collapsed_pass(old_rows)
    new_pass = _collapsed_pass(new_rows)
    categories = tuple(sorted({ticket.true_category for ticket in tickets}))
    slices = tuple(
        _delta(
            name,
            [ticket.id for ticket in tickets if ticket.slice == name],
            old_pass,
            new_pass,
            bootstrap_rounds=bootstrap_rounds,
            bootstrap_seed=bootstrap_seed,
        )
        for name in SLICES
    )
    category_deltas = tuple(
        _delta(
            name,
            [ticket.id for ticket in tickets if ticket.true_category == name],
            old_pass,
            new_pass,
            bootstrap_rounds=bootstrap_rounds,
            bootstrap_seed=bootstrap_seed,
            with_interval=False,
        )
        for name in categories
    )
    overall = _delta(
        "overall",
        [ticket.id for ticket in tickets],
        old_pass,
        new_pass,
        bootstrap_rounds=bootstrap_rounds,
        bootstrap_seed=bootstrap_seed,
    )
    new_worse = sum(1 for ticket in tickets if old_pass[ticket.id] and not new_pass[ticket.id])
    new_better = sum(1 for ticket in tickets if new_pass[ticket.id] and not old_pass[ticket.id])
    runs = len({row.seed for row in old_rows})
    return Metrics(
        slices=slices,
        categories=category_deltas,
        overall=overall,
        format_failure_rate_old=_ticket_flag_rate(old_rows, lambda row: row.check.format_failed),
        format_failure_rate_new=_ticket_flag_rate(new_rows, lambda row: row.check.format_failed),
        tool_failure_rate_old=_ticket_flag_rate(old_rows, lambda row: row.check.tool_failed),
        tool_failure_rate_new=_ticket_flag_rate(new_rows, lambda row: row.check.tool_failed),
        harmful_old=_harmful_tickets(old_rows),
        harmful_new=_harmful_tickets(new_rows),
        contract_mismatch_old=_contract_tickets(old_rows),
        contract_mismatch_new=_contract_tickets(new_rows),
        p95_latency_ms_old=percentile([row.completion.latency_ms for row in old_rows], 95),
        p95_latency_ms_new=percentile([row.completion.latency_ms for row in new_rows], 95),
        p50_latency_ms_old=percentile([row.completion.latency_ms for row in old_rows], 50),
        p50_latency_ms_new=percentile([row.completion.latency_ms for row in new_rows], 50),
        cost_per_run_old=sum(row.cost_usd for row in old_rows) / runs,
        cost_per_run_new=sum(row.cost_usd for row in new_rows) / runs,
        mcnemar_new_worse=new_worse,
        mcnemar_new_better=new_better,
        mcnemar_p_regression=mcnemar_regression_pvalue(new_worse, new_better),
        bootstrap_low=overall.bootstrap_low,
        bootstrap_high=overall.bootstrap_high,
        analysis_n=len(tickets),
    )


def _delta(
    name: str,
    ids: list[str],
    old_pass: dict[str, bool],
    new_pass: dict[str, bool],
    *,
    bootstrap_rounds: int,
    bootstrap_seed: int,
    with_interval: bool = True,
) -> SliceDelta:
    if not ids:
        raise ValueError("slice or category has no tickets")
    low = 0.0
    high = 0.0
    if with_interval:
        old_map = {item: 1.0 if old_pass[item] else 0.0 for item in ids}
        new_map = {item: 1.0 if new_pass[item] else 0.0 for item in ids}
        low, high = bootstrap_rate_delta(
            old_map,
            new_map,
            rounds=bootstrap_rounds,
            seed=bootstrap_seed,
        )
    return SliceDelta(
        name=name,
        old_pass_rate=sum(1 for item in ids if old_pass[item]) / len(ids),
        new_pass_rate=sum(1 for item in ids if new_pass[item]) / len(ids),
        n=len(ids),
        bootstrap_low=low,
        bootstrap_high=high,
    )


def _collapsed_pass(rows: list[Graded]) -> dict[str, bool]:
    """A ticket passes only when every repeat passed. One seed cannot mint extra pairs."""
    buckets: dict[str, list[bool]] = {}
    for row in rows:
        buckets.setdefault(row.ticket.id, []).append(row.check.passed)
    return {key: all(values) for key, values in buckets.items()}


def _ticket_flag_rate(rows: list[Graded], pred: Callable[[Graded], bool]) -> float:
    flagged: dict[str, bool] = {}
    for row in rows:
        flagged[row.ticket.id] = flagged.get(row.ticket.id, False) or pred(row)
    if not flagged:
        return 0.0
    return sum(1 for value in flagged.values() if value) / len(flagged)


def _harmful_tickets(rows: list[Graded]) -> int:
    return len({row.ticket.id for row in rows if row.check.harmful})


def _contract_tickets(rows: list[Graded]) -> int:
    return len({row.ticket.id for row in rows if row.check.contract_mismatch})


class IncompleteLiveRun(RuntimeError):
    """A live compare stopped. Completed rows are the partial report."""

    def __init__(self, message: str, old_rows: list[Graded], new_rows: list[Graded], ticket_id: str) -> None:
        super().__init__(message)
        self.old_rows = old_rows
        self.new_rows = new_rows
        self.ticket_id = ticket_id


def _is_live_stop(exc: Exception) -> bool:
    from migration_eval.providers.openai_compat import LiveTransportError, SpendCapExceeded

    return isinstance(exc, (LiveTransportError, SpendCapExceeded))


def _contract_warning(metrics: Metrics, old_name: str, new_name: str) -> str:
    scripted = old_name.startswith("fake-") and new_name.startswith("fake-")
    if scripted or metrics.analysis_n <= 0:
        return ""
    near_zero = metrics.overall.old_pass_rate <= 0.05 and metrics.overall.new_pass_rate <= 0.05
    old_rate = metrics.contract_mismatch_old / metrics.analysis_n
    new_rate = metrics.contract_mismatch_new / metrics.analysis_n
    if near_zero and old_rate >= 0.8 and new_rate >= 0.8:
        return CONTRACT_SANITY_WARNING
    return ""


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

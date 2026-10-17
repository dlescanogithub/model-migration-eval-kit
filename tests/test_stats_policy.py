from __future__ import annotations

import math

from migration_eval.policy import Metrics, Policy, SliceDelta, decide
from migration_eval.stats import bootstrap_rate_delta, mcnemar_regression_pvalue, percentile


def test_percentile_nearest_rank() -> None:
    assert percentile([10.0], 95) == 10.0
    assert percentile([1.0, 2.0, 3.0, 4.0], 50) == 2.0
    assert math.isclose(percentile([1.0, 2.0, 3.0, 4.0], 100), 4.0)


def test_mcnemar_fair_coin_and_total_imbalance() -> None:
    assert mcnemar_regression_pvalue(0, 0) == 1.0
    balanced = mcnemar_regression_pvalue(5, 5)
    assert 0.5 < balanced <= 1.0
    skewed = mcnemar_regression_pvalue(20, 0)
    assert skewed < 0.001


def test_bootstrap_is_deterministic() -> None:
    old = {"a": 1.0, "b": 1.0, "c": 0.0}
    new = {"a": 1.0, "b": 0.0, "c": 0.0}
    first = bootstrap_rate_delta(old, new, rounds=50, seed=3)
    second = bootstrap_rate_delta(old, new, rounds=50, seed=3)
    assert first == second
    assert first[0] <= first[1]


def _policy() -> Policy:
    return Policy(
        max_slice_drop_points=5,
        adversarial_must_not_regress=True,
        min_cost_savings_ratio=0.2,
        max_p95_latency_ms=1000,
        max_format_failure_rate=0.05,
        max_tool_failure_rate=0.01,
        alpha=0.05,
        min_pass_rate=0.99,
        max_cost_per_run_usd=1.0,
    )


def _metrics(**overrides: object) -> Metrics:
    base = Metrics(
        slices=(
            SliceDelta("happy", 1.0, 1.0),
            SliceDelta("edge", 1.0, 1.0),
            SliceDelta("adversarial", 1.0, 1.0),
        ),
        categories=(SliceDelta("order_status", 1.0, 1.0),),
        overall=SliceDelta("overall", 1.0, 1.0),
        format_failure_rate_old=0.0,
        format_failure_rate_new=0.0,
        tool_failure_rate_old=0.0,
        tool_failure_rate_new=0.0,
        harmful_old=0,
        harmful_new=0,
        p95_latency_ms_old=400,
        p95_latency_ms_new=200,
        p50_latency_ms_old=400,
        p50_latency_ms_new=200,
        cost_per_run_old=1.0,
        cost_per_run_new=0.4,
        mcnemar_new_worse=0,
        mcnemar_new_better=0,
        mcnemar_p_regression=1.0,
        bootstrap_low=0.0,
        bootstrap_high=0.0,
    )
    data = base.__dict__.copy()
    data.update(overrides)
    return Metrics(**data)  # type: ignore[arg-type]


def test_policy_go_no_go_and_need_human() -> None:
    policy = _policy()
    assert decide(_metrics(), policy).status == "GO"
    regressed = _metrics(
        slices=(
            SliceDelta("happy", 1.0, 1.0),
            SliceDelta("edge", 1.0, 0.5),
            SliceDelta("adversarial", 1.0, 1.0),
        )
    )
    assert decide(regressed, policy).status == "NO_GO"
    unsafe = _metrics(harmful_old=0, harmful_new=2)
    assert decide(unsafe, policy).status == "NO_GO"
    flat_cost = _metrics(cost_per_run_old=1.0, cost_per_run_new=1.0)
    assert decide(flat_cost, policy).status == "NEED_HUMAN"
    slow = _metrics(p95_latency_ms_new=5000)
    assert decide(slow, policy).status == "NO_GO"

"""Paired comparison stats: exact McNemar and a ticket bootstrap.

Plain version: each ticket is graded on both models. Pairs that agree do not
say who is better. Pairs that disagree should split about evenly if the new
model is no worse. McNemar asks how surprising the one-sided disagreements
are. The bootstrap redraws tickets and shows a range for the pass-rate gap.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence


def percentile(values: Sequence[float], pct: float) -> float:
    """Nearest-rank percentile. pct is in 0..100. Rank uses ceil."""
    if not values:
        raise ValueError("percentile of empty data")
    if pct < 0 or pct > 100:
        raise ValueError("pct must be between 0 and 100")
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = math.ceil((pct / 100.0) * len(ordered))
    index = min(len(ordered), max(1, rank)) - 1
    return float(ordered[index])


def mcnemar_regression_pvalue(new_worse: int, new_better: int) -> float:
    """One-sided exact p-value for 'the new model fails more often on disagreements'.

    new_worse: old passed and new failed.
    new_better: old failed and new passed.
    Under a fair coin, P(X >= new_worse) for X ~ Binomial(n, 0.5).
    When there are no disagreements the p-value is 1.
    """
    if new_worse < 0 or new_better < 0:
        raise ValueError("counts must be >= 0")
    n = new_worse + new_better
    if n == 0:
        return 1.0
    return _binom_sf(new_worse, n)


def bootstrap_rate_delta(
    old_pass: dict[str, float],
    new_pass: dict[str, float],
    *,
    rounds: int = 1000,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile interval (2.5, 97.5) for mean(new - old) over resampled tickets."""
    if rounds < 1:
        raise ValueError("rounds must be >= 1")
    ids = sorted(set(old_pass) & set(new_pass))
    if not ids:
        raise ValueError("bootstrap needs tickets")
    rng = random.Random(seed)
    deltas: list[float] = []
    width = len(ids)
    for _ in range(rounds):
        drawn = [rng.choice(ids) for _ in range(width)]
        delta = sum(new_pass[item] - old_pass[item] for item in drawn) / width
        deltas.append(delta)
    return percentile(deltas, 2.5), percentile(deltas, 97.5)


def _binom_sf(k: int, n: int) -> float:
    """P(X >= k) for X ~ Binomial(n, 0.5), via log-sum-exp."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    logs = [_log_binom_pmf(i, n) for i in range(k, n + 1)]
    top = max(logs)
    total = math.exp(top) * sum(math.exp(item - top) for item in logs)
    if total < 0.0:
        return 0.0
    if total > 1.0:
        return 1.0
    return total


def _log_binom_pmf(k: int, n: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) - n * math.log(2.0)

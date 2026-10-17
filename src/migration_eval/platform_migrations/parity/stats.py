"""Deterministic PSI and two-sample KS. No SciPy and no network."""

from __future__ import annotations

import math
from collections.abc import Sequence


def population_stability_index(
    expected: Sequence[float],
    actual: Sequence[float],
    *,
    bins: int = 10,
    epsilon: float = 1e-6,
) -> float:
    """PSI on fixed-width bins spanning both samples.

    Equal samples return 0. A constant pair returns 0. Empty bins are floored
    at epsilon on both sides, so shared empty bins do not move the score.
    """
    if len(expected) == 0 or len(actual) == 0:
        raise ValueError("population_stability_index needs both samples")
    if bins < 1:
        raise ValueError("bins must be >= 1")
    if epsilon <= 0:
        raise ValueError("epsilon must be > 0")
    low = min(min(expected), min(actual))
    high = max(max(expected), max(actual))
    if high == low:
        return 0.0
    width = (high - low) / bins

    def proportions(values: Sequence[float]) -> list[float]:
        counts = [0] * bins
        for value in values:
            index = int((value - low) / width)
            if index >= bins:
                index = bins - 1
            if index < 0:
                index = 0
            counts[index] += 1
        total = float(len(values))
        return [count / total for count in counts]

    score = 0.0
    for left, right in zip(proportions(expected), proportions(actual), strict=True):
        left_adj = max(left, epsilon)
        right_adj = max(right, epsilon)
        score += (right_adj - left_adj) * math.log(right_adj / left_adj)
    return score


def ks_statistic(expected: Sequence[float], actual: Sequence[float]) -> float:
    """Two-sample Kolmogorov-Smirnov statistic in [0, 1]."""
    if len(expected) == 0 or len(actual) == 0:
        raise ValueError("ks_statistic needs both samples")
    left = sorted(expected)
    right = sorted(actual)
    n_left = len(left)
    n_right = len(right)
    i_left = 0
    i_right = 0
    delta = 0.0
    for value in sorted(set(left) | set(right)):
        while i_left < n_left and left[i_left] <= value:
            i_left += 1
        while i_right < n_right and right[i_right] <= value:
            i_right += 1
        delta = max(delta, abs((i_left / n_left) - (i_right / n_right)))
    return delta

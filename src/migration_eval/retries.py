"""Bounded retries: a max attempt count and a capped exponential backoff."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class RetryableError(Exception):
    """A transient failure that may be tried again."""


def run_with_retries(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    base_delay_s: float = 0.01,
    backoff_cap_s: float = 0.2,
    jitter_ratio: float = 0.0,
    sleep: Callable[[float], None] = time.sleep,
    rng: Callable[[], float] | None = None,
) -> tuple[T, int]:
    """Call fn until it returns or attempts are exhausted.

    Delays are base_delay_s, then double, and never exceed backoff_cap_s.
    jitter_ratio spreads each delay by that fraction up or down, still inside the cap.
    The sleep callable and rng are injectable so tests do not wait or draw entropy.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if base_delay_s < 0 or backoff_cap_s < 0 or jitter_ratio < 0:
        raise ValueError("delays must be >= 0")
    attempt = 0
    while True:
        attempt += 1
        try:
            return fn(), attempt
        except RetryableError:
            if attempt >= max_attempts:
                raise
            delay = _delay(attempt, base_delay_s, backoff_cap_s, jitter_ratio, rng)
            sleep(delay)


def _delay(
    attempt: int,
    base_delay_s: float,
    backoff_cap_s: float,
    jitter_ratio: float,
    rng: Callable[[], float] | None,
) -> float:
    raw = float(min(backoff_cap_s, base_delay_s * (2 ** (attempt - 1))))
    if jitter_ratio == 0 or raw == 0:
        return raw
    draw = float((rng or _default_unit)())
    factor = 1.0 + jitter_ratio * ((draw * 2.0) - 1.0)
    return float(max(0.0, min(backoff_cap_s, raw * factor)))


def _default_unit() -> float:
    import random

    return random.random()

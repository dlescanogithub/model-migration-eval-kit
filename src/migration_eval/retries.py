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
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[T, int]:
    """Call fn until it returns or attempts are exhausted.

    Delays are base_delay_s, then double, and never exceed backoff_cap_s.
    The sleep callable is injectable so tests do not wait.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if base_delay_s < 0 or backoff_cap_s < 0:
        raise ValueError("delays must be >= 0")
    attempt = 0
    while True:
        attempt += 1
        try:
            return fn(), attempt
        except RetryableError:
            if attempt >= max_attempts:
                raise
            delay = min(backoff_cap_s, base_delay_s * (2 ** (attempt - 1)))
            sleep(delay)

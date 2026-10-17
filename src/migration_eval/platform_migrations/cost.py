"""Illustrative dual-run arithmetic. Inputs are caller-supplied, not a price list."""

from __future__ import annotations


def dual_run_cost(
    *,
    jobs: int,
    hours_per_job: float,
    rate_per_hour: float,
    overlap_days: int,
) -> float:
    """Return jobs * hours_per_job * rate_per_hour * overlap_days.

    rate_per_hour is an input you choose for a scenario. This function does not
    look up a vendor price.
    """
    if jobs < 0 or overlap_days < 0:
        raise ValueError("jobs and overlap_days must be >= 0")
    if hours_per_job < 0 or rate_per_hour < 0:
        raise ValueError("hours_per_job and rate_per_hour must be >= 0")
    return float(jobs) * hours_per_job * rate_per_hour * float(overlap_days)


# Simulated cap used by the eval invariant for the Aerolito fixture.
# The number is a local policy constant, not a budget from a finance system.
SIMULATED_DUAL_RUN_CAP = 1000.0
AEROLITO_SIMULATED_INPUTS: dict[str, float] = {
    "jobs": 4.0,
    "hours_per_job": 0.5,
    "rate_per_hour": 10.0,
    "overlap_days": 14.0,
}

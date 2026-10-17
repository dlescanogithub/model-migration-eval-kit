# ADR 0004: Three-way decision with explicit caps

- Status: accepted for this repo
- Date: 2026-10-17

## Context

A single accuracy number hides a bad slice. A pure cost comparison hides a safety miss. A binary pass/fail hides the case where nothing is unsafe and nothing was gained.

## Decision

`config/policy.yaml` holds the caps: 5 points per slice, adversarial may not regress, format and tool failure caps, p95 budget, alpha for the paired test, and a minimum savings ratio. Hard misses return NO_GO. If nothing hard failed and the savings ratio is below the minimum, or the bootstrap interval crosses zero while the rates differ, the result is NEED_HUMAN. Otherwise GO, with the reason text stating that a human still approves.

The degraded profile exists so CI can prove the decision can be NO_GO. `eval-regression` exits 1 in that case on purpose. The paired test counts tickets, after seed repeats are collapsed. A scripted NO_GO shows that this policy fires. It is not a measured gap between two real models.

## Consequences

Changing a cap changes decisions. That edit is a policy change and should be reviewed, not tuned until the report turns green. The measured `fake-old` versus `fake-new` run on 2026-10-17 is NO_GO under these caps.

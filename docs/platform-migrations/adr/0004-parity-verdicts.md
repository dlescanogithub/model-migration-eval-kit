# ADR 0004 — Parity verdicts

- Status: accepted
- Date: 2026-10-17

## Context

A single boolean hides the difference between "do not ship" and "a person should look".

## Decision

`compare_tables` returns `PASS`, `FAIL`, or `NEED_HUMAN`. Any failing finding forces `FAIL`. Watch findings (extra columns, thin types, PSI/KS in the watch band) force `NEED_HUMAN` when nothing failed. The cutover gate treats `FAIL` as `NOT_READY`. `NEED_HUMAN` stays open until `parity_approved_by` is set. Row-level key alignment is not part of this verdict.

Default bands: PSI watch 0.10, PSI fail 0.25, KS watch 0.10, KS fail 0.20. Row-count and aggregate relative tolerances default to 0. These are local defaults, not an external standard.

## Consequences

Scripts can branch on the process exit code: 0 PASS, 3 NEED_HUMAN, 1 FAIL. A human still owns the watch band.

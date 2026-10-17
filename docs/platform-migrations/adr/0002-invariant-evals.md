# ADR 0002 — Invariant evals, not trajectories

- Status: accepted
- Date: 2026-10-17

## Context

Asserting the exact sequence of helper calls makes tests brittle and does not tell you whether a migration is safe.

## Decision

`python -m migration_eval platform-migrations eval` checks invariants: source registry unchanged, simulated cost under the local cap, no unapproved external action, cycles blocked, migrate idempotent, a broken parity fixture is FAIL, rollback restores, cassette replay performs zero network calls.

A separate command, `eval-regression`, is expected to exit non-zero because that broken fixture fails the parity gate. CI asserts the non-zero exit and checks the JSON flag `gate_went_red`.

## Consequences

Refactors can change internal call order. Weakening the parity checker so the broken fixture passes turns the regression command into exit 0, and CI goes red.

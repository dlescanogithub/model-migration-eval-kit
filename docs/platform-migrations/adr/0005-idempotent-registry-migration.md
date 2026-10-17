# ADR 0005 — Idempotent registry migration with a rollback log

- Status: accepted
- Date: 2026-10-17

## Context

A migration job will be retried. A retry that appends duplicate versions or edits the legacy registry is a harmful effect.

## Decision

`migrate` copies versions, stages, and aliases onto the target. The source object is not mutated. A second call returns an empty log when the target already matches. Content mismatches raise `RegistryConflict` before writes. Each changed model records a snapshot taken beforehand. `rollback` restores those snapshots in reverse. At most one Staging and one Production version exist per name. Moving a version into one of those stages archives the previous holder. Target-only versions are not deleted.

## Consequences

The eval can assert "no harmful effect" on the source and "rollback restores" on the target. Operators must still drill a real registry before using these semantics outside the simulator. Archiving a target Production version is intentional and reversible.

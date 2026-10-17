# ADR 0003: Thin providers, cassette by default for anything recorded

- Status: accepted for this repo
- Date: 2026-10-17

## Context

The comparison should not import a vendor SDK. Tests must not open network connections. A recorded answer should replay exactly, and a missing recording must not quietly call out.

## Decision

`Provider.complete` is the only method the grader uses. Built-in names are the fake profiles, `cassette`, and `openai-compat` (a chat-completions HTTP adapter). Cassette replay raises `CassetteMiss` when the key is absent. Recording is explicit. The live adapter refuses to run when `LIVE_MODE` is off, refuses before any request when config is missing, and retries with a max attempt count and a backoff cap. `compare-live` records both sides under `var/cassettes/`.

## Consequences

Adding a vendor means a new adapter behind the same method, still off in CI. The fakes are allowed to use simulator metadata. That is documented so nobody confuses them with a model.

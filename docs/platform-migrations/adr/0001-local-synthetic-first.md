# ADR 0001 — Local and synthetic first

- Status: accepted
- Date: 2026-10-17

## Context

A migration playbook is easy to over-claim. Connecting it to a live platform on day one would require credentials, client schemas, and a network, and CI would become a paid integration test.

## Decision

All runnable behavior uses synthetic files committed in this repo or generated from a seed. Configuration is environment variables. The default provider is `fake`. Tests and evals do not open sockets.

## Consequences

The demo is reproducible and costs nothing. It does not prove a client's platform. Real connectors stay behind a disabled port (ADR 0003).

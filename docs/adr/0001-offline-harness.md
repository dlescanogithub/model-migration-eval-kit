# ADR 0001: Offline harness, human gate

- Status: accepted for this repo
- Date: 2026-10-17

## Context

The question is whether a new model may replace an old one for ticket triage. A portfolio repo that calls a vendor in CI would spend money and could leak a prompt. A repo that applies a GO by itself would pretend to be production.

## Decision

Default providers are local fakes or cassettes. The live adapter is off unless `MIGRATION_EVAL_ENABLE_LIVE=1`. CI does not set that variable. A GO recommendation is written into a draft ADR. Nothing in the process routes a ticket.

## Consequences

Results are about the harness and the scripted profiles. They are not a leaderboard of published models. A later phase can opt into a live endpoint outside CI, with a human holding the key.

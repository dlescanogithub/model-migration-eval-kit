# Scope

## In scope now

- A synthetic golden set of 63 Casa Brisa tickets (28 happy, 21 edge, 14 adversarial).
- Invariant scoring, not exact text.
- Providers: `fake-old`, `fake-new`, `fake-new-degraded`, `fake-new-close`, `fake-new-flat`, cassette replay, and a chat-completions HTTP adapter that stays off unless `LIVE_MODE=1`. That adapter is `python -m migration_eval compare-live`. It is not used in CI. No live result is recorded in this repo.
- Comparison report (JSON and Markdown), paired test, bootstrap interval, go/no-go/need-human.
- A draft ADR filled from the report.
- A synthetic canary with a rollback decision and a JSONL audit.
- A deprecation calendar checked against an injected date.
- CI that runs lint, types, tests, the eval gate, a forced red regression, and a secret scan. CI does not call a vendor.

## Phases

| Phase | What | Status |
| --- | --- | --- |
| 0. Freeze the task and the rules | Category, priority, queue, allowed tool | Done for the fictional task |
| 1. Offline compare | Golden set, fakes or cassettes, report | Done |
| 2. Human reads the report | ADR draft, stakeholder note | Template only. No person has signed it |
| 3. Synthetic canary rehearsal | Stratified cohort, rollback audit | Done as a simulator |
| 4. Shadow on real traffic | Mirror, no customer effect | Design only |
| 5. Live canary | Real split, real rollback switch | Design only |
| 6. Decommission | Remove the old model id after a human sign-off | Calendar checklist only |

## Assumptions

- The shop, the tickets, the prices, and the cutoff date are fictional or [EST].
- Fake providers may read simulator metadata (`variant`). Live prompts do not include it.
- Quality of the bundled fakes is a pure function of provider and ticket. Seeds move simulated latency only.
- "Today" is an argument. The calendar does not read the clock, so tests stay stable.

## Out of scope

- Real customer data, and real prices scraped from a vendor.
- Production routing, paging, identity, or a legal review of a contract.
- Training or fine-tuning.
- Exact tool-call trajectories as the pass condition.
- Fees. This repo does not quote a service price.

## Exit criteria for this repo

- `pytest` passes with coverage at least 80%.
- `python -m migration_eval eval --provider fake-old` exits 0.
- `python -m migration_eval eval-regression` exits non-zero and the report decision is NO_GO.
- Default commands make no network call to a model vendor.
- The example report in `docs/` matches a fresh run of the documented command.

## Exit criteria before a real client (not met here)

- Labels written by people who do not maintain the provider.
- A written owner for GO.
- A rollback switch that has been exercised on a non-production route.
- Prices taken from a public page with URL and date, or marked [EST] in the decision record.
- Contract and versioning risks reviewed by whoever signs the vendor paper. This repo only lists that risk.

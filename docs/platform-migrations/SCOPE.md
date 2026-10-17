# Scope

## Phases and exit criteria

| Phase | In this repo | Exit criterion |
| --- | --- | --- |
| Discover | Questions and the way answers change design | Sponsor, boundary, open questions written down |
| Inventory | Scanner and synthetic generator | `scan` ok, owners and sensitivity set |
| Target design | Decision-record template, registry semantics in the simulator | A decision record exists. No live catalog is configured |
| Parity | Schema, row count, aggregates, PSI, KS | `PASS`, or `NEED_HUMAN` with an approver |
| Cutover | Waves, gate, registry copy, rollback log, report | Complete plan, gate `READY` or approved exception, rollback drill on the simulator |
| Decommission | Checklist and runbook only | Legacy schedule owner accepts a date. The tool does not disable a scheduler |

## Assumptions

- The manifest you feed the scanner is the scope. Anything absent is out of the wave.
- `effort` is a relative weight supplied by the manifest.
- One Staging version and one Production version per model name match the synthetic decision DR-001.
- Default parity tolerances are exact for row count and aggregates (`0.0`). Widen them in a policy object when discovery says so.
- PSI watch `0.10` and fail `0.25`, KS watch `0.10` and fail `0.20`, are local defaults. They are not a regulatory standard.
- Providers default to `fake`. Cassettes replay JSON. `real` is disabled.

## Out of scope

- A connector to any commercial or open-source platform.
- Copying files or tables between stores.
- Performance benchmarks on a real cluster.
- Row-level (key-aligned) diffs.
- Training models, computing business metrics such as AUC, or serving predictions.
- Feature-store consolidation as a runnable workflow.
- Turning off schedules, paging humans, or sending the communication plan.
- Loading a `.env` file. Configuration is the process environment.
- Fees, rate cards, or staffing proposals. There are no prices in this repo.

## Exit criteria for the repository itself

The repo is fit to show when CI runs lint, types, tests with coverage at or above 80%, the invariant eval, the secret scan, and a forced regression that exits non-zero because the broken fixture is `FAIL`.

## Fees

No engagement fees are stated. A client conversation starts from discovery, not from a number in this file.

# Metrics

These are the success signals for a migration rehearsal. A number produced by a command on the synthetic fixtures is a measurement of this repo. A number about a client's estate is not available here.

| Metric | Definition | Where it comes from | Fixture reading |
| --- | --- | --- | --- |
| Inventory coverage | 1 when `scan` returns ok, else 0 | `python -m migration_eval platform-migrations scan` | The Aerolito manifest is the covered set. It is not a percentage of a real estate |
| Asset counts | Datasets, jobs, models | Scan summary | 4 datasets, 4 jobs, 1 model on `src/migration_eval/platform_migrations/data/examples/aerolito_manifest.yaml`. Seeded estate defaults are 60 / 25 / 6; seed 11 on 2026-10-17 scanned as that size |
| Cycle count | 1 when the plan is cyclic, else 0 | `plan` | 0 on the example. 1 on the two-node cyclic fixture and on the seeded estate (one cycle path is reported; blocked nodes include both injected cycles) |
| Wave count | Number of topological waves | `plan` | 6 on the example. 9 on the seeded estate with seed 11 (2026-10-17), with 24 nodes blocked |
| Critical-path effort | Sum of `effort` on the longest path | `plan` | 14 on the example |
| Parity verdict | PASS, FAIL, or NEED_HUMAN | `parity` | PASS on the identical tables, FAIL on `src/migration_eval/platform_migrations/data/evals/fixtures/broken_parity.json` |
| Gate verdict | READY, NOT_READY, or NEED_HUMAN | `gate` | READY on `src/migration_eval/platform_migrations/data/examples/aerolito_gate.yaml` |
| Idempotent rerun | Models touched on the second `migrate` | Registry simulator | 0 when the target already matches |
| Rollback drill | Registry document returns to the pre-image | `rollback` | An empty target returns to 0 versions. A target that already held `local_hold` returns to that same document after rollback |
| Secret findings | Count from the heuristic scan | `python -m migration_eval secretscan .` | 0 is the expected repo result |
| Eval invariants | Each named check passed | `python -m migration_eval platform-migrations eval` | All must pass in CI |
| Local tool latency | Wall time of one local command | README Results, 2026-10-17 | demo 0.080s, pytest 1.243s, eval 0.085s. Not a percentile |
| Dual-run cost | Formula output | `dual_run_cost` | Simulated 280 for the illustrative inputs. Not a metric of a cloud account |
| Business AUC or revenue | Not computed | — | Out of scope |

The asset counts, wave count, effort, and verdicts above are the fixture contract locked by tests. The README records the command, the date, and the tool version that reproduced them.

## What would count as success on a real wave

- Inventory coverage stays 1 as new assets are added, or the new assets are written into the out-of-scope list.
- Cycle count is 0 or every blocked node has an accepted decision record.
- Parity is PASS or an approved NEED_HUMAN before the consumer flag moves.
- The rollback drill has been done on a non-production registry, not only on this simulator.
- Hypercare has a named owner and a calendar end.

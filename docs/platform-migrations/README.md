# Platform migrations

Second axis of this repository: after a model swap, a platform move. The model chapter compares two providers on the same tickets. This chapter rehearses moving jobs, datasets, and a model registry from one platform to another.

The shop in the examples is **Aerolito Data**. It is fictional. Every manifest, table, and registry file is synthetic. Nothing here is a client estate.

The runnable code is `migration_eval.platform_migrations`. The command is:

```text
python -m migration_eval platform-migrations <subcommand>
```

Default `--root` is the fixture directory inside the package (`src/migration_eval/platform_migrations/data`). `eval`, `eval-regression`, and `demo` need no path.

## Flow

Inventory, then waves, then parity, then cutover, then rollback.

1. **Inventory.** `scan` reads a YAML or JSON manifest and refuses a duplicate id or a dangling reference.
2. **Waves.** `plan` builds the lineage graph and emits topological waves. A cycle is reported and the plan exits 1. It does not invent an order.
3. **Parity.** `parity` compares schema, row count, aggregates, PSI, and KS. The verdict is `PASS`, `FAIL`, or `NEED_HUMAN`.
4. **Cutover.** `gate` reads a checklist. `READY` requires the required controls, parity that is not `FAIL`, a rollback plan, and no open high risk. `NEED_HUMAN` exits 3.
5. **Rollback.** `migrate` copies registry versions, stages, and aliases into an in-memory target. The source file is unchanged. A second run touches nothing. Rollback restores the previous target snapshot. The drill is the invariant `rollback_restores_registry_state`.

The phase write-up, with exit criteria, is [playbook/phases.md](playbook/phases.md). The night-of sequence is [RUNBOOK.md](RUNBOOK.md).

```text
python -m migration_eval platform-migrations scan src/migration_eval/platform_migrations/data/examples/aerolito_manifest.yaml
python -m migration_eval platform-migrations plan src/migration_eval/platform_migrations/data/examples/aerolito_manifest.yaml
python -m migration_eval platform-migrations parity src/migration_eval/platform_migrations/data/examples/parity_legacy.json src/migration_eval/platform_migrations/data/examples/parity_target.json
python -m migration_eval platform-migrations gate src/migration_eval/platform_migrations/data/examples/aerolito_gate.yaml
python -m migration_eval platform-migrations migrate src/migration_eval/platform_migrations/data/examples/aerolito_registry.json
python -m migration_eval platform-migrations demo --out out/platform-demo
python -m migration_eval platform-migrations eval
python -m migration_eval platform-migrations eval-regression
```

`eval-regression` is supposed to exit 1. The broken table is `FAIL`, and the payload sets `gate_went_red` to true. Exit 0 would mean the broken fixture was accepted.

Measured on 2026-10-17, package 0.2.0, Python 3.12.3:

| Command | Result |
| --- | --- |
| `python -m pytest` | 71 passed, coverage 87.93% (floor 80%). One sample: 1.92s |
| `python -m migration_eval platform-migrations eval` | exit 0, 12/12. One sample: 0.109s |
| `python -m migration_eval platform-migrations eval-regression` | exit 1, verdict FAIL, `gate_went_red` true. One sample: 0.100s |
| `python -m migration_eval platform-migrations demo` | exit 0. 4 datasets, 4 jobs, 1 model, 6 waves, critical path effort 14, parity PASS, gate READY, second migrate touches 0, simulated dual-run 280. One sample: 0.107s |
| `python -m migration_eval platform-migrations plan` on `aerolito_manifest.yaml` | exit 0, complete, not cyclic, 6 waves, critical path effort 14 |

The model axis, same date and package, `python -m migration_eval eval --provider fake-old --runs 5 --today 2026-10-17`: exit 0, `pass_rate=1.0000`, `harmful=0`, `cost_per_run=0.069515`, `p95_ms=459.0`. `python -m migration_eval eval-regression --runs 5 --today 2026-10-17` exits 1 with decision NO_GO. Those model figures match the committed report. The simulated dual-run 280 is arithmetic on [EST] inputs, not a price.

## Invariants

`eval` runs twelve checks. They judge effects, not a scripted call order.

| Invariant | What it holds |
| --- | --- |
| `no_harmful_effect` | The source registry export is unchanged and the target does not lose versions |
| `cost_within_cap` | The simulated dual-run product stays under the local cap (1000) |
| `no_unapproved_external_action` | `MLMIG_PROVIDER=real` raises before any socket |
| `cycles_blocked` | A cycle is not planned as a complete wave list |
| `idempotent_migration` | The second migrate touches nothing |
| `fail_never_reported_as_pass` | The broken parity fixture is not `PASS` |
| `rollback_restores_target` | Rollback puts the target registry back |
| `cassette_replays_without_network` | Cassette replay does not open a socket |
| `waves_respect_dependencies` | Every node is scheduled after its dependencies |
| `cycles_reported` | The seeded estate names the cycle instead of hiding it |
| `parity_failure_blocks_cutover` | Parity `FAIL` keeps the gate off `READY` |
| `rollback_restores_registry_state` | After rollback, the registry object matches the snapshot |

## Business illustration

The money sketch in [BUSINESS_CASE.md](BUSINESS_CASE.md) is **negative**, on fictional Aerolito data. With the plugged [EST] day rate of 500 and the simulated dual-run of 280, the first-year illustration is `4000 - 4280 = -280` before any avoided incident is priced. That sign is the point of the example. It is not a client invoice.

Risks: [RISKS.md](RISKS.md). Cost formula and the local timings: [COST.md](COST.md).

## Where to read next

| Doc | What it is |
| --- | --- |
| [HOW_IT_WORKS.md](HOW_IT_WORKS.md) | The same flow, in rioplatense Spanish |
| [playbook/README.md](playbook/README.md) | Phases, checklists, RACI, communication |
| [RUNBOOK.md](RUNBOOK.md) | Local operate sequence and rollback limits |
| [RISKS.md](RISKS.md) | R1–R10, owners are roles |
| [BUSINESS_CASE.md](BUSINESS_CASE.md) | Negative illustration on fictional inputs |
| [DISCOVERY.md](DISCOVERY.md) | Ten questions before a target design |
| [SCOPE.md](SCOPE.md) | What is implemented and what stays design-only |
| [architecture.md](architecture.md) | Module map. Shared utilities are not copied |
| [adr/](adr/) | Local-synthetic, invariants, ports, parity verdicts, idempotent registry |

Shared utilities stay one copy in this repository: `secretscan`, `evalkit`, `logging_setup`, `retries`, and `trace`. The digest of `secretscan.py` is in [../PROVENANCE.md](../PROVENANCE.md).

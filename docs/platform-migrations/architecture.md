# Architecture

```mermaid
flowchart LR
  manifest["Synthetic manifest YAML or JSON"] --> scanner["Inventory scanner"]
  scanner --> graph["Lineage graph"]
  graph --> planner["Wave planner"]
  legacy["Legacy table"] --> parity["Parity checker"]
  target["Target table"] --> parity
  sourceReg["Registry export"] --> migrate["Migration simulator"]
  migrate --> rollback["Rollback snapshots"]
  checklist["Checklist YAML"] --> gate["Cutover gate"]
  parity --> gate
  planner --> report["Status report"]
  gate --> report
  cassette["Cassette JSON"] --> evals["Invariant evals"]
  fake["Fake provider"] --> evals
```

## Modules

| Module | Role |
| --- | --- |
| `migration_eval.platform_migrations.inventory` | Manifest types, validation, normalisation, small-chain generator, and the larger seeded estate |
| `migration_eval.platform_migrations.lineage` | Edges, cycle detection, topological waves, critical path, blast radius |
| `migration_eval.platform_migrations.parity` | Schema, row count, aggregates, PSI, KS, verdict |
| `migration_eval.platform_migrations.registry` | Versions, stages, aliases, idempotent migrate, rollback |
| `migration_eval.platform_migrations.cutover` | Policy over a checklist |
| `migration_eval.platform_migrations.report` | Markdown and HTML |
| `migration_eval.platform_migrations.adapters` | Factory. `real` raises `ProviderDisabled` |
| `migration_eval.platform_migrations.evals` | Migration invariants and the forced-regression fixture |
| `migration_eval.platform_migrations.cost` | Illustrative dual-run formula |
| `migration_eval.evalkit` | Shared package. Operation cassette, fake fetch, and the invariant runner used here. Ticket checks for the model axis live in the same package |
| `migration_eval.retries` | Shared retry helper. The scanner uses it for a transient read error |
| `migration_eval.trace` | Shared JSONL audit |
| `migration_eval.logging_setup` | Shared structured log |
| `migration_eval.secretscan` | Shared secret scanner. One file, digest in [../PROVENANCE.md](../PROVENANCE.md) |

## Boundaries

- Inputs are files and environment variables.
- Outputs are stdout JSON, a report directory, and a trace file.
- No socket is part of the design. Tests monkeypatch `socket.socket.connect` and run `eval` and `demo`.
- YAML uses `yaml.safe_load`. JSON uses the standard library.

## Design-only ports

`build_provider` accepts `fake` and `cassette`. `MLMIG_PROVIDER=real` and `MLMIG_CASSETTE_RECORD=1` raise before any connection. A future adapter would implement `fetch(operation, request)` and would stay out of CI. See [adr/0003-vendor-neutral-ports.md](adr/0003-vendor-neutral-ports.md).

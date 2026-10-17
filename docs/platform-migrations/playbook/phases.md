# Phases

Each phase has an exit criterion. The local tools cover the checks named below. Connectors, data copy, and cluster benchmarks stay design-only (see [SCOPE.md](../SCOPE.md)).

## 1. Discover

Interview owners before drawing a target. Use the ten questions in [DISCOVERY.md](../DISCOVERY.md). Write down SLAs, sensitivity, downtime tolerance, and who can approve a cutover.

Exit: a named sponsor, a scope boundary, and a list of systems in play. Unknown owners are an open item, not a guess.

## 2. Inventory

Collect a legacy manifest: jobs, models, datasets, schedules, owners, dependencies. Validate it.

```bash
python -m migration_eval platform-migrations scan src/migration_eval/platform_migrations/data/examples/aerolito_manifest.yaml
```

Exit: `scan` reports `ok: true`, every asset has an owner, and sensitivity is set on every dataset. The scanner is the check. A spreadsheet that never passes `scan` is not an inventory.

## 3. Target design

Choose the lakehouse table format, the experiment tracker, and the model-registry semantics (versions, stages, aliases). Record the choice with [decisions.md](decisions.md). This repo does not connect to a catalog. The design is a document plus the registry simulator's stage and alias rules.

Vendor-neutral references, accessed 2026-10-17:

- Lakehouse table patterns are documented by projects such as [Apache Iceberg](https://iceberg.apache.org/docs/latest/) and [Delta Lake](https://docs.delta.io/latest/index.html).
- An experiment tracker with a registry of versions, stages, and aliases is documented by the [MLflow Model Registry](https://mlflow.org/docs/latest/ml/model-registry/).

Exit: a decision record, a mapping from each legacy asset to a target home, and an explicit list of assets that will not move.

## 4. Parity

Compare legacy and target outputs for each in-scope model or dataset. This repo compares schema, row count, numeric aggregates, PSI, and KS. It does not join rows on a key.

```bash
python -m migration_eval platform-migrations parity src/migration_eval/platform_migrations/data/examples/parity_legacy.json src/migration_eval/platform_migrations/data/examples/parity_target.json
```

Exit: verdict `PASS`, or `NEED_HUMAN` with a named approver on the cutover gate. `FAIL` blocks the wave.

## 5. Cutover

Plan waves from lineage, confirm the gate, then move one wave at a time. Keep the legacy jobs running until the wave's hypercare window ends (dual-run). The registry simulator shows an idempotent copy and a rollback log. It does not publish a model.

```bash
python -m migration_eval platform-migrations plan src/migration_eval/platform_migrations/data/examples/aerolito_manifest.yaml
python -m migration_eval platform-migrations gate src/migration_eval/platform_migrations/data/examples/aerolito_gate.yaml
python -m migration_eval platform-migrations migrate src/migration_eval/platform_migrations/data/examples/aerolito_registry.json
```

Exit: the plan is complete (no blocked cycle), the gate is `READY` or a recorded human approval, and a rollback drill restores the target registry snapshot.

## 6. Decommission

After hypercare, disable legacy schedules for the wave, keep the rollback window that discovery agreed, then remove credentials and documents that only the legacy platform needed.

Exit: the legacy schedule is off, consumers read the target, and the rollback window has a calendar date. This repo does not turn off a scheduler. The exit is a checklist item, design-only for the actual switch.

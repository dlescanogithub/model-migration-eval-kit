# Playbook

This folder is the migration playbook for the platform chapter. The code in `src/migration_eval/platform_migrations` runs the parts that can be checked on synthetic files. The playbook is the sequence a team follows. It is written for a fictional analytics group, Aerolito Data, so the examples stay concrete without describing a real client.

| Document | What it is for |
| --- | --- |
| [phases.md](phases.md) | Discover, inventory, target design, parity, cutover, decommission |
| [checklists.md](checklists.md) | Inventory, data, features, models, pipelines, governance, security, cutover/rollback, hypercare |
| [decisions.md](decisions.md) | Decision-record template and one filled synthetic example |
| [communication.md](communication.md) | Who hears what, and when |
| [raci.md](raci.md) | RACI template with fictional Aerolito roles |

The runnable checklist gate reads a YAML file shaped like `src/migration_eval/platform_migrations/data/examples/aerolito_gate.yaml`. The control ids in [checklists.md](checklists.md) match that file.

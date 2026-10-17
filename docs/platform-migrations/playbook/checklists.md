# Checklists

Copy a section into the gate file when a wave is ready for review. `required: true` items block `READY`. A waiver needs an approver string. Status values are `pass`, `fail`, `pending`, and `waived`.

## Inventory

- [ ] `inventory.complete` — manifest scans with zero errors (`python -m migration_eval platform-migrations scan`).
- [ ] `owners.assigned` — every asset owner is one of the manifest's teams.
- [ ] IDs are stable and unique.
- [ ] Schedules are filled for jobs that will keep running during dual-run.

## Data

- [ ] `sensitivity.classified` — each dataset is `public`, `internal`, or `confidential`.
- [ ] Row-count expectations are written down, with the tolerance the parity policy will use.
- [ ] Retention and a rollback window are named. The tool does not delete data.

## Features

- [ ] Feature definitions have an owner team.
- [ ] Upstream datasets are listed. The wave planner treats those edges as "migrate first".
- [ ] Feature-store consolidation across products is design-only in this repo. Do not mark it implemented.

## Models

- [ ] Each model has a framework, a stage, a version, and a `registry_name` when it will be copied.
- [ ] Training or scoring jobs are listed.
- [ ] The registry export used by `migrate` matches the versions you intend to copy.

## Pipelines

- [ ] `lineage.reviewed` — `plan` is complete, or a cycle is accepted in writing and those nodes stay blocked.
- [ ] Blast radius of the wave's root datasets has been read by the owning team.
- [ ] Critical path effort is understood as a relative weight, not a calendar estimate from this repo.

## Governance

- [ ] Sponsor and approver are named in the RACI.
- [ ] Open high risks are zero, or the gate stays `NOT_READY`.
- [ ] Decision records exist for table format and registry semantics.

## Security

- [ ] `security.reviewed` — no live credentials in the manifest, the repo, or CI.
- [ ] `python -m migration_eval secretscan .` is clean for the repo you are about to commit.
- [ ] The real-provider setting stays off. `MLMIG_PROVIDER=real` aborts.

## Cutover and rollback

- [ ] `parity.accepted` — parity is `PASS`, or `NEED_HUMAN` with `parity_approved_by` set.
- [ ] `rollback.documented` — rollback steps in [RUNBOOK.md](../RUNBOOK.md) match the wave.
- [ ] `rollback_plan_present` is true on the gate file.
- [ ] A drill has restored a registry snapshot with `rollback` on a non-production copy. The simulator can do this locally. A real registry drill is design-only.

## Hypercare

- [ ] `hypercare.named` — a team owns the first days after cutover.
- [ ] Dual-run length is an explicit number of days. Cost during that window is an estimate, labelled as such in [COST.md](../COST.md).
- [ ] Consumers to call if scores look wrong are listed in the communication plan.

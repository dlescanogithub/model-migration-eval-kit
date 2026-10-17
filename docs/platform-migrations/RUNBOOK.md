# Runbook

Operate the local tools. A real cutover night adds the client's change process on top of this sequence. This file does not page anyone.

## Roles

| Role | Synthetic stand-in | Owns |
| --- | --- | --- |
| Sponsor | Aerolito sponsor (fictional) | Accepts the gate |
| Platform | team-platform | Plan, registry drill, report |
| Data | team-data | Manifest truth |
| Scoring | team-scoring | Parity evidence |
| Hypercare | Named on the checklist | The first days after a wave |

## Before cutover night

1. `python -m migration_eval platform-migrations scan <manifest>` returns ok.
2. `python -m migration_eval platform-migrations plan <manifest>` exits 0. Read blocked nodes if it exits 1. Do not proceed on a blocked wave.
3. `python -m migration_eval platform-migrations parity <legacy> <target>` is PASS, or NEED_HUMAN with the approver filled on the gate file.
4. Registry export matches the versions you mean to copy. Run `python -m migration_eval platform-migrations migrate <export>` on a scratch target (the command uses an empty in-memory target). Confirm `second_run_touched` is 0.
5. Rollback drill: the eval `rollback_restores_target` is the local drill. Repeat it against a non-production registry when a real one exists. That step is design-only here.
6. `python -m migration_eval platform-migrations gate <checklist>` is READY, or you have a written reason to stop.

## Cutover night

1. Announce the wave using [playbook/communication.md](playbook/communication.md). Include the blast radius of the root datasets.
2. Keep legacy schedules running (dual-run). This tool will not disable them.
3. Apply the wave in the target environment using the client's pipeline tooling. **Design-only.** This repo stops at the plan and the gate.
4. Re-run parity on the outputs the target actually wrote. A FAIL stops the wave. Do not flip consumer traffic.
5. If parity is PASS, the sponsor accepts the gate again with the new evidence path written into `evidence`.
6. Consumer cutover is a flag owned by the application team. **Design-only.**

## Monitor

During hypercare, re-run parity on the agreed sample and read the gate. Watch for:

- Verdict moving from PASS to FAIL or NEED_HUMAN.
- A new cycle after someone edits the manifest.
- `secretscan` findings if new files were added.
- Two scores being served. That is an application incident, not a scanner incident.

The tool's own log line is JSON on stderr (`event`, `level`, `message`). The demo also appends `trace.jsonl`.

## Incidents

| Symptom | What you do |
| --- | --- |
| Parity FAIL | Stop the wave. Leave legacy in place. Open the finding list. Scoring owns the analysis |
| Gate NOT_READY | Do not announce completion. Fix the blocking reason or record a waiver with an approver |
| Cycle appeared | Plan exits 1. Platform and data decide whether the edge is real |
| Registry drill diverged | Call `rollback` on the simulator snapshot. On a real registry, follow that product's restore. Do not improvise deletes |
| Suspected secret in a file | Rotate the credential outside this repo. Delete the file. Re-run `python -m migration_eval secretscan .` |

## Rollback

Registry simulator:

- `migrate` returns snapshots taken before each model was changed.
- Applying them in reverse restores stages, aliases, and version presence for those models.
- The source export is never modified.
- Target-only versions are not deleted by migrate. A singleton stage promotion can archive the version that held Staging or Production. The snapshot puts that stage back.

Tables and files are not rolled back by this tool. The data owner restores a table snapshot with the lakehouse tools chosen in the decision record. References, accessed 2026-10-17: [Apache Iceberg](https://iceberg.apache.org/docs/latest/) (version rollback described in the project docs) and [Delta Lake](https://docs.delta.io/latest/index.html) (time travel). Picking either is a decision record, not a default of this repo.

## Handoff

Send the status report (`report.md`), the plan JSON, the parity verdict, the gate verdict, and the open risks. The next owner is the hypercare role until the rollback window date, then team-platform for decommission.

## Decommission

Only after hypercare exit and the retention window from discovery. Disabling schedules is design-only. Record the date in the decision log.

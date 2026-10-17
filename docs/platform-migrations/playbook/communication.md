# Communication plan

Fill the names with teams. The Aerolito column is a fictional illustration.

| When | Message | Aerolito illustration | Channel | Owner |
| --- | --- | --- | --- | --- |
| Discovery opens | Scope, systems in play, questions still open | "We are listing scheduled jobs and the churn scorer. No cutover date yet." | Sponsor meeting | team-platform |
| Inventory baseline | Manifest location, scan result, missing owners | Link the manifest and the `scan` JSON | Team channel | team-data |
| Wave plan published | Wave order, blast radius, what is blocked by a cycle | Paste the `plan` JSON | Team channel | team-platform |
| Parity result | PASS, FAIL, or NEED_HUMAN, with the finding lines | Identical synthetic tables are PASS | Scoring and features | team-scoring |
| Cutover approval ask | Gate verdict and the rollback drill result | Ask for READY only after the local gate is READY | Sponsor | team-platform |
| Cutover start | Which wave, which legacy jobs stay on, who is on point | One wave, dual-run still on | Incident channel | team-platform |
| Hypercare daily | Parity spot checks, open incidents, rollback yes/no | Short note, even when nothing moved | Incident channel | hypercare owner |
| Decommission | Legacy schedules that will stop, date of the rollback window end | Only after hypercare exit | Sponsor | team-platform |

Rules:

- A FAIL parity result goes to the owning team the same day. It does not wait for a weekly status mail.
- Nobody announces "migrated" while the gate is `NOT_READY`.
- This repository sends no messages. The plan is a script for humans.

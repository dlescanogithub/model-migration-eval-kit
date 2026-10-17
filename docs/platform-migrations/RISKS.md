# Risks

Owners are roles. On the synthetic Aerolito exercise the role maps to a fictional team. Probability and impact are qualitative: low, medium, high.

| ID | Risk | Probability | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- | --- |
| R1 | Manifest misses jobs, so the wave plan looks complete and is not | High | High | Discovery question 1. Keep an explicit out-of-scope list. Do not treat `scan` ok as full estate coverage | team-data |
| R2 | A cycle is "fixed" by deleting a real dependency | Medium | High | Planner leaves the cycle blocked. A human accepts an edge change in a decision record | team-platform |
| R3 | Parity `PASS` on aggregates hides a row-level swap | Medium | High | Documented limit. Add a key-aligned check before a real cutover. `NEED_HUMAN` when columns appear or types are thin | team-scoring |
| R4 | PSI/KS defaults are used as if they were a policy from risk management | Medium | Medium | Defaults are local. Discovery sets the bands. The README says they are not a standard | team-scoring |
| R5 | Registry migration archives a target Production version via the singleton rule | Medium | High | Rollback snapshot restores it. Drill on the simulator. Real registries stay design-only until DR-001 is re-decided | team-platform |
| R6 | Dual-run leaves two live scores and no one owns the flag | Medium | High | Communication plan and RACI. Gate does not flip the flag. Hypercare owner is required on the checklist | sponsor |
| R7 | A secret lands in a fixture or a log | Low | High | `secretscan` in CI, `.env` gitignored, no dotenv loader, real provider cannot be constructed | team-platform |
| R8 | `READY` on synthetic data is mistaken for approval to cut over a client | Medium | High | Report text says it does not authorize a cutover. Use-case table marks design-only work | sponsor |
| R9 | Cost placeholder `rate_per_hour=10` is copied into a budget | Medium | Medium | Labelled simulated / [EST]. COST.md forbids treating it as a price | sponsor |
| R10 | Rollback of tables is assumed because registry rollback worked | Medium | High | Runbook separates registry snapshot from table rollback. Table restore is design-only | team-data |

## Not covered yet

- Threat model of a multi-tenant catalog.
- Identity, SSO, and row-level permissions on the target.
- Backfill cost for historical partitions.
- Model-quality monitoring after hypercare.
- Legal retention schedules beyond a free-text window in discovery.

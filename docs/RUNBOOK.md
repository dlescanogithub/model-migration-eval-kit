# Runbook

This system has no production process. The "operate" steps are local commands. Rollback of a real router is not implemented; the canary command only decides ROLLBACK or HOLD on synthetic rows.

## Operate

From a checkout, with dev extras installed:

```text
python -m migration_eval eval --provider fake-old --runs 5 --today 2026-10-17
python -m migration_eval compare --old fake-old --new fake-new --runs 10 --today 2026-10-17 --out out/demo
python -m migration_eval canary --old fake-old --new fake-new --today 2026-10-17 --out out/canary-audit.jsonl
python -m migration_eval deprecation-check --today 2026-10-17
```

`make eval`, `make demo` match the first two. Logs are JSON lines on stderr.

Exit codes:

| Command | 0 | Non-zero |
| --- | --- | --- |
| eval | Reference provider cleared the gate | Gate failed |
| compare | Report written. Read the decision inside the file. Compare itself exits 0 even on NO_GO | Bad arguments or missing config |
| eval-regression | The degraded model was not NO_GO. That means the gate is broken | NO_GO, which is the expected red result (exit 1) |
| canary | Audit written. Read decision=HOLD or decision=ROLLBACK | Bad arguments |
| deprecation-check | No required item overdue | A required item is overdue relative to --today |
| secretscan | No finding | At least one finding |

## Monitor

There is no dashboard. Watch:

- The decision line and the slice table in the report.
- `harmful` counts. Anything above zero on a candidate is a stop.
- The canary audit's last JSON line (`event=decision`).
- Calendar lines marked `due_soon` or `overdue`.

## Incidents

| Symptom | What to do |
| --- | --- |
| eval-regression exits 0 | Do not trust the gate. The degraded profile must be NO_GO. Fix the check before reading any GO |
| compare says NO_GO | Keep the old provider. Do not start a canary plan from that report |
| canary says ROLLBACK | The synthetic cohort missed the bar. Do not describe this as a live rollback; there was nothing live to roll back |
| secretscan fails | Remove the secret, rotate it if it was real, and do not push it |
| Someone set LIVE_MODE=1 | Turn it off. Confirm CI does not have the variable. Treat any ticket text that was sent as exposed. Cassettes under `var/` may contain ticket text; that directory is gitignored |

## Ownership

| Piece | Role |
| --- | --- |
| Golden set and thresholds | Harness owner |
| Priority rules | Support lead |
| GO signature | A named human. The tool does not sign |
| Cutoff date | Finance partner |
| Real traffic switch, if one ever exists | Platform. Not this repo |

## Rollback

1. Read `out/canary-audit.jsonl` (or the committed example) and confirm the decision line.
2. If a real flag existed, the human who owns it would point traffic back at the old model. This repository has no flag and no router.
3. Keep the audit file with the report. Do not delete it to make the dashboard look calm.
4. Re-run compare before anyone proposes the new provider again.

## Handoff

Give the next person: this file, `docs/example-report.md`, `config/policy.yaml`, `config/deprecation_calendar.yaml`, and the command list above. Tell them the fakes are scripted and the prices are [EST]. Tell them GO is not approval.

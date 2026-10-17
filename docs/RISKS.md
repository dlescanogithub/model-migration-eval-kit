# Risks

Owners below are roles in the fictional exercise, not a staff list.

| Risk | Probability | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| New model looks cheaper and fails the edge slice | High in the scripted `fake-new` profile (measured drop 33.33 points on 2026-10-17) | Wrong queue on lost parcels, failed payments, complaints | Slice cap in `config/policy.yaml`; NO_GO blocks the recommendation | Support lead |
| Prompt injection in the ticket body is obeyed | High for `fake-new-degraded` (adversarial pass rate 0 in the measured 10-run compare) | Unapproved tool or echoed contact token | Adversarial slice may not regress; harmful-effect count; degraded profile is the red test in CI | Harness owner |
| Format drift breaks the parser | Low on `fake-new` (format-failure rate 0.0159, under the 0.05 cap, measured 2026-10-17) | Ticket not routed | Format-failure gate; schema check ignores unknown keys but rejects missing ones | Harness owner |
| Labels and the "good" fake share one function, so the report looks perfect while the rule is wrong | High if someone treats `fake-old` as a real baseline | False GO | Docs say so; a real rollout needs human labels. Not built | Support lead |
| Simulated latency or [EST] prices get quoted as a vendor result | Medium if the report is forwarded without the labels | Bad commercial decision | Report text says simulated and [EST]; COST.md repeats it | Deployment strategist |
| Live adapter turned on in CI or with a real ticket export | Low by default (flag off, CI does not set it) | Data leaves the machine; possible bill | Flag default 0; cassette has no network fallback; secret scan | Harness owner |
| Cassette miss silently calls a vendor | Low: a miss raises `CassetteMiss` | Surprise bill or data leak | Unit test locks the raise | Harness owner |
| Vendor contract / versioning: model id retired on a date the team did not track | Medium in any real migration; here the date is fictional (2026-11-30 in the calendar) | Sudden outage of the old path | Calendar check with injected today; cutoff item is a reminder, not a legal review | Finance partner |
| Vendor changes the model behind a stable name | Not measured. Design-only | Silent quality shift after GO | Pin a version or snapshot id in the ADR; re-run the golden set on a schedule. Not automated here | Finance partner plus harness owner |
| Canary sample misses the bad slice | Mitigated in the simulator by taking the first tickets of each slice, which include an edge failure for `fake-new` (measured canary fail rate 0.3333, ROLLBACK) | False HOLD | Stratified cohort; still a simulator, not live traffic | Support lead |
| Rollback exists only on paper | Certain for production: there is no live switch | A bad GO cannot be undone by this repo | RUNBOOK says the human holds the real switch; this repo only writes an audit | Platform |
| Secret committed | Low if the scan and review hold | Key in git history | `secretscan` in CI; `.env` gitignored | Harness owner |
| Thresholds gamed (cap raised until the report is green) | Medium | Meaningless GO | Threshold changes belong in an ADR, not in a quiet edit the day of the decision | Deployment strategist |
| `old` and `new` are the same model, and the report is read as a migration | High if that GO or NO_GO is forwarded | Sampling noise looks like a model change | On 2026-10-17, `compare-live --runs 1`, 29/63 raw responses were identical across sides; the rest differed by model variation. McNemar and GO/NO_GO on that self-compare are not evidence of anything | Harness owner |

Legal review of a vendor contract is not done here. The versioning row is the reminder to do it before any real cutoff.

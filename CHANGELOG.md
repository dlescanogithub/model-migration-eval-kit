# Changelog

## Unreleased

- The repository is in English. Walkthroughs, the Casa Brisa golden set, injection text, rationales, the contract-mismatch warning, and the demo script and subtitles are English. The Spanish subtitle file was removed; the English subtitle file remains. The video file was not edited. Interview framing was removed from the walkthroughs. They are written for engineers and buyers.
- Offline quality figures were confirmed unchanged on 2026-10-23, package 0.2.3, Python 3.12.3, after the tickets were translated to English. Simulated cost was re-measured the same day because token counts follow character length: fake-old 0.067275 USD, fake-new 0.014511 USD, savings ratio 0.7843, prices [EST]. The 2026-10-17 dollar figures in the narrated demo stay labeled as measured on the original Spanish ticket text.
- Live compare figures (priority 37/63, pass 55/63 and 56/63, real cost about US$0.053) stay the 2026-10-17 measurements on the original Spanish ticket text. They were not re-run.

## 0.2.3 - 2026-10-22

- Business value section in the README, and the synthetic value plan in [docs/BUSINESS_VALUE.md](docs/BUSINESS_VALUE.md). That plan is in English. Invented business assumptions are tagged **[SYN]**.
- README opening is a three-line Start here: what the offline check proves, the one-command demo, and the link to [docs/demo/](docs/demo/).
- README Tests section: **MEASURED** 2026-10-22, Python 3.12.3, `python -m pytest`, 85 passed, line coverage 91.82% (3,423 of 3,728 statements). The same run's combined statement and branch total was 88.62%.
- Narrated recording of a real offline run, with number trace, in [docs/demo/](docs/demo/).

## 0.2.2 - 2026-10-17

- The live prompt's priority lines are generated from `PRIORITY_RULES`, the same table `expected_priority` walks. A test checks that every rule line is in the prompt and that the grader uses that table.
- Reports count `priority_ok` separately from the overall pass rate. When a dimension depends on rules that are not in the prompt, the report says so and withholds the blended pass rate. That rate is not a live quality number.
- A cassette of representative raw responses checks the live contract: schema, category, queue, and one `route_ticket` can pass while priority fails, and that split is not harmful.
- Documented the 2026-10-17 self-compare, measured on the original Spanish ticket text: priority 37/63 (58.7%) because the rules were missing, contract 63/63, harmful 0/63. That priority figure is historical. The cost estimate ignores cached tokens (real US$0.053 versus an estimate of about US$0.100).
- A later `compare-live --runs 1` the same day, `grok-4.20-0309-non-reasoning` on both sides, measured on that same Spanish text, pass 55/63 old and 56/63 new, and priority_ok 56 and 57. It is a self-compare. 29/63 raw responses were identical. The gap is not evidence of improvement or regression. Real cost about US$0.053 per run; the repo estimate of about US$0.100 ignores cached tokens.

## 0.2.1 - 2026-10-17

- Live HTTP timeouts and connection errors retry with a capped backoff and jitter. A spent attempt counts against `MAX_LIVE_SPEND_USD`. When retries are exhausted the command exits 2 with a clear error and a partial report, without a traceback.
- The live prompt includes the category-to-queue table the grader uses, requires exactly one `route_ticket`, and shows the JSON schema plus an example.
- Contract mismatch (invalid JSON, invented queue, missing or wrong tool call) is reported apart from harmful effects (contact-token echo, obeyed injection, dangerous action). An invented queue is not harmful.
- A live compare whose pass rate is about zero on both sides because of contract mismatch warns: possible prompt/grader mismatch, not model quality.
- Documented: the cost formula ignores cached tokens and overestimates, and the same model on both sides of `compare-live` is a self-compare, not a migration. Live status stays "implemented, live verification still pending".

## 0.2.0 - 2026-10-17

- Platform migrations are the second axis: inventory, waves, parity, cutover, and registry rollback under `python -m migration_eval platform-migrations`, with docs in `docs/platform-migrations/`.
- Twelve platform invariants and a forced parity regression (exit 1, `gate_went_red` true) run beside the model evals.
- Secret scan, evalkit, logging, retries, and the JSON trace stay one copy. The operation cassette and the invariant runner live in `migration_eval.evalkit`.

## 0.1.1 - 2026-10-17

- The paired test now uses the ticket as the unit. Seed repeats collapse before McNemar and before the bootstrap, and n is reported. Extra repeats do not change the p-value or the intervals.
- Reports state that labels and the scripted providers share one spec, and that a fake-versus-fake NO_GO demonstrates the gate.
- Optional `compare-live` talks to a chat-completions HTTP endpoint only when `LIVE_MODE=1` and the price, spend cap, and credentials are set in the environment. Missing config exits before any request. Cassettes go to gitignored `var/`. No live result is recorded.
- The secret scanner covers the shared key shapes, and `secretscan --check-hash` checks the digest in `docs/PROVENANCE.md`.

## 0.1.0 - 2026-10-17

- Initial offline kit: synthetic Casa Brisa golden set, fake and cassette providers, comparison report, go/no-go policy, canary simulator, deprecation calendar, and a forced regression that exits non-zero.

# Cost

Default commands do not call a vendor. The dollar figures below are simulated token counts times the [EST] rates in `config/prices.yaml` (date on that file: 2026-10-17, source text: illustrative, invented for this exercise). Latency is simulated.

Measured 2026-10-17, package 0.2.2, Python 3.12.3. The same command on this package matches the committed report.

Platform-move cost (a different formula, still simulated) is in [platform-migrations/COST.md](platform-migrations/COST.md).

Command shape: `python -m migration_eval compare --old fake-old --new <name> --runs 10 --today 2026-10-17`

Token totals are for one pass (seed 0). They do not depend on the seed. Cost per run is the mean across the 10 runs; with stable tokens it matches the seed-0 cost.

| Scenario | Model / provider | Tokens or units (one pass, simulated) | Cost / run | p50 / p95 latency | Quality | Price date / source |
| --- | --- | --- | ---: | --- | --- | --- |
| Baseline | fake-old, simulated | 2182 input, 3907 output | 0.069515 USD | 440.0 / 459.0 ms, simulated | Pass rate 1.0000 | 2026-10-17, [EST] in config/prices.yaml |
| Cheaper, worse on edge | fake-new, simulated | 2182 input, 4244 output | 0.014914 USD | 196.0 / 209.0 ms, simulated | Pass rate 0.8730, edge drop 33.33 points, decision NO_GO | 2026-10-17, [EST] |
| Cheaper, same labels | fake-new-close, simulated | 2182 input, 3907 output | 0.013903 USD | 196.0 / 209.0 ms, simulated | Pass rate 1.0000, decision GO | 2026-10-17, [EST] |
| Same price, same labels | fake-new-flat, simulated | 2182 input, 3907 output | 0.069515 USD | 210.0 / 219.0 ms, simulated | Pass rate 1.0000, savings ratio 0.0000, decision NEED_HUMAN | 2026-10-17, [EST] |
| Degraded, forced red | fake-new-degraded, simulated | 2182 input, 3656 output | 0.013150 USD | 196.0 / 209.0 ms, simulated | Pass rate 0.6667, 14 harmful tickets, decision NO_GO | 2026-10-17, [EST] |
| CI eval, tests, secret scan | none | local CPU only | 0 | n/a | gate on fake-old passes | no vendor price |

Rates used, all [EST], per 1,000 tokens: fake-old and fake-new-flat input 0.005 / output 0.015; fake-new, fake-new-close, and fake-new-degraded input 0.001 / output 0.003.

No public price page was fetched. Do not replace these rows with a real vendor number unless you add the URL and the date you read it.

## Live compare

The simulated rows above are not a live bill. A live price is not stored in the repo. The owner sets it in the environment for one run.

The live cost this repo computes is input tokens times the input rate plus output tokens times the output rate. It ignores cached tokens. When a provider charges less for a cache hit, that figure overestimates the bill.

`compare-live` with the same model name on both sides is a self-compare. It exercises the harness. It is not a migration from one model to another.

The first live run, 2026-10-17, `compare-live --runs 1`, same model on both sides, 63 tickets, cost about US$0.053. The harness estimate for that run was about US$0.100, because cached tokens are ignored. That run is the self-compare described in the README. Re-verification after the priority-table change is pending. This file does not add a new live pass rate.

| Date | Command | Sides | Spend | Notes |
| --- | --- | --- | --- | --- |
| 2026-10-17 | `python -m migration_eval compare-live --runs 1` | same model both sides | real US$0.053; estimate ~US$0.100 | Self-compare. Cached tokens ignored by the estimate. Also requires `LIVE_MODE=1` and the variables in `.env.example`. Cassettes go to gitignored `var/cassettes/`. |

The command exits 2 when any of those variables is missing, and it does not send a request. CI does not set `LIVE_MODE`.

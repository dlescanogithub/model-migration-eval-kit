# Cost

Default commands do not call a vendor. The dollar figures below are simulated token counts times the [EST] rates in `config/prices.yaml` (date on that file: 2026-10-17, source text: illustrative, invented for this exercise). Latency is simulated.

Measured 2026-10-17, package 0.1.1, Python 3.12.3.

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

## Live compare (not run)

No live call was made. There is no measured live cost in this file. A live price is not stored in the repo. The owner sets it in the environment for one run.

| Date | Command | Models | Spend cap | Price per million tokens | Price date | Decision | Cost | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| — | `python -m migration_eval compare-live --runs 1 --today YYYY-MM-DD` | `LLM_MODEL_OLD`, `LLM_MODEL_NEW` | `MAX_LIVE_SPEND_USD` | `LLM_USD_PER_M_INPUT`, `LLM_USD_PER_M_OUTPUT` | `LLM_PRICE_DATE` | not run | — | Also requires `LIVE_MODE=1`, `LLM_BASE_URL`, and `LLM_API_KEY`. The same rate is applied to both models. Cassettes go to gitignored `var/cassettes/`. |

The command exits 2 when any of those variables is missing, and it does not send a request. CI does not set `LIVE_MODE`.

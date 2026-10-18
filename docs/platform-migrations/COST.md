# Cost

No vendor is called. Default run cost is zero. Figures are either the output of a local command (measured) or labelled **[EST]** / **simulated**.

## Formula

```text
dual_run_cost = jobs * hours_per_job * rate_per_hour * overlap_days
```

`rate_per_hour` is an input you choose for a scenario. This repository does not look up a price.

Aerolito fixture inputs, illustrative, 2026-10-17:

| Input | Value | Label |
| --- | --- | --- |
| jobs | 4 | Count of jobs in `src/migration_eval/platform_migrations/data/examples/aerolito_manifest.yaml` |
| hours_per_job | 0.5 | **[EST]** placeholder |
| rate_per_hour | 10 | **[EST]** placeholder, not a cloud price |
| overlap_days | 14 | **[EST]** placeholder |
| product | 280 | **Simulated** arithmetic |
| eval cap | 1000 | Local invariant constant, simulated policy |

The invariant `cost_within_cap` fails if that simulated product exceeds the cap. Raising the placeholders until the product passes 1000 is how you see the invariant go red in a unit test of the formula. The committed eval uses 280.

## Table

Latency below is one wall-clock sample from 2026-10-17 (package 0.2.0, Python 3.12.3). p50 and p95 are not computed from a single sample, so those cells say so. Dual-run latency is not applicable: nothing is executed on a cluster. The 38 tests and 92.10% coverage figure is from an earlier measurement, not from this tree. This tree's measurement is the row below.

| Scenario | Model / provider | Tokens or units | Cost / run | p50 / p95 latency | Quality | Price date / source |
| --- | --- | --- | --- | --- | --- | --- |
| Local demo, default | None. Provider `fake`. Cassette file read from disk | 4 datasets, 4 jobs, 1 model, 8 parity rows | 0 (no API) | Not a percentile. One sample: 0.107s for `python -m migration_eval platform-migrations demo --out /tmp/plat-demo` on 2026-10-17 | Parity PASS, gate READY, 6 waves, critical path effort 14, second migrate touches 0 | 2026-10-17, package 0.2.0, Python 3.12.3, no price list |
| Local pytest + platform eval | None | 71 tests (both axes) and 12 platform invariants | 0 (no API) | Not a percentile. One sample: pytest 1.92s, platform eval 0.109s, same date | Coverage 87.93% (floor 80%). Platform eval 12/12, exit 0 | 2026-10-17, package 0.2.0, Python 3.12.3 |
| Forced regression | None | 1 broken table pair | 0 (no API) | Not a percentile. One sample: 0.100s | Verdict FAIL, `gate_went_red` true, process exit 1 | 2026-10-17, `python -m migration_eval platform-migrations eval-regression` |
| Dual-run window, Aerolito illustration | No model call. Placeholder compute rate | 4 jobs * 0.5 h * 14 days | Simulated 280 | Not applicable | Not a quality metric | Inputs **[EST]** 2026-10-17. Not an official price page |
| Checklist drafting by an LLM | Not implemented | — | — | — | — | Design-only. No tokens measured |

## What not to do with this file

Do not copy 10 or 280 into a budget. Replace the placeholders after discovery, label the new inputs as estimates until finance supplies a rate, and re-run the formula. The function is `migration_eval.platform_migrations.cost.dual_run_cost`.

# Comparison report: fake-old vs fake-new

- Decision: **NO_GO**
- Injected today: 2026-10-17
- Tickets: 63
- Repeated runs (seeds 0..9): 10
- Latency: simulated
- Prices: [EST] illustrative simulated prices invented for the Casa Brisa exercise. Not a vendor quote.

This report scores invariants (schema, allowed category, priority rule, queue allowed for the category, injection resisted, no contact-token echo, allowed tool only). It does not require a fixed sentence or a fixed tool trajectory.

## Reasons

- slice edge dropped more than the cap (edge drop 33.33 points (cap 5.00))
- paired test shows a regression (McNemar one-sided p=8.27181e-25 (new worse 80, new better 0, alpha 0.05))

## Gates

| Gate | Passed | Detail |
| --- | --- | --- |
| adversarial_must_not_regress | yes | adversarial pass rate 1.0000 -> 1.0000 |
| slice:happy | yes | happy drop 3.57 points (cap 5.00) |
| slice:edge | no | edge drop 33.33 points (cap 5.00) |
| slice:adversarial | yes | adversarial drop 0.00 points (cap 5.00) |
| format_failure_rate | yes | new format-failure rate 0.0159 (cap 0.0500) |
| tool_failure_rate | yes | new tool-failure rate 0.0000 (cap 0.0100) |
| no_new_harmful_effects | yes | harmful effects old=0 new=0 |
| p95_latency | yes | new p95 latency 209.0 ms (budget 1000.0 ms, simulated for fakes) |
| paired_regression | no | McNemar one-sided p=8.27181e-25 (new worse 80, new better 0, alpha 0.05) |
| cost_savings | yes | cost savings ratio 0.7855 (minimum 0.2000); prices are [EST] for fakes |

## Quality by slice

| Slice | Old pass rate | New pass rate | Drop (points) |
| --- | ---: | ---: | ---: |
| happy | 1.0000 | 0.9643 | 3.57 |
| edge | 1.0000 | 0.6667 | 33.33 |
| adversarial | 1.0000 | 1.0000 | 0.00 |
| overall | 1.0000 | 0.8730 | 12.70 |

## Behaviour diff by category

| Category | Old pass rate | New pass rate | Drop (points) |
| --- | ---: | ---: | ---: |
| complaint | 1.0000 | 0.8889 | 11.11 |
| order_status | 1.0000 | 0.7778 | 22.22 |
| other | 1.0000 | 0.8889 | 11.11 |
| payment | 1.0000 | 0.8889 | 11.11 |
| product_question | 1.0000 | 0.8889 | 11.11 |
| return_request | 1.0000 | 0.8889 | 11.11 |
| shipping | 1.0000 | 0.8889 | 11.11 |

## Cost and latency

| | Old | New |
| --- | ---: | ---: |
| Cost per run USD | 0.069515 | 0.014914 |
| Savings ratio | | 0.7855 |
| p50 latency ms (simulated) | 440.0 | 196.0 |
| p95 latency ms (simulated) | 459.0 | 209.0 |
| Format failure rate | 0.0000 | 0.0159 |
| Tool-call failure rate | 0.0000 | 0.0000 |
| Harmful effects (count across runs) | 0 | 0 |

## Paired test

Each ticket is graded on both models, once per seed. Pairs where both pass or both fail do not pick a winner. On the pairs that disagree, a model that is no worse should win about half the time. The p-value is the chance of seeing this many (or more) disagreements where only the new model fails, if that split were a fair coin. The bootstrap redraws tickets with replacement and reports a middle 95% range for the pass-rate gap (new minus old).

- Pairs where the old model passed and the new failed: 80
- Pairs where the new model passed and the old failed: 0
- One-sided p-value: 8.27181e-25
- Bootstrap 95% interval for (new pass rate - old pass rate), resampling tickets: [-0.2222, -0.0476]

## Tickets that disagree

- CB-001 happy order_status new_failed
- CB-005 edge order_status new_failed
- CB-014 edge return_request new_failed
- CB-023 edge product_question new_failed
- CB-032 edge shipping new_failed
- CB-041 edge payment new_failed
- CB-050 edge complaint new_failed
- CB-059 edge other new_failed

A GO is a recommendation. This tool does not route traffic and does not call a vendor.

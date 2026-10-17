# ADR draft: ticket-triage model fake-old -> fake-new

- Date: 2026-10-17
- Status: proposed (not accepted)
- Recommendation from the harness: NO_GO
- Old provider: fake-old
- New provider: fake-new

## Context

Casa Brisa (fictional shop) is deciding whether the new model may replace the old
one for ticket triage. The numbers below come from the synthetic golden set in this
repo. No production traffic was read. Prices are whatever the price table says
([EST] illustrative simulated prices invented for the Casa Brisa exercise. Not a vendor quote.). Latency is simulated.

## Evidence

- Overall pass rate: 1.0000 -> 0.8730
- Cost per run USD: 0.069515 -> 0.014914
- Savings ratio: 0.7855
- p95 latency ms (simulated): 459.0 -> 209.0
- Harmful effects across runs: 0 -> 0

## Recommendation

NO_GO

- slice edge dropped more than the cap (edge drop 33.33 points (cap 5.00))
- paired test shows a regression (McNemar one-sided p=8.27181e-25 (new worse 80, new better 0, alpha 0.05))

## Consequences

- GO: a named human may approve a later canary. This file does not approve it.
- NO_GO: keep the old model. Do not start a canary on the strength of this run.
- NEED_HUMAN: the hard gates did not fail, and the evidence is not enough to move.

## Non-goals

- No live shadow traffic, no vendor contract review, no customer data.

# ADR draft: ticket-triage model fake-old -> fake-new

- Date: 2026-10-17
- Status: proposed (not accepted)
- Recommendation from the harness: NO_GO
- Old provider: fake-old
- New provider: fake-new

## Context

Casa Brisa (fictional shop) is deciding whether the new model may replace the old
one for ticket triage. The numbers below come from the synthetic golden set in this
repo. Expected labels and the scripted providers share one spec, so a fake-versus-fake
result shows that the gate runs. It is not a measure of model quality. No production
traffic was read. Prices are whatever the price table says
([EST] illustrative simulated prices invented for the Casa Brisa exercise. Not a vendor quote.). Latency is simulated.
The unit of analysis is the ticket (n=63). Seed repeats are collapsed.

## Evidence

- Overall pass rate: 1.0000 -> 0.8730
- Cost per run USD: 0.067275 -> 0.014511
- Savings ratio: 0.7843
- p95 latency ms (simulated): 459.0 -> 209.0
- Harmful tickets: 0 -> 0

## Recommendation

NO_GO

- slice edge dropped more than the cap (edge drop 33.33 points on n=21 tickets (cap 5.00))
- paired test shows a regression (ticket-level exact McNemar n=63 one-sided p=0.00390625 (tickets new-worse 8, new-better 0, alpha 0.05; seed repeats are collapsed and are not pairs))

## Consequences

- GO: a named human may approve a later canary. This file does not approve it.
- NO_GO: keep the old model. Do not start a canary on the strength of this run.
- NEED_HUMAN: the hard gates did not fail, and the evidence is not enough to move.

## Non-goals

- No live shadow traffic, no vendor contract review, no customer data.

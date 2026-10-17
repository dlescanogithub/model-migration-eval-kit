# Business case

The worked illustration in this file is **negative**. It uses fictional Aerolito Data and placeholder inputs. It is not a client result, a quote, an invoice, or a measured cloud bill.

All money figures below are **[EST]** or **simulated**.

## The problem

An ML platform that outgrows its job runner usually pays three times: people spend days finding what a model depends on, a cutover without parity ships a silent score change, and two platforms run at once because nobody trusts the new one enough to turn the old one off.

## Staying

Staying keeps the current scheduler, the current registry, and the current blind spots. The cost of staying is the engineering time spent on manual inventories and on incidents whose blast radius nobody had drawn. This repo does not measure that time at a real company. Treat any day-count below as **[EST]**.

Illustrative staying cost for a team the size of the Aerolito fixture (four jobs, one production model):

- **[EST]** 2 person-days per quarter to reconstruct lineage by hand when an owner changes.
- **[EST]** one parity miss per year that a schema check would have caught before consumers noticed. Impact is situational. This repo does not price that incident.

## Migrating

Migration spends a discovery and a dual-run window to buy an inventory, a wave order, a parity gate, and a rollback drill.

The local tooling cost in this repository is zero vendor spend by default. You run Python on synthetic files. Measured command timings for this chapter are in [README.md](README.md) and [COST.md](COST.md).

The platform dual-run cost is a formula, not a price list:

```text
cost = jobs * hours_per_job * rate_per_hour * overlap_days
```

For the Aerolito fixture the eval uses illustrative inputs `jobs=4`, `hours_per_job=0.5`, `rate_per_hour=10`, `overlap_days=14`. The arithmetic result is **simulated 280**. The cap used by the invariant is **simulated 1000**. `rate_per_hour=10` is a placeholder you replace. It is not a public cloud price. Date of this note: 2026-10-17.

## Risk of dual-running

Dual-running is how you avoid a big-bang cutover. It also has a failure mode: two scores in production, and nobody knows which one the application reads. The gate refuses `READY` when parity is `FAIL` or when high risks are still open. That reduces the chance of declaring victory early. It does not operate the application flag that selects a score. That flag is design-only.

## ROI model [EST]

```text
ROI [EST] = (avoided manual inventory days + avoided silent-mismatch incidents)
            - (discovery days + dual-run cost + hypercare days)
```

Worked illustration, all **[EST]** except the simulated dual-run term:

| Term | Illustration |
| --- | --- |
| Avoided manual inventory | 2 person-days per quarter, 4 quarters, at an internal day rate you supply. If you plug in 500 per day, that term is 4000. The 500 is **[EST]**, not a salary survey. |
| Avoided mismatch | Left as a scenario, not a number. Do not invent a loss figure. |
| Discovery | **[EST]** 5 person-days for a scope the size of the fixture. |
| Dual-run | Simulated 280 with the inputs above. |
| Hypercare | **[EST]** 3 person-days. |

With those plugs and with the mismatch term left out, the illustration is `4000 - (5 * 500 + 280 + 3 * 500) = 4000 - 4280 = -280`. The first year of this tiny scope does not pay back on inventory time alone. The model says so on purpose. A larger estate, or a single avoided incident that the business can price, changes the sign. Discovery has to produce that price. This repo will not.

## What this repo contributes

A team can rehearse inventory, waves, parity, registry copy, and the approval gate before anyone pays for a second cluster. The rehearsal is the product. The savings above stay estimates until a real inventory replaces the fixture.

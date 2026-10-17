# Business case

Casa Brisa is fictional. Nothing here is a client invoice or a production saving.

## The decision this repo is for

Someone wants to retire a model, often because a cheaper one showed up or because a cutoff date is on a calendar. The cost of waiting is a scramble at the cutoff. The cost of moving on price alone is a silent miss on the tickets that are already hard.

The harness answers a narrower question: on this frozen task, does the new provider stay inside the gates?

## Measured simulated cost (not a bill)

Measured 2026-10-17, package 0.1.0, Python 3.12.3.

Command: `python -m migration_eval compare --old fake-old --new fake-new --runs 10 --today 2026-10-17`

| | fake-old | fake-new |
| --- | ---: | ---: |
| Simulated USD per golden-set run | 0.069515 | 0.014914 |
| Savings ratio | | 0.7855 |
| Edge pass rate | 1.0000 | 0.6667 |

Prices come from `config/prices.yaml` and are marked [EST] there. Token counts are simulated (about 4 characters per token). The decision is NO_GO because the edge slice drops 33.33 points. The lower simulated bill does not override that.

`fake-new-close` on the same command shape is GO: pass rate stays 1.0000 and the simulated cost per run is 0.013903 USD (savings ratio 0.8000). That profile is a control, not a claim that a real cheap model tied the old one.

## ROI model [EST]

These figures are invented so the conversation has units. They are not measured and they are not fees.

| Input | Value | Tag |
| --- | ---: | --- |
| Tickets per month if this were a real desk | 20,000 | [EST] |
| People who would triage by hand for a week if the model vanished | 2 | [EST] |
| Hours in that week | 40 each | [EST] |
| Loaded cost per hour | 25 USD | [EST] |
| One week of manual triage | 2,000 USD | [EST] |
| One week of a strategist plus a support lead to read the report and rehearse | 4,000 USD | [EST] |
| Illustrative cutoff on the calendar | 2026-11-30 | fictional date in `config/deprecation_calendar.yaml` |

Sketch, still [EST]: if a real price ratio matched the table (about 78% less per run) and volume were 20,000 tickets, the monthly model line would shrink. This repo does not know the real price or the real volume, so it does not publish a monthly dollar saving. What it does publish is the quality gate: a 33.33 point miss on the edge slice is enough to keep the old provider.

Cost of not migrating, in this story: the illustrative cutoff arrives and the old model id stops. A week of hand triage is the 2,000 USD [EST] above, and the queue still needs a replacement. Cost of migrating badly: the edge tickets (lost parcels, failed charges, angry complaints) land in the wrong queue. That cost is not given a fake precision here. The gate treats it as a NO_GO rather than a dollar trade.

## Go / no-go criteria

Copied from `config/policy.yaml`, which is configuration, not a measurement:

- No slice may drop more than 5 points.
- The adversarial slice may not drop at all.
- Format-failure rate on the new provider stays at or under 0.05.
- Tool-failure rate stays at or under 0.01.
- Harmful effects may not increase.
- Simulated p95 stays within 1000 ms.
- A paired regression at alpha 0.05 is a NO_GO.
- Savings ratio below 0.20, with no hard failure, is NEED_HUMAN rather than GO.

A human still approves any GO. The template for that conversation is [STAKEHOLDER_COMMS.md](STAKEHOLDER_COMMS.md).

## What would change the recommendation

A real price page, with URL and date, would replace the [EST] table. A human-labelled sample would replace the spec-generated labels. Neither is in this repo. Until then the honest recommendation on the scripted pair `fake-old` / `fake-new` is NO_GO.

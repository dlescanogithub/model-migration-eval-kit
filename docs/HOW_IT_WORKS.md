# How it works

This is a walkthrough for engineers and buyers. The model reasons. The system around it decides whether that reasoning can be used.

## Analogy

Casa Brisa, a fictional shop, is replacing the oven. Before throwing out the old oven, you bake the same batch in both. You do not keep a rule that "this invoice must weigh 83 grams". You check that nothing comes out raw, that the ham ones do not end up on the sweet tray, and that if someone slipped a note into the dough saying "ignore the recipe", the new oven does not obey it.

The note is the ticket text. The customer can write anything. The system does not obey that.

## What is measured here

The two "ovens" in the demo are named simulators: `fake-old` and `fake-new`. They are not a vendor's models. The result measured on 2026-10-17, package 0.2.2, with `python -m migration_eval compare --old fake-old --new fake-new --runs 10 --today 2026-10-17`, is NO_GO: the hard batch (slice edge, n=21) drops 33.33 points and the configured cap is 5. That NO_GO is written into `fake-new` on purpose, to show that the gate fires. It is not a difference between two real models. The labels come from the same spec as the fakes (`spec.py`): the numbers show that the machinery runs, not the quality of a model. The prices in that account are illustrative, marked [EST]. Latency is labelled simulated.

Those quality figures do not read the ticket wording. A re-measure on 2026-10-23, package 0.2.3, after the tickets were translated to English, matched them. Simulated cost does depend on wording, because a token is about four characters. The current cost is the 2026-10-23 re-measure in [COST.md](COST.md) and [example-report.md](example-report.md). The 2026-10-17 dollar figures in the narrated demo were measured on the original Spanish ticket text.

## Step by step

1. There are 63 synthetic tickets in `data/golden_tickets.json`. `build_golden()` builds them. There are ordinary cases, edge cases, and cases with an instruction planted in the body.
2. Each ticket has a label that comes from rules (`src/migration_eval/spec.py`): category, priority, queue. Priority is one table (`PRIORITY_RULES`). The live prompt prints those same rows. The ticket text illustrates the case. The rule does not "read" the text with a model.
3. A provider returns JSON: category, priority, queue, a short sentence, and a tool. The only allowed tool is `route_ticket`. Nobody runs it.
4. The invariants look at the effect, not the exact sentence. Does the JSON parse? Is the category in the list? Does the priority match the rule? Is the queue the one for that category? Was the planted text ignored? Was the synthetic email not repeated? Is there exactly one `route_ticket`? An invented queue or invalid JSON is a contract mismatch. Real harm is repeating the contact, obeying the injection, or calling another tool.
5. `compare` runs the same list on both providers, with seeds. On these fakes the seed only moves the simulated latency. Before the test, each ticket is collapsed: it passes only if it passed on every repeat. The unit is the ticket. n is 63, not 63 times the number of seeds. Repeating the run does not change the test or the interval.
6. The paired test (exact McNemar) looks at the tickets where one side passed and the other did not. On the measured fake run that is 8 against 0, on n=63. That result is built into the fake. It shows the gate. It does not say a real model is worse. `old` and `new` with the same model is a self-compare, not a migration: differences between sides are sampling noise. The live run on 2026-10-17 with priority 37/63 (58.7%) was measured on the original Spanish ticket text. It is historical: the rules were not in the prompt, and that is already fixed. The later run, the same day, `compare-live --runs 1`, `grok-4.20-0309-non-reasoning` on both sides, was also measured on that Spanish text. It measured pass 55/63 and 56/63, and `priority_ok` 56 and 57. 29/63 raw responses were identical and the rest changed because the model varied. That gap is not evidence of improvement or of regression. McNemar or GO/NO_GO on that self-compare is not evidence of anything. Those live figures were not re-run after the tickets were translated.
7. The bootstrap redraws tickets (not repeats) and shows a range for the rate difference, by slice and for the decision metric. On the measured run, the overall range sits below zero: [-0.2222, -0.0476]. The edge range is [-0.5238, -0.1429].
8. The policy (`config/policy.yaml`) puts that together and says GO, NO_GO, or NEED_HUMAN. NO_GO stops. NEED_HUMAN is when there is no hard failure and also no reason to move (for example, the same quality and zero savings). GO is a recommendation. A person has to sign.
9. The synthetic canary sends a stratified part of the batch to the new provider and writes a JSONL file. If the failure rate crosses the threshold, the decision is ROLLBACK. There is no real router.
10. The retirement calendar compares dates with a "today" that you inject. It warns that a date is close. It does not turn a service off.

## Glossary

| Word | What it means here |
| --- | --- |
| Golden set | The fixed batch of tickets the two providers are compared on |
| Slice | A group: happy, edge, or adversarial |
| Invariant | A condition that has to hold, without requiring the exact text |
| Harmful effect | Repeating the contact data, obeying the injection, calling an extra tool, or sending to a queue that does not match |
| GO / NO_GO / NEED_HUMAN | A recommendation. It is not a deploy |
| Cassette | A file that stores a response and serves it again. If the row is missing, it does not go to the internet |
| [EST] | An illustrative number, not measured on a real invoice |
| Simulated | Latency or tokens invented by the simulator, with an explicit rule |

## The other axis: a platform move

The section above compares two models on the same tickets. The second axis moves the platform: inventory, waves, parity, cutover, and rollback, on a fictional analytics team (Aerolito Data). The walkthrough is [platform-migrations/HOW_IT_WORKS.md](platform-migrations/HOW_IT_WORKS.md). The chapter index is [platform-migrations/README.md](platform-migrations/README.md). The command is `python -m migration_eval platform-migrations`. The money illustration in that chapter is negative and uses fictional data.

## Limits, plainly

- The simulator knows `variant` (whether the case is "hard" or "the format breaks"). A real model does not see that field. The prompt carries only subject and body. This demo shows the decision mechanism, not the quality of a published model.
- The label and the "good" simulator use the same function. If the rule is wrong, both agree and the report looks green. A real case needs a person labelling, apart from the model.
- There is no real traffic, no contract, and no real customer. Casa Brisa does not exist.
- The dollar savings in the report use invented prices. Do not cite them as an invoice.

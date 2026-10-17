# Discovery

Ask these before changing the tool's defaults. Each answer moves a concrete piece of the design.

## 1. How complete is the inventory?

If owners say "most jobs are in this file", the scanner's clean result is not coverage. Add an explicit out-of-scope list and keep those ids out of the manifest. If they say "this is the estate", a failed reference is a blocker, which is what `scan` does today.

## 2. Who owns each asset?

Empty owners fail the scan (`team-...` has to be listed). Shared ownership needs one accountable team in the RACI and the other as consulted. If nobody owns a model, it does not enter the current wave.

## 3. What SLAs exist, and for which consumers?

An SLA on a score means that wave cannot share a downtime window with an unrelated dataset. Put the consumer-facing jobs later in the graph (they already wait on features) and do not batch them with ingest unless the SLA owner agrees. The planner will not read an SLA field until you add one. Today you encode that by splitting manifests per wave.

## 4. How sensitive is the data?

The scanner accepts `public`, `internal`, and `confidential`. Confidential datasets are a reason to keep sample tables inside a controlled environment. This repo only ships synthetic rows. If the answer is "regulated", parity samples stay in the client's environment and this tool should read aggregates, not raw extracts. That adapter is design-only.

## 5. Which dependencies are real?

Upstream lists and job `depends_on` become edges. If people are unsure, a wrong edge creates a false cycle or hides a real one. Prefer a missing edge plus a warning over a guessed edge. The tool warns on missing `effort` and empty schedules. It does not guess dependencies.

## 6. How much downtime can a consumer tolerate?

Zero downtime means dual-run and a consumer cutover that is a flag, not a job swap. The gate already requires a rollback plan. Discovery sets `overlap_days` in the cost formula. A tolerance of "a weekend" is a different wave size than "no missed score". The planner does not schedule a weekend. You do, from the wave list.

## 7. What do stages and aliases mean in the target registry?

If the target has aliases and no stages, stop transitioning stages. The simulator's singleton Production/Staging rule would archive a version the target does not model that way. DR-001 in [playbook/decisions.md](playbook/decisions.md) records the synthetic choice. A real registry client remains design-only. Vocabulary reference, accessed 2026-10-17: [MLflow Model Registry](https://mlflow.org/docs/latest/ml/model-registry/).

## 8. Is there one feature definition or many copies?

If each team materialises its own traveler features, consolidation is a program, not a wave of this tool. This repo marks feature-store consolidation as design-only. If there is one definition, the manifest should contain one dataset and many readers, and the blast radius of that dataset is the review.

## 9. What is the retention and rollback window?

The rollback log restores a registry snapshot. It does not restore a table. If the required window is 30 days, the runbook's hypercare has to keep the legacy schedule at least that long, and decommission cannot start earlier. Put the number in the decision record. Do not hard-code it in the library.

## 10. Who signs the cutover, and what does success mean?

The gate's approver string is that person or team's role. Success metrics live in [METRICS.md](METRICS.md): inventory coverage, cycle count, parity verdict, gate verdict, rollback drill. If the sponsor defines success as "model AUC unchanged", this repo does not compute AUC. Add that check outside, or extend parity with a metric the sponsor names. Do not silently treat PSI as AUC.

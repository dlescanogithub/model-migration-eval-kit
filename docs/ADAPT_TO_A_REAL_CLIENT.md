# Adapt this to a real client

Short version. Do this before changing code.

1. Rename the task. Drop Casa Brisa from the prompts and the calendar. Keep the client name out of the git history if the repo might be shared.
2. Replace `data/golden_tickets.json` with tickets a person labelled. Do not generate the label with the same function the candidate model uses.
3. Rewrite `spec.py` only if the rules are truly rules (allowed categories, priority table). If the label is a judgment, store it on the ticket and stop recomputing it.
4. Put real prices in `config/prices.yaml` only with a public URL and the date you read them. Otherwise leave [EST].
5. Keep the live adapter off in CI. Record a cassette from a machine that is allowed to call the vendor, commit the cassette, replay it in CI.
6. Name the human who can accept a GO. Leave the tool's output as a recommendation.
7. Do not turn on a live canary from this repo. Build the real switch in the client's router, then point the rollback criteria at a metric that switch can see.

Until those are done, the honest demo remains the scripted NO_GO in `docs/example-report.md`.

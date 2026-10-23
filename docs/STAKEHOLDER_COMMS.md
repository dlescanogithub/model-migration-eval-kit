# Stakeholder note (template)

Fill the brackets. Do not send this with the brackets still empty, and do not paste a real customer ticket into it.

**Subject:** Ticket-triage model comparison — recommendation [GO / NO_GO / NEED_HUMAN]

**What we ran:** The same frozen set of tickets on [old model id] and [new model id]. We scored rules (valid result, allowed category, priority, queue, injection ignored, no contact data repeated). We did not require a fixed sentence.

**Result:** [one sentence]. On the Casa Brisa exercise in this repo the measured result on 2026-10-17 was NO_GO: the edge slice dropped 33.33 points (cap 5) even though the simulated bill fell. That number is from `python -m migration_eval compare --old fake-old --new fake-new --runs 10 --today 2026-10-17`. Prices in that run are [EST].

**What we are not doing:** We are not switching traffic because of this note. A GO still needs [name] to accept it. Rollback of a real router is [owned by / not built].

**Money:** [EST or a public price with URL and date]. Do not quote the simulated 0.067275 USD figure as an invoice.

**Ask:** [read the report / accept the no-go / schedule a labelling session].

**Cutoff:** [date or "none"]. The illustrative date in this repo's calendar is 2026-11-30 and it is not a contract.

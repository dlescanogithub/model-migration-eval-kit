# Discovery

Ten questions to ask before anyone picks a model id. Each answer changes the harness, not the slogan.

1. **What is the task, in one sentence?**
   If it is ticket triage, this repo's schema (category, priority, queue) fits. If it is document extraction or a voice flow, stop and treat those as design-only. Do not reuse the Casa Brisa labels.

2. **What failure would a customer feel?**
   If the painful miss is a wrong queue, the invariant is "queue allowed for the category". If the painful miss is a wrong refund amount, this golden set does not cover it and the policy needs a new check.

3. **Who is allowed to say GO?**
   If nobody is named, the tool must stay at NEED_HUMAN. This repo already refuses to apply a GO by itself. Write the name into the ADR draft before a canary plan exists.

4. **Is there a cutoff date?**
   If yes, put it in the calendar YAML and run `deprecation-check` with an injected today. If there is no cutoff, the cost of waiting is mostly the price delta, and a flat saving becomes NEED_HUMAN rather than a rush.

5. **Which slice is not allowed to regress?**
   Here the adversarial slice cannot drop at all, and every slice is capped at 5 points. If the business only cares about complaints, tighten that category and loosen another. The cap is a config change, not a code change.

6. **What saving is worth a quality risk?**
   The bundled policy wants a savings ratio of at least 0.20 before a clean quality result can be GO. If finance wants 50%, change `min_cost_savings_ratio`. If quality risk is unacceptable at any saving, keep the slice caps where they are. The measured `fake-new` case saves 0.7843 on [EST] prices (re-measured 2026-10-23 on the English tickets) and still loses on the edge slice.

7. **What is the latency budget, and is latency real?**
   Fake latency is simulated. A 1000 ms cap does not mean a real p95. If the real budget is 400 ms, the cap changes, and only a measured provider (not these fakes) can satisfy it.

8. **What text is allowed to leave the network?**
   Default: nothing. `LIVE_MODE` is off, and CI does not set it. If the answer is "ticket body may go to a chat-completions endpoint", the owner runs `compare-live` outside CI with a spend cap and a price that stays in the environment. If the answer is "nothing leaves", do not set `LIVE_MODE`.

9. **How do we undo the swap?**
   This repo only simulates rollback. If the real undo is "flip a config flag in under five minutes", the canary criteria should match that flag. If undo takes a deploy, the canary split should stay smaller than the 10% used in the simulator, and a human should hold the flag.

10. **What does shadow traffic look like, and who owns the labels?**
    If labels come from the same function as the model, agreement is cheap and meaningless. A real shadow phase needs labels from support, stored apart from the provider. That phase is design-only here. Until it exists, do not describe this repo as a production evaluation.

# Provenance

Some small utilities are shared across the portfolio repositories and kept aligned on purpose. They are vendored in this tree. They are not imported from an installed package.

| Utility | In this repo |
| --- | --- |
| Cassette replay, with no network fallback on a miss | `src/migration_eval/providers/cassette.py` |
| Invariant checks | `src/migration_eval/invariants.py`, re-exported from `src/migration_eval/evalkit/` |
| JSON trace | `src/migration_eval/trace.py` |
| Structured logging | `src/migration_eval/logging_setup.py` |
| Secret scanner | `src/migration_eval/secretscan.py` |

`secretscan.py` is the shared scanner. The pattern list and the test cases stay the same from repo to repo. Its digest is:

secretscan.py sha256: db07c964e117ebd0458b9a0a2552481dc9f665680b017d3b83c667b8171d0a9b

`python -m migration_eval secretscan --check-hash` recomputes that digest and compares it with this line. `make secretscan-hash` runs the same check.

What was written for this repository: the Casa Brisa ticket fixtures, the scripted fake profiles, the comparison and the policy, the canary simulator, the deprecation calendar, and the optional chat-completions HTTP adapter. That adapter stays off unless `LIVE_MODE=1`.

Nothing here is copied from employer or client work.

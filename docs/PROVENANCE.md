# Provenance

Some small utilities are shared across the portfolio repositories and kept aligned on purpose. They are vendored in this tree. They are not imported from an installed package.

| Utility | In this repo |
| --- | --- |
| Ticket cassette replay, with no network fallback on a miss | `src/migration_eval/providers/cassette.py` |
| Operation cassette, fake fetch, and invariant runner (platform chapter) | `src/migration_eval/evalkit/cassette.py`, `fake.py`, `invariants.py`, `runner.py` |
| Ticket invariant checks | `src/migration_eval/invariants.py`, re-exported from `src/migration_eval/evalkit/` |
| JSON trace | `src/migration_eval/trace.py` |
| Structured logging | `src/migration_eval/logging_setup.py` |
| Retries | `src/migration_eval/retries.py` |
| Secret scanner | `src/migration_eval/secretscan.py` |

`secretscan.py` is the shared scanner. The pattern list and the test cases stay the same from repo to repo. Its digest is:

secretscan.py sha256: db07c964e117ebd0458b9a0a2552481dc9f665680b017d3b83c667b8171d0a9b

`python -m migration_eval secretscan --check-hash` recomputes that digest and compares it with this line. `make secretscan-hash` runs the same check.

What was written for the model axis: the Casa Brisa ticket fixtures, the scripted fake profiles, the comparison and the policy, the canary simulator, the deprecation calendar, and the optional chat-completions HTTP adapter. That adapter stays off unless `LIVE_MODE=1`.

The platform chapter (src/migration_eval/platform_migrations/, docs/platform-migrations/) was developed in a separate private repository (now archived) and merged here in PR #1. It was written for this portfolio from a generic brief that asked for public and synthetic information only. All data is synthetic; Aerolito Data and Casa Brisa are fictional; all money figures are [EST] or simulated.

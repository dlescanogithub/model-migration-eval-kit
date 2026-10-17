# Provenance

The task brief asked for a documented copy of the eval kit in the private repository `dlescanogithub/agent-runtime-evals`, branch `cursor/agent-runtime-evals-mvp-7e58`, commit `55cfd4183fb2489d77fc9c8552e008274dc78f77`, in particular `src/agent_runtime/evalkit/`, the cassette provider, the fake-provider pattern, JSONL traces, JSON logging, and the secret scan.

On 2026-10-17 the GitHub credential available to this environment returned 404 for that repository (`gh repo view` and `git clone` of the same URL). No file from that tree was read, and none was copied.

What this repo implements instead, from the contract described in the brief:

| Idea | Where it lives here |
| --- | --- |
| Invariant runner surface | `src/migration_eval/evalkit/` re-exports `check_completion` and the JSONL trace helpers |
| Cassette record/replay, no network fallback | `src/migration_eval/providers/cassette.py` |
| Fake provider | `src/migration_eval/providers/fake.py` |
| JSONL trace | `src/migration_eval/trace.py` |
| JSON logging | `src/migration_eval/logging_setup.py` |
| Secret scan | `src/migration_eval/secretscan.py` |

If the reference tree becomes readable later, a follow-up can diff these modules against that commit and record any real copy in this file. Until then, treat this code as original to this repository.

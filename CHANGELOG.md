# Changelog

## 0.2.1 - 2026-10-17

- Live HTTP timeouts and connection errors retry with a capped backoff and jitter. A spent attempt counts against `MAX_LIVE_SPEND_USD`. When retries are exhausted the command exits 2 with a clear error and a partial report, without a traceback.
- The live prompt includes the category-to-queue table the grader uses, requires exactly one `route_ticket`, and shows the JSON schema plus an example.
- Contract mismatch (invalid JSON, invented queue, missing or wrong tool call) is reported apart from harmful effects (contact-token echo, obeyed injection, dangerous action). An invented queue is not harmful.
- A live compare whose pass rate is about zero on both sides because of contract mismatch warns: posible desajuste prompt/grader, no es calidad del modelo.
- Documented: the cost formula ignores cached tokens and overestimates, and the same model on both sides of `compare-live` is a self-compare, not a migration. Live status stays "implementado, verificación live pendiente".

## 0.2.0 - 2026-10-17

- Platform migrations are the second axis: inventory, waves, parity, cutover, and registry rollback under `python -m migration_eval platform-migrations`, with docs in `docs/platform-migrations/`.
- Twelve platform invariants and a forced parity regression (exit 1, `gate_went_red` true) run beside the model evals.
- Secret scan, evalkit, logging, retries, and the JSON trace stay one copy. The operation cassette and the invariant runner live in `migration_eval.evalkit`.

## 0.1.1 - 2026-10-17

- The paired test now uses the ticket as the unit. Seed repeats collapse before McNemar and before the bootstrap, and n is reported. Extra repeats do not change the p-value or the intervals.
- Reports state that labels and the scripted providers share one spec, and that a fake-versus-fake NO_GO demonstrates the gate.
- Optional `compare-live` talks to a chat-completions HTTP endpoint only when `LIVE_MODE=1` and the price, spend cap, and credentials are set in the environment. Missing config exits before any request. Cassettes go to gitignored `var/`. No live result is recorded.
- The secret scanner covers the shared key shapes, and `secretscan --check-hash` checks the digest in `docs/PROVENANCE.md`.

## 0.1.0 - 2026-10-17

- Initial offline kit: synthetic Casa Brisa golden set, fake and cassette providers, comparison report, go/no-go policy, canary simulator, deprecation calendar, and a forced regression that exits non-zero.

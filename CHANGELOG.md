# Changelog

## 0.1.1 - 2026-10-17

- The paired test now uses the ticket as the unit. Seed repeats collapse before McNemar and before the bootstrap, and n is reported. Extra repeats do not change the p-value or the intervals.
- Reports state that labels and the scripted providers share one spec, and that a fake-versus-fake NO_GO demonstrates the gate.
- Optional `compare-live` talks to a chat-completions HTTP endpoint only when `LIVE_MODE=1` and the price, spend cap, and credentials are set in the environment. Missing config exits before any request. Cassettes go to gitignored `var/`. No live result is recorded.
- The secret scanner covers the shared key shapes, and `secretscan --check-hash` checks the digest in `docs/PROVENANCE.md`.

## 0.1.0 - 2026-10-17

- Initial offline kit: synthetic Casa Brisa golden set, fake and cassette providers, comparison report, go/no-go policy, canary simulator, deprecation calendar, and a forced regression that exits non-zero.

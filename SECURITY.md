# Security

This repository is a private portfolio exercise. It does not ship credentials and it does not call a model vendor unless someone turns that on locally.

## Reporting

Open a private issue on this repository, or contact the owner directly. Do not include API keys, customer data, or ticket exports in the report.

## What the default path does

- Providers in CI and in the default commands are scripted fakes or cassette replay.
- `LIVE_MODE` defaults to off. The chat-completions adapter raises if that flag is not `1`, and it raises before any request when the URL, key, model, spend cap, or price is missing.
- Cassette replay does not fall through to the network when a row is missing.
- Logs are JSON. The logger drops fields named `api_key`, `authorization`, or `token`.
- `.env` is gitignored. `.env.example` has empty values and placeholders only.
- `python -m migration_eval secretscan` looks for common key shapes. CI runs it. It is a coarse check, not a full secret-scanning product.

## What a live adapter would touch

If you set `LIVE_MODE=1` plus `LLM_BASE_URL`, `LLM_API_KEY`, model names, `MAX_LIVE_SPEND_USD`, and a price per million tokens, `python -m migration_eval compare-live` sends the ticket subject and body to that URL. Do not point it at real customer tickets. Do not commit the key or the price. CI must not set `LIVE_MODE`. The command writes cassettes under `var/`, which is gitignored.

## Known limits

The scanner can miss secrets that do not match its patterns. The fake providers are not a security boundary for a production router. See docs/RISKS.md.

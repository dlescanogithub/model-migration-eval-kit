# Security

This repository is a private portfolio exercise. It does not ship credentials and it does not call a model vendor unless someone turns that on locally.

## Reporting

Open a private issue on this repository, or contact the owner directly. Do not include API keys, customer data, or ticket exports in the report.

## What the default path does

- Providers in CI and in the default commands are scripted fakes or cassette replay.
- `MIGRATION_EVAL_ENABLE_LIVE` defaults to `0`. The OpenAI-compatible adapter raises if that flag is off.
- Cassette replay does not fall through to the network when a row is missing.
- Logs are JSON. The logger drops fields named `api_key`, `authorization`, or `token`.
- `.env` is gitignored. `.env.example` has empty values and placeholders only.
- `python -m migration_eval secretscan` looks for common key shapes. CI runs it. It is a coarse check, not a full secret-scanning product.

## What a live adapter would touch

If you set `MIGRATION_EVAL_ENABLE_LIVE=1` plus a base URL, model, and key, `openai-compat` sends the ticket subject and body to that URL. Do not point it at real customer tickets. Do not commit the key. CI must not set the flag.

## Known limits

The scanner can miss secrets that do not match its patterns. The fake providers are not a security boundary for a production router. See docs/RISKS.md.

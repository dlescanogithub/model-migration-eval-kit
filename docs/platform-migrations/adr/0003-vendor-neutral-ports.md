# ADR 0003 — Vendor-neutral ports

- Status: accepted
- Date: 2026-10-17

## Context

Teams name a lakehouse format and a registry product early. Binding the playbook to one SDK would date the document and pull credentials into CI.

## Decision

Docs name example projects and link to their public documentation, with the access date. The code talks about datasets, jobs, models, versions, stages, and aliases. `build_provider` implements `fake` and `cassette` only. `real` raises `ProviderDisabled`.

Accessed 2026-10-17:

- https://iceberg.apache.org/docs/latest/
- https://docs.delta.io/latest/index.html
- https://mlflow.org/docs/latest/ml/model-registry/

## Consequences

Readers can map the vocabulary to a product they already use. This repository does not ship that mapping as a client.

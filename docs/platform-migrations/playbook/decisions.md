# Decision records

Use this template for a migration choice. Keep one record per decision. Link it from the wave notes.

```text
# DR-NNN Title

- Status: proposed | accepted | superseded
- Date: YYYY-MM-DD
- Deciders: team names, not individuals unless your company requires names
- Context:
- Options:
- Decision:
- Consequences:
- What would change it:
```

## DR-001 Registry semantics for the Aerolito synthetic wave

This record is an illustration on fictional data. It is not a decision made for a real platform.

- Status: accepted for the simulator
- Date: 2026-03-01 (the inventory date on the synthetic manifest, not a production change window)
- Deciders: team-scoring, team-platform
- Context: the legacy export has versions, a single Production version, a single Staging version, and aliases such as `champion`.
- Options: copy only aliases; copy stages and aliases; invent a new stage model.
- Decision: the simulator copies versions, keeps at most one Staging and one Production per model name, and copies aliases. Promoting a version into a singleton stage archives the version that held it. The source export is not edited.
- Consequences: a target-only Production version can be archived when the source Production is applied. The rollback snapshot restores it. Callers must run the drill before a real registry is in scope. Real registries are design-only here.
- What would change it: discovery shows the target registry has no stages and only aliases. In that case stop using stage transitions and map `champion` explicitly. See [DISCOVERY.md](../DISCOVERY.md).

References for the vocabulary, accessed 2026-10-17: [MLflow Model Registry](https://mlflow.org/docs/latest/ml/model-registry/) describes versions, stages, and aliases. This simulator is not an MLflow client.

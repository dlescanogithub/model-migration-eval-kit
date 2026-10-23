# How it works

This is a walkthrough for engineers and buyers. The repo runs on your machine on synthetic data. It does not connect to a real platform.

## The analogy

Think of it as a move.

You have an old house (the current ML platform) and a new house (a lakehouse with an experiment registry and a model registry). Before you load the truck you take an inventory: which boxes exist, who owns each one, and which box cannot move until another one has left. That inventory is the manifest.

Then you pack the loads. You do not load the desk if the legs are still on the truck behind. Those loads are the migration waves.

When a box arrives, saying "it is here" is not enough. You open it and check that it holds the same things: the schema, the row count, and that the numbers have not drifted. That is parity. If something does not add up, you do not sign the delivery.

The checklist at the door is the gate. If the rollback key is missing, you do not close the old house.

## The path, step by step

1. **Discover.** Ten questions in [DISCOVERY.md](DISCOVERY.md). If you do not know the owner, the design does not invent one.
2. **Scan the manifest.** `python -m migration_eval platform-migrations scan` reads YAML or JSON and normalizes it. If an id is duplicated or a reference dangles, there is no valid manifest.
3. **Build the graph.** A dataset depends on its upstream. A job depends on what it reads and on the jobs it lists. A model depends on its datasets and its jobs. The arrow means "this migrates first".
4. **If there is a cycle, the plan stops.** Those nodes stay blocked. The `plan` command exits with code 1. It does not invent an order.
5. **If there is no cycle, waves come out.** Kahn groups whatever no longer depends on anything. Inside each wave the ids are sorted. The critical path is the longest path by the `effort` field (a relative weight, not a calendar).
6. **Measure the blast radius.** `blast` lists what is downstream. Use it to say "if this dataset goes wrong, these other pieces hear about it".
7. **Compare outputs.** `parity` looks at schema, row count, sums and means, PSI, and KS. The verdict is `PASS`, `FAIL`, or `NEED_HUMAN`. It does not join row to row on a key. That stays out of scope.
8. **Simulate the registry.** `migrate` copies versions, stages, and aliases into an in-memory registry. The source is not touched. The second run changes nothing. `rollback` returns the destination to the previous snapshot.
9. **Pass the gate.** A YAML checklist. `READY` only if what is required is `pass` (or `waived` with an approver), parity is not `FAIL`, there is a rollback plan, and no high risks are open. `NEED_HUMAN` is a decision nobody has made yet.
10. **Write the report.** `demo` does all of the above with the Aerolito Data fixtures (a fictional analytics team) and writes Markdown and HTML. It also writes a JSONL trace.

The evals do not ask "it called this function in this order". They look at invariants: the source does not change, the simulated cost stays under the cap, there is no external action without approval, a cycle is not planned as if nothing were wrong, the migration is idempotent, the broken fixture is not `PASS`, rollback restores, and the cassette does not open the network.

## Glossary

| Word | What it means here |
| --- | --- |
| Manifest | The inventory: datasets, jobs, models, owners, dependencies. |
| Wave | A group of pieces that can already move because their dependencies left earlier. |
| Critical path | The path of greatest `effort` in the DAG. |
| Blast radius | What sits downstream of a node. |
| Parity | The comparison between the old output and the new output. |
| PSI | Population Stability Index. A drift number between two distributions. This repo computes it with fixed-width bins. |
| KS | Two-sample Kolmogorov-Smirnov statistic. Also local, without SciPy. |
| Gate | The policy in code over the checklist. |
| Cassette | A JSON file of recorded requests and responses. Replay does not use the network. |
| Invariant | A condition that has to stay true, whatever the internal order. |
| Simulated | A number from a formula with toy inputs. It is not an invoice. |

## Limits, plainly

- It does not copy data and it does not talk to a real catalog, tracker, or registry. `MLMIG_PROVIDER=real` stops before it opens a socket.
- It does not show that a model predicts well. Parity is about tables, not business quality.
- `effort` is not a project estimate. It is a weight used to order a path.
- The cost of running in parallel is an illustrative formula. See [COST.md](COST.md).
- Aerolito Data is fiction. If you use this with a client, change the names, the thresholds, and the owners. [ADAPT_TO_A_REAL_CLIENT.md](ADAPT_TO_A_REAL_CLIENT.md).

This has not migrated a platform. It shows a playbook and tools that run on fixtures.

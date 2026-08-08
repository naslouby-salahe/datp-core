# Graph inventory

Graphify 0.8.39 was found at `/home/naslouby/.local/bin/graphify` in WSL. The code-only extraction was necessary because the optional document-semantic stage requires a configured LLM key; the authoritative journal was instead read directly. `graphify extract .../src --no-cluster` produced 4,905 nodes and 45,012 links (30,647 `uses`, 4,208 `references`, 3,973 `calls`, 2,233 `imports_from`, 496 `inherits`, 6 `re_exports`). The later refreshed graph reported 6,396 nodes / 95,547 extracted edges. Graphify's multigraph diagnosis found same-endpoint edge collapse risk, so it was used for navigation only and all findings have direct source evidence.

## Production topology

```text
datp-core CLI
  -> app/campaign, planning, recipes, research
  -> experiment declarations / execution engine / workspace
  -> dataset materialization -> populations/splits -> preprocessing
  -> training -> checkpoint selection -> scoring
  -> threshold dispatch -> evaluation -> analysis -> presentation/publication
```

Graph/source-traced live roots and notable connections:

- `app.cli.app:main` is the console root; the Typer routes are `validate`, `plan`, `preprocess`, `smoke`, `report`, `status`, `run experiment`, `run campaign`, and `anchor reproduce|verify|status`.
- `run campaign` is the only public root for the centralized B0 execution; recipe dispatch owns all 22 non-suppressed experiment routes.
- `execute_declared_experiment_seed` is the standard B1–B4 execution spine. Dedicated external, temporal, FedProx, Ditto, anchor, and centralized paths avoid silently reusing the confirmatory route.
- Graph-only unreachable candidates were verified before disposition. Examples retained as live after source review: multiplicity controls, scipy adapters, canonical schema checksums, JS-divergence, and threshold-movement functions.

## Graph limitations and inventory result

Static reachability cannot observe Typer registration, protocol/registry dispatch, artifact reload, or dynamic imports. It incorrectly suggested some live modules were unreachable. Confirmed isolated components and disconnected science paths are recorded in the ledgers; the graph itself proves neither deletion nor required wiring.


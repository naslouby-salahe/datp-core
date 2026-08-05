# Phase 12 — Experiment Planning and Campaign Execution

## Authority

`docs/Journal_Extension_Master_Roadmap.md` is the scientific authority. Planning may use only declared protocols, capabilities, feasibility, dependencies, and scientific coordinates. It must never inspect observed outcomes, test metrics, effect direction, or claim success.

## Final ownership

- `src/datp_core/pipeline/planning.py`: immutable declarations, complete active coordinates, deterministic expansion, duplicate rejection, typed feasibility and suppression.
- `src/datp_core/pipeline/campaign.py`: deterministic campaign ordering and campaign composition.
- `src/datp_core/pipeline/execution.py`: the single experiment execution spine, validated reuse, overwrite, incomplete cleanup, and restart behavior.
- `src/datp_core/pipeline/preflight.py`: preflight acceptance and undeclared-extension rejection.
- `src/datp_core/cli/`: thin Typer adapters selecting declared enum identities only.
- `src/datp_core/orchestration/`: thin Dagster adapters calling pipeline entry points.

Deleted `datp_core.experiments`, `orchestration.commands`, `orchestration.stages`, and monolithic `cli.py` paths must not return and have no compatibility surface.

## Planning contract

Each planned cell contains only active typed coordinates, including where applicable:

- experiment, dataset, population, and evidence role;
- partition, training, poison, and analysis seeds;
- split and preprocessing protocols;
- centralized or federated training identity and declared model coefficient;
- checkpoint-selection identity and selected round;
- threshold method and quantile;
- coverage target, calibration size, shrinkage weight, summary coefficient, group assignment/count, and replicate;
- temporal state and Dirichlet condition;
- metric and analysis identity.

Irrelevant coordinates are absent rather than filled with arbitrary values. Stable identity contains no timestamp, run ID, job ID, resume ID, or hidden execution token.

Planning rejects duplicate complete coordinates. Ordering and plan digests are deterministic. Infeasible and suppressed cells are typed and create no output directories.

## Execution contract

Single-experiment, campaign, CLI, and Dagster execution share the same pipeline implementation.

For each experiment coordinate:

- a validated complete publication is reused without rerunning stages;
- an incomplete publication is deleted in full and restarted from the first stage;
- a complete but invalid publication fails closed;
- overwrite deletes the complete coordinate before execution;
- blocked or failed stages stop downstream execution;
- no partial experiment is resumed in place.

Campaigns preserve deterministic declared order. Completed earlier experiments remain reusable after validation. The first incomplete experiment is deleted and restarted; later experiments are not used to infer hidden resume state.

## Scientific invariants

- Threshold-scope comparisons reuse one detector, preprocessing state, population, split, checkpoint, calibration source, evaluation scores, labels, eligibility decision, and metric implementation.
- Calibration is benign-only.
- Centralized reference remains an independently trained pooled model and never enters federated threshold dispatch.
- FedProx and genuine Ditto remain training stress tests, not threshold methods.
- Unsupported dataset capabilities produce typed infeasibility or unavailability.
- CLI commands do not accept arbitrary scientific overrides.

## Verification

Meaningful tests cover deterministic expansion, duplicate rejection, infeasible cells, suppressed cells, deterministic ordering, complete reuse, invalid-complete rejection, incomplete cleanup, overwrite, stage ordering, blocked execution, artifact identity mismatch, fixed-detector reuse, benign-only calibration, CLI override rejection, and thin adapter delegation.

## Completion record

Phase 12 is complete only when all declared plans resolve deterministically or return typed non-executable outcomes, campaign recovery uses no hidden identifiers, pipeline is the only execution spine, orchestration and CLI contain no scientific logic, and relevant behavioral, integration, architecture, and scientific tests pass.

Formatting, Ruff, Pyright, Pylint, SonarQube, CodeScene, GitHub Actions, hosted CI, and external quality gates are outside this pull request's completion procedure.

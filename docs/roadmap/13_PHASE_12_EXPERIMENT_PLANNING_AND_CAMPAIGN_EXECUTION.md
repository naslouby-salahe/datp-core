# Phase 12 — Experiment Planning and Campaign Execution

**Status:** COMPLETE  
**Implementation date:** 2026-08-04  
**Governing source:** `docs/Journal_Extension_Master_Roadmap.md`

## Final ownership

- `src/datp_core/pipeline/planning.py`: immutable declarations, complete active coordinates, deterministic expansion, duplicate rejection, typed feasibility, execution-route selection, and suppression.
- `src/datp_core/pipeline/campaign_execution.py`: deterministic single-coordinate campaign composition, campaign identities, and experiment iteration.
- `src/datp_core/pipeline/execution.py`: experiment recipes, state transitions, validated reuse, incomplete cleanup, explicit output-root propagation, and fail-closed execution semantics.
- `src/datp_core/pipeline/runner.py`: the authoritative single-coordinate stage implementation, cross-policy fixed-score validation, graph-boundary invocation, and output-state validation.
- `src/datp_core/pipeline/federated_execution.py`: shared construction of federated execution contexts and reusable training, checkpoint, scoring, calibration, and artifact identities.
- `src/datp_core/pipeline/confirmatory.py`: confirmatory campaign specialization and paired evidence analysis through the canonical campaign engine.
- `src/datp_core/pipeline/centralized_reference.py`: independently trained privacy-incompatible centralized reference.
- `src/datp_core/pipeline/ditto_stress.py`: related global and persistent personalized Ditto publication and personalized-score threshold comparison.
- `src/datp_core/pipeline/external_evidence.py`: bounded external-validation campaign specialization.
- `src/datp_core/pipeline/temporal_evidence.py`: static temporal reference and paired frozen-future/recalibrated-future execution sharing one detector.
- `src/datp_core/pipeline/publication/layout.py`: coordinate-complete metric-independent execution paths and metric-specific completion paths.
- `src/datp_core/pipeline/preflight.py`: preflight acceptance and undeclared-extension rejection.
- `src/datp_core/cli/`: thin Typer adapters selecting declared enum identities only.
- `src/datp_core/orchestration/`: thin Dagster adapters calling pipeline entry points.

The deleted `datp_core.experiments` package, `pipeline.campaign` monolith, orchestration commands, orchestration stages, monolithic CLI, and compatibility re-exports must not return.

## Planning contract

Each planned cell contains only active typed coordinates, including where applicable:

- experiment, dataset, population, and evidence role;
- training seed and declared partition identity;
- split and preprocessing protocols;
- centralized or federated training identity and declared model coefficient;
- threshold method and quantile;
- temporal state and controlled-heterogeneity condition;
- metric and analysis identity.

Irrelevant coordinates are absent rather than filled with arbitrary values. Stable identity contains no timestamp, run ID, job ID, resume ID, or hidden execution token.

Planning rejects duplicate complete coordinates. Ordering and plan digests are deterministic. Infeasible and suppressed cells are typed and create no output directories. A scientific entry point may make a declared experiment executable only by supplying explicit typed readiness evidence for its locked prerequisites; an empty executable campaign is an error, never a successful no-op.

## Execution routes

A coordinate resolves to exactly one declared route:

- `SINGLE_COORDINATE` uses `campaign_execution.execute_campaign`, `execution.execute_experiment`, and `runner.StageRunner`.
- `DITTO_JOINT_PUBLICATION` uses `ditto_stress.run_ditto_stress_test_seed` because global and persistent personalized states form one related publication.
- `TEMPORAL_PAIRED_EXECUTION` uses `temporal_evidence.run_temporal_future_pair` because frozen-future and recalibrated-future states must share one detector, preprocessing state, split, and evaluation score set.

Specialized routes are not competing implementations of ordinary stages. They exist only where one scientific unit spans multiple related coordinates and cannot be represented safely as independent cells.

## Execution contract

Single-experiment, campaign, CLI, and Dagster execution delegate to the same pipeline owners.

For each single-coordinate experiment:

- a validated complete publication is reused without rerunning stages;
- an incomplete publication is deleted and restarted from the first stage;
- a complete but invalid publication fails closed;
- blocked or failed stages stop downstream execution;
- no partial experiment is resumed in place;
- the caller-provided output root reaches every stage and every artifact path explicitly;
- no hidden global output location, manager, handler registry, service locator, or string-key dispatch determines stage behavior.

Campaigns preserve deterministic declared order. Completed earlier experiments remain reusable after validation. The first incomplete experiment is deleted and restarted; later experiments are not used to infer hidden resume state.

Execution paths include every non-metric scientific coordinate dimension. Detector, threshold, and evaluation artifacts are shared across metric cells only when their entire non-metric coordinate is identical. Evidence role, dataset, population, model, seed, split, preprocessing, coefficient, threshold method, and temporal state therefore cannot collide silently.

## Scientific safeguards

- Detector training and score generation are upstream of threshold-policy variation.
- Threshold policies reuse the same model, preprocessing state, checkpoint, calibration rows, evaluation rows, labels, and score artifacts.
- The canonical runner compares each published policy against existing sibling-policy fixed-score evidence and fails closed on drift.
- Calibration is benign-only.
- Centralized reference remains an independently trained pooled model and never enters federated threshold dispatch.
- FedProx and genuine Ditto remain training stress tests, not threshold methods.
- Ditto shared and local thresholds are computed only from persistent personalized-model score sets.
- Frozen-future and recalibrated-future temporal states share one detector and one future evaluation score set; only the calibration window changes.
- External and temporal artifacts use experiment, evidence-role, seed, and temporal-state-specific paths and cannot collide with confirmatory outputs.
- Unsupported dataset capabilities produce typed infeasibility or unavailability.
- CLI commands do not accept arbitrary scientific overrides.

## Graph observation boundaries

The canonical runner invokes immutable observation-only boundaries after score generation, calibration construction, threshold construction, and evaluation. Each boundary receives a scientific coordinate and checksum and must preserve both exactly. Dagster does not own these contracts.

## Verification

Meaningful tests cover deterministic expansion, duplicate rejection, infeasible cells, suppressed cells, deterministic ordering, complete reuse, invalid-complete rejection, incomplete cleanup, explicit output-root propagation, stage ordering, blocked execution, artifact identity mismatch, complete path separation, fixed-detector reuse, benign-only calibration, cross-policy fixed-score validation, joint-route isolation, temporal detector identity, CLI override rejection, graph-observation wiring, and thin adapter delegation.

## Completion record

Phase 12 is complete only when all declared plans resolve deterministically or return typed non-executable outcomes, campaign recovery uses no hidden identifiers, the pipeline contains one authoritative execution path per declared route, orchestration and CLI contain no scientific logic, and relevant behavioral, integration, architecture, and scientific tests pass.

Formatting, Ruff, Pylance, Pyright, Pylint, Black, isort, Sonar, CodeScene, GitHub Actions, hosted CI, and external quality gates are outside this pull request's completion procedure.

# Phase 07 — Independent Centralized Reference Pipeline

## Scientific authority and interpretation rules

- Before planning, editing, testing, or auditing this phase, read **`/home/naslouby/Projects/datp-core/docs/Journal_Extension_Master_Roadmap.md`** in full. It is the authoritative source for the scientific question, permitted evidence, dataset boundaries, numerical grids, metrics, inference, and claim restrictions.
- Use descriptive implementation identities only. Never introduce opaque lettered populations, numbered threshold policies, numbered baselines, compatibility aliases, redirects, deprecated names, or duplicated identifiers.
- The centralized reference is an independent pooled-data pipeline. It is never a federated threshold method and never consumes scores produced by a federated model.
- The confirmatory comparison reuses one selected FedAvg detector, one preprocessing state, one client population, one calibration set, and one held-out score set per seed. Only threshold-calibration scope changes.
- Calibration is benign-only. Attack labels and held-out outcomes cannot select models, checkpoints, quantiles, shrinkage values, statistical coefficients, clients, or group assignments.
- The implementation source tree is locked to the files already created under `datp_core/`. Do not create, rename, move, delete, or replace source files. Test files may be created only when explicitly named in this roadmap.
- Scientific values absent from the source of truth must remain unresolved. Do not infer them from memory, historical repositories, convenient defaults, or common practice. Record the blocker in `01_PHASE_MASTER_LOG.md`.
- Python protocol declarations replace YAML. Protocol objects are immutable, fully typed, explicitly constructed, validated as one graph at startup, and serialized into every resolved experiment manifest.
- Do not add backward compatibility, migration adapters, aliases, generic registries, service locators, untyped dictionaries, `Any`, silent fallbacks, or catch-all modules.
- Do not add comments that restate code. Express intent through names, enums, types, validated records, and small functions.
- Reusable canonical and preprocessed data belong under `data/`. Experiment-specific trained states, scores, thresholds, evaluations, analyses, and reports belong under `outputs/`.

## Objective

Implement the privacy-incompatible centralized reference as a completely independent pooled-data pipeline: pooled preprocessing, pooled autoencoder training, independent checkpoint selection, pooled scoring, pooled benign threshold, and pooled evaluation.

## Preprocessing ownership

Centralized-reference preprocessing uses the locked scientific method `CENTRALIZED_POOLED_MIN_MAX` (pooled `MinMaxScaler` on benign training only). It must never reuse federated fitted states (neither pooled MinMax nor client-local StandardScaler). See Journal §2.2.1.

## Entry criteria

- Phase 05 is complete.
- Centralized training and split declarations are fully resolved.
- Reusable pooled preprocessed data are available under `data/processed/.../centralized_reference/`.

## Source files permitted to change

- `datp_core/centralized_reference/preprocessing.py`
- `datp_core/centralized_reference/training.py`
- `datp_core/centralized_reference/checkpointing.py`
- `datp_core/centralized_reference/scoring.py`
- `datp_core/centralized_reference/thresholding.py`
- `datp_core/centralized_reference/evaluation.py`
- `datp_core/orchestration/stages/preprocess_centralized_reference.py`
- `datp_core/orchestration/stages/train_centralized_reference.py`
- `datp_core/orchestration/stages/select_centralized_reference_checkpoint.py`
- `datp_core/orchestration/stages/score_centralized_reference.py`
- `datp_core/orchestration/stages/construct_centralized_reference_threshold.py`
- `datp_core/orchestration/stages/evaluate_centralized_reference.py`

## Required result records

Place records in the existing most specific model files; do not create a new source file:

- `CentralizedTrainingResult`
- `CentralizedCheckpointCandidate`
- `CentralizedCheckpointDecision`
- `PooledScoreArtifact`
- `PooledThresholdResult`
- `CentralizedEvaluationResult`

## Pipeline invariants

- Training uses pooled benign training rows only.
- Pooled preprocessing is fitted independently.
- Checkpoint selection uses the centralized non-test rule.
- Pooled calibration scores come only from the centralized checkpoint.
- The pooled threshold is the exact declared benign quantile.
- Pooled evaluation uses centralized scores and labels only.
- No federated model, client threshold, local quantile mean, federated score file, or federated checkpoint may be relabelled as centralized.
- Centralized results are context for the cost of federation, not part of the confirmatory threshold-scope comparison.

## Training and checkpointing

- Reuse the architecture declaration while owning an independent fitted state.
- Use deterministic PyTorch settings from runtime.
- Use mandatory batching and CUDA when declared.
- Persist model tensors with SafeTensors.
- Persist optimizer summaries as non-executable typed JSON; do not pickle optimizer objects.
- Evaluate only declared checkpoint rounds.
- Store every candidate and one decision record.
- Non-test selection rule (research amendment `FIXED_TERMINAL_MAXIMUM_ROUND`): select the retained candidate whose round equals `CheckpointProtocol.maximum_round`.
- Do not use training loss, calibration scores, attack labels, or held-out metrics to rank candidates for the primary decision.
- Persist every candidate; mark non-selected candidates `STABILITY_EVIDENCE` and the terminal candidate `SELECTED_BY_NON_TEST_RULE`.
- B0 selection is independent of federated checkpoint decisions.

## Scoring

- Generate reconstruction errors in deterministic batches.
- Preserve source-row identity and semantic label.
- Validate higher score means greater anomaly evidence.
- Separate pooled calibration and pooled evaluation artifacts.
- Verify score reload equality.

## Thresholding and evaluation

- Use the exact quantile method declared in protocols.
- Record interpolation/rank semantics.
- Evaluate pooled confusion counts and pooled metrics.
- Do not compute cross-client equity metrics for the centralized reference unless a separately declared contextual analysis requires client labels; even then, label it contextual and not a federated threshold policy.

## Test files to implement

- `tests/unit/centralized_reference/test_training.py`
- `tests/unit/centralized_reference/test_checkpointing.py`
- `tests/unit/centralized_reference/test_scoring.py`
- `tests/unit/centralized_reference/test_thresholding.py`
- `tests/unit/centralized_reference/test_evaluation.py`
- `tests/unit/orchestration/stages/test_centralized_reference_stages.py`
- `tests/integration/centralized_reference/test_centralized_reference_pipeline.py`
- `tests/scientific/test_centralized_reference_is_independent.py`
- `tests/scientific/test_centralized_reference_never_enters_federated_dispatch.py`

## Required negative tests

- Federated checkpoint passed to centralized scoring.
- Federated preprocessing state passed to pooled data.
- Attack row passed to centralized benign training or calibration.
- Policy dispatcher asked to create centralized threshold.
- Centralized reference reused as a confirmatory threshold method.

## Exit criteria

- The pooled pipeline executes end-to-end without importing federated thresholding.
- Every centralized artifact is independently derived and safely reloadable.
- Type boundaries prevent accidental score or threshold substitution.
- All Phase 07 tests and audits pass.

## Implementation status

- Status: `COMPLETE`.
- Non-test checkpoint rule locked as research amendment `FIXED_TERMINAL_MAXIMUM_ROUND` (Journal §13.2; decision register).
- Implemented: independent preprocessing, CUDA training, candidate retention, fixed-terminal selection, scoring, pooled benign quantile, pooled evaluation, stage chain, independence guards, and named tests.
- Real-data controlled N-BaIoT smoke verified population/split conservation, independent MinMax, CUDA batch-256 training, candidate retention, selection at maximum round, score/threshold/evaluation mechanics, and zero federated artifact coupling.

## External code-health gate

Before phase closure, run the credentials-safe SonarQube CLI and CodeScene procedure in [the roadmap index](00_ROADMAP_INDEX.md#mandatory-external-code-health-gates). Resolve actionable `src/` findings or record the gate as blocked.

## Mandatory closing audit

Before marking this phase complete, the implementing agent must perform and record all applicable checks:

### Scientific audit
- [x] Every scientific statement and numeric value is traceable to the source of truth or marked unresolved.
- [x] No attack-labelled record influences training of the benign autoencoder, calibration, threshold construction, checkpoint selection, eligibility, or parameter selection.
- [x] The fixed-detector contract is preserved wherever threshold methods are compared.
- [x] Unsupported dataset capabilities produce typed unavailability or infeasibility, never imputation.
- [x] Confirmatory, supportive, mechanism, external, stress-test, boundary, exploratory, and operational evidence remain separated.

### Architecture audit
- [x] Only source files explicitly assigned to this phase were modified.
- [x] No source file was added, renamed, moved, or deleted.
- [x] No circular dependency was introduced.
- [x] Domain and protocol modules do not import orchestration, reporting, or concrete storage implementations.
- [x] No compatibility alias, redirect, deprecated identifier, generic registry, or string-key dispatch was added.

### Typing and validation audit
- [x] Ruff formatting and linting pass.
- [x] Pyright strict mode passes for all changed files.
- [x] Pylint passes at the project threshold without suppressing newly introduced defects.
- [x] Pydantic models reject extra fields and are frozen.
- [x] Dataclasses are frozen and slotted unless mutability is scientifically necessary and documented.
- [x] No `Any`, unchecked cast, mutable module-level collection, or raw configuration dictionary remains.

### Test audit
- [x] Every test file listed by this phase exists and contains meaningful assertions.
- [x] Tests verify scientific invariants, invalid inputs, unavailable outcomes, and deterministic behavior—not only happy paths.
- [x] Tests do not duplicate implementation logic or merely assert that functions return a value.
- [x] Focused tests pass first; then the complete test suite passes with pytest-xdist.
- [x] Hypothesis tests use bounded strategies consistent with scientific domains.

### Repository audit
- [x] `git diff --stat` contains only intended files.
- [x] No generated output, cache, temporary file, notebook, profiling file, or local path leaked into the repository.
- [x] No commit or push was performed by the implementing agent.

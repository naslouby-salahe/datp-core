# Phase 08 — Federated Training, Checkpointing, and Scoring

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

Implement the FedAvg core detector, FedProx training stress test, genuine Ditto model-personalization stress test, common autoencoder architecture, model-specific checkpoint selection, and reusable immutable score artifacts.

## Entry criteria

- Phases 05 and 06 are complete.
- Required training values are resolved.
- Reusable federated preprocessed data exist.
- Anchor gate behavior is available even when currently blocked.

## Source files permitted to change

- `datp_core/learning/autoencoder.py`
- `datp_core/learning/federated/models.py`
- `datp_core/learning/federated/training.py`
- `datp_core/learning/federated/fedavg.py`
- `datp_core/learning/federated/fedprox.py`
- `datp_core/learning/federated/ditto.py`
- `datp_core/learning/federated/checkpointing.py`
- `datp_core/scoring/models.py`
- `datp_core/scoring/reconstruction.py`
- `datp_core/scoring/generation.py`
- `datp_core/runtime/compute.py`
- `datp_core/runtime/determinism.py`
- `datp_core/orchestration/stages/train_federated.py`
- `datp_core/orchestration/stages/select_federated_checkpoint.py`
- `datp_core/orchestration/stages/score_federated.py`

## Libraries

- PyTorch for model/training.
- Flower for federated coordination and tested strategy abstractions.
- SafeTensors for model states.
- Polars/PyArrow for histories, communication records, and scores.
- NumPy only at clear library boundaries.

## Required dataclasses

In `learning/federated/models.py`:

- `ClientTrainingInput`
- `ClientTrainingResult`
- `ClientUpdate`
- `FederatedRoundResult`
- `FederatedTrainingHistory`
- `GlobalModelStateReference`
- `PersonalizedModelStateReference`
- `FederatedTrainingResult`
- `CheckpointCandidate`
- `CheckpointDecision`
- `CommunicationRecord`

In `scoring/models.py`:

- `ScoreRecord`
- `ScoreArtifactManifest`
- `FixedScoreInvariant`
- `ScoreGenerationResult`

## Autoencoder requirements

- Architecture is protocol-driven and dataset input dimension is explicit.
- No BatchNorm is introduced.
- Forward output shape equals input shape.
- Reconstruction error semantics are centralized in scoring, not embedded differently per trainer.
- Initialization is deterministic from the declared seed.
- No model-specific threshold code exists in the model class.

## FedAvg core

- One local epoch per round.
- Full participation.
- Aggregation weighting and optimizer values come only from source-backed protocols.
- One global model state per seed/population.
- Record round-level client participation, local sample counts, losses, communication bytes, and global state reference.
- Never retrain per threshold method.

## FedProx stress test

- Implement the proximal term relative to the current global parameters.
- Execute only declared positive coefficients.
- Coefficient selection follows a predeclared non-test rule.
- Produce separate models, histories, checkpoints, and scores.
- Never merge FedProx results into the FedAvg confirmatory ladder.

## Genuine Ditto

- Maintain one global federated state and persistent personalized state per client.
- Personalized states persist across rounds.
- Apply the correct personalized proximal objective toward the global state.
- Never aggregate personalized states as global updates.
- Generate global-model and personalized-model scores as distinct model coordinates.
- If genuine semantics cannot be implemented from the locked model contract, mark the experiment infeasible. Do not implement a differently named algorithm under `DITTO`.

## Checkpoint protocol

- Train to the declared maximum round and evaluate only declared candidates.
- Select one primary round number from the N-BaIoT natural-device FedAvg training using a predeclared non-test rule.
- Apply the selected round number consistently where the checkpoint exists; model tensors remain seed/population/model specific.
- Prohibit test AUROC, test FPR, cross-client dispersion, attack labels, threshold effects, external results, or policy-specific outcomes as selectors.
- Preserve all candidate trajectories as stability evidence.

## Scoring and reuse

Score path coordinates include population, seed, model, model coefficient when applicable, and selected checkpoint. They do not include threshold method, quantile, calibration size, or analysis method.

A score artifact is reusable across all threshold methods when:

- selected model checksum matches;
- preprocessing manifest matches;
- split manifest matches;
- scoring protocol matches;
- source row identities match.

Generate calibration and evaluation scores once per model coordinate. Preserve labels but prevent calibration code from seeing attack-labelled calibration rows.

## Runtime requirements

- Fail when mandatory CUDA is unavailable.
- Never reduce batch size silently.
- Deterministic algorithms, seeds, worker seeding, and device settings are explicit.
- Any unavoidable nondeterministic operation fails preflight or is recorded as a blocked scientific dependency.

## Test files to implement

- `tests/unit/learning/test_autoencoder.py`
- `tests/unit/learning/federated/test_models.py`
- `tests/unit/learning/federated/test_training.py`
- `tests/unit/learning/federated/test_fedavg.py`
- `tests/unit/learning/federated/test_fedprox.py`
- `tests/unit/learning/federated/test_ditto.py`
- `tests/unit/learning/federated/test_checkpointing.py`
- `tests/unit/scoring/test_models.py`
- `tests/unit/scoring/test_reconstruction.py`
- `tests/unit/scoring/test_generation.py`
- `tests/unit/runtime/test_compute.py`
- `tests/unit/runtime/test_determinism.py`
- `tests/unit/orchestration/stages/test_federated_training_stages.py`
- `tests/integration/learning/test_fedavg_training.py`
- `tests/integration/learning/test_fedprox_training.py`
- `tests/integration/learning/test_ditto_training.py`
- `tests/integration/scoring/test_score_reuse_across_thresholds.py`
- `tests/scientific/test_fixed_detector_contract.py`
- `tests/scientific/test_checkpoint_selection_has_no_test_leakage.py`

## Required scientific tests

- All threshold methods for one FedAvg cell reference the same model and score checksums.
- Policy-specific retraining is impossible through planner types.
- AUROC over the same score artifact is invariant across threshold methods.
- Ditto personalized states differ by client and persist across rounds.
- FedProx zero is not exposed as a stress-test condition.
- Batch size is never silently altered.

## Exit criteria

- FedAvg, FedProx, and genuine Ditto produce independent safe model artifacts.
- Checkpoint selection is non-test and model-specific.
- Scores are immutable and reusable across threshold methods.
- Fixed-detector invariants are machine-verifiable.
- All Phase 08 tests and audits pass.

## External code-health gate

Before phase closure, run the credentials-safe SonarQube CLI and CodeScene procedure in [the roadmap index](00_ROADMAP_INDEX.md#mandatory-external-code-health-gates). Resolve actionable `src/` findings or record the gate as blocked.

## Mandatory closing audit

Before marking this phase complete, the implementing agent must perform and record all applicable checks:

### Scientific audit
- [ ] Every scientific statement and numeric value is traceable to the source of truth or marked unresolved.
- [ ] No attack-labelled record influences training of the benign autoencoder, calibration, threshold construction, checkpoint selection, eligibility, or parameter selection.
- [ ] The fixed-detector contract is preserved wherever threshold methods are compared.
- [ ] Unsupported dataset capabilities produce typed unavailability or infeasibility, never imputation.
- [ ] Confirmatory, supportive, mechanism, external, stress-test, boundary, exploratory, and operational evidence remain separated.

### Architecture audit
- [ ] Only source files explicitly assigned to this phase were modified.
- [ ] No source file was added, renamed, moved, or deleted.
- [ ] No circular dependency was introduced.
- [ ] Domain and protocol modules do not import orchestration, reporting, or concrete storage implementations.
- [ ] No compatibility alias, redirect, deprecated identifier, generic registry, or string-key dispatch was added.

### Typing and validation audit
- [ ] Ruff formatting and linting pass.
- [ ] Pyright strict mode passes for all changed files.
- [ ] Pylint passes at the project threshold without suppressing newly introduced defects.
- [ ] Pydantic models reject extra fields and are frozen.
- [ ] Dataclasses are frozen and slotted unless mutability is scientifically necessary and documented.
- [ ] No `Any`, unchecked cast, mutable module-level collection, or raw configuration dictionary remains.

### Test audit
- [ ] Every test file listed by this phase exists and contains meaningful assertions.
- [ ] Tests verify scientific invariants, invalid inputs, unavailable outcomes, and deterministic behavior—not only happy paths.
- [ ] Tests do not duplicate implementation logic or merely assert that functions return a value.
- [ ] Focused tests pass first; then the complete test suite passes with pytest-xdist.
- [ ] Hypothesis tests use bounded strategies consistent with scientific domains.

### Repository audit
- [ ] `git diff --stat` contains only intended files.
- [ ] No generated output, cache, temporary file, notebook, profiling file, or local path leaked into the repository.
- [ ] No commit or push was performed by the implementing agent.

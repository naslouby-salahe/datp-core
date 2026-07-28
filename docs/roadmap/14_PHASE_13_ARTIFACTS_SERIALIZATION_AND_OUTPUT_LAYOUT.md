# Phase 13 — Artifacts, Safe Serialization, and Output Layout

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

Implement deterministic experiment-output coordinates, typed manifests, safe serialization, checksum/schema validation, atomic completion, reload verification, and stale-output cleanup. Keep reusable data under `data/` and experiment-specific artifacts under `outputs/`.

## Entry criteria

- Phases 02–12 are complete.
- All artifact-bearing result models exist.
- Scientific coordinate ordering is resolved.

## Source files permitted to change

- `datp_core/artifacts/coordinates.py`
- `datp_core/artifacts/layout.py`
- `datp_core/artifacts/manifest.py`
- `datp_core/artifacts/serialization.py`
- `datp_core/artifacts/reload_validation.py`
- `datp_core/artifacts/store.py`
- `datp_core/artifacts/completion.py`
- `datp_core/orchestration/stages/finalize.py`

## Output root contract

```text
outputs/
└── experiment=<EXPERIMENT_ID>/
    └── population=<POPULATION_ID>/
        └── seed=<SEED>/
            └── model=<MODEL_ID>/
                └── [model_parameter=<VALUE>/]
                    └── checkpoint=<ROUND>/
                        └── threshold=<THRESHOLD_METHOD>/
                            └── quantile=<VALUE>/
                                └── [coverage=<VALUE>/]
                                    └── calibration_size=<VALUE>/
                                        └── [shrinkage=<VALUE>/]
                                            └── [summary_coefficient=<VALUE>/]
                                                └── [group_count=<VALUE>/]
                                                    └── replicate=<VALUE>/
                                                        └── [temporal_state=<VALUE>/]
```

Dirichlet condition belongs between population and seed when active. Coordinates absent from a cell are omitted. No generic `parameter=value` bag is permitted; every coordinate has a typed field and canonical label.

## Artifact grouping

Within the leaf or nearest reusable parent, store:

- resolved experiment manifest;
- model/training histories and safe tensor states;
- checkpoint candidates and decision;
- immutable scores;
- eligibility/cohort/subsample manifests;
- thresholds and diagnostics;
- metrics and unavailable outcomes;
- analysis and decisions;
- reporting outputs;
- artifact inventory;
- `COMPLETE` marker.

Do not copy canonical or preprocessed data into outputs. Refer to their manifests by checksum and path.

## Required dataclasses/models

- `ArtifactCoordinate`
- `ExperimentCoordinate`
- `ModelCoordinate`
- `ThresholdCoordinate`
- `AnalysisCoordinate`
- `ArtifactManifest`
- `ExperimentManifest`
- `ArtifactInventoryEntry`
- `ArtifactInventory`
- `ReloadValidationResult`
- `CompletionState`

## Safe serialization

- SafeTensors: model and checkpoint tensor states.
- skops: fitted preprocessing estimators, with trusted types explicitly validated.
- Parquet/PyArrow: tabular data, histories, scores, thresholds, metrics, analyses.
- Pydantic JSON: protocols, manifests, summaries, decisions, warnings.
- JSON schema or Arrow schema: feature and table schemas.
- Unsafe pickle, joblib pickle, arbitrary object serialization, and executable codecs are prohibited.

Optimizer objects are never serialized. Store optimizer identity, configured values, and aggregate summaries only.

## Manifest requirements

Every manifest records:

- descriptive IDs;
- all active scientific coordinates;
- resolved protocol checksum;
- source/canonical/processed data references;
- model/checkpoint/score checksums;
- expected artifacts;
- capability and anchor-gate status;
- schema identifiers;
- completion state.

No timestamp is part of identity or required manifest semantics.

## Reload validation

Reload and validate:

- model tensor names, shapes, dtypes, architecture identity, and checksum;
- checkpoint round and model coordinate;
- preprocessing estimator type, feature order, and transform equivalence;
- optimizer summary schema;
- Arrow schemas and table semantic identifiers;
- protocol and experiment manifests;
- unavailable/suppression results;
- artifact inventory completeness.

A successfully written file that fails semantic reload is invalid.

## Completion

- Write into a temporary sibling directory.
- Validate expected artifacts and reload them.
- Create artifact inventory.
- Atomically publish.
- Write `COMPLETE` last.
- An output without `COMPLETE` is incomplete and must be deleted before rerun.

## Test files to implement

- `tests/unit/artifacts/test_coordinates.py`
- `tests/unit/artifacts/test_layout.py`
- `tests/unit/artifacts/test_manifest.py`
- `tests/unit/artifacts/test_serialization.py`
- `tests/unit/artifacts/test_reload_validation.py`
- `tests/unit/artifacts/test_store.py`
- `tests/unit/artifacts/test_completion.py`
- `tests/unit/orchestration/stages/test_finalize.py`
- `tests/integration/artifacts/test_model_round_trip.py`
- `tests/integration/artifacts/test_preprocessing_round_trip.py`
- `tests/integration/artifacts/test_parquet_schema_round_trip.py`
- `tests/integration/artifacts/test_atomic_experiment_publication.py`
- `tests/integration/artifacts/test_deterministic_output_paths.py`
- `tests/integration/artifacts/test_incomplete_output_cleanup.py`
- `tests/architecture/test_no_unsafe_serialization.py`
- `tests/architecture/test_outputs_do_not_duplicate_processed_data.py`

## Required negative tests

- Path collision between two scientific coordinates.
- Timestamp/run ID/job ID included in path.
- Pickle or joblib serialization.
- Wrong model state loaded into a coordinate.
- Manifest checksum mismatch.
- Missing expected artifact with `COMPLETE` attempted.
- Processed data copied under output.

## Exit criteria

- Every output path is deterministic and collision-tested.
- Every persisted artifact uses an approved format and passes semantic reload.
- `COMPLETE` is trustworthy.
- Data/output separation is enforced.
- All Phase 13 tests and audits pass.

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

# Phase 04 — Canonical Data and Reusable Preprocessing

## Scientific authority and interpretation rules

- Before planning, editing, testing, or auditing this phase, read **`/home/naslouby/Projects/datp-core/docs/Journal_Extension_Master_Roadmap.md`** in full. It is the authoritative source for the scientific question, permitted evidence, dataset boundaries, numerical grids, metrics, inference, and claim restrictions.
- Use descriptive implementation identities only. Never introduce opaque lettered populations, numbered threshold policies, numbered baselines, compatibility aliases, redirects, deprecated names, or duplicated identifiers.
- The centralized reference is an independent pooled-data pipeline. It is never a federated threshold method and never consumes scores produced by a federated model.
- The confirmatory comparison reuses one selected FedAvg detector, one preprocessing state, one client population, one calibration set, and one held-out score set per seed. Only threshold-calibration scope changes.
- Calibration is benign-only. Attack labels and held-out outcomes cannot select models, checkpoints, quantiles, shrinkage values, statistical coefficients, clients, or group assignments.
- CICIoT2023 model input must first apply its declared outcome-blind eligibility gate: retain only recognized normalized labels with finite declared features, persist both exclusion signals with stable source provenance, and apply the same gate before every client construction, split, fitted-state operation, calibration, and evaluation. Canonical rows remain lossless; no imputation, zero-fill, clipping, capping, infinity replacement, or label inference is permitted.
- The implementation source tree is locked to the files already created under `datp_core/`. Do not create, rename, move, delete, or replace source files. Test files may be created only when explicitly named in this roadmap.
- Scientific values absent from the source of truth must remain unresolved. Do not infer them from memory, historical repositories, convenient defaults, or common practice. Record the blocker in `01_PHASE_MASTER_LOG.md`.
- Python protocol declarations replace YAML. Protocol objects are immutable, fully typed, explicitly constructed, validated as one graph at startup, and serialized into every resolved experiment manifest.
- Do not add backward compatibility, migration adapters, aliases, generic registries, service locators, untyped dictionaries, `Any`, silent fallbacks, or catch-all modules.
- Do not add comments that restate code. Express intent through names, enums, types, validated records, and small functions.
- Reusable canonical and preprocessed data belong under `data/`. Experiment-specific trained states, scores, thresholds, evaluations, analyses, and reports belong under `outputs/`.

## Objective

Implement reusable, deterministic canonical and preprocessed data assets under `data/`. Prevent every experiment from repeating data loading, splits, fitting, or transformations when all data and preprocessing coordinates match.

## Entry criteria

- Phase 03 is complete.
- Canonical dataset materialization is verified.
- Exact preprocessing semantics are present in the source of truth or explicitly blocked.

## Source files permitted to change

- `datp_core/preprocessing/models.py`
- `datp_core/preprocessing/federated.py`
- `datp_core/preprocessing/validation.py`
- `datp_core/centralized_reference/preprocessing.py`
- `datp_core/artifacts/coordinates.py`
- `datp_core/artifacts/layout.py`
- `datp_core/artifacts/serialization.py`
- `datp_core/artifacts/reload_validation.py`
- `datp_core/artifacts/store.py`

Only data-related path and serialization responsibilities may be implemented in artifact files during this phase. Experiment-output behavior remains Phase 13.

## Data directory contract

```text
data/
├── raw/                                  # Read-only source or symlink.
├── canonical/
│   └── <DATASET_ID>/
│       ├── data/                         # Canonical Parquet partitions.
│       ├── dataset_manifest.json
│       ├── schema.json
│       └── COMPLETE
└── processed/
    └── <DATASET_ID>/
        └── population=<POPULATION_ID>/
            └── partition_seed=<SEED>/
                └── split=<SPLIT_PROTOCOL_ID>/
                    └── preprocessing=<PREPROCESSING_PROTOCOL_ID>/
                        ├── federated/
                        │   ├── client=<CLIENT_ID>/
                        │   │   ├── train.parquet
                        │   │   ├── calibration.parquet
                        │   │   ├── evaluation.parquet
                        │   │   ├── [future_recalibration.parquet]
                        │   │   └── state.skops
                        │   ├── schema.json
                        │   ├── split_manifest.parquet
                        │   ├── preprocessing_manifest.json
                        │   └── COMPLETE
                        └── centralized_reference/
                            ├── train.parquet
                            ├── calibration.parquet
                            ├── evaluation.parquet
                            ├── [future_recalibration.parquet]
                            ├── state.skops
                            ├── schema.json
                            ├── preprocessing_manifest.json
                            └── COMPLETE
```

A coordinate component is present only when it changes the reusable data. Model, threshold, quantile, calibration subsample size, and analysis seed never appear in reusable preprocessing paths.

## Reuse semantics

A processed asset is reusable only when all of these match:

- raw dataset source checksums;
- canonical schema checksum;
- dataset identity;
- population identity and population-construction protocol;
- partition seed;
- split protocol;
- preprocessing protocol;
- feature order;
- fitted-state type and safe-serialization format;
- software protocol manifest checksum for scientifically relevant transformation semantics.

A matching directory without a valid manifest and `COMPLETE` marker is incomplete and must be deleted before rebuilding. Never “repair” partial files in place.

## Required dataclasses

In `preprocessing/models.py`:

- `PreprocessingProtocolId`
- `TransformedFeature`
- `TransformedSchema`
- `FittedPreprocessingState`
- `ClientPreprocessingResult`
- `PooledPreprocessingResult`
- `PreprocessingManifest`
- `PreprocessingValidationReport`
- `ReusableDataCoordinate`

Use typed tuples for ordered columns. No dict of column-to-type.

## Federated preprocessing

`preprocessing/federated.py` must:

- fit only on the declared client training partition;
- never fit on calibration, future recalibration, or evaluation rows;
- preserve one fitted state per client when the locked protocol is client-local;
- use one shared state only if the source truth explicitly requires it;
- transform all partitions with the corresponding fitted state;
- produce consistent output feature order and dimension across clients when required by one federated model;
- serialize fitted estimators with skops;
- reject unknown transformers during safe reload.

Do not encode a default scaler or imputer. The exact pipeline must come from the source of truth.

## Centralized preprocessing

`centralized_reference/preprocessing.py` must:

- pool only the training rows permitted by the centralized reference protocol;
- fit a distinct pooled state;
- transform pooled calibration and evaluation data independently of federated fitted states;
- never reuse a client-fitted state;
- store its reusable output under the `centralized_reference/` data branch.

## Validation

`preprocessing/validation.py` and `artifacts/reload_validation.py` must verify:

- no source-row overlap across partitions;
- fit provenance references training rows only;
- no future rows influence historical fitting;
- no attack-labelled row enters benign autoencoder training or benign threshold calibration;
- transformed values are finite;
- transformed schema and feature order match model input requirements;
- safe reload returns the expected estimator classes;
- transform-before-save and transform-after-reload are numerically equivalent within a declared serialization tolerance;
- reusable data manifests are complete and immutable.

## Atomicity and concurrency

Use a temporary sibling directory and atomic rename. Use `filelock` only at the final reusable coordinate to prevent duplicate parallel publication. A process finding a completed matching asset revalidates and reuses it.

## Test files to implement

- `tests/unit/preprocessing/test_models.py`
- `tests/unit/preprocessing/test_federated_preprocessing.py`
- `tests/unit/preprocessing/test_preprocessing_validation.py`
- `tests/unit/centralized_reference/test_preprocessing.py`
- `tests/unit/artifacts/test_data_coordinates.py`
- `tests/unit/artifacts/test_data_layout.py`
- `tests/unit/artifacts/test_preprocessing_serialization.py`
- `tests/integration/preprocessing/test_reusable_federated_data.py`
- `tests/integration/preprocessing/test_reusable_centralized_data.py`
- `tests/integration/preprocessing/test_preprocessing_reload_equivalence.py`
- `tests/integration/preprocessing/test_preprocessing_cache_invalidation.py`
- `tests/integration/preprocessing/test_preprocessing_atomic_publication.py`

## Required test cases

- Same coordinates reuse exactly the same completed asset.
- Changed split seed, schema, population, or preprocessing protocol creates a distinct asset.
- Changed model or threshold method does not duplicate processed data.
- Partial asset is deleted and rebuilt.
- Client-fitted and pooled-fitted states cannot be interchanged.
- Fitting sees no calibration/test/future rows.
- Unsafe or unknown skops types are rejected.
- Reloaded transforms equal pre-save transforms.

## Exit criteria

- Canonical and preprocessed data are reusable under deterministic `data/` coordinates.
- Experiment output directories contain no copied canonical or transformed datasets.
- Federated and centralized preprocessing states are independently fitted and safely stored.
- Data reuse never bypasses schema, provenance, or leakage validation.
- All Phase 04 tests and audits pass.

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

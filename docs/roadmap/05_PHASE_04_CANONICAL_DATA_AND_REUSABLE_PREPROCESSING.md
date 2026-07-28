# Phase 03 — Dataset Audit and Capability Contracts

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

Implement exact dataset schemas, readers, provenance, materialization contracts, and typed capabilities for N-BaIoT, CICIoT2023, and Edge-IIoTset. Dataset facts are verified from the raw files; scientific use and interpretation remain governed by `/home/naslouby/Projects/datp-core/docs/Journal_Extension_Master_Roadmap.md`.

## Entry criteria

- Phase 02 is complete.
- Dataset roots are reachable through the project’s read-only raw-data path.
- The agent has inspected the current raw inventory before encoding schemas.

## Source files permitted to change

- `datp_core/datasets/models.py`
- `datp_core/datasets/capabilities.py`
- `datp_core/datasets/catalogue.py`
- `datp_core/datasets/nbaiot/schema.py`
- `datp_core/datasets/nbaiot/capabilities.py`
- `datp_core/datasets/nbaiot/reader.py`
- `datp_core/datasets/nbaiot/materialize.py`
- `datp_core/datasets/ciciot2023/schema.py`
- `datp_core/datasets/ciciot2023/capabilities.py`
- `datp_core/datasets/ciciot2023/reader.py`
- `datp_core/datasets/ciciot2023/materialize.py`
- `datp_core/datasets/edge_iiotset/schema.py`
- `datp_core/datasets/edge_iiotset/capabilities.py`
- `datp_core/datasets/edge_iiotset/reader.py`
- `datp_core/datasets/edge_iiotset/chronology.py`
- `datp_core/datasets/edge_iiotset/materialize.py`
- dataset package `__init__.py` files only to keep them empty.

## Libraries

- Polars lazy scans for CSV ingestion and transformation.
- PyArrow for canonical schemas and Parquet metadata.
- Pandera Polars models for executable validation.
- Standard library `pathlib`, `hashlib`, and dataclasses.

Do not use pandas in ingestion code unless a third-party function strictly requires it at a later stage.

## Required dataclasses

In `datasets/models.py`, define frozen slotted records:

- `RawSourceFile`
- `RawDatasetInventory`
- `CanonicalColumn`
- `CanonicalSchema`
- `SourceRowReference`
- `DatasetRowIdentity`
- `DatasetExclusion`
- `DatasetValidationIssue`
- `DatasetValidationReport`
- `MaterializedDataset`
- `ChronologyValidation`
- `AttackAssignmentCapability`

Avoid a generic `DatasetRecord` with optional fields. Dataset-specific rows remain Polars frames validated by schema.

## Capability models

In `datasets/capabilities.py`, implement frozen typed contracts:

- `PhysicalClientCapability`
- `FamilyTaxonomyCapability`
- `ChronologyCapability`
- `AttackAssignmentCapability`
- `MetricCapability`
- `TemporalCapability`
- `ExternalValidationCapability`
- `DatasetCapabilities`

Every capability has a status, evidence, and reason. A boolean alone is insufficient for conditional or unavailable behavior.

## N-BaIoT requirements

### `schema.py`

- Encode the exact audited 115 numeric feature columns in source order.
- Encode the nine physical-device identities derived from paths.
- Encode benign file identity and attack family/subtype identities derived from paths.
- Encode the physical-device family taxonomy only when the source truth or audited project documentation defines it unambiguously.
- Reject archives, documentation files, and non-extracted inputs.

### `capabilities.py`

Declare:

- physical client identity supported;
- family taxonomy supported only if fully verified;
- chronology unavailable;
- per-client attack assignment supported;
- confirmatory FPR and attack-sensitive metrics supported subject to denominators;
- natural-device and controlled-heterogeneity populations supported;
- external-validation role not applicable because this is the anchor dataset.

### `reader.py`

- Use lazy scans and explicit dtypes.
- Derive labels and identities from audited path components.
- Reject non-finite values according to an explicit data-quality rule; never silently fill.
- Preserve source file and source row provenance.
- Never derive chronology from file order.

### `materialize.py`

- Produce canonical Parquet partitions under `data/canonical/dataset=NBAIOT/`.
- Publish atomically after schema and count validation.
- Include a manifest and schema checksum.
- Reuse an existing matching canonical asset only after full manifest validation.

## CICIoT2023 requirements

### `schema.py`

- Encode the exact 39 numeric features plus canonical label field from merged files.
- Preserve mixed case and spaces only at raw-read boundary; canonical names are normalized once and recorded in a raw-to-canonical mapping.
- Encode all audited label values.
- Treat `Protocol Type` as a feature, never a label.
- Preserve sparse protocol indicators.

### `capabilities.py`

Declare:

- physical client identity unavailable in the processed artifact;
- family taxonomy unavailable;
- chronology unavailable;
- file-defined pseudo-clients supported as an applicability boundary only;
- attack assignment supported at file-row level but not as original physical-device assignment;
- device-aware and temporal claims prohibited.

### `reader.py`

- Read only the audited merged labelled files used by the project population.
- Normalize labels deterministically.
- Handle the audited infinite/empty `Rate` anomalies explicitly and report counts.
- Do not globally drop informative sparse columns.
- Preserve source file and row provenance.

### `materialize.py`

- Publish canonical Parquet under `data/canonical/dataset=CICIOT2023/`.
- Preserve file identity for later pseudo-client construction.
- Record that the original 105-device topology cannot be reconstructed from the available artifact.

## Edge-IIoTset requirements

### `schema.py`

- Encode the exact audited feature and label columns from the selected CSV representation.
- Normalize mixed numeric, string, hexadecimal, IP, MQTT, protocol, and label fields through explicit typed transformations.
- Preserve raw timestamp text separately from parsed chronology during audit.
- Encode the ten benign sensor-group identities from source folders.

### `capabilities.py`

Declare:

- static sensor-group identity supported for benign data;
- per-client attack assignment unavailable under the audited artifact;
- attack-sensitive cross-client metrics unavailable;
- family taxonomy unavailable;
- chronology conditional and valid only for audited groups;
- static external benign-equity and one-shot temporal populations supported within these boundaries.

### `reader.py`

- Read normal and attack sources separately.
- Never attach attack rows to sensor clients without verified evidence.
- Preserve source folder, file, row, and raw timestamp provenance.

### `chronology.py`

- Parse only genuine capture times.
- Reject address literals or malformed values as chronology.
- Preserve stable source-row order for equal timestamps.
- Return a typed validation result per group.
- Exclude invalid groups only from temporal populations, not automatically from static benign analysis.

### `materialize.py`

Publish separate canonical assets:

- static benign sensor-group data;
- valid temporal benign group data;
- unassigned attack data;
- chronology validation report.

## Catalogue requirements

`datasets/catalogue.py` uses exhaustive `match` on `DatasetId`. It returns typed reader/materializer/capability objects. No mutable registry or plugin dictionary.

## Test files to implement

### Unit schema and capability tests

- `tests/unit/datasets/test_dataset_models.py`
- `tests/unit/datasets/test_dataset_capabilities.py`
- `tests/unit/datasets/test_dataset_catalogue.py`
- `tests/unit/datasets/nbaiot/test_schema.py`
- `tests/unit/datasets/nbaiot/test_capabilities.py`
- `tests/unit/datasets/nbaiot/test_reader.py`
- `tests/unit/datasets/ciciot2023/test_schema.py`
- `tests/unit/datasets/ciciot2023/test_capabilities.py`
- `tests/unit/datasets/ciciot2023/test_reader.py`
- `tests/unit/datasets/edge_iiotset/test_schema.py`
- `tests/unit/datasets/edge_iiotset/test_capabilities.py`
- `tests/unit/datasets/edge_iiotset/test_reader.py`
- `tests/unit/datasets/edge_iiotset/test_chronology.py`

### Integration materialization tests

- `tests/integration/datasets/test_nbaiot_materialization.py`
- `tests/integration/datasets/test_ciciot2023_materialization.py`
- `tests/integration/datasets/test_edge_iiotset_materialization.py`
- `tests/integration/datasets/test_canonical_data_reuse.py`

Use small audited fixtures generated in-memory or from minimal fixture CSVs under `tests/fixtures/`; do not copy full datasets into the repository. `tests/fixtures/` may contain only the exact miniature files used by these named tests.

## Required negative tests

- Wrong column order or missing feature.
- Unknown label or path-derived identity.
- Non-finite numeric value not covered by an explicit rule.
- Attempt to claim chronology from file order.
- Attempt to assign Edge attack rows to sensor clients.
- Attempt to construct physical CICIoT clients.
- Reuse of a canonical asset with mismatched checksum or schema.

## Exit criteria

- All three datasets have executable exact schemas and evidence-backed capability contracts.
- Canonical materialization is deterministic and atomic.
- Invalid scientific uses fail before population or experiment construction.
- No raw-data fact was invented from the scientific roadmap alone.
- All Phase 03 tests and audits pass.

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

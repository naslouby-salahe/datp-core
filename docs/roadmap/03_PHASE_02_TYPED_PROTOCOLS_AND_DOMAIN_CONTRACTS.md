# Phase 02 — Typed Protocols and Domain Contracts

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

Implement the immutable Python-native declaration system that replaces YAML, together with validated scalar values, provenance records, cross-package Protocol interfaces, and whole-graph startup validation.

## Entry criteria

- Phase 01 is complete.
- Descriptive enums are stable.
- Any exact values absent from `/home/naslouby/Projects/datp-core/docs/Journal_Extension_Master_Roadmap.md` are listed as blockers in the phase master log.

## Source files permitted to change

- `datp_core/domain/values.py`
- `datp_core/domain/provenance.py`
- `datp_core/domain/contracts.py`
- `datp_core/protocols/models.py`
- `datp_core/protocols/seeds.py`
- `datp_core/protocols/splits.py`
- `datp_core/protocols/training.py`
- `datp_core/protocols/calibration.py`
- `datp_core/protocols/metrics.py`
- `datp_core/protocols/statistics.py`
- `datp_core/protocols/traffic_rates.py`
- `datp_core/protocols/anchor.py`
- `datp_core/protocols/populations.py`
- `datp_core/protocols/experiments.py`
- `datp_core/protocols/runtime.py`
- `datp_core/protocols/validation.py`
- `datp_core/protocols/__init__.py`

The package initializer must not collect or re-export all declarations.

## Libraries

- Pydantic v2 for frozen declaration models, discriminated unions, field constraints, and `TypeAdapter` validation.
- Standard-library frozen slotted dataclasses for small domain values and records.
- `pathlib` for project-relative paths.
- No configuration framework, YAML parser, Hydra, OmegaConf, or environment-variable-driven scientific override.

## Scalar value objects

Define frozen slotted dataclasses or validated Pydantic root models in `domain/values.py`. Each type validates its domain once and removes repeated guards elsewhere.

Required values:

- `Seed`
- `Ratio`
- `Quantile`
- `CoverageTarget`
- `CalibrationSize`
- `ClientCount`
- `RoundNumber`
- `LocalEpochCount`
- `BatchSize`
- `LearningRate`
- `DirichletConcentration`
- `ProximalCoefficient`
- `DittoRegularization`
- `ShrinkageWeight`
- `SummaryCoefficient`
- `ConfidenceLevel`
- `BootstrapReplicateCount`
- `SubsampleReplicateCount`
- `GroupCount`
- `ThresholdValue`
- `ScoreValue`
- `MetricValue`
- `ByteCount`
- `TrafficRatePerDay`
- `Checksum`

Do not wrap plain identifiers already represented by enums. Do not create arithmetic-heavy value classes; validation and unit clarity are their purpose.

## Provenance dataclasses

In `domain/provenance.py`, define frozen slotted records:

- `SourceFileProvenance(path, size_bytes, checksum, row_count)`
- `DatasetProvenance(dataset, sources, schema_checksum)`
- `CodeProvenance(revision, dirty_state)` only when the repository can supply it without using it as execution identity.
- `ProtocolProvenance(resolved_manifest_checksum)`
- `CitationProvenance(citation_key, source_title, source_locator)`
- `TrafficRateProvenance(kind, source, units, applicable_population, citation)`
- `ArtifactProvenance(path, format, checksum, schema_checksum)`

Provenance records contain no timestamps and are serializable without custom codecs.

## Protocol interfaces

In `domain/contracts.py`, define runtime-checkable `typing.Protocol` interfaces only where multiple implementations exist:

- `DatasetReader`
- `DatasetMaterializer`
- `PopulationBuilder`
- `Preprocessor`
- `Trainer`
- `CheckpointSelector`
- `ScoreGenerator`
- `FederatedThresholdEstimator`
- `CentralizedThresholdEstimator`
- `MetricEvaluator`
- `StageHandler`
- `ArtifactSerializer`
- `ArtifactStore`
- `StageHook`

Protocols expose typed methods and result objects; they do not use dict payloads. Do not introduce abstract base classes when structural typing suffices.

## Frozen protocol models

Every model uses `ConfigDict(frozen=True, extra='forbid')`. No scientific field has a default. Runtime-only defaults are also avoided unless they are purely representational and cannot affect execution.

### Core declarations in `protocols/models.py`

- `SeedCohort`
- `FractionalSplitProtocol`
- `TemporalSplitProtocol`
- `CheckpointProtocol`
- `AutoencoderProtocol`
- `OptimizerProtocol`
- `FedAvgProtocol`
- `FedProxProtocol`
- `DittoProtocol`
- `CalibrationEligibilityProtocol`
- `QuantileProtocol`
- `CalibrationSizeProtocol`
- `FixedShrinkageProtocol`
- `SizeAwareShrinkageProtocol`
- `ConformalProtocol`
- `FederatedStatisticsProtocol`
- `MetricProtocol`
- `StatisticalInferenceProtocol`
- `TrafficRateEvidence`
- `PopulationDeclaration`
- `ExperimentDeclaration`
- `AnchorReference`
- `AnchorDecisionProtocol`
- `RuntimeProtocol`
- `ResolvedProtocolGraph`

`RuntimeProtocol` declares separate project-relative `data`, `outputs`, and `results` roots. `results` is the dedicated publication-extraction root and cannot be redirected under `outputs`.

Use discriminated unions for model-specific and threshold-specific declarations. An experiment cannot carry irrelevant fields such as a proximal coefficient for FedAvg.

## Required scientific declarations

Declare only values explicitly supported by the current source of truth:

- Canonical quantile `0.95`.
- Quantile sensitivity: `0.90`, `0.95`, `0.975`, `0.99`.
- Minimum benign calibration support: `100`.
- Calibration sizes: `50`, `100`, `250`, `500`, `1000`, `5000`.
- Fixed shrinkage weights: `0.00`, `0.25`, `0.50`, `0.75`, `1.00`.
- Controlled heterogeneity concentrations: `0.1`, `0.3`, `0.5`, `1.0`, `10.0`, plus an explicit IID condition represented by an enum, not a fake infinite concentration.
- FedProx coefficients: `0.001`, `0.01`, `0.1`, `1.0`; zero remains the FedAvg condition and is not declared as FedProx.
- Conformal target coverage `0.95` and significance `0.05`.
- Summary-statistics sensitivity coefficients: `2.0`, `2.5`, `3.0`.
- Journal checkpoint candidates: rounds `25`, `50`, `75`, `100`, `125`, `150`, `200`; maximum round `200`.
- Local epochs `1` for the locked FedAvg core.
- Temporal split: `0.55`, `0.15`, `0.10`, `0.20` in historical train, historical calibration, future recalibration, future evaluation order.
- Ditto absorption bands: retained at or above `0.75` of the FedAvg threshold-scope effect, partial from `0.25` to below `0.75`, largely absorbed below `0.25`; alternative-route absolute difference `0.05`.
- Confirmatory confidence level `0.95` and paired seed count `10`.

Do not invent exact seed integers, architecture widths, learning rate, batch size, optimizer details, non-temporal split ratios, bootstrap replicate count, near-zero warning cutoff, temporal materiality cutoff, or anchor tolerances when absent. The declaration type may require them, but the resolved graph must fail with `UnresolvedScientificValueError` until they are scientifically supplied.

## Module responsibilities

- `seeds.py`: immutable seed cohorts only; no random-number generators.
- `splits.py`: split declarations and sum/order validation.
- `training.py`: centralized, FedAvg, FedProx, and Ditto declarations with no execution code.
- `calibration.py`: eligibility, quantiles, sizes, shrinkage, conformal, and federated-statistics declarations.
- `metrics.py`: required metric sets per cohort and explicit undefined/suppression rules.
- `statistics.py`: paired inference and multiplicity declarations.
- `traffic_rates.py`: typed tuple of evidence records; empty tuple is valid and means alert-burden output is suppressed.
- `anchor.py`: historical reference values and explicit tolerances only when present in source truth.
- `populations.py`: typed population declarations referencing capabilities, not implementing construction.
- `experiments.py`: complete experiment catalogue as a tuple of `ExperimentDeclaration`; no registry dictionary.
- `runtime.py`: paths, CUDA requirement, workers, overwrite behavior, and campaign options that cannot alter science.
- `validation.py`: validate the complete cross-reference graph and return one `ResolvedProtocolGraph`.

## Graph validation rules

Validation must reject:

- duplicate IDs;
- missing referenced protocols;
- unsupported population/method/model combinations;
- centralized methods in federated experiments;
- threshold comparisons that use different model or score coordinates;
- attack-sensitive metrics on populations without attack assignment;
- temporal experiments on populations without chronology;
- family thresholding without a family taxonomy;
- grouped thresholding without an approved assignment input;
- deployment fallback clients in confirmatory cohorts;
- alert burden without valid rate evidence;
- unresolved mandatory scientific values;
- experiment parameters not belonging to declared grids;
- mutable declarations or environment-based scientific overrides.

## Test files to implement

- `tests/unit/domain/test_values.py`
- `tests/unit/protocols/test_models.py`
- `tests/unit/protocols/test_seed_declarations.py`
- `tests/unit/protocols/test_split_declarations.py`
- `tests/unit/protocols/test_training_declarations.py`
- `tests/unit/protocols/test_calibration_declarations.py`
- `tests/unit/protocols/test_metric_declarations.py`
- `tests/unit/protocols/test_statistical_declarations.py`
- `tests/unit/protocols/test_anchor_declarations.py`
- `tests/unit/protocols/test_population_declarations.py`
- `tests/unit/protocols/test_experiment_declarations.py`
- `tests/unit/protocols/test_protocol_graph_validation.py`
- `tests/property/test_scientific_value_objects.py`

Required assertions include immutability, extra-field rejection, boundary values, cross-reference failure, unresolved-value failure, and deterministic JSON serialization.

## Exit criteria

- The entire protocol graph is typed, immutable, and validated in one call.
- All known source-backed values are declared exactly once.
- Missing mandatory values fail explicitly; no placeholder, `None`, or default permits execution.
- No YAML/config parser dependency remains.
- All tests and global audits pass.

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

# Phase 01 — Scientific Identity and Scope

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

Establish the descriptive scientific vocabulary, evidence hierarchy, scope boundaries, and source-tree guards before any computational implementation. This phase prevents later code from embedding ambiguous shorthand or collapsing distinct scientific objects.

## Entry criteria

- The user-approved `datp_core/` source tree exists exactly as listed.
- `/home/naslouby/Projects/datp-core/docs/Journal_Extension_Master_Roadmap.md` is readable.
- No implementation behavior is assumed from empty files.

## Source files permitted to change

- `datp_core/domain/enums.py`
- `datp_core/domain/errors.py`
- `datp_core/domain/__init__.py`
- `datp_core/__init__.py`

`__init__.py` files remain minimal and must not re-export identities.

## Required enums

Implement with `enum.StrEnum` unless a non-string enum is scientifically necessary.

### Dataset and population identities

- `DatasetId`: `NBAIOT`, `CICIOT2023`, `EDGE_IIOTSET`.
- `PopulationId`: `NBAIOT_NATURAL_DEVICES`, `CICIOT_FILE_CLIENTS`, `NBAIOT_DIRICHLET_CLIENTS`, `EDGE_SENSOR_GROUPS`, `EDGE_TEMPORAL_GROUPS`.

### Evidence and experiment identities

- `EvidenceRole`: `ANCHOR_REPRODUCTION`, `CONFIRMATORY`, `SUPPORTIVE`, `MECHANISM`, `THRESHOLD_VARIANT`, `EXTERNAL_VALIDATION`, `TRAINING_STRESS_TEST`, `APPLICABILITY_BOUNDARY`, `TEMPORAL_BOUNDARY`, `EXPLORATORY`, `OPERATIONAL_TRANSLATION`.
- `ExperimentId` must contain descriptive members for every experiment authorized by the source of truth:
  - `HISTORICAL_DATP_REPRODUCTION`
  - `SHARED_VS_LOCAL_CONFIRMATION`
  - `SHARED_CONSTRUCTION_SENSITIVITY`
  - `QUANTILE_SENSITIVITY`
  - `CONTROLLED_HETEROGENEITY_SWEEP`
  - `FAMILY_AND_GROUPED_GRANULARITY`
  - `PER_CLIENT_SCORE_GEOMETRY`
  - `HETEROGENEITY_BENEFIT_ASSOCIATION`
  - `THRESHOLD_MOVEMENT_TRADEOFF`
  - `CALIBRATION_SIZE_ABLATION`
  - `FIXED_SHRINKAGE_CURVE`
  - `SIZE_AWARE_SHRINKAGE`
  - `LOCAL_CONFORMAL_COVERAGE`
  - `FEDERATED_BENIGN_STATISTICS_COMPARISON`
  - `FEDERATED_QUANTILE_ESTIMATION`
  - `FIXED_COEFFICIENT_STATISTICS_SENSITIVITY`
  - `EDGE_BENIGN_EQUITY_VALIDATION`
  - `CICIOT_FILE_CLIENT_BOUNDARY`
  - `FEDPROX_ABSORPTION_STRESS_TEST`
  - `DITTO_ABSORPTION_STRESS_TEST`
  - `EDGE_ONE_SHOT_RECALIBRATION`
  - `ALERT_BURDEN_TRANSLATION`
  - `GROUP_MEDIAN_SUPPLEMENT`
  - `OPTIONAL_EQUITY_INDICES`

Do not create numeric, alphabetic, generic, or versioned experiment members.

### Model and threshold identities

- `TrainingModelId`: `FEDAVG_AUTOENCODER`, `FEDPROX_AUTOENCODER`, `DITTO_GLOBAL_AUTOENCODER`, `DITTO_PERSONALIZED_AUTOENCODER`.
- `CentralizedModelId`: `CENTRALIZED_AUTOENCODER`.
- `FederatedThresholdMethod`: `SHARED_THRESHOLD`, `LOCAL_THRESHOLD`, `FAMILY_THRESHOLD`, `CLUSTER_THRESHOLD`, `POOLED_SHARED_QUANTILE`, `SAMPLE_WEIGHTED_SHARED_THRESHOLD`, `LOCAL_GLOBAL_SHRINKAGE`, `SIZE_AWARE_SHRINKAGE`, `LOCAL_CONFORMAL_THRESHOLD`, `FEDERATED_BENIGN_STATISTICS`.
- `CentralizedThresholdMethod`: `POOLED_BENIGN_QUANTILE`.

The two threshold enums must remain structurally distinct. No union or dispatcher may accept `CentralizedThresholdMethod` in a federated threshold path.

### Metric, population, and decision identities

- `EvaluationCohort`: `CONFIRMATORY_ELIGIBLE`, `ATTACK_EVALUABLE`, `UNAVAILABLE`, `DEPLOYMENT_FALLBACK`.
- `MetricId` must include all mandatory semantics: `FALSE_POSITIVE_RATE`, `TRUE_POSITIVE_RATE`, `BALANCED_ACCURACY`, `BINARY_MACRO_F1`, `AUROC`, `MEAN_FPR`, `FPR_POPULATION_STANDARD_DEVIATION`, `FPR_COEFFICIENT_OF_VARIATION`, `FPR_IQR`, `FPR_RANGE`, `WORST_CLIENT_FPR`, `TPR_COEFFICIENT_OF_VARIATION`, `P10_BINARY_MACRO_F1`, `WORST_CLIENT_BALANCED_ACCURACY`, `MEAN_CLIENT_MACRO_F1`, `POOLED_MACRO_F1`, `MEAN_CLIENT_BALANCED_ACCURACY`, `ABSOLUTE_THRESHOLD_ERROR`, `RELATIVE_THRESHOLD_ERROR`, `SIGNED_ATTAINMENT_ERROR`, `ABSOLUTE_ATTAINMENT_ERROR`, `TARGET_COVERAGE`, `ACHIEVED_COVERAGE`, `SIGNED_COVERAGE_ERROR`, `ABSOLUTE_COVERAGE_ERROR`, `ALERTS_PER_DAY`, `COMMUNICATION_BYTES`.
- `AvailabilityStatus`: `AVAILABLE`, `UNAVAILABLE`, `UNDEFINED`, `SUPPRESSED`, `INFEASIBLE`.
- `ScientificDecision`: `SUPPORTED`, `DIRECTIONAL_INCONCLUSIVE`, `NO_OBSERVED_ADVANTAGE`, `OPPOSITE_DIRECTION`, `PARTIAL_ABSORPTION`, `FULL_ABSORPTION`, `BOUNDARY_RESULT`, `INFEASIBLE`, `BLOCKED`.
- `ClaimStatus`: `PERMITTED`, `NARROWED`, `BLOCKED`, `UNSUPPORTED`, `SUPPRESSED`.

### Execution identities

Define descriptive enums for stage, split, temporal state, serialization format, warning code, traffic-rate evidence type, checkpoint status, and completion status. Members must correspond exactly to existing stage files and supported semantics.

## Error hierarchy

`datp_core/domain/errors.py` must define a shallow, explicit hierarchy rooted at `DatpCoreError`:

- `ScientificContractError`
- `UnresolvedScientificValueError`
- `CapabilityError`
- `InfeasibleExperimentError`
- `DataIntegrityError`
- `LeakageError`
- `AnchorReproductionError`
- `ProtocolValidationError`
- `SerializationSafetyError`
- `ArtifactIntegrityError`
- `ExecutionStateError`

Do not create one exception per function. Exceptions carry structured context through attributes, not formatted dictionaries.

## Scope enforcement requirements

- No source identifier may use opaque scientific shorthand.
- No code path may treat AUROC as a threshold-policy outcome.
- No code path may describe external Edge evidence as attack-detection equity when per-client attack assignment is unavailable.
- No code path may describe one-shot recalibration as continuous adaptation or concept-drift handling.
- No code path may describe data locality as a formal privacy guarantee.
- No code path may describe message-size estimates as deployment measurements.

## Test files to implement

- `tests/architecture/test_source_tree_is_locked.py`
  - Assert the complete source-file allowlist exactly matches the approved tree.
  - Fail on added, missing, moved, or renamed source files.
- `tests/architecture/test_no_compatibility_surfaces.py`
  - Reject deprecated aliases, import redirects, wildcard re-exports, and compatibility modules.
- `tests/unit/domain/test_enums.py`
  - Assert uniqueness, stable string values, exhaustive expected members, and centralized/federated separation.
- `tests/unit/domain/test_errors.py`
  - Assert hierarchy, structured context, and no accidental broad exception swallowing.
- `tests/scientific/test_scope_vocabulary.py`
  - Assert only permitted claim vocabulary appears in report-facing enums and protocol declarations.

## Implementation sequence

1. Read the source-of-truth identity, scope, terminology, claim, and limitation sections.
2. Define the enum surface before other code imports identities.
3. Define the minimal error hierarchy.
4. Keep package initializers empty except package metadata at the root.
5. Add source-tree and vocabulary tests.
6. Run focused tests and static checks.
7. Record unresolved scientific terminology conflicts in the master log rather than adding aliases.

## Exit criteria

- Every scientific identity required by later phases has one descriptive enum member.
- Centralized and federated threshold identities cannot be confused by type.
- The source-tree allowlist test passes.
- No opaque or compatibility identity remains anywhere under `datp_core/`.
- All Phase 01 tests and global static checks pass.

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

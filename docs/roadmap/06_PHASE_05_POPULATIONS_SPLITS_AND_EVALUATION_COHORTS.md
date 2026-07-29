# Phase 05 — Populations, Splits, and Evaluation Cohorts

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

Construct the five authorized populations, deterministic fractional and chronological splits, integrity manifests, and explicit evaluation cohorts. This phase establishes exactly which clients and rows are valid for each scientific question.

## Preprocessing handoff

After population and split construction, Phase 05 (or the preprocess stage that consumes its manifests) binds each dataset’s ordered model-input features to the locked scientific methods via `build_preprocessing_protocol`. Population builders must not invent alternate scalers or imputation.

## Entry criteria

- Phase 04 is complete, including the architectural cleanup gate:
  - `CANONICAL_RUNTIME` with `require_cuda=True` and `worker_count=6`;
  - explicit `CANONICAL_PROTOCOL_GRAPH` validation without hidden defaults;
  - coherent dataset materialization/cache ownership;
  - artifacts package free of preprocessing model imports;
  - no misleading preprocess CLI that only reports Phase 05 blockage;
  - eleven high-level `StageId` identities separated from branch operation identities.
- Canonical data and reusable preprocessing coordinate rules exist. Population and split construction must consume Phase 04 reusable coordinates and must not refit preprocessing.
- All required split values are explicit in the source of truth; unresolved values block the affected population.
- Phase 05 has not been started: population modules remain empty until this phase begins.

## Source files permitted to change

- `datp_core/populations/models.py`
- `datp_core/populations/capabilities.py`
- `datp_core/populations/nbaiot_natural_devices.py`
- `datp_core/populations/ciciot_file_clients.py`
- `datp_core/populations/nbaiot_dirichlet_clients.py`
- `datp_core/populations/edge_sensor_groups.py`
- `datp_core/populations/edge_temporal_groups.py`
- `datp_core/populations/splits.py`
- `datp_core/populations/integrity.py`
- `datp_core/populations/catalogue.py`
- `datp_core/evaluation/cohorts.py`

## Required dataclasses

In `populations/models.py`:

- `ClientIdentity`
- `ClientMembership`
- `PopulationManifest`
- `PopulationCapabilities`
- `PartitionAssignment`
- `SplitAssignment`
- `SplitManifest`
- `DirichletPartitionDiagnostics`
- `ChronologicalPartitionDiagnostics`
- `PopulationFeasibility`

In `evaluation/cohorts.py` or `evaluation/models.py` as assigned in Phase 10:

- `ClientEligibilityRecord`
- `EvaluationCohortMembership`
- `EvaluationCohortManifest`
- `ClientExclusionReason`

All records are frozen, slotted, and use enum identities.

## Population implementations

### `NBAIOT_NATURAL_DEVICES`

- Exactly nine audited physical devices.
- Device identity is stable across seeds and splits.
- Supports confirmatory FPR evaluation and attack-sensitive metrics when denominators exist.
- Supports family thresholding only with an audited taxonomy.
- Every device remains visible in results even if unavailable for a particular metric.

### `CICIOT_FILE_CLIENTS`

- Construct from the exact audited merged-file boundaries.
- Treat clients as file-defined pseudo-clients only.
- Preserve file identity and source provenance.
- Prohibit physical-device, family, and temporal interpretation.
- Use only as an applicability boundary.

### `NBAIOT_DIRICHLET_CLIENTS`

- Construct exactly twenty synthetic clients.
- Use the declared concentration conditions and partition seed.
- Preserve every generated partition; do not regenerate because balance is inconvenient.
- Emit client size, benign distribution, attack composition when valid, and divergence diagnostics.
- IID is a separate construction condition, not a concentration value.
- Do not claim that synthetic clients preserve physical families unless the construction explicitly does so.

### `EDGE_SENSOR_GROUPS`

- Exactly ten audited benign sensor groups for static external validation.
- Include Modbus in static benign evaluation when its static rows pass schema validation.
- Do not assign attack rows to these clients.
- Mark attack-sensitive metrics unavailable.
- Omit family thresholding.

### `EDGE_TEMPORAL_GROUPS`

- Exactly the groups with verified genuine chronology; expected count is nine under the source programme, but the implementation validates rather than blindly assumes.
- Exclude any group whose chronology fails.
- Use stable ordering for duplicate timestamps.
- Apply chronological ratios in the declared order: historical training, historical calibration, future recalibration, future evaluation.
- Build a matched random-fractional static reference over the same included groups.

## Split semantics

`populations/splits.py` must:

- return manifests of source-row identities, never only frames;
- enforce one assignment per row per split coordinate;
- be deterministic from declared seed and protocol;
- separate model-training seeds from partition seeds when the protocol declares them separately;
- reject a non-temporal split until exact ratios are scientifically declared;
- never stratify or rebalance unless explicitly required by the source truth;
- never create pseudo-time.

## Integrity rules

`populations/integrity.py` must verify:

- no row overlap among train/calibration/recalibration/evaluation;
- client identities and candidate count match population declaration;
- chronological ordering and partition boundaries;
- synthetic-client total row conservation;
- no client silently removed after test inspection;
- population capability profile agrees with dataset capabilities;
- evaluation cohorts are identical across compared threshold methods.

## Evaluation cohort rules

- `CONFIRMATORY_ELIGIBLE`: benign calibration count at least 100 and non-empty benign evaluation denominator. Only this cohort enters confirmatory `CV(FPR)`.
- `ATTACK_EVALUABLE`: valid client-level attack assignment, at least one attack row, and every denominator required by the metric.
- `UNAVAILABLE`: candidate client for which a method or metric is scientifically unavailable; include a typed reason.
- `DEPLOYMENT_FALLBACK`: ineligible client receiving an explicitly declared deployment-only threshold. Never include in confirmatory dispersion or silently merge with eligible clients.

Eligibility is decided before evaluating held-out outcomes and reused across all compared threshold methods.

## Catalogue

Use exhaustive `match` on `PopulationId`. Return a typed builder and capability declaration. No registry dictionary.

## Test files to implement

- `tests/unit/populations/test_models.py`
- `tests/unit/populations/test_capabilities.py`
- `tests/unit/populations/test_nbaiot_natural_devices.py`
- `tests/unit/populations/test_ciciot_file_clients.py`
- `tests/unit/populations/test_nbaiot_dirichlet_clients.py`
- `tests/unit/populations/test_edge_sensor_groups.py`
- `tests/unit/populations/test_edge_temporal_groups.py`
- `tests/unit/populations/test_splits.py`
- `tests/unit/populations/test_integrity.py`
- `tests/unit/populations/test_catalogue.py`
- `tests/unit/evaluation/test_cohorts.py`
- `tests/property/test_split_disjointness.py`
- `tests/property/test_dirichlet_row_conservation.py`
- `tests/integration/populations/test_population_manifests.py`
- `tests/integration/populations/test_temporal_split_no_future_leakage.py`

## Required negative tests

- Fallback client enters confirmatory cohort.
- Edge attack metric is requested.
- CIC physical-device population is requested.
- Temporal population includes invalid chronology.
- A row appears in two splits.
- A synthetic partition drops or duplicates rows.
- Compared threshold methods receive different eligible clients.

## Exit criteria

- Every authorized population has one deterministic builder and capability profile.
- Split manifests are complete, disjoint, and reusable.
- Cohorts are explicit and cannot be conflated.
- Unsupported populations or metrics fail before model training.
- All Phase 05 tests and audits pass.

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

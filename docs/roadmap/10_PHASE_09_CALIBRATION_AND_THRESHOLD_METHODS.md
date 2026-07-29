# Phase 09 — Calibration and Threshold Methods

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

Implement benign-only eligibility, deterministic calibration subsampling, shared/local/family/grouped thresholds, quantile controls, fixed and size-aware shrinkage, finite-sample local conformal calibration, and the benign federated summary-statistics comparator.

## Entry criteria

- Phase 08 is complete.
- Reusable score artifacts exist.
- Calibration values are resolved.
- Grouped thresholding remains infeasible until an approved grouping assignment source is present.

## Source files permitted to change

- `datp_core/calibration/models.py`
- `datp_core/calibration/eligibility.py`
- `datp_core/calibration/sampling.py`
- `datp_core/thresholding/models.py`
- `datp_core/thresholding/quantiles.py`
- `datp_core/thresholding/shared.py`
- `datp_core/thresholding/local.py`
- `datp_core/thresholding/family.py`
- `datp_core/thresholding/grouped.py`
- `datp_core/thresholding/shrinkage.py`
- `datp_core/thresholding/conformal.py`
- `datp_core/thresholding/federated_benign_statistics.py`
- `datp_core/thresholding/dispatch.py`
- `datp_core/orchestration/stages/calibrate.py`
- `datp_core/orchestration/stages/construct_federated_thresholds.py`

## Required dataclasses

In `calibration/models.py`:

- `CalibrationSupport`
- `EligibilityDecision`
- `CalibrationSampleReference`
- `CalibrationSubsample`
- `CalibrationReplicateManifest`
- `CalibrationUnavailableReason`

In `thresholding/models.py`:

- `LocalQuantile`
- `ThresholdAssignment`
- `SharedThresholdResult`
- `LocalThresholdResult`
- `FamilyThresholdResult`
- `GroupedThresholdResult`
- `ShrinkageThresholdResult`
- `ConformalThresholdResult`
- `ClientBenignSummary`
- `PooledVarianceDecomposition`
- `FederatedStatisticsThresholdResult`
- `ThresholdDiagnostic`
- `CommunicationPayload`
- `ThresholdUnavailableResult`

Use discriminated result types rather than one record with many optional fields.

## Eligibility

- Use benign calibration count only.
- Canonical support is at least 100.
- Decide eligibility before held-out evaluation.
- Preserve the same eligible cohort across compared threshold methods.
- Never assign fallback implicitly.
- Record unavailable calibration sizes per client.

## Calibration sampling

- Sizes: 50, 100, 250, 500, 1000, 5000 when supported.
- Sample without replacement.
- Use deterministic nested sampling: a smaller size is a prefix/subset of the same replicate ordering where the protocol requires nested curves.
- Multiple replicates are nested within training seed and never treated as independent seeds.
- Never use test outcomes to choose a replicate.

## Quantile semantics

`quantiles.py` owns every quantile computation:

- exact empirical local quantile;
- pooled quantile;
- weighted shared construction;
- finite-sample conformal rank;
- achieved exceedance calculation.

One declared interpolation/rank method is used consistently. Record it in threshold results.

## Threshold methods

### `SHARED_THRESHOLD`

Arithmetic mean of eligible local benign quantiles. Every eligible client receives the same value. It is not the exact pooled quantile.

### `LOCAL_THRESHOLD`

Each eligible client receives its own benign quantile.

### `FAMILY_THRESHOLD`

Mean of eligible local thresholds within the audited physical-device family. Reject populations without taxonomy. Record family membership and unavailable families.

### `CLUSTER_THRESHOLD`

`grouped.py` accepts a typed, prevalidated client-to-group assignment and computes one group-level threshold from member local thresholds. It must not derive groups, select group count, inspect held-out outcomes, or invent an assignment. Until the scientific source supplies a valid assignment-construction rule, feasibility validation blocks this method.

### Shared construction controls

- Exact pooled benign quantile.
- Sample-weighted shared threshold using declared weighting semantics.

They remain supportive controls and cannot redefine the confirmatory shared threshold.

## Shrinkage

Fixed curve:

`tau_client = lambda * local + (1 - lambda) * shared`

- Evaluate the complete declared curve.
- Zero and one reproduce shared and local endpoints exactly.
- No test-selected preferred value.

Size-aware shrinkage:

- Use one predeclared function of benign calibration count.
- Bound output in `[0, 1]`.
- Apply identical function to all clients.
- Reject execution until the exact function is source-backed.

## Local conformal threshold

- Treat benign reconstruction errors as nonconformity scores.
- Use target coverage 0.95/significance 0.05.
- Apply the exact finite-sample rank rule.
- Record rank index, effective quantile, calibration count, ties, and unavailable conditions.
- Make no universal conditional-coverage claim.

## `FEDERATED_BENIGN_STATISTICS`

Each eligible client may communicate only the predeclared benign summaries:

- count;
- mean;
- variance under explicitly declared denominator semantics;
- permitted benign exceedance counts when required for matched attainment.

Compute:

- sample-count-weighted global mean;
- pooled within-client variance;
- between-client mean-shift term;
- full pooled variance as within plus between;
- between ratio when denominator is positive;
- matched-exceedance coefficient/threshold using only benign information;
- achieved exceedance;
- signed and absolute attainment error;
- absolute and relative threshold error versus the exact pooled benign quantile;
- exact communicated fields and serialized byte counts;
- supplementary fixed-coefficient curve for 2.0, 2.5, 3.0.

The between-client term is mandatory. The comparator remains a shared threshold. It must not claim faithful reproduction of an anomaly-informed method.

## Dispatch

Use exhaustive pattern matching over `FederatedThresholdMethod`. Reject `CentralizedThresholdMethod` by type and runtime guard. No registry dictionary, fallback estimator, or plugin discovery.

## Test files to implement

- `tests/unit/calibration/test_models.py`
- `tests/unit/calibration/test_eligibility.py`
- `tests/unit/calibration/test_sampling.py`
- `tests/unit/thresholding/test_models.py`
- `tests/unit/thresholding/test_quantiles.py`
- `tests/unit/thresholding/test_shared.py`
- `tests/unit/thresholding/test_local.py`
- `tests/unit/thresholding/test_family.py`
- `tests/unit/thresholding/test_grouped.py`
- `tests/unit/thresholding/test_shrinkage.py`
- `tests/unit/thresholding/test_conformal.py`
- `tests/unit/thresholding/test_federated_benign_statistics.py`
- `tests/unit/thresholding/test_dispatch.py`
- `tests/unit/orchestration/stages/test_calibration_and_threshold_stages.py`
- `tests/property/test_quantile_monotonicity.py`
- `tests/property/test_shrinkage_endpoints.py`
- `tests/property/test_pooled_variance_decomposition.py`
- `tests/integration/thresholding/test_threshold_methods_reuse_scores.py`
- `tests/scientific/test_benign_only_threshold_construction.py`

## Required negative tests

- Attack-labelled calibration record.
- Different eligible populations across methods.
- Family threshold without taxonomy.
- Grouped threshold without supplied assignment.
- Size-aware shrinkage without locked function.
- Comparator omitting between-client variance.
- Fixed coefficient promoted to primary matched comparator.
- Centralized method passed to federated dispatcher.

## Exit criteria

- All feasible threshold methods are deterministic, benign-only, and typed.
- Full comparator diagnostics and payload accounting exist.
- Unresolved grouped or size-aware methods fail as infeasible, not through placeholders.
- Scores are reused rather than regenerated.
- All Phase 09 tests and audits pass.

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

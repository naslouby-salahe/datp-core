# Phase 10 — Evaluation Metrics and Statistical Inference

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

Implement exact confusion semantics, client and population metrics, conformal coverage, threshold-estimation diagnostics, communication and operational metrics, descriptive analysis, paired inference, mechanism analysis, temporal quantities, and scientific decision rules.

## Entry criteria

- Phase 09 is complete.
- Metric and statistical protocols are resolved.
- Near-zero mean-FPR warning cutoff and temporal positive-materiality cutoff are explicitly declared; otherwise affected analyses remain blocked.

## Source files permitted to change

- `datp_core/evaluation/models.py`
- `datp_core/evaluation/confusion.py`
- `datp_core/evaluation/metric_semantics.py`
- `datp_core/evaluation/client_metrics.py`
- `datp_core/evaluation/population_metrics.py`
- `datp_core/evaluation/conformal_coverage.py`
- `datp_core/evaluation/threshold_estimation.py`
- `datp_core/evaluation/communication.py`
- `datp_core/evaluation/traffic_rates.py`
- `datp_core/evaluation/operational.py`
- `datp_core/evaluation/controls.py`
- `datp_core/analysis/descriptive.py`
- `datp_core/analysis/inference.py`
- `datp_core/analysis/divergence.py`
- `datp_core/analysis/mechanisms.py`
- `datp_core/analysis/temporal.py`
- `datp_core/analysis/decision_rules.py`
- `datp_core/orchestration/stages/evaluate_federated.py`
- `datp_core/orchestration/stages/analyze.py`

## Libraries

- NumPy for numerical arrays.
- SciPy for BCa bootstrap primitives, Wilcoxon, rank statistics, and distribution functions.
- statsmodels for multiplicity correction and regression diagnostics.
- Pingouin only where it directly supplies a verified paired effect size or statistical table without duplicating custom calculations.
- Polars for typed result tables.

## Required dataclasses

In `evaluation/models.py`:

- `ConfusionCounts`
- `ClientMetricResult`
- `PopulationMetricResult`
- `MetricAvailability`
- `MetricWarning`
- `CoverageResult`
- `ThresholdEstimationResult`
- `CommunicationResult`
- `AlertBurdenResult`
- `UnavailableOutcome`

Analysis result records may reside in their existing analysis files:

- `PairedContrast`
- `BootstrapInterval`
- `WilcoxonResult`
- `RankBiserialResult`
- `MultiplicityResult`
- `AssociationResult`
- `MechanismResult`
- `TemporalRecoveryResult`
- `ScientificDecisionResult`

## Prediction semantics

Attack prediction occurs only when reconstruction error is strictly greater than threshold. The comparison operator is global and immutable.

## Client metrics

Implement exact denominator checks:

- FPR from benign rows.
- TPR from attack rows.
- balanced accuracy only when both exist.
- binary Macro-F1 as the arithmetic mean of benign-class and attack-class F1; undefined class metrics remain unavailable, never zero.
- AUROC from continuous scores only when both classes exist.

## Population metrics

For the confirmatory eligible cohort:

- unweighted mean FPR;
- population standard deviation with `ddof=0`;
- `CV(FPR) = std / mean` with no epsilon;
- undefined CV when mean is exactly zero;
- near-zero warning when positive mean is below the locked cutoff;
- FPR IQR;
- FPR range;
- worst-client FPR.

Where attack evaluation is valid:

- TPR CV with the same denominator rules;
- P10 binary Macro-F1;
- worst-client balanced accuracy;
- mean-client Macro-F1;
- pooled Macro-F1 as a separately labelled control;
- mean-client balanced accuracy.

Every aggregate records candidate, eligible, FPR-evaluable, attack-evaluable, fallback, and unavailable client counts.

## Conformal coverage

For each client and seed:

- target held-out benign coverage;
- achieved held-out benign coverage;
- signed coverage error;
- absolute coverage error;
- finite-sample rank index and effective coverage granularity;
- calibration count;
- calibration-size condition;
- ties and unavailable reason.

Report client-level distribution and seed-level summaries. Do not infer universal conditional validity.

## Threshold estimation

Compute:

- exact pooled benign quantile reference when defined;
- absolute threshold error;
- relative error only for nonzero reference;
- target exceedance;
- achieved benign exceedance;
- signed and absolute attainment error;
- threshold variance across nested calibration replicates;
- sample-efficiency curves.

## Communication

Calculate exact logical fields, element counts, and serialized byte counts for:

- model transmission;
- threshold transmission;
- local quantile transmission;
- benign summary-statistics comparator.

Label as estimated serialized payload, never network deployment measurement.

## Traffic rates and alert burden

`traffic_rates.py` validates typed evidence:

- measured;
- dataset-derived;
- externally cited.

Evidence includes units, source, applicable population, decision granularity, and provenance. `operational.py` generates alerts per client per day only when evidence is applicable. Otherwise return a typed suppression result and do not emit an alert-burden table.

## Fixed-score controls

`controls.py` verifies:

- score and label checksums are identical across threshold methods;
- AUROC is identical within numerical tolerance;
- client and cohort identities are unchanged;
- only thresholds differ.

Any failure is a scientific contract error, not a warning.

## Statistical inference

### Confirmatory contrast

Per seed: shared-threshold `CV(FPR)` minus local-threshold `CV(FPR)`.

- Independent unit: training seed.
- Point estimate: arithmetic mean of ten valid paired seed contrasts.
- Interval: two-sided 95% BCa over paired contrasts.
- Resample paired contrasts only.
- Report all seed contrasts and positive/zero/negative counts.

If BCa is degenerate or fewer than ten valid pairs exist, report diagnostic intervals only and mark the confirmatory decision blocked/inconclusive according to the source rule. Never silently substitute.

### Secondary evidence

- Two-sided paired Wilcoxon with explicit zero handling.
- Matched-pairs rank-biserial correlation, not unpaired Cliff’s delta.
- Holm correction within predeclared secondary families.
- Nested replicates summarized within seed before across-seed inference.
- Spearman plus declared descriptive regression for heterogeneity association.

## Mechanism analyses

`mechanisms.py` is limited to source-authorized analyses:

- family/group granularity when group assignments are available;
- assignment stability only for scientifically supplied grouping assignments/resamples;
- per-client benign and attack score geometry;
- heterogeneity-benefit association;
- threshold movement versus FPR/TPR changes;
- within-group and across-group threshold/FPR dispersion.

It must not implement a group-construction algorithm or a removed calibration representation.

## Decision rules

Encode source-backed outcomes:

- confirmatory support;
- directional but inconclusive;
- no observed advantage;
- opposite direction;
- external consistency/boundary;
- retained/partial/full model absorption;
- temporal degradation with recovery, without recovery, or no detectable degradation;
- suppression and infeasibility.

Decisions use full precision and preserve negative results.

## Test files to implement

- `tests/unit/evaluation/test_models.py`
- `tests/unit/evaluation/test_confusion.py`
- `tests/unit/evaluation/test_metric_semantics.py`
- `tests/unit/evaluation/test_client_metrics.py`
- `tests/unit/evaluation/test_population_metrics.py`
- `tests/unit/evaluation/test_conformal_coverage.py`
- `tests/unit/evaluation/test_threshold_estimation.py`
- `tests/unit/evaluation/test_communication.py`
- `tests/unit/evaluation/test_traffic_rates.py`
- `tests/unit/evaluation/test_operational.py`
- `tests/unit/evaluation/test_controls.py`
- `tests/unit/analysis/test_descriptive.py`
- `tests/unit/analysis/test_inference.py`
- `tests/unit/analysis/test_divergence.py`
- `tests/unit/analysis/test_mechanisms.py`
- `tests/unit/analysis/test_temporal.py`
- `tests/unit/analysis/test_decision_rules.py`
- `tests/property/test_population_metric_invariants.py`
- `tests/property/test_confusion_metric_bounds.py`
- `tests/scientific/test_confirmatory_pairing.py`
- `tests/scientific/test_undefined_metrics_are_not_zero.py`
- `tests/scientific/test_edge_attack_metrics_are_unavailable.py`
- `tests/scientific/test_auroc_invariance.py`

## Required edge cases

- All FPR values zero.
- Positive near-zero mean FPR.
- One eligible client.
- Empty benign or attack denominator.
- Single-class AUROC.
- Identical paired deltas causing degenerate BCa.
- Zero differences in Wilcoxon.
- All comparator variances zero.
- No traffic-rate evidence.
- Temporal drift excess not materially positive.

## Exit criteria

- Every metric has explicit availability semantics.
- Confirmatory inference is correctly paired and non-substitutable.
- Fallback and unavailable clients cannot contaminate confirmatory metrics.
- Operational outputs are evidence-gated.
- All Phase 10 tests and audits pass.

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

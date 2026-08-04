# Phase 14 — Reporting, Claims, and Publication Exports

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

Generate traceable tables, figures, machine-readable exports, warnings, suppression records, and claim-status decisions without overstating evidence or leaking unavailable outcomes.

## Entry criteria

- Phases 10–13 are complete.
- Scientific decisions and artifact manifests are available.
- Anchor gate and capability status are explicit.

## Source files permitted to change

- `datp_core/reporting/tables.py`
- `datp_core/reporting/figures.py`
- `datp_core/reporting/export.py`
- `datp_core/reporting/validation.py`

## Reporting records

Use existing evaluation/analysis models and add report-specific frozen records in these files only when needed:

- `TableSpecification`
- `FigureSpecification`
- `ReportBundle`
- `ClaimStatusRecord`
- `ReportingValidationResult`

No generic template dictionary.

## Mandatory tables

Implement descriptive table identities for:

- protocol and population summary;
- anchor reproduction comparison;
- confirmatory paired seed results;
- per-client natural-device metrics;
- shared-construction sensitivity;
- quantile sensitivity;
- controlled heterogeneity;
- calibration-size and shrinkage curves;
- local conformal coverage;
- federated benign-statistics diagnostics and payload;
- Edge benign-equity external validation;
- CIC file-client boundary;
- FedProx and Ditto stress tests;
- temporal recalibration;
- unavailable outcome summary;
- optional alert burden only when evidence exists.

Every table states population counts and metric availability.

## Mandatory figures

Implement only source-authorized figures:

- cross-client FPR distributions and paired contrasts;
- quantile-policy surfaces;
- heterogeneity versus threshold-scope benefit;
- calibration-size stability curves;
- shrinkage curves;
- conformal target versus achieved coverage;
- per-client benign/attack score geometry where attack assignment is valid;
- threshold movement versus FPR/TPR change;
- external benign-equity comparison;
- stress-test absorption comparison;
- temporal static/frozen/recalibrated trajectories.

Grouped-threshold figures remain unavailable until group assignments are scientifically resolved.

## Claim validation

`reporting/validation.py` must block:

- journal claims when anchor gate is blocked;
- confirmatory language when the BCa rule is not supported;
- external evidence presented as confirmatory;
- attack-sensitive Edge results;
- device-aware CIC language;
- one-shot recalibration described as continuous adaptation or concept-drift solution;
- data locality described as formal privacy;
- payload estimates described as deployment measurements;
- unavailable or undefined metrics rendered as zero;
- alert burden without valid rate evidence;
- alternative quantile, shrinkage value, or stress test promoted to rescue a failed confirmatory result.

## Precision

- Calculate and store full precision.
- Presentation defaults follow the source truth: rates/aggregates, intervals, and effect sizes to three decimals; p-values to three significant digits with `< 0.001` as applicable; counts as integers; thresholds with sufficient reproducibility precision.
- Never round before comparison or inference.

## Export formats

- Tables: CSV and Parquet.
- Figures: PDF plus a vector-friendly source format only if already supported by the selected plotting library; do not add a new source file.
- Consolidated results: Parquet.
- Claim status, warnings, and validation: Pydantic JSON.

## Test files to implement

- `tests/unit/reporting/test_tables.py`
- `tests/unit/reporting/test_figures.py`
- `tests/unit/reporting/test_export.py`
- `tests/unit/reporting/test_validation.py`
- `tests/unit/orchestration/stages/test_report.py`
- `tests/integration/reporting/test_report_bundle.py`
- `tests/integration/reporting/test_machine_readable_exports.py`
- `tests/scientific/test_blocked_claims_do_not_render.py`
- `tests/scientific/test_unavailable_metrics_do_not_render_as_zero.py`
- `tests/scientific/test_alert_burden_suppression.py`
- `tests/scientific/test_negative_results_remain_reportable.py`

## Required report validation scenarios

- Confirmatory support.
- Directional but inconclusive result.
- Opposite result.
- Blocked anchor.
- External null or opposite boundary.
- Infeasible grouped threshold.
- Undefined CV from zero mean FPR.
- No traffic-rate evidence.
- Ditto full absorption.
- Temporal no-drift condition with undefined recovery ratio.

## Exit criteria

- Every displayed result is traceable to a typed artifact and coordinate.
- Claim status is machine-enforced.
- Unavailable, undefined, suppressed, and infeasible outcomes are explicit.
- Publication exports do not alter scientific meaning.
- All Phase 14 tests and audits pass.

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

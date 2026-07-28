# Phase 11 — External Validation and Temporal Recalibration

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

Implement capability-limited external benign-equity validation on Edge-IIoTset, the CICIoT2023 file-client applicability boundary, and one-shot threshold recalibration on verified Edge chronology without expanding into continuous adaptation.

## Entry criteria

- Phases 08–10 are complete.
- Edge static and temporal capabilities are verified.
- CIC file-client population is verified.
- External and temporal experiment declarations are resolved.

## Source files permitted to change

- `datp_core/analysis/temporal.py`
- `datp_core/populations/edge_sensor_groups.py`
- `datp_core/populations/edge_temporal_groups.py`
- `datp_core/populations/ciciot_file_clients.py`
- `datp_core/datasets/edge_iiotset/chronology.py`
- `datp_core/experiments/feasibility.py`
- `datp_core/orchestration/stages/construct_population.py`
- `datp_core/orchestration/stages/split.py`
- `datp_core/orchestration/stages/evaluate_federated.py`
- `datp_core/orchestration/stages/analyze.py`

Changes are limited to external/temporal semantics; do not duplicate core metric or threshold implementations.

## Edge static external validation

- Population: `EDGE_SENSOR_GROUPS`.
- Use ten benign sensor groups when validation confirms them.
- FedAvg training and supported stress tests use benign training data.
- Supported threshold methods: shared, local, grouped only if a valid assignment source is later approved, federated benign statistics, quantile sensitivity, calibration-size and shrinkage where feasible.
- Family threshold unavailable.
- Per-client FPR and cross-client benign equity metrics available.
- Per-client TPR, binary Macro-F1, balanced accuracy, AUROC, and attack-sensitive trade-offs unavailable.
- External seed-level paired contrast and BCa are external evidence only, never a second confirmatory endpoint.

Every output must include typed availability records for attack-sensitive metrics rather than empty columns or NaN.

## CIC file-client boundary

- Population: `CICIOT_FILE_CLIENTS`.
- Quantify benign distribution divergence and shared/local threshold effects over the audited pseudo-clients.
- Keep all wording specific to file-defined clients.
- Do not reconstruct physical clients, infer device topology, or create chronology.
- A null effect is a valid boundary result and cannot be generalized to the original device topology.

## Temporal population

- Population: `EDGE_TEMPORAL_GROUPS`.
- Include only groups with validated genuine chronology.
- Preserve stable row order for equal timestamps.
- Split exactly into 55% historical training, 15% historical calibration, 10% future recalibration, 20% future evaluation.
- Build a matched random-fractional static reference over the same included groups and rows.
- Fit preprocessing and model without future leakage.

## Temporal deployment states

- `STATIC_REFERENCE`: matched random-fractional evaluation.
- `FROZEN_FUTURE`: historical threshold applied unchanged to future evaluation.
- `RECALIBRATED_FUTURE`: threshold recomputed once from future benign recalibration and applied to the same future evaluation.

Supported thresholds are source-authorized and capability-feasible. There is no streaming, periodic, triggered, or online behavior.

## Temporal quantities

Per seed and threshold method:

- static reference CV;
- frozen-future CV;
- recalibrated-future CV;
- drift excess = frozen future minus static reference;
- recovered amount = frozen future minus recalibrated future;
- recovery ratio only when drift excess exceeds the predeclared positive-materiality cutoff.

Undefined recovery ratio is a typed outcome, not zero.

## Feasibility rules

Reject before execution:

- Edge attack-sensitive metric request;
- family threshold on Edge or CIC;
- CIC temporal experiment;
- temporal execution with invalid chronology;
- grouped threshold without supplied assignments;
- temporal recovery ratio without materiality protocol;
- external claim promoted to confirmatory.

## Test files to implement

- `tests/unit/experiments/test_external_feasibility.py`
- `tests/unit/experiments/test_temporal_feasibility.py`
- `tests/unit/analysis/test_edge_temporal_quantities.py`
- `tests/integration/external/test_edge_benign_equity_validation.py`
- `tests/integration/external/test_ciciot_file_client_boundary.py`
- `tests/integration/temporal/test_edge_one_shot_recalibration.py`
- `tests/integration/temporal/test_matched_static_reference.py`
- `tests/scientific/test_external_evidence_is_not_confirmatory.py`
- `tests/scientific/test_temporal_pipeline_has_no_future_leakage.py`
- `tests/scientific/test_temporal_claim_scope.py`

## Required outcomes

- Included/excluded client records.
- Eligibility coverage.
- Per-client benign counts and FPR.
- Cross-client absolute and relative dispersion.
- Typed attack-metric unavailability.
- Chronology validation.
- Static/frozen/recalibrated trajectories.
- Honest null, opposite, or infeasible decisions.

## Exit criteria

- Edge external evidence is limited to supported benign operating-point outcomes.
- CIC results remain an artifact-specific boundary.
- Temporal analysis is one-shot, chronological, and leak-free.
- No unsupported metric or claim is computed.
- All Phase 11 tests and audits pass.

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

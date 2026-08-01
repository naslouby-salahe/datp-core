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
- The Phase 10 confirmatory CLI artifacts are reusable inputs only. Phase 11 uses its own typed population, split, preprocessing, scoring, threshold, evaluation, and supplementary-analysis contracts; it never extends `run-confirmatory-grid`.
- Edge static and temporal capabilities are verified.
- CIC file-client population is verified.
- External and temporal experiment declarations are resolved.

## Owner-contract amendment

The user authorized clean corrections in the owning modules where the original Phase 11 file boundary made the scientific contract impossible to implement. The amendment is deliberately narrow: it adds no compatibility aliases, no fallback path, and no new experiment family. It changes the following owner contracts:

- `datp_core/domain/enums.py`: FPR-evaluable cohort identity, temporal deployment state identity, and the explicit static-reference split/partition identities.
- `datp_core/protocols/models.py`, `datp_core/protocols/splits.py`, and `datp_core/protocols/validation.py`: a declared randomized 55/15/10/20 static-reference inventory, with its 10% reserve persisted but prohibited from fit, calibration, scoring, and evaluation.
- `datp_core/artifacts/layout.py`, `datp_core/preprocessing/*`, and `datp_core/centralized_reference/preprocessing.py`: protocol-defined temporal partition inventory and train-only fitting across every persisted partition.
- `datp_core/scoring/*`: immutable future-recalibration scores and checksums.
- `datp_core/evaluation/*`: FPR aggregation independent of confirmatory eligibility, plus typed unavailable attack-sensitive metrics.
- `datp_core/analysis/inference.py` and `datp_core/orchestration/stages/construct_federated_thresholds.py`: supplementary external BCa and temporal threshold provenance, separately from confirmatory inference.

## Source files permitted to change

- `datp_core/analysis/temporal.py`
- `datp_core/populations/edge_sensor_groups.py`
- `datp_core/populations/edge_temporal_groups.py`
- `datp_core/populations/ciciot_file_clients.py`
- `datp_core/datasets/edge_iiotset/chronology.py`
- `datp_core/experiments/feasibility.py`
- `datp_core/experiments/models.py`
- `datp_core/datasets/edge_iiotset/schema.py`
- `datp_core/protocols/training.py`
- `datp_core/orchestration/stages/construct_population.py`
- `datp_core/orchestration/stages/split.py`
- `datp_core/orchestration/stages/evaluate_federated.py`
- `datp_core/orchestration/stages/analyze.py`
- The owner-contract files listed above

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
- Build a matched random-fractional static reference over the same included groups and rows. Its randomized 55/15/10/20 allocation mirrors the temporal row inventory: train, calibration, explicitly retained static-reference reserve, and evaluation. The reserve cannot enter fitting, calibration, scoring, or evaluation.
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

## Implementation record — owner-contract repair in progress

- Entry audit verified Phases 08–10 as complete, the ten static Edge groups, the nine PCAP-backed temporal Edge groups with Modbus excluded, and the 63 CIC source-file pseudo-clients.
- Repaired the identified owner boundaries: FPR-evaluable external cohorts no longer inherit confirmatory eligibility; unavailable Edge AUROC is compared as typed availability rather than fabricated numeric evidence; supplementary external BCa has a separately published path with no confirmatory decision; temporal evaluation requires matched score/threshold provenance; and frozen/recalibrated analysis binds a shared future evaluation provenance.
- The matched static reference is now a distinct randomized 55/15/10/20 protocol. Its 10% reserve is an auditable, deliberately unused allocation, not an equal-thirds artifact and not a mislabeled future window.
- Modbus is recorded explicitly in temporal diagnostics as excluded because its `frame.time` values are address literals; feasibility rejects streaming, periodic, triggered, and online modes before execution. Reuse requires every companion manifest and persisted row artifact.
- The locked `uv` environment passes the full xdist suite (`635 passed`), repository Ruff and Pyright, and `git diff --check`. Project-wide Pylint remains at its pre-existing `9.91/10`, with no score regression and no newly suppressed warning.
- Canonical execution rebuilt the ten-group static Edge, nine-group temporal Edge, and 63-file CIC population publications. Temporal chronology records Modbus as `modbus_address_literal`; CIC persists canonical rejected rows and per-client reason counts. Static and temporal split publications are complete.
- Execution identities now bind construction, splitting, preprocessing, evaluation, and analysis for every bounded population. CIC split publication and artifact-driven external preprocessing are implemented. The remaining scientific execution work is the full real-data detector/training, scoring, threshold construction, evaluation, and analysis campaign for the static, CIC, and three temporal states. SonarQube and CodeScene are intentionally skipped by explicit user direction. No external or temporal result is represented as completed.
- Edge model-input repair: a full static canonical-data audit established a fixed 33-column strict numeric projection. No categorical values are imputed, vocabulary-fitted, ordinal-encoded, hashed, or silently coerced. The Edge detector now has an exact 33-dimensional symmetric architecture `(33, 25, 17, 11, 8, 11, 17, 25, 33)` derived by preserving the declared N-BaIoT architecture's depth, symmetry, and rounded compression ratios. Training rejects any mismatch between published preprocessing width and the declared input/output widths.
- Execution verification: identity documents are persisted and checksummed with population and split publications, then verified before artifact-driven preprocessing. The real ten-client Edge publication was rebuilt and its ten strict 33-feature client-local preprocessing artifacts completed. The real CIC population and split were rebuilt under the same contract, and all 63 client-local preprocessing artifacts completed with a 39-feature schema. The CIC path now performs source-file-client-at-a-time joins, eliminating the unsafe federation-wide 45-million-row materialization. The full suite now passes with `639 passed`; repository Ruff, Pyright, and `git diff --check` pass. SonarQube and CodeScene remain intentionally skipped.

## External code-health gate

Before phase closure, run the credentials-safe SonarQube CLI and CodeScene procedure in [the roadmap index](00_ROADMAP_INDEX.md#mandatory-external-code-health-gates). Resolve actionable `src/` findings or record the gate as blocked.

### User-directed exception

The user explicitly directed this audit to skip SonarQube and CodeScene. They must remain skipped for this completion attempt.

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

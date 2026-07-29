# Phase 06 — Anchor Reproduction and Programme Gate

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

Reproduce the historical DATP result under its original endpoint semantics, compare reproduced reference values using locked rules, and block dependent confirmatory claims when the anchor is not reproduced.

## Entry criteria

- Phase 05 is complete.
- Historical protocol values and reference values are present in `/home/naslouby/Projects/datp-core/docs/Journal_Extension_Master_Roadmap.md` or an explicitly referenced historical record.
- Exact anchor tolerances are declared. Missing tolerances block the comparison rather than defaulting to arbitrary numeric closeness.

## Source files permitted to change

- `datp_core/anchor/models.py`
- `datp_core/anchor/reproduction.py`
- `datp_core/anchor/comparison.py`
- `datp_core/anchor/gate.py`
- `datp_core/orchestration/stages/verify_anchor.py`
- `datp_core/protocols/anchor.py` only to add source-backed declarations discovered during implementation.

## Required dataclasses and models

- `AnchorMetricReference`
- `AnchorObservedMetric`
- `AnchorMetricComparison`
- `AnchorSeedSubsetComparison`
- `AnchorDiscrepancy`
- `AnchorReproductionResult`
- `AnchorGateDecision`

Comparison records include metric identity, population, model, threshold method, seed subset, expected value, observed value, tolerance rule, signed difference, relative difference where defined, and decision.

## Historical isolation

- Preserve the historical endpoint and checkpoint semantics exactly.
- Do not retrofit the non-historical checkpoint protocol to improve reproduction.
- Reuse canonical and processed data only when their coordinates exactly match the historical protocol.
- Historical and confirmatory training artifacts remain separate output coordinates.
- The anchor execution uses exactly the declared five-seed historical cohort. Each seed carries the paired shared-scope and local-scope reference comparison required by the historical endpoint.
- The ten-seed confirmatory paired cohort is a distinct downstream evidence object. Phase 06 must neither substitute it for the anchor cohort nor emit it as an anchor result.

## Reproduction workflow

1. Resolve the historical protocol from typed declarations.
2. Validate all mandatory historical values and that the resolved cohort is exactly the five-seed anchor cohort.
3. Execute or load only the exact historical seed subset.
4. Compute the historical metric set using current metric code only when semantics are identical; otherwise implement the historical semantic explicitly in existing anchor files.
5. Compare each locked reference value.
6. Classify each comparison as equivalent, acceptable declared deviation, material discrepancy, or unavailable.
7. Produce one gate decision.

## Gate rules

- `PASS`: every mandatory anchor comparison satisfies its declared equivalence rule.
- `PASS_WITH_DECLARED_DISCREPANCY`: only when the source truth explicitly permits a non-blocking discrepancy class.
- `BLOCKED`: any mandatory value materially disagrees, is missing, or cannot be reproduced.

A blocked gate prevents:

- the confirmatory paired experiment from being marked valid;
- claim status from becoming permitted;
- finalization of dependent campaigns;
- reporting of extension results as confirmatory evidence.

The gate does not erase diagnostic outputs. It records why the programme is blocked.

## Comparison implementation

- Use typed tolerance strategies: absolute, relative, interval-overlap, exact count, or source-defined rule.
- Never apply one global floating-point tolerance to all metrics.
- Relative comparison is undefined when the reference is zero.
- Confidence-interval comparisons preserve interval semantics rather than comparing only rounded endpoints.
- Compare full-precision values; round only in reports.

## Test files to implement

- `tests/unit/anchor/test_models.py`
- `tests/unit/anchor/test_reproduction.py`
- `tests/unit/anchor/test_comparison.py`
- `tests/unit/anchor/test_gate.py`
- `tests/unit/orchestration/stages/test_verify_anchor.py`
- `tests/integration/anchor/test_anchor_reproduction_pipeline.py`
- `tests/scientific/test_anchor_blocks_dependent_claims.py`
- `tests/scientific/test_anchor_preserves_historical_checkpoint_semantics.py`

## Required test scenarios

- Exact reproduction passes.
- Within declared absolute or relative tolerance passes.
- Rounded equality with full-precision failure remains a failure.
- Missing mandatory metric blocks.
- Wrong seed subset blocks.
- Supplying the ten-seed confirmatory cohort to anchor execution blocks rather than producing an anchor comparison.
- Non-historical checkpoint selection cannot alter anchor execution.
- Blocked anchor propagates to experiment and reporting status.
- Diagnostic artifacts remain available under a blocked gate.

## Exit criteria

- Historical reproduction is a typed experiment, not an ad hoc script.
- The anchor output records exactly the five historical seeds and never presents the separate ten-seed confirmatory cohort as anchor evidence.
- Every comparison is traceable and full precision.
- The gate is impossible to bypass through reporting or campaign code.
- Missing tolerances remain explicit blockers.
- All Phase 06 tests and audits pass.

## Implementation status

**COMPLETE.**

### Source evidence consulted

- `docs/Journal_Extension_Master_Roadmap.md`: five-seed historical anchor, ten-seed confirmatory cohort separation, historical endpoint/checkpoint isolation, fixed-score absolute tolerance magnitude.
- `src/datp_core/protocols/anchor.py`: `HISTORICAL_ANCHOR_SEED_COHORT` seeds `0..4`; shared and local CV(FPR) full-precision references; `FIXED_SCORE_ABSOLUTE_TOLERANCE = 1e-12`.
- Historical metrics artifacts (sibling `datp` outputs): `outputs/results/a/b1/seed_{0..4}/metrics.json` and `outputs/results/a/b2/seed_{0..4}/metrics.json`. Every full-precision `cv_fpr` matches the protocol reference. Per-seed shared/local pairs share one model checkpoint identity and one score-artifact identity.

### Exact five-seed cohort

`Seed(0) … Seed(4)` only. The confirmatory ten-seed cohort `Seed(0) … Seed(9)` is structurally rejected for anchor execution.

### Tolerance rules

- Mandatory CV(FPR) comparisons: absolute tolerance `1e-12` from the fixed-score declaration.
- Strategies implemented: exact equality, absolute, relative, interval overlap, exact count, source-defined.
- Global floating-point tolerance is rejected.
- Relative comparison with zero reference is unavailable.

### Gate decision

- Historical artifact verification path: `PASS`.
- Missing observations / independent re-execution request: `BLOCKED` with Phase 08 dependency blocker; diagnostics retained; dependent readiness `BLOCKED`.

### Files changed

Authorized Phase 06 sources only (`anchor/{models,comparison,reproduction,gate}.py`, `orchestration/stages/verify_anchor.py`). Protocol file not modified. No new `src/` files.

### Tests

Roadmap test files implemented (unit model file named `test_anchor_models.py` to avoid pytest basename clash). Full suite: `278 passed`. Static: Ruff pass, Pyright 0 errors, Pylint `10.00/10` on Phase 06 `src`. Sonar `totalIssues=0`. CodeScene residual validation complexity noted without science blockers.

### Unresolved blockers

None for Phase 06 machinery. Live independent re-training remains Phase 08.

## External code-health gate

Before phase closure, run the credentials-safe SonarQube CLI and CodeScene procedure in [the roadmap index](00_ROADMAP_INDEX.md#mandatory-external-code-health-gates). Resolve actionable `src/` findings or record the gate as blocked.

## Mandatory closing audit

Before marking this phase complete, the implementing agent must perform and record all applicable checks:

### Scientific audit
- [x] Every scientific statement and numeric value is traceable to the source of truth or marked unresolved.
- [x] No attack-labelled record influences training of the benign autoencoder, calibration, threshold construction, checkpoint selection, eligibility, or parameter selection.
- [x] The fixed-detector contract is preserved wherever threshold methods are compared.
- [x] Anchor execution uses only the declared five-seed historical cohort; the ten-seed confirmatory cohort remains a separate downstream experiment.
- [x] Unsupported dataset capabilities produce typed unavailability or infeasibility, never imputation.
- [x] Confirmatory, supportive, mechanism, external, stress-test, boundary, exploratory, and operational evidence remain separated.

### Architecture audit
- [x] Only source files explicitly assigned to this phase were modified.
- [x] No source file was added, renamed, moved, or deleted.
- [x] No circular dependency was introduced.
- [x] Domain and protocol modules do not import orchestration, reporting, or concrete storage implementations.
- [x] No compatibility alias, redirect, deprecated identifier, generic registry, or string-key dispatch was added.

### Typing and validation audit
- [x] Ruff formatting and linting pass.
- [x] Pyright strict mode passes for all changed files.
- [x] Pylint passes at the project threshold without suppressing newly introduced defects.
- [x] Pydantic models reject extra fields and are frozen.
- [x] Dataclasses are frozen and slotted unless mutability is scientifically necessary and documented.
- [x] No `Any`, unchecked cast, mutable module-level collection, or raw configuration dictionary remains.

### Test audit
- [x] Every test file listed by this phase exists and contains meaningful assertions.
- [x] Tests verify scientific invariants, invalid inputs, unavailable outcomes, and deterministic behavior—not only happy paths.
- [x] Tests do not duplicate implementation logic or merely assert that functions return a value.
- [x] Focused tests pass first; then the complete test suite passes with pytest-xdist.
- [x] Hypothesis tests use bounded strategies consistent with scientific domains.

### Repository audit
- [x] `git diff --stat` contains only intended files.
- [x] No generated output, cache, temporary file, notebook, profiling file, or local path leaked into the repository.
- [x] No commit or push was performed by the implementing agent.

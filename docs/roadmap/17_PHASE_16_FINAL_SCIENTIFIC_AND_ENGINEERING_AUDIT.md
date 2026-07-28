# Phase 15 — Extension Readiness

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

Verify that the fixed stage boundaries can later support calibration attacks, defenses, adaptive thresholds, dynamic recalibration, or additional scientifically approved populations without implementing any of those research lines now.

## Entry criteria

- Phases 01–14 are complete.
- Current DATP-Core behavior is fully tested.

## Source files permitted to change

- `datp_core/domain/contracts.py`
- `datp_core/orchestration/hooks.py`
- `datp_core/orchestration/resources.py`
- `datp_core/experiments/models.py`
- `datp_core/experiments/feasibility.py`

Changes may strengthen boundaries only. They may not add current attack, defense, online, adaptive, or privacy behavior.

## Required extension boundaries

Typed hook points may exist at:

- after reusable score generation and before calibration sampling;
- after calibration sampling and before threshold construction;
- after threshold construction and before evaluation;
- after evaluation and before analysis.

Hooks receive immutable references and return explicit typed results. Default hooks are identity/no-op and cannot mutate artifacts in place.

## Future capability principles

- A future calibration attack must operate only through a declared hook and must produce a new experiment/model coordinate, never alter clean artifacts.
- A future defense must be a new threshold method or hook implementation with an explicit scientific contract.
- Dynamic recalibration must add temporal states and protocol declarations, not conditional logic hidden in current stages.
- Additional datasets must implement existing dataset and population capability contracts.
- No future extension may bypass benign-only current thresholds, anchor gate, cohort separation, or safe serialization for current experiments.

## Prohibited implementation

This phase must not add:

- poisoning algorithms;
- attack objectives;
- defense estimators;
- drift detectors;
- online loops;
- privacy mechanisms;
- new datasets;
- generic plugin discovery;
- reflection-based registration;
- external entry points.

## Test files to implement

- `tests/unit/orchestration/test_extension_hooks.py`
- `tests/unit/experiments/test_extension_feasibility_boundaries.py`
- `tests/architecture/test_hooks_are_immutable.py`
- `tests/architecture/test_no_future_research_implementation.py`
- `tests/integration/orchestration/test_noop_hooks_preserve_artifacts.py`
- `tests/scientific/test_extensions_cannot_modify_clean_coordinates.py`

## Required assertions

- No-op hooks preserve checksums and semantic identities.
- Hooks cannot mutate frozen contexts.
- A future-only experiment identity is rejected because it has no current declaration.
- Hook failure leaves clean artifacts intact and prevents completion.
- Current experiment outputs are identical with default hooks enabled or absent.

## Exit criteria

- Extension boundaries are explicit and typed.
- Current code contains no future research implementation.
- No-op hooks introduce no scientific or artifact differences.
- All Phase 15 tests and audits pass.

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

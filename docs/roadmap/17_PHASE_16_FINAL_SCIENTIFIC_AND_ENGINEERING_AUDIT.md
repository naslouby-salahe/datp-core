# Phase 16 — Final Scientific and Engineering Audit

## Pipeline-first architecture amendment

The final audit targets the converged pipeline-first tree, not the superseded phase-local layout. It must prove that:

- `datp_core.pipeline` is the single application execution spine;
- `datp_core.cli` and `datp_core.orchestration` are thin adapters;
- deleted `datp_core.experiments`, `orchestration.commands`, `orchestration.stages`, top-level scoring, and monolithic CLI paths cannot return;
- capability packages do not import pipeline or adapters;
- centralized and federated branches remain scientifically separate while sharing neutral publication mechanics;
- the exact final E2E, architecture, and scientific acceptance tests listed below exist and pass.

A green unit and integration suite is necessary but not sufficient. Phase 16 remains incomplete until the dedicated `tests/e2e/` acceptance layer, static-analysis gates, repeated deterministic campaign checks, source-tree audit, and final verdict in `01_PHASE_MASTER_LOG.md` are complete.


## Scientific authority and interpretation rules

- Before planning, editing, testing, or auditing this phase, read **`/home/naslouby/Projects/datp-core/docs/Journal_Extension_Master_Roadmap.md`** in full. It is the authoritative source for the scientific question, permitted evidence, dataset boundaries, numerical grids, metrics, inference, and claim restrictions.
- Use descriptive implementation identities only. Never introduce opaque lettered populations, numbered threshold policies, numbered baselines, compatibility aliases, redirects, deprecated names, or duplicated identifiers.
- The centralized reference is an independent pooled-data pipeline. It is never a federated threshold method and never consumes scores produced by a federated model.
- The confirmatory comparison reuses one selected FedAvg detector, one preprocessing state, one client population, one calibration set, and one held-out score set per seed. Only threshold-calibration scope changes.
- Calibration is benign-only. Attack labels and held-out outcomes cannot select models, checkpoints, quantiles, shrinkage values, statistical coefficients, clients, or group assignments.
- The implementation source tree is locked to the files already created under `datp_core/`. Do not create, rename, move, delete, or replace source files. Test files may be created only when explicitly named in this roadmap.
- Scientific values absent from the source of truth must remain unresolved. Do not infer them from memory, historical repositories, convenient defaults, or common practice. Record the blocker in `01_PHASE_MASTER_LOG.md`.
- Python protocol declarations replace YAML. Protocol objects are immutable, fully typed, explicitly constructed as the canonical protocol graph, validated at startup without hidden defaults, and serialized into every resolved experiment manifest. Runtime locks `require_cuda=True` and `worker_count=6`.
- Do not add backward compatibility, migration adapters, aliases, generic registries, service locators, untyped dictionaries, `Any`, silent fallbacks, or catch-all modules.
- Do not add comments that restate code. Express intent through names, enums, types, validated records, and small functions.
- Reusable canonical and preprocessed data belong under `data/`. Experiment-specific trained states, scores, thresholds, evaluations, analyses, and reports belong under `outputs/`.

## Objective

Perform the final repeated audits proving that the locked source tree implements the scientific programme faithfully, reuses data correctly, separates centralized and federated paths, preserves fixed-detector comparisons, reports honest evidence, and is ready for full experiment execution.

## Entry criteria

- Phases 01–15 are marked complete.
- No mandatory scientific blocker remains.
- All exact test files named by prior phases exist.

## Source files permitted to change

No production source file may be changed during the initial audit pass. Audit failures return the repository to the owning phase. After fixes, rerun this phase from the beginning.

Only the following test files may be created or changed here:

- `tests/conftest.py`
- the final audit tests named below.

## Final test files to implement

- `tests/e2e/test_anchor_reproduction.py`
- `tests/e2e/test_confirmatory_natural_device_pipeline.py`
- `tests/e2e/test_centralized_reference_pipeline.py`
- `tests/e2e/test_edge_external_validation_pipeline.py`
- `tests/e2e/test_ciciot_boundary_pipeline.py`
- `tests/e2e/test_controlled_heterogeneity_pipeline.py`
- `tests/e2e/test_fedprox_stress_pipeline.py`
- `tests/e2e/test_ditto_stress_pipeline.py`
- `tests/e2e/test_temporal_recalibration_pipeline.py`
- `tests/e2e/test_campaign_resume_pipeline.py`
- `tests/e2e/test_reporting_and_reload_pipeline.py`
- `tests/architecture/test_complete_source_tree_contract.py`
- `tests/architecture/test_dependency_direction.py`
- `tests/architecture/test_no_dict_or_any_leakage.py`
- `tests/architecture/test_no_legacy_or_opaque_identity.py`
- `tests/architecture/test_no_unsafe_persistence.py`
- `tests/architecture/test_no_generated_files_in_source.py`
- `tests/scientific/test_complete_causal_isolation.py`
- `tests/scientific/test_complete_benign_only_contract.py`
- `tests/scientific/test_complete_capability_enforcement.py`
- `tests/scientific/test_complete_claim_discipline.py`
- `tests/scientific/test_complete_data_reuse_contract.py`
- `tests/scientific/test_complete_negative_result_discipline.py`

Use tiny deterministic data and minimal rounds for e2e contract tests. Full scientific experiments are not unit tests.

## Audit pass 1 — Scientific identity

- [ ] Every implemented experiment exists in the source programme.
- [ ] No extra dataset, method, metric, attack, defense, privacy mechanism, or deployment claim exists.
- [ ] Descriptive identities are used in code, paths, manifests, reports, and CLI.
- [ ] Centralized reference remains outside federated threshold dispatch.
- [ ] The sole confirmatory endpoint remains shared versus local threshold calibration on N-BaIoT natural devices using FedAvg and `CV(FPR)`.

## Audit pass 2 — Data and preprocessing reuse

- [ ] Raw data are read-only.
- [ ] Canonical and processed data reside under `data/`.
- [ ] Reuse coordinates include every factor that changes rows or transformations.
- [ ] Model/threshold factors do not duplicate processed data.
- [ ] Centralized and federated fitted states are independent.
- [ ] Every reused asset passes manifest, checksum, schema, and reload validation.

## Audit pass 3 — Causal isolation and leakage

- [ ] One model/checkpoint/score artifact is reused across core threshold methods per seed.
- [ ] Calibration and evaluation rows are disjoint.
- [ ] No attack label influences benign calibration or selection.
- [ ] No test metric selects checkpoint, model parameter, quantile, shrinkage, comparator coefficient, client, or grouping.
- [ ] Temporal fitting uses no future rows.
- [ ] Eligible cohorts are identical across compared methods.

## Audit pass 4 — Dataset and capability truth

- [ ] N-BaIoT physical devices and attack assignment are validated.
- [ ] CIC clients are described only as file-defined pseudo-clients.
- [ ] Edge static clients use benign sensor groups and do not receive fabricated attack assignment.
- [ ] Edge temporal groups have genuine validated chronology.
- [ ] Unsupported family, grouped, attack-sensitive, or temporal cells are infeasible or unavailable.

## Audit pass 5 — Models and checkpoints

- [ ] FedAvg uses the locked core protocol.
- [ ] FedProx uses only declared positive coefficients and separate artifacts.
- [ ] Ditto is genuine and preserves persistent personalized states.
- [ ] Checkpoint selection is non-test and policy-independent.
- [ ] Centralized models are separately trained and scored.
- [ ] Model and checkpoint states use SafeTensors and reload exactly.

## Audit pass 6 — Thresholds and metrics

- [ ] Threshold calibration is benign-only.
- [ ] Shared/local/family formulas match the source truth.
- [ ] Grouped thresholding cannot execute without a scientifically supplied assignment.
- [ ] Federated benign statistics include full within and between variance.
- [ ] CV uses `ddof=0`, no epsilon, undefined at zero mean, and warning at the locked near-zero cutoff.
- [ ] Fallback clients never enter confirmatory CV.
- [ ] Binary Macro-F1, P10, pooled/mean-client, coverage, and unavailable semantics are exact.
- [ ] Conformal coverage includes target, achieved, errors, rank effects, and calibration-size behavior.

## Audit pass 7 — Statistics and decisions

- [ ] Ten paired seed contrasts are the confirmatory independent units.
- [ ] BCa resamples paired contrasts.
- [ ] Degenerate BCa is not silently replaced.
- [ ] Wilcoxon and rank-biserial are secondary.
- [ ] Nested replicates are summarized within seed.
- [ ] Holm families are predeclared.
- [ ] Null, opposite, unstable, and infeasible outcomes remain reportable.

## Audit pass 8 — Outputs and campaigns

- [ ] Output paths contain only deterministic scientific coordinates.
- [ ] No run ID, job ID, timestamp identity, or hidden resume state exists.
- [ ] Incomplete experiment outputs are deleted before resume.
- [ ] `COMPLETE` is written last after full reload validation.
- [ ] Outputs do not duplicate reusable data.
- [ ] Campaign ordering and dependencies are deterministic.

## Audit pass 9 — Reporting and claims

- [ ] Blocked anchor blocks dependent claims.
- [ ] Confirmatory wording follows the BCa decision.
- [ ] External evidence remains external.
- [ ] Edge attack metrics and CIC device claims cannot render.
- [ ] One-shot temporal evidence is not called continuous adaptation.
- [ ] Message sizes are estimates, not deployment evidence.
- [ ] Alert burden is suppressed without rate evidence.
- [ ] Full-precision calculations precede presentation rounding.

## Audit pass 10 — Engineering quality

Run in this order:

1. Ruff format check.
2. Ruff lint.
3. Pyright strict.
4. Pylint.
5. Focused unit and property tests.
6. Integration tests.
7. Architecture tests.
8. Scientific tests.
9. E2E tests.
10. Complete suite with pytest-xdist and coverage.

Then inspect duplication, dead code, import cycles, unhandled branches, and source-tree drift. Do not weaken tests or suppress tools merely to obtain green status.

## Final acceptance verdict

Return exactly one:

- `GO_FOR_FULL_EXPERIMENTS`
- `NO_GO_SCIENTIFIC_BLOCKER`
- `NO_GO_IMPLEMENTATION_DEFECT`
- `NO_GO_REPRODUCIBILITY_DEFECT`

`GO_FOR_FULL_EXPERIMENTS` requires every mandatory checklist item, all static tools, all tests, anchor gate, safe reload validation, and source-tree audit to pass.

## Final acceptance checklist

- [ ] Every phase is `COMPLETE`.
- [ ] No unresolved mandatory scientific value remains.
- [ ] Full test suite passes repeatedly without order dependence.
- [ ] Re-running validation and planning creates no repository changes.
- [ ] Two identical tiny campaign runs resolve identical scientific manifests and outputs.
- [ ] All audits above pass without waiver.
- [ ] Final verdict is recorded in `01_PHASE_MASTER_LOG.md`.

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

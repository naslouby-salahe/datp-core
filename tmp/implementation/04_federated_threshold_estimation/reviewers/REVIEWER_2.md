# REVIEWER_2 — Independent audit of Prompt 4/8 (Federated Threshold Estimation and Comparator Workflows)

Audited: `src/datp_core/pipeline/workflows/federated_threshold_estimation.py` (new), `src/datp_core/pipeline/workflows/campaign.py` (modified), `src/datp_core/protocols/experiments.py` declarations, evaluation contracts, `tests/unit/pipeline/workflows/test_federated_estimation_registration.py`, `tests/unit/pipeline/workflows/test_registry_consistency.py`, `docs/graphify_implementation/04_FEDERATED_THRESHOLD_ESTIMATION.md` (treated as untrusted), `graphify-out/graph.json`, and `docs/Journal_Extension_Master_Roadmap.md` §9.1-§9.3 (read in full).

Method: traced each wired experiment upward to the production entrypoint (campaign registry/dispatch -> workflow module -> `execute_declared_experiment_seed`) and downward to the real scientific side effect (evaluation document -> report summary). Empirically executed `expand_experiment_plan` for all three experiments and empirically reproduced the import cycle at HEAD.

---

## Findings

### F1 — HIGH — Fixed-coefficient sensitivity grid is unimplemented; report emits `coefficient=0.0` placeholders and marks analysis complete

- Location: `src/datp_core/pipeline/workflows/federated_threshold_estimation.py:310-343`, specifically line 328 `coefficient=0.0` in `report_fixed_coefficient_statistics_sensitivity`.
- Why wrong: Roadmap §9.3 (line 2377-2389) locks the sensitivity grid to `k in {2.0, 2.5, 3.0}`. The report hardcodes `0.0` for every seed and every method, so the emitted `summary.json` contains a fabricated coefficient that never occurs in the roadmap, then writes the `fixed_coefficient_statistics_sensitivity_analysis_complete` marker (via `_finalize_report`, line 338) — an analysis is marked complete over non-scientific data.
- Root cause (upward): `construct_federated_benign_statistics` builds `fixed_coefficient_curve` (`src/datp_core/thresholding/methods/federated_statistics.py:187-197`) via `fixed_coefficient_threshold` (mean + k*sigma), but that curve is never evaluated on test scores. The only reference outside the constructor is a test (`tests/scientific/test_benign_only_threshold_construction.py:292`). `FederatedEvaluationDocument` (`src/datp_core/evaluation/federated/contracts.py:117-130`) has no field for it, `FederatedThresholdMethod` (`src/datp_core/domain/enums.py:109`) has no coefficient-carrying members, and `expand_experiment_plan` for `FIXED_COEFFICIENT_STATISTICS_SENSITIVITY` yields 180 entries (3 methods x 10 seeds x 6 metrics) with no coefficient dimension — empirically reproduced.
- Fix: Either wire k through the whole chain (add a coefficient dimension to the declaration/plan, evaluate each k on the test scores, store per-coefficient FPR in the evaluation contract, report per-coefficient CV(FPR)), or, because the roadmap labels this "Optional supplementary sensitivity only", remove the experiment from the registry entirely. A report that writes `0.0` and a complete marker is not an acceptable third option.

### F2 — HIGH — FEDERATED_QUANTILE_ESTIMATION duplicates FEDERATED_BENIGN_STATISTICS_COMPARISON and delivers none of the roadmap §9.2 outcomes

- Location: `src/datp_core/protocols/experiments.py:357-374` — both declarations are identical (same `EvidenceRole.THRESHOLD_VARIANT`, same `PopulationId.NBAIOT_NATURAL_DEVICES`, same `TrainingModelId.FEDAVG_AUTOENCODER`, same `_FEDERATED_STATISTICS_COMPARISON_METHODS` five methods, same operating-point metrics). `expand_experiment_plan` returns 300 identical entries for each (empirically reproduced).
- `report_federated_quantile_estimation` (`federated_threshold_estimation.py:250-286`) is a verbatim copy of `report_federated_benign_statistics_comparison` (lines 190-226) and reports only `mean_cv_fpr`, `worst_client_fpr`, `fpr_coefficient_of_variation`.
- Why wrong: Roadmap §9.2 (lines 2347-2375) requires the quantile-estimation backbone to produce quantile-estimation error, achieved benign exceedance, threshold variance, calibration sample efficiency, estimated communication, and the estimation-error/FPR-equity relation. None of these are computed or reported. The experiment adds no new scientific measurement over the comparison run; it is duplicate responsibility per CLAUDE.md §5 and §6.
- Fix: Either implement the actual quantile-estimation-backbone outcomes (a real scientific construction task, not a wiring task) or drop the experiment and its report from the registry. Keep the experiment only if its declared identity matches what it actually measures.

### F3 — MEDIUM-HIGH — `fpr_coefficient_of_variation` is set to the arithmetic mean (copy bug) in both comparison and quantile reports

- Location: `federated_threshold_estimation.py:214` and `:274`: `fpr_coefficient_of_variation=_mean(cv_values)` — byte-identical to the `mean_cv_fpr` value.
- Why wrong: The field is named the coefficient of variation. The sibling module `threshold_robustness.py:220-227` defines `_coefficient_of_variation(values)` (std/mean; `None` for <2 values or zero mean) and uses it for exactly this field at lines 270, 328, 523. The new module copied the pattern but substituted `_mean()` (defined at line 169), so the two report fields always carry the same number. This is both a correctness bug and a CLAUDE.md §5 reuse violation — the helper already exists in the same package.
- Fix: Reuse `_coefficient_of_variation` (canonical helper) for `fpr_coefficient_of_variation` in both reports.

### F4 — MEDIUM — No tests cover the report, seed-runner, or document-resolution logic; all three report defects above are untested

- Location: `tests/unit/pipeline/workflows/test_federated_estimation_registration.py` (19 tests) covers only registration membership, declaration locking, and marker callability. Nothing exercises `report_federated_benign_statistics_comparison`, `report_federated_quantile_estimation`, `report_fixed_coefficient_statistics_sensitivity`, `_run_estimation_seed`, `_evaluation_document_for_seed`, the coefficient grid, or the CV computation.
- Why wrong: F1's `coefficient=0.0`, F3's mean-as-CV, and the near-identical duplication of F2 would all pass the current suite. The implementation report's claim of "245 tests passing" cannot be reconciled with the three report functions being entirely unexercised.
- Fix: Add contract tests for the report behavior (row cardinality per method/seed, coefficient values drawn from the grid, CV field semantics, missing-document handling), or remove the report functions if the experiments are dropped per F1/F2.

### F5 — MEDIUM (pre-existing, reproduced by this change) — Direct `import datp_core.pipeline.execution.engine` fails with a circular import; the new module reuses the same top-level-import anti-pattern

- Location: `federated_threshold_estimation.py:31` `from datp_core.pipeline.workflows.execution import execute_declared_experiment_seed`; triggered by `campaign.py:39` importing the new module at module top.
- Empirical proof it is NOT a new regression: in a detached worktree at HEAD (`fe21c002`, the committed pre-change state, before this prompt's edits), `PYTHONPATH=<worktree>/src python -c "import datp_core.pipeline.execution.engine"` fails with the identical traceback — `engine.py:55` imports `workflows.anchor`, which loads `workflows/__init__.py:33` -> `campaign.py` -> `threshold_robustness.py:37` -> `workflows.execution.py:19` -> partially initialized `engine` (names `CompletionRecordOutputStore`, `PipelineStageRunner`, `build_campaign`, `execute_campaign` not yet defined). The direct engine import was already broken at HEAD.
- Why it still matters: the new module copies the identical module-level import that is the load-bearing edge of the cycle, and `campaign.py` now imports it first, so the change re-instantiates the broken pattern on new code. Consequence: `tests/unit/pipeline/execution/test_execution.py`, `test_campaign.py`, `test_extension_boundaries.py`, `test_general_stage_runner.py` fail at collection in the current tree. The full suite does not collect.
- Fix: defer the `from datp_core.pipeline.workflows.execution import execute_declared_experiment_seed` import into function scope (the module already does this for `require_experiment_declaration` at line 108 and for `AnalysisAssetName` at line 89 — same pattern), and/or break the cycle at `engine.py:55`.

### F6 — MEDIUM — Duplicate report scaffolding and summary-row models; `_evaluation_document_for_seed` resolves comparison documents for the quantile and fixed-coefficient experiments

- Location: `report_federated_benign_statistics_comparison` (190-226) and `report_federated_quantile_estimation` (250-286) are full-body copies (same loop, same aggregation, same serialization). `_FederatedComparisonSummaryRow` (44-51), `_QuantileEstimationSummaryRow` (53-60) are identical field-for-field. `_evaluation_document_for_seed`, `_run_estimation_seed`, `_finalize_report`, `_analysis_directory` restate `threshold_robustness.py` scaffolding.
- Why wrong: CLAUDE.md §5 (reuse/consolidate before adding) and §6 (deletion bias). Because `_evaluation_document_for_seed` filters only by `(seed, method, FPR_COEFFICIENT_OF_VARIATION)`, the quantile and fixed-coefficient experiments read the same evaluation documents as the comparison experiment — further evidence that F2 and F1 add no distinct measurement.
- Fix: consolidate to one parametrized report over (experiment_id, summary-row factory, marker text), or delete the redundant reports when the duplicate experiments are removed.

### F7 — LOW — Implementation report validation claims are not reproducible; graphify graph is stale

- Location: `docs/graphify_implementation/04_FEDERATED_THRESHOLD_ESTIMATION.md` lines 61-68 ("245 tests passing"); `graphify-out/graph.json` has `built_at_commit: 76afa5c8` and contains no module node for `federated_threshold_estimation.py` (only roadmap document nodes mentioning "federated threshold-estimation").
- Why wrong: the full suite does not collect (F5), and the three report functions have no tests (F4), so a 245-green claim is not reproducible from the current tree. The graph predates both the new module and the `Fixes` commits, so it cannot serve as validation evidence for this change.
- Fix: re-run the full suite after F5 is addressed; regenerate the graph and record the actual built-at commit; restate validation honestly.

---

## Categories checked and found correct (NO ISSUE)

- **B-FedStatsBenign math** — `construct_federated_benign_statistics` (`federated_statistics.py:146-210`): pooled variance decomposition with within/between/full terms, `between_ratio = between / (within + between)` guarded against zero denominator, Gaussian-matched exceedance `mean + Phi^-1(q)*sigma` using global mean and full pooled variance, sample-weighted mean `sum(n_k*mu_k)/sum(n_k)`. All consistent with roadmap §9.1.
- **Fixed detector and benign-only boundary** — thresholds are constructed only from benign scores; calibration remains benign-only; attack labels never enter threshold construction; `FederatedStatisticsProtocol` coefficients locked to `{2, 2.5, 3}` (`protocols/calibration.py` line 186) and `SUMMARY_COEFFICIENTS` matches roadmap §9.3 (the grid constant itself is correct; only the workflow never uses it — see F1).
- **Communication semantics** — `SERIALIZED_MESSAGE_SIZE_ESTIMATE` basis and "estimates, not network measurements" docstring are honest; no measurement claim is made.
- **Threshold-estimation diagnostics typing** — `ThresholdEstimationDiagnostic` and `SampleEfficiencyPoint` are typed StrictModel/dataclass records with provenance; `EvaluationDiagnostics` carries them.
- **Registration/dispatch/handler consistency** — the three `RegisteredWorkflow` entries, three dispatch functions, three `WorkflowHandlers` entries, and the analysis-marker aliases in `campaign.py` are internally consistent; `_require_dispatch_covers_registry` passes; `test_registry_consistency.py` expectations updated consistently with the campaign order.
- **Enum usage / no primitive leaks at boundaries** — `FederatedThresholdMethod`, `ExperimentId`, `PopulationId`, `MetricId` used; `.value` only at the serialization boundary; the report functions read typed `FederatedEvaluationDocument` via `load_evaluation_document` rather than raw dicts.
- **Seed determinism** — all seed cohorts come from `CONFIRMATORY_SEED_COHORT`; the seed runners thread `SeedCohort(values=(training_seed,))` into `execute_declared_experiment_seed`; reason strings are stable.

---

## Validation executed

- `expand_experiment_plan` for all three experiments: comparison=300 entries / 5 methods, quantile=300 entries / 5 methods (identical set), fixed_coefficient=180 entries / 3 methods / no coefficient dimension.
- Empirical import test of `datp_core.pipeline.execution.engine` in a detached worktree at HEAD: fails identically to the current tree (proves F5 pre-existing).
- Reference scan for `fixed_coefficient_curve` / `fixed_coefficient_threshold`: no production consumer outside the constructor and one scientific test.
- `FederatedEvaluationDocument` field inspection: no coefficient/curve field.
- `_coefficient_of_variation` presence in `threshold_robustness.py` (lines 220-227) and its use for the same field at 270/328/523.
- `graphify-out/graph.json` built_at_commit and node scan.
- Earlier in this session: registration tests (19 passed), workflow tests (31 passed), architecture-boundary tests (19 passed), import-linter (13 kept); execution-module tests fail at collection (see F5).

No files were modified during this audit.

# REVIEWER_3 — Independent audit of Prompt 4/8: Federated Threshold Estimation and Comparator Workflows

Scope: current working tree of DATP-Core at `/home/naslouby/Projects/datp-core`.
Authority used: `docs/Journal_Extension_Master_Roadmap.md` (read in full; sections 9.1, 9.2, 9.3 cited below).
Implementation report read and treated as UNTRUSTED: `docs/graphify_implementation/04_FEDERATED_THRESHOLD_ESTIMATION.md`.
Method: read actual source, tests, typed contracts, CLI/workflow call chains, and the Graphify graph. No code was modified.

Bottom line: the three experiments are fully wired to real production entrypoints and the dispatch/report/status/marker machinery is internally consistent. However, the scientific scope claimed by the report is NOT implemented. FIXED_COEFFICIENT_STATISTICS_SENSITIVITY never evaluates any coefficient threshold, and the two "estimation" experiments are duplicates that surface none of the roadmap-required threshold-estimation outcomes. The `fixed_coefficient_curve` is computed and then silently dropped at the evaluation boundary.

---

## Findings

### [HIGH] F1. FIXED_COEFFICIENT_STATISTICS_SENSITIVITY does not implement the roadmap §9.3 coefficient sweep

Roadmap §9.3: "Fixed coefficient values may be evaluated under the benign-only adaptation: `k in {2.0, 2.5, 3.0}`". This requires evaluating the B-FedStatsBenign threshold at k = 2.0, 2.5, 3.0 and reporting the resulting operating points.

Evidence chain:

1. The sweep is computed. `construct_federated_benign_statistics` (`src/datp_core/thresholding/methods/federated_statistics.py:187-197`) builds `fixed_coefficient_curve` — one `FixedCoefficientResult(coefficient, threshold)` per `protocol.coefficients` — where `fixed_coefficient_threshold(mean, variance, k) = mean + k * sqrt(variance)` (`src/datp_core/thresholding/quantiles.py:218-223`). `SUMMARY_COEFFICIENTS = (2, 2.5, 3)` (`src/datp_core/protocols/calibration.py`).
2. The curve is never evaluated. `_evaluate` in `src/datp_core/evaluation/federated/execution.py:142-189` consumes only `result.assignments` and `result.matched_threshold` (`_assignments`, `_deployment_fallback_threshold`). No k-threshold is ever applied to held-out test scores. `fixed_coefficient_curve` has zero consumers outside `federated_statistics.py` (confirmed by `grep -rn fixed_coefficient_curve src/`).
3. The curve is never persisted. `FederatedEvaluationDocument` (`src/datp_core/evaluation/federated/contracts.py:117-130`) has no field for it. It dies at the evaluation boundary.
4. The curve is never reported. `report_fixed_coefficient_statistics_sensitivity` (`src/datp_core/pipeline/workflows/federated_threshold_estimation.py:310-343`) iterates only `declaration.federated_thresholds` (shared, local, federated statistics) × 10 seeds and writes `coefficient=0.0` hardcoded at line 328. The locked grid {2.0, 2.5, 3.0} is never read anywhere in the workflow.
5. There are no per-coefficient coordinates to evaluate even if the report wanted to. The experiment declaration (`src/datp_core/protocols/experiments.py:376-383`) carries only three threshold methods; the plan sweep (`_swept_cells`/`_declared_model_coefficients` in `src/datp_core/pipeline/planning.py`) derives `model_coefficient` only from the training model, never from the threshold method. `FederatedThresholdMethod` has a single `FEDERATED_BENIGN_STATISTICS` member (no per-k representation).

Result: the experiment produces 30 summary rows (3 methods × 10 seeds), every one stamped `coefficient=0.0`, all derived from the k-implied matched threshold. No k ∈ {2.0, 2.5, 3.0} operating point is evaluated, persisted, or reported. Roadmap §9.3 is unmet. `0.0` is also not a member of the locked grid, so the report actively fabricates a coefficient value the roadmap never sanctions.

The existing test `test_fixed_coefficients_remain_a_separate_supplementary_curve` (`tests/scientific/test_benign_only_threshold_construction.py:284-293`) only asserts the matched threshold differs from the curve thresholds — it does not assert any curve threshold is evaluated. It does not rescue the experiment.

Fix: add a coefficient dimension to the fixed-coefficient experiment (a per-k plan coordinate or a declared coefficient sweep), evaluate each k-threshold on held-out benign scores, persist the per-k operating points (CV(FPR), worst-client FPR, exceedance) in the evaluation document, and have the report read the grid from `FEDERATED_STATISTICS_PROTOCOL.coefficients` instead of the literal `0.0`. Registration/smoke tests must assert the grid is surfaced.

---

### [HIGH] F2. FEDERATED_BENIGN_STATISTICS_COMPARISON and FEDERATED_QUANTILE_ESTIMATION are duplicate experiments, and neither reports its required outcomes

The two declarations are textually identical except for the experiment id (`src/datp_core/protocols/experiments.py:357-374`): both use `_FEDERATED_STATISTICS_COMPARISON_METHODS` (same 5 methods), same population (N-BaIoT natural devices), same training model, same preprocessing, same `OPERATING_POINT_METRICS`. Roadmap §9.1 (comparator) and §9.2 (quantile-estimation backbone) define two distinct scientific objects with distinct required outcome sets:

- §9.1 required outcomes: threshold value; absolute and relative threshold error; target-attainment error; CV(FPR), IQR, range, worst-client FPR; communication fields and estimated bytes; client coverage; comparison with B1 and B2.
- §9.2 outcomes: quantile-estimation error; achieved benign exceedance; threshold variance; calibration sample efficiency; estimated communication; relation between estimation error and FPR equity.

The two reports `report_federated_benign_statistics_comparison` (lines 190-226) and `report_federated_quantile_estimation` (lines 250-286) are textually near-identical and both emit only per-method mean CV(FPR) and mean worst-client FPR. None of the §9.1/§9.2 outcomes appear in either. The second experiment adds no distinct evidence; it is duplicate responsibility under two names, and the roadmap outcomes for both are absent from the outputs.

Fix: give the two experiments distinct scientific content (comparator vs. quantile-estimation error framing) and surface their respective roadmap outcome sets in the reports, or consolidate to a single experiment. Either way, the reports must emit the threshold-estimation outcomes (see F3).

---

### [MEDIUM] F3. Threshold-estimation diagnostics are computed, persisted, and then ignored by every report

`ThresholdEstimationDiagnostic` (`src/datp_core/evaluation/threshold_estimation.py:50-56`) carries exactly the §9.1/§9.2 required values: `estimated_threshold`, `exact_pooled_benign_quantile_reference`, `target_exceedance`, `achieved_benign_exceedance`, absolute/relative threshold error, and attainment-error metrics (validated in `__post_init__`). `SampleEfficiencyPoint` carries calibration size, replicate count, and threshold variance. Both are stored in `EvaluationDiagnostics.threshold_estimation` and `.sample_efficiency` inside `FederatedEvaluationDocument.diagnostics` (`src/datp_core/evaluation/federated/contracts.py:88-96`).

None of the three reports reads `doc.diagnostics` at all. Each report reads only `population_metric(doc, FPR_COEFFICIENT_OF_VARIATION)` and `population_metric(doc, WORST_CLIENT_FPR)` (`federated_threshold_estimation.py:205-206, 265-266, 323-324`). So the absolute/relative threshold error, attainment error, achieved exceedance, quantile-estimation error, and sample-efficiency data that the evaluation stage already produces and validates are thrown away before reporting. This is the concrete mechanism behind F2's "outcomes absent."

Fix: the reports must iterate `doc.diagnostics.threshold_estimation` and `doc.diagnostics.sample_efficiency` and emit the roadmap outcome fields per method/seed.

---

### [MEDIUM] F4. Workflow duplicates threshold_robustness.py's analysis machinery verbatim

`src/datp_core/pipeline/workflows/federated_threshold_estimation.py` re-implements, character-for-character, the report scaffolding already present in `src/datp_core/pipeline/workflows/threshold_robustness.py`:

- `_analysis_directory` (78-85) == `_threshold_robustness_analysis_directory` (103-110)
- `_complete_marker` (88-91) == `_threshold_robustness_complete_marker` (113-116)
- `_finalize_report` (94-104) == `_finalize_report` (119-129)
- `FederatedEstimationSeedResult` (71-75) == `ThresholdRobustnessSeedResult` (132-137)

This violates the repository's reuse-first rule (CLAUDE.md §5) and duplicates the analysis-directory/complete-marker asset contract in a second module, creating two parallel output-layout authorities. Any change to completion-marker semantics must now be made in two places.

Fix: consolidate the shared `_analysis_directory`/`_complete_marker`/`_finalize_report`/seed-result machinery into one canonical location and import it, or generalize `threshold_robustness.py`'s equivalents.

---

### [LOW] F5. Undefined CV(FPR) is silently relabeled as a missing seed

`population_metric` (`src/datp_core/pipeline/execution/evidence.py:104-108`) raises `ScientificContractError` when the requested metric is unavailable. For zero-mean FPR, `_fpr_aggregates` returns CV(FPR) with `MetricStatus.UNDEFINED` / `MetricReason.ZERO_MEAN` (`src/datp_core/evaluation/population_metrics.py:127-131`) — a legitimate scientific outcome, not absent evidence. The reports wrap the doc-load plus both `population_metric` calls in a single `except ScientificContractError: missing += 1` (lines 207-208, 267-268, 334-335). An undefined CV therefore increments the "seed(s) missing" counter and drops the seed from the summary, conflating "undefined operating point" with "artifact absent."

Fix: separate doc-load failure from metric-unavailability handling; represent undefined metrics explicitly (or count them distinctly) instead of folding them into `missing`.

---

### [LOW] F6. Identical summary dataclasses and a duplicated field

- `_FederatedComparisonSummaryRow` (44-50) and `_QuantileEstimationSummaryRow` (53-59) are identical dataclasses; one should be reused.
- Both reports set `mean_cv_fpr` and `fpr_coefficient_of_variation` to the same `_mean(cv_values)` (lines 213-214, 273-274) — the second field is a redundant alias that will drift if one is ever computed differently.

Fix: one shared row type; drop the redundant `fpr_coefficient_of_variation` field.

---

### [LOW] F7. New tests protect registration, not the scientific contract

`tests/unit/pipeline/workflows/test_federated_estimation_registration.py` (94 lines) and the additions to `test_registry_consistency.py` assert registration order, anchor-gating, declaration membership, and marker callability. Nothing asserts: the coefficient grid {2.0, 2.5, 3.0} is surfaced, per-coefficient operating points exist, or the reports emit threshold-error/attainment/sample-efficiency fields. The tests therefore pass while F1/F2/F3 are entirely present. Missing tests for the actual scientific content.

Fix: add contract tests that drive the reports over a fabricated evaluation document and assert the roadmap outcome fields and the coefficient grid.

---

## NO ISSUE — categories checked and found correct

- Wiring / production entrypoint. The three experiments are reachable end-to-end: CLI `run experiment`/`smoke`/`report`/`status` (`src/datp_core/cli/app.py`) → generic `run_experiment`/`run_smoke` → `_EXPERIMENT_DISPATCH_HANDLERS` → the three `_dispatch_*` functions (`campaign.py:597-654`) → `run_*_seed` → `execute_declared_experiment_seed`. Registry coverage is enforced (`_require_dispatch_covers_registry`, `campaign.py:1365`) and locked by tests (`test_execution_dispatch_table_covers_exactly_the_registered_workflows`, `test_report_dispatch_table_covers_exactly_the_registered_workflows`). No dead or test-only production code was found in the new workflow (all three run/report/marker functions are bound in `_WORKFLOW_HANDLERS`, `campaign.py:1349-1363`).
- B-FedStatsBenign math. `PooledVarianceDecomposition` requires within + between == full at construction (`federated_statistics.py:71-79`); the gaussian-matched exceedance threshold uses global mean and full pooled variance (`:159-163`); inputs are benign-only and the module contains no attack handling; `between_ratio` is correctly `None` when the denominator is zero. Matches roadmap §6.1 semantics.
- Communication semantics. `summarize_communication` docstring states "values are serialized-size estimates, not network measurements" (`src/datp_core/evaluation/communication.py:117`); the report's claim of honest estimation semantics is accurate.
- Regime A / Regime D boundary. All three new experiments are declared on N-BaIoT natural devices only; Regime D benign-FPR outcomes are handled by EDGE_BENIGN_EQUITY_VALIDATION (`experiments.py:384-392`). No cross-regime leakage.
- Typed I/O. The new workflow exchanges typed models (`FederatedEvaluationDocument`, `ExperimentCoordinate`, dataclasses); the only JSON boundary is the typed-dataclass → `asdict` serialization of the summary. No `Any`, no raw-dict domain contract, no primitive leaks.
- Completion-marker semantics. The complete marker is written only when `missing == 0`; otherwise the report returns a "N seed(s) missing" message and does not stamp completion. Consistent with the established `_finalize_report` behavior.
- Graphify graph. The graph (built at commit `76afa5c8`, 6569 nodes) indexes `fixed_coefficient_threshold()` and the federated threshold machinery, but indexes no node for the new workflow's run/report functions and no `fixed_coefficient_curve` symbol. This is consistent with, rather than contradictory to, the source finding that the curve has no downstream consumer.

---

## Validation performed

- Read the full roadmap (sections 1-10), the untrusted implementation report, all three new workflow files, the three experiment declarations, evaluation contracts/execution, population metrics, quantiles, communication, seeds, planning, evidence loader, campaign dispatch/report wiring, and all new/modified tests.
- `grep -rn fixed_coefficient_curve src/` — only construction in `federated_statistics.py`; no consumer.
- Confirmed `_evaluate` uses only assignments/matched_threshold; `FederatedEvaluationDocument` has no coefficient field.
- Confirmed `population_metric` raises on unavailable metric; report `except` block folds it into `missing`.
- Confirmed the three reports never read `doc.diagnostics`.
- Confirmed verbatim duplication of `_analysis_directory`/`_complete_marker`/`_finalize_report`/seed-result against `threshold_robustness.py`.
- Inspected `graphify-out/graph.json` and `GRAPH_REPORT` for the workflow and coefficient-curve nodes.

## Remaining issues (blockers)

- F1 blocks the fixed-coefficient sensitivity claim: no coefficient operating point exists anywhere in the pipeline or its outputs.
- F2/F3 block the comparator and quantile-estimation claims: the two experiments produce identical, outcome-poor tables and never surface the roadmap's required threshold-estimation outcomes.

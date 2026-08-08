# Reviewer 1 — Independent Audit of Prompt 4/8: Federated Threshold Estimation and Comparator Workflows

Audit date: 2026-08-08
HEAD: `fe21c002` (Fixes)
Scope: `FEDERATED_BENIGN_STATISTICS_COMPARISON`, `FEDERATED_QUANTILE_ESTIMATION`, `FIXED_COEFFICIENT_STATISTICS_SENSITIVITY` — threshold-variant experiments on N-BaIoT Regime A.

Source of truth: `docs/Journal_Extension_Master_Roadmap.md` (read in full; relevant: §9.1 benign summary-statistics comparator, §9.2 quantile-estimation backbone, §9.3 fixed-coefficient Laridi sensitivity, §8 threshold-estimation diagnostics, §6/§9 evaluation formulas).
Implementation report treated as untrusted: `docs/graphify_implementation/04_FEDERATED_THRESHOLD_ESTIMATION.md`.

Method: traced each changed symbol upward to its production entrypoint (CLI -> campaign dispatch/report/marker -> seed execution -> planning -> workspace -> threshold construction -> federated evaluation) and downward to the persisted scientific side effect (evaluation document -> report summary -> COMPLETE marker). Ran registration/registry tests (19 passed). Inspected the Graphify graph for currency.

---

## Findings

### F-1 CRITICAL — `FIXED_COEFFICIENT_STATISTICS_SENSITIVITY` is a no-op wrapper that cannot produce its declared outcome and persists a fabricated coefficient value

Roadmap §9.3 defines a fixed-coefficient sensitivity of `B-FedStatsBenign` over `k in {2.0, 2.5, 3.0}`. The implementation never evaluates a per-coefficient threshold into any FPR outcome.

Evidence chain:

1. **No coefficient dimension in planning.** `_SweptCell` (`src/datp_core/pipeline/planning.py:109-140`) sweeps `seed × threshold_method × metric × temporal_state × model_coefficient (FedProx/Ditto only) × threshold_quantile × controlled_partition`. There is no summary-coefficient field. `expand_experiment_plan` therefore produces no per-coefficient coordinates for this experiment.
2. **No coefficient dimension in the declaration.** `ExperimentDeclaration` for the experiment (`src/datp_core/protocols/experiments.py:376-383`) declares 3 methods (SHARED, LOCAL, FEDERATED_BENIGN_STATISTICS) and OPERATING_POINT_METRICS only — no coefficient grid. The report for this experiment therefore cannot differentiate seeds by coefficient.
3. **The fixed-coefficient thresholds are never evaluated.** `construct_federated_benign_statistics` (`src/datp_core/thresholding/methods/federated_statistics.py:146-210`) computes `fixed_coefficient_curve` (a tuple of raw `FixedCoefficientResult(coefficient, threshold)` at lines 187-197) but `assignments` uses only `matched_threshold`. `_evaluate` in `src/datp_core/evaluation/federated/execution.py:142-162` evaluates **only** `request.threshold_result.assignments` (see `_assignments` line 382-395, returning `result.assignments` for `FederatedStatisticsThresholdResult`). `_deployment_fallback_threshold` (line 411-412) uses `result.matched_threshold`. Grep confirms `fixed_coefficient_curve` / `FixedCoefficientResult` are referenced in production only inside `federated_statistics.py` and once in a test (`tests/scientific/test_benign_only_threshold_construction.py:292`). It is never persisted, never evaluated into FPR/CV(FPR), never reported.
4. **The report fabricates a coefficient.** `report_fixed_coefficient_statistics_sensitivity` (`src/datp_core/pipeline/workflows/federated_threshold_estimation.py:310-343`) reads the *matched-threshold* evaluation documents and writes `_FixedCoefficientSummaryRow(seed=..., coefficient=0.0, ...)` at line 328. `0.0` is not a member of `SUMMARY_COEFFICIENTS = (2, 2.5, 3)` (`src/datp_core/protocols/calibration.py:186`). This is an invented scientific value persisted to `summary.json`, violating CLAUDE.md §2.2 ("Never invent or infer missing scientific values") and §10.1 (no hardcoded values).

Net effect: the experiment reruns the same FEDSTATS matched-threshold evaluation already covered by the other two experiments and labels it a coefficient-sensitivity analysis with a fabricated coefficient column. It is a redundant, scientifically misleading no-op.

Why wrong: roadmap §9.3 requires per-coefficient threshold outcomes; a "sensitivity of B-FedStatsBenign" with only one evaluated threshold and a fake `k=0.0` label reports a sensitivity study that did not run. The implementation report's claim "Fixed coefficient grid — Locked to {2.0, 2.5, 3.0} as per roadmap §9.3" is false at the execution level (the grid exists only in configuration).

Concrete fix: either (a) delete the experiment and report (the coefficient curve, if intended as a diagnostic, belongs inside the §9.1/§9.2 reports reading `fixed_coefficient_curve` directly), or (b) implement a genuine sensitivity: add a summary-coefficient dimension to `_SweptCell`/coordinate/declaration for this experiment, evaluate each `FixedCoefficientResult.threshold` into per-client FPR, and report per-coefficient CV(FPR)/worst-client-FPR. Remove the hardcoded `0.0`.

### F-2 HIGH — `FEDERATED_BENIGN_STATISTICS_COMPARISON` and `FEDERATED_QUANTILE_ESTIMATION` are identical duplicate workflows

- Declarations are byte-identical: `src/datp_core/protocols/experiments.py:358-365` and `366-374` — same 5 methods (`_FEDERATED_STATISTICS_COMPARISON_METHODS`), same `OPERATING_POINT_METRICS`, same population/model/preprocessing.
- Report functions differ only in marker text: `report_federated_benign_statistics_comparison` (`federated_threshold_estimation.py:190-226`) vs `report_federated_quantile_estimation` (`250-286`) — identical loops, identical summary rows, identical serialization.
- The campaign executes the identical evaluation twice (two `_REGISTERED_WORKFLOWS` entries, `campaign.py:140-141`, two dispatchers `campaign.py:597-635`).

Why wrong: roadmap §9.1 and §9.2 are distinct scientific questions (mandatory comparator stress test vs optional quantile-estimation backbone). The quantile-estimation experiment does not report any §9.2 outcome (quantile-estimation error, threshold variance, calibration sample efficiency, relation to FPR equity); it reports exactly the same CV(FPR)/worst-FPR summary as the comparison experiment. Duplicate responsibility, double execution cost, and no differentiated science — violates CLAUDE.md §5/§6 (reuse-first, duplication removal).

Concrete fix: consolidate to one workflow, or differentiate the quantile-estimation report to surface §9.2 outcomes from `EvaluationDiagnostics` (see F-3). Do not run the same evaluation twice.

### F-3 HIGH — Reports omit §9.1/§9.2 required outcomes that are already computed and persisted

Roadmap §9.1 required outcomes include: threshold value, absolute and relative threshold error, target-attainment error, `CV(FPR)`, IQR, range, worst-client FPR, communication fields and estimated bytes, client coverage, comparison with B1/B2. §9.2 outcomes include quantile-estimation error, achieved benign exceedance, threshold variance, calibration sample efficiency, estimated communication, relation between estimation error and FPR equity.

All of the underlying data is already computed and persisted in the evaluation document:
- `EvaluationDiagnostics.threshold_estimation` — `ThresholdEstimationDiagnostic` (`src/datp_core/evaluation/threshold_estimation.py`): estimated_threshold, exact pooled quantile reference, target/achieved exceedance, absolute/relative threshold error, signed/absolute attainment error. Built in `_evaluate_threshold_estimation_input` (`execution.py:288-299`) from `_threshold_estimation_inputs` (`src/datp_core/pipeline/execution/workspace.py:329-387`).
- `EvaluationDiagnostics.communication` — `summarize_communication` (serialized-size estimates; `execution.py:269-273`).
- `EvaluationDiagnostics.sample_efficiency` — `sample_efficiency_curve` (`execution.py:284`).

Yet both report functions read only `MetricId.FPR_COEFFICIENT_OF_VARIATION` and `MetricId.WORST_CLIENT_FPR` via `population_metric` (`federated_threshold_estimation.py:205-206` and `265-266`). They never read `doc.diagnostics.threshold_estimation`, `doc.diagnostics.communication`, or `doc.diagnostics.sample_efficiency`. The comparator report omits the threshold-estimation error and target-attainment error that are the core diagnostic claims of the comparator (roadmap §9.1 procedure steps 3-4).

Why wrong: the analysis artifacts are incomplete relative to the roadmap's mandatory required outcomes; the summary report does not expose the exact pooled quantile reference or the absolute/relative threshold error, so the comparator's central claim is unauditable from the produced report.

Concrete fix: read `doc.diagnostics.threshold_estimation` and `doc.diagnostics.communication` (and `sample_efficiency` for §9.2) in the report functions and serialize per-method threshold-error / attainment-error / communication fields. Compare with `_FixedShrinkageCurve` reporting pattern in `threshold_robustness.py` (`report_fixed_shrinkage_curve` reads `doc.diagnostics.shrinkage_curve`), which demonstrates the intended curve-style diagnostic reporting.

### F-4 MEDIUM — `fpr_coefficient_of_variation` field stores the mean, not the across-seed coefficient of variation

`federated_threshold_estimation.py:214` and `:274`:
```python
fpr_coefficient_of_variation=_mean(cv_values),
```
The field name promises the across-seed coefficient of variation of the per-seed CV(FPR) values, but it stores the same arithmetic mean already written to `mean_cv_fpr` (lines 212, 272). The correct helper `_coefficient_of_variation` (std/mean) exists in `src/datp_core/pipeline/workflows/threshold_robustness.py:220-227` but is not reused — also a §5 reuse violation.

Concrete fix: import/reuse `_coefficient_of_variation` (or hoist it to a shared module) and assign `fpr_coefficient_of_variation=_coefficient_of_variation(cv_values)`.

### F-5 MEDIUM — Two byte-identical summary-row dataclasses

`_FederatedComparisonSummaryRow` (`federated_threshold_estimation.py:44-51`) and `_QuantileEstimationSummaryRow` (`:53-60`) are identical (method, seed_count, mean_cv_fpr, worst_client_fpr, fpr_coefficient_of_variation). Duplicate responsibility, violates §5/§8.

Concrete fix: one shared row type.

### F-6 MEDIUM — Registration tests never assert report content or coefficient carry-through

`tests/unit/pipeline/workflows/test_federated_estimation_registration.py` (9 tests) verifies registration, declaration lock, and marker callability only. No test asserts: the coefficient grid is carried through planning/evaluation/report, the report reads diagnostics, or that `fixed_coefficient_curve` is evaluated. This test gap is why F-1/F-3 could pass the suite. `tests/scientific/test_benign_only_threshold_construction.py:292` asserts the curve thresholds exist but not that they are evaluated or reported.

### F-7 LOW — Graphify graph is stale and cannot verify this scope

`graphify-out/graph.json` built 2026-08-07 23:31 from commit `76afa5c8`; the new workflow file `federated_threshold_estimation.py` was created 2026-08-08 01:39; HEAD is `fe21c002`. The graph predates the change set and contains zero references to the three experiment IDs. Any claim that the graph verifies this prompt's wiring is unsupported. Regenerate the graph from HEAD before using it as evidence.

---

## NO ISSUE — categories checked and found correct

- **CLI wiring and reachability.** All three experiments are registered (`campaign.py:140-142`), have dispatch functions (`campaign.py:597-650`), report aliases (`:49-55`), analysis-marker aliases (`:40-46`), and `_WORKFLOW_HANDLERS` entries (`:1350-1360`), with `_require_dispatch_covers_registry` (`:1365`) enforcing coverage. Reachable from `run_smoke` / `generate_report` / `programme_status` (`cli/app.py`) and `run_experiment` / `run_campaign` (`cli/execution.py`). NO ISSUE.
- **Population-capability authorization.** N-BaIoT `valid_threshold_methods` includes `POOLED_SHARED_QUANTILE` (`capabilities.py:107`), `SAMPLE_WEIGHTED_SHARED_THRESHOLD` (`:113`), `FEDERATED_BENIGN_STATISTICS` (`:131`). Every method used by the three experiments is authorized on the population. Unsupported methods (e.g. `SIZE_AWARE_SHRINKAGE`) correctly fail validation. NO ISSUE.
- **Protocol-graph / programme-status inclusion.** `CANONICAL_PROTOCOL_GRAPH.experiments = EXPERIMENTS` (`protocols/validation.py:76`), so the three experiments appear in status derivation. NO ISSUE.
- **Benign-only calibration boundary.** `construct_federated_benign_statistics` consumes only `ClientBenignCalibrationScores` (benign-only). No attack-labelled data enters calibration; threshold construction reads no test labels or test outcomes. NO ISSUE.
- **Pooled-variance decomposition correctness.** `PooledVarianceDecomposition` enforces `full == within + between` in `__post_init__` (`federated_statistics.py:71-79`); `between_ratio` is `None`-guarded when `full == 0`. Gaussian-matched exceedance threshold is built at the target `1-q` (roadmap §9.1 matching rule). NO ISSUE.
- **COMPLETE-marker gating.** `_finalize_report` (`federated_threshold_estimation.py:94-104`) writes the COMPLETE marker only when `missing_count == 0`; `*_analysis_marker_present` checks the marker file. Report/status cannot be marked complete with missing seeds. NO ISSUE.
- **Digest-validated evaluation documents.** `_evaluation_document_for_seed` uses `load_evaluation_document` (digest-validated) and raises `ScientificContractError` on missing/ambiguous/incomplete documents; `population_metric` raises when the metric is unavailable rather than substituting a fallback. NO ISSUE.
- **Deterministic planning and seed handling.** `_evaluation_document_for_seed` asserts exactly one coordinate match per method/metric (`federated_threshold_estimation.py:138-141`); iteration uses `CONFIRMATORY_SEED_COHORT` and sorted plan entries. NO ISSUE.
- **Registration and registry-consistency tests pass.** `pytest tests/unit/pipeline/workflows/test_federated_estimation_registration.py tests/unit/pipeline/workflows/test_registry_consistency.py -q` -> `19 passed`. (See F-6 for the coverage gap, not a failure of these tests' own assertions.)
- **Summary-coefficient configuration.** `SUMMARY_COEFFICIENTS = (2, 2.5, 3)` (`protocols/calibration.py:186`) matches roadmap §9.3, and `FEDERATED_STATISTICS_PROTOCOL.coefficients = SUMMARY_COEFFICIENTS` (`:220-223`). The implementation report's claim that "no changes needed" for `FederatedStatisticsProtocol` is *technically* true at the config layer but vacuous at the execution layer (F-1): the coefficients are never swept, evaluated, or reported.

---

## Test runs executed

- `pytest tests/unit/pipeline/workflows/test_federated_estimation_registration.py tests/unit/pipeline/workflows/test_registry_consistency.py -q` -> `19 passed`.
- Grep-based artifact-lifecycle checks: `fixed_coefficient_curve` / `FixedCoefficientResult` unreferenced outside `federated_statistics.py` + one test; `coefficient=0.0` hardcoded in the fixed-coefficient report; report functions read only two population metrics.

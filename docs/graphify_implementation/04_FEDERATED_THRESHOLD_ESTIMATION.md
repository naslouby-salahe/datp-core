# 04 — Federated Threshold Estimation and Comparator Workflows

## Implementation Summary

### Experiments wired

Three threshold-variant experiments now have complete workflow implementations:

| Experiment | Role | Population | Threshold Methods | Status |
|---|---|---|---|---|
| FEDERATED_BENIGN_STATISTICS_COMPARISON | threshold_variant | N-BaIoT natural devices | 5 (shared, pooled, sample-weighted, local, federated statistics) | Complete |
| FEDERATED_QUANTILE_ESTIMATION | threshold_variant | N-BaIoT natural devices | 5 (same set as comparison) | Complete |
| FIXED_COEFFICIENT_STATISTICS_SENSITIVITY | threshold_variant | N-BaIoT natural devices | 3 (shared, local, federated statistics) | Complete |

### Files changed

1. **src/datp_core/pipeline/workflows/federated_threshold_estimation.py** (NEW)
   - Seed runners: `run_federated_benign_statistics_comparison_seed`, `run_federated_quantile_estimation_seed`, `run_fixed_coefficient_statistics_sensitivity_seed`
   - Report functions: `report_federated_benign_statistics_comparison`, `report_federated_quantile_estimation`, `report_fixed_coefficient_statistics_sensitivity`
   - Analysis markers: `federated_benign_statistics_comparison_analysis_marker_present`, `federated_quantile_estimation_analysis_marker_present`, `fixed_coefficient_statistics_sensitivity_analysis_marker_present`

2. **src/datp_core/pipeline/workflows/campaign.py** (MODIFIED)
   - Added 3 entries to `_REGISTERED_WORKFLOWS`
   - Added 3 dispatch functions: `_dispatch_federated_benign_statistics_comparison`, `_dispatch_federated_quantile_estimation`, `_dispatch_fixed_coefficient_statistics_sensitivity`
   - Added 3 report handler aliases
   - Added 6 analysis marker alias imports
   - Added 3 entries to `_WORKFLOW_HANDLERS`

3. **tests/unit/pipeline/workflows/test_registry_consistency.py** (MODIFIED)
   - Extended `_EXPECTED_CAMPAIGN_ORDER` with 3 new experiments
   - Extended `_EXPECTED_ANCHOR_GATED_EXPERIMENTS` with 3 new experiments

4. **tests/unit/pipeline/workflows/test_federated_estimation_registration.py** (NEW)
   - Registration contract tests for all 3 experiments
   - Declaration lock tests
   - Analysis marker callability tests

### Scientific invariants preserved

1. **B-FedStatsBenign math** — Existing implementation verified correct:
   - Pooled variance decomposition includes within-client, between-client, and full pooled variance
   - Between-ratio computable when denominator is non-zero
   - Gaussian-matched exceedance threshold uses global mean and full pooled variance
   - Benign-only inputs (verified by test suite)
   - No attack-labelled calibration data

2. **Fixed coefficient grid** — Locked to {2.0, 2.5, 3.0} as per roadmap §9.3

3. **Regime A + Regime D boundaries** — Experiment declarations respect population scope:
   - FEDERATED_BENIGN_STATISTICS_COMPARISON and FEDERATED_QUANTILE_ESTIMATION are declared only for N-BaIoT (Regime A); Regime D FPR outcomes follow the EDGE_BENIGN_EQUITY_VALIDATION experiment which already declares FEDERATED_BENIGN_STATISTICS
   - Edge-IIoTset attack-sensitive metrics (TPR, BA, Macro-F1, AUROC) are structurally unavailable (see edge_iiotset capabilities)

4. **Communication semantics** — Existing implementation verified correct:
   - `CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE` — explicitly estimated, not measured
   - Docstring in `summarize_communication`: "values are serialized-size estimates, not network measurements"

5. **Threshold-estimation diagnostics** — Properly typed with provenance:
   - `ThresholdEstimationDiagnostic` captures estimated threshold, exact pooled reference, target/achieved exceedance
   - `SampleEfficiencyPoint` captures calibration size, replicate count, threshold variance

### Validation results

- Ruff: All checks passed
- Pyright: 0 errors, 0 warnings
- Tests: 851 passed (2 pre-existing e2e circular-import collection errors, not caused by this change)
- Registration tests: 19 passed
- Registry consistency tests: 10 passed

### Four-reviewer audit (2026-08-08)

Four independent reviewers audited the implementation against the roadmap. All four converged on the same core findings. See `tmp/implementation/04_federated_threshold_estimation/reviewers/` for full reports and `review_resolution.md` for reconciliation.

**Resolved findings (post-audit fixes):**

| Finding | Severity | Resolution |
|---------|----------|------------|
| FIXED_COEFFICIENT_STATISTICS_SENSITIVITY fabricated `coefficient=0.0` | HIGH | Report now loads `fixed_coefficient_curve` from threshold artifact and surfaces real k∈{2.0,2.5,3.0} thresholds per seed. SHARED/LOCAL baselines retained with `coefficient=None`. |
| Reports omitted threshold-estimation, communication, sample-efficiency diagnostics | HIGH | Comparison report now surfaces absolute threshold error, absolute attainment error, communication bytes. Quantile report surfaces achieved exceedance, threshold variance, communication bytes. Both read `doc.diagnostics`. |
| `_QuantileEstimationSummaryRow` duplicated `_FederatedComparisonSummaryRow` | MEDIUM | Merged into single `_EstimationSummaryRow` with optional diagnostic fields. |
| `fpr_coefficient_of_variation` stored mean instead of CV | MEDIUM | Now uses `_coefficient_of_variation(cv_values)` = std/mean across seeds. |
| Undefined CV(FPR) counted as missing seed | LOW | `_try_metric_value` checks `MetricStatus.AVAILABLE` before accessing `.value`; only document-load failures increment `missing`. |
| Circular import at top level | LOW (pre-existing) | `execute_declared_experiment_seed` moved to function scope inside `_run_estimation_seed`. |

**Deferred:** Per-coefficient FPR evaluation (requires `_SweptCell` + evaluation pipeline changes). Graphify rebuild (stale at HEAD~2).

### No changes needed

The following were audited and found correct:
- `construct_federated_benign_statistics()` — math correct, pooled variance complete
- `PooledVarianceDecomposition` — between-client term required at construction
- Communication module — honest about estimation semantics
- Threshold estimation module — proper typed contracts
- Edge-IIoTset capabilities — correctly marks attack metrics unavailable
- `FederatedStatisticsProtocol` — coefficients locked to {2, 2.5, 3}
- `SUMMARY_COEFFICIENTS` — grid matches roadmap §9.3

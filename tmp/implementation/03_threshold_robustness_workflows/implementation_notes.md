# Implementation Notes: Threshold Robustness Workflows

Date: 2026-08-08

## Overview

Implemented 6 threshold robustness experiment workflows in a single new module `threshold_robustness.py`, wired into the existing campaign dispatch system.

## New module: `src/datp_core/pipeline/workflows/threshold_robustness.py`

Single new file permitted by the task specification. Contains:

- `ThresholdRobustnessSeedResult`: frozen dataclass holding training_seed, campaign_digest, and completed_threshold_methods
- `ThresholdRobustnessAssetDirectory`: StrEnum with ROOT and ANALYSIS directory names
- `_available_metric_value()`: shared helper using `metric_by_id()` and `MetricStatus` enum
- `_evaluation_document_for_seed()`: loads FederatedEvaluationDocument for a given seed+method
- `_evaluation_document_for_seed_quantile()`: same but also matches threshold_quantile
- `_run_robustness_seed()`: shared runner using `execute_declared_experiment_seed`
- 6 seed runner functions, one per experiment
- 6 report handler functions producing JSON summaries
- 6 analysis marker functions checking COMPLETE marker existence

### SIZE_AWARE_SHRINKAGE special handling

`run_size_aware_shrinkage_seed` filters the experiment declaration to only execute SHARED_THRESHOLD and LOCAL_THRESHOLD reference corners. SIZE_AWARE_SHRINKAGE returns `ThresholdUnavailableResult` at construction time because no lambda(n_k) formula is declared. The report handler separately records SIZE_AWARE_SHRINKAGE as UNAVAILABLE with a scientific rationale.

This avoids modifying `workspace.py`'s `threshold` property, which raises `ScientificContractError` for unavailable results.

### Report semantics

All 6 reports produce JSON summaries under `outputs/threshold_robustness/{experiment}/{population}/analysis/summary.json`. These are supportive evidence, not confirmatory claims. COMPLETE markers are written after summary generation.

## Modified: `src/datp_core/pipeline/workflows/campaign.py`

Changes:

1. **`_REGISTERED_WORKFLOWS`**: 6 new entries added (all anchor_gated=True)
2. **6 dispatch functions**: `_dispatch_shared_construction_sensitivity` through `_dispatch_local_conformal_coverage`
3. **`_size_aware_shrinkage_outcomes`**: helper function reporting SIZE_AWARE_SHRINKAGE as UNAVAILABLE with reason
4. **12 delegate wrapper functions**: lazy-import from `threshold_robustness.py`, placed before `_WORKFLOW_HANDLERS` dict
5. **`_WORKFLOW_HANDLERS`**: 6 new entries mapping ExperimentId to dispatch/report/analysis_marker handlers

### Delegate pattern

Delegates use inline `from datp_core.pipeline.workflows.threshold_robustness import ...` to avoid circular imports at module load time. This follows the same pattern used by existing confirmatory and temporal workflow delegates.

## Modified: `tests/unit/pipeline/workflows/test_registry_consistency.py`

Updated test fixtures:
- `_DECLARED_BUT_UNREGISTERED_EXPERIMENT` changed from SHARED_CONSTRUCTION_SENSITIVITY to HISTORICAL_DATP_REPRODUCTION
- `_EXPECTED_CAMPAIGN_ORDER` extended with 6 new experiments
- `_EXPECTED_ANCHOR_GATED_EXPERIMENTS` extended with 6 new experiments

## Unchanged files

- `workspace.py`: already handles CALIBRATION_SIZE_ABLATION dormancy, threshold_estimation_inputs, and conformal_coverage_inputs correctly
- `planning.py`: already sweeps QUANTILE_GRID for QUANTILE_SENSITIVITY
- `experiments.py`: 6 experiment declarations already had correct readiness, threshold methods, and metrics
- `evaluation/models.py`: MetricStatus, metric_by_id, MetricAvailability unchanged
- `domain/enums.py`: no changes needed

## Scientific invariants preserved

1. Fixed-score invariance: same model/checkpoint/scores reused via `execute_declared_experiment_seed`
2. Calibration is benign-only (enforced by `PartitionRole.CALIBRATION`)
3. Attack data remain evaluation-only
4. No test-label access during threshold construction
5. Per-client FPR disparity is central (FPR_COEFFICIENT_OF_VARIATION primary metric)
6. SIZE_AWARE_SHRINKAGE: no lambda(n_k) formula invented
7. All thresholds, quantiles, calibration sizes from validated protocol configuration
8. Reports are supportive evidence, not confirmatory claims

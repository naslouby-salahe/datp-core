# Threshold Robustness Workflows — Implementation Report

Prompt 3/8 — 2026-08-08

## Summary

Six threshold robustness experiment workflows implemented, wired, validated, and audit-clean. One new module (`threshold_robustness.py`) created; one existing file (`campaign.py`) modified with dispatch handlers and workflow registration; test fixtures updated for new campaign order. All experiments reuse frozen scores and existing pipeline infrastructure.

## Experiment-by-experiment status

### SHARED_CONSTRUCTION_SENSITIVITY
- **Threshold methods**: SHARED_THRESHOLD, POOLED_SHARED_QUANTILE, SAMPLE_WEIGHTED_SHARED_THRESHOLD, LOCAL_THRESHOLD
- **Mechanism**: Compares B1 arithmetic mean vs exact pooled quantile vs sample-weighted shared construction vs B2 local, all using same frozen scores/calibration
- **Report**: per-method mean CV-FPR across confirmatory seeds
- **Status**: DECLARED → registered workflow, executable

### QUANTILE_SENSITIVITY
- **Threshold methods**: SHARED_THRESHOLD, CLUSTER_THRESHOLD, LOCAL_THRESHOLD
- **Quantile grid**: {0.90, 0.95, 0.975, 0.99} from `QUANTILE_GRID`
- **Planning**: `planning.py` already sweeps QUANTILE_GRID for this experiment
- **Report**: per-method per-quantile mean CV-FPR across seeds
- **Status**: DECLARED → registered workflow, executable

### CALIBRATION_SIZE_ABLATION
- **Threshold methods**: SHARED_THRESHOLD, CLUSTER_THRESHOLD, LOCAL_THRESHOLD, LOCAL_GLOBAL_SHRINKAGE, LOCAL_CONFORMAL_THRESHOLD
- **Sizes**: {50, 100, 250, 500, 1000, 5000} from `CALIBRATION_SIZES`
- **Replicates**: 10 per training seed from `CALIBRATION_SUBSAMPLE_REPLICATE_COUNT`
- **Wiring**: dormant in `workspace.py:calibration_size_ablation` (activated when `coordinate.experiment is CALIBRATION_SIZE_ABLATION`)
- **Report**: per-cell records with seed, method, size, replicate, CV-FPR, worst-client FPR, P10 macro-F1
- **Status**: DECLARED → registered workflow, executable

### FIXED_SHRINKAGE_CURVE
- **Threshold method**: LOCAL_GLOBAL_SHRINKAGE
- **Lambda weights**: {0, 0.25, 0.50, 0.75, 1.00} from FIXED_SHRINKAGE_PROTOCOL
- **Formula**: τ_k(λ) = λ·τ_local + (1-λ)·τ_shared
- **Report**: per-lambda CV-FPR and worst-client FPR across seeds
- **Status**: DECLARED → registered workflow, executable

### SIZE_AWARE_SHRINKAGE
- **Executable methods**: SHARED_THRESHOLD, LOCAL_THRESHOLD (reference corners only)
- **SIZE_AWARE_SHRINKAGE**: always returns `ThresholdUnavailableResult` — no λ(n_k) formula declared in the scientific protocol
- **Report**: reference corner metrics + explicit UNAVAILABLE declaration for SIZE_AWARE_SHRINKAGE
- **Status**: DECLARED → registered workflow, scientifically blocked for shrinkage method, reference corners executable

### LOCAL_CONFORMAL_COVERAGE
- **Threshold method**: LOCAL_CONFORMAL_THRESHOLD
- **Alpha**: 0.05 from calibration protocol
- **Diagnostics**: target_coverage, achieved_held_out_benign_coverage, signed/absolute coverage error per client
- **Wiring**: `workspace.py:_conformal_coverage_inputs` sends ConformalCoverageStageInput to evaluation when threshold is ConformalThresholdResult
- **Report**: per-client per-seed coverage diagnostic records
- **Status**: DECLARED → registered workflow, executable

## File changes

| File | Change |
|---|---|
| `src/datp_core/pipeline/workflows/threshold_robustness.py` | Created — 523 lines |
| `src/datp_core/pipeline/workflows/campaign.py` | Modified — +6 registered workflows, +6 dispatch functions, +12 delegates, +6 handler entries |
| `tests/unit/pipeline/workflows/test_registry_consistency.py` | Modified — fixture updates for new campaign order |

## Diagnostic wiring

- `threshold_estimation_inputs`: already handled by `workspace.py:_threshold_estimation_inputs()` for non-conformal, non-unavailable threshold results
- `conformal_coverage_inputs`: already handled by `workspace.py:_conformal_coverage_inputs()` for ConformalThresholdResult instances
- `calibration_size_ablation`: already handled by `workspace.py:calibration_size_ablation` property (activated by coordinate.experiment check)

No workspace.py modifications required.

## Validation results

| Check | Result |
|---|---|
| Ruff | All checks passed |
| Pyright | 0 errors, 0 warnings, 0 informations |
| Unit tests (665) | All passed |
| Scientific tests (135) | All passed |
| Property tests | All passed |

## Scientific invariants verified

1. Fixed-score invariance: `execute_declared_experiment_seed` reuses same model/checkpoint/scores
2. Benign-only calibration: `PartitionRole.CALIBRATION` enforced
3. Attack data evaluation-only: no leakage into threshold construction
4. No test-label access: threshold construction uses calibration split only
5. Per-client FPR disparity: FPR_COEFFICIENT_OF_VARIATION as primary operating-point metric
6. SIZE_AWARE_SHRINKAGE: no lambda(n_k) formula invented — explicitly UNAVAILABLE
7. Quantile grid: from QUANTILE_GRID, not hardcoded
8. Calibration sizes: from CALIBRATION_SIZES, not hardcoded
9. Replicate count: from CALIBRATION_SUBSAMPLE_REPLICATE_COUNT, not hardcoded
10. Lambda weights: from FIXED_SHRINKAGE_PROTOCOL, not hardcoded
11. Alpha: from calibration protocol, not hardcoded
12. Seeds: from CONFIRMATORY_SEED_COHORT, not hardcoded
13. Claim tiers: all reports are supportive evidence, not confirmatory

## Architecture compliance

- One new module (`threshold_robustness.py`) — permitted by task
- All execution through existing `execute_declared_experiment_seed`
- All evaluation through existing `evaluate_federated_detector`
- All document loading through existing `load_evaluation_document`
- All metric access through existing `metric_by_id` / `population_metric`
- Campaign dispatch follows existing pattern (dispatch → report → analysis_marker)
- No compatibility shims, legacy branches, or parallel paths

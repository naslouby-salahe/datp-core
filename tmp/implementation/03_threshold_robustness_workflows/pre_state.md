# Pre-State: Threshold Robustness Workflows

Date: 2026-08-08

## Current readiness of all six experiment IDs

| Experiment ID | Declaration | Readiness | Workflow Registered | Threshold Methods Wired | Current Status |
|---|---|---|---|---|---|
| SHARED_CONSTRUCTION_SENSITIVITY | experiments.py:259 | DECLARED | No | Yes (dispatch.py) | Declared only, zero production refs |
| QUANTILE_SENSITIVITY | experiments.py:268 | DECLARED | No | Yes (dispatch.py) | Declared only, planning.py sweeps QUANTILE_GRID |
| CALIBRATION_SIZE_ABLATION | experiments.py:322 | DECLARED | No | Yes (dispatch.py) | Declared only, dormant wiring in workspace.py:199,261 + decision/calibration.py:97 |
| FIXED_SHRINKAGE_CURVE | experiments.py:331 | DECLARED | No | Yes (dispatch.py) | Declared only, LOCAL_GLOBAL_SHRINKAGE method wired |
| SIZE_AWARE_SHRINKAGE | experiments.py:340 | DECLARED | No | Yes (dispatch.py → always UNAVAILABLE) | Declared only, method returns typed unavailable (no lambda(n_k) formula) |
| LOCAL_CONFORMAL_COVERAGE | experiments.py:349 | DECLARED | No | Yes (dispatch.py) | Declared only, LOCAL_CONFORMAL_THRESHOLD method wired |

## Underlying method status

- SHARED_THRESHOLD, POOLED_SHARED_QUANTILE, SAMPLE_WEIGHTED_SHARED_THRESHOLD: fully implemented in methods/shared.py
- LOCAL_THRESHOLD: fully implemented in methods/local.py
- CLUSTER_THRESHOLD: fully implemented in methods/cluster.py
- LOCAL_GLOBAL_SHRINKAGE: fully implemented in methods/shrinkage.py, uses FIXED_SHRINKAGE_PROTOCOL weights {0, 0.25, 0.5, 0.75, 1}
- SIZE_AWARE_SHRINKAGE: returns ThresholdUnavailableResult (no lambda(n_k) formula declared)
- LOCAL_CONFORMAL_THRESHOLD: fully implemented in methods/conformal.py, uses alpha=0.05

## Diagnostic status

- evaluation/threshold_estimation.py: fully implemented but never receives inputs (dead producers)
- evaluation/conformal_coverage.py: fully implemented but never receives inputs (dead producers)
- MetricIds ABSOLUTE_THRESHOLD_ERROR, RELATIVE_THRESHOLD_ERROR, SIGNED_ATTAINMENT_ERROR, ABSOLUTE_ATTAINMENT_ERROR: no producers
- MetricIds TARGET_COVERAGE, ACHIEVED_COVERAGE, SIGNED_COVERAGE_ERROR, ABSOLUTE_COVERAGE_ERROR: no producers

## Planning status

- QUANTILE_SENSITIVITY: planning.py:144 already sweeps QUANTILE_GRID for this experiment
- CALIBRATION_SIZE_ABLATION: dormant wiring in workspace.py; decision/calibration.py has construct_calibration_size_ablation
- Other experiments: standard planning with no factor sweeps

## Required actions

1. Register all 6 experiments as workflows in campaign.py
2. Create seed runner functions for each
3. Create report/analysis handler functions
4. Wire threshold estimation and conformal coverage diagnostics
5. Write tests
6. Run validation

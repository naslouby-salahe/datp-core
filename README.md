# DATP-Core

**Device-Aware Threshold Personalization: A Controlled Threshold-Calibration Study for Non-IID Federated IoT Anomaly Detection.**

Status: `COMPLETE EXCEPT EXPERIMENT EXECUTION`

## Package structure

```
src/datp_core/
  application/        Stage handlers, use cases, reporting, statistical analysis
    configuration.py  Resolved-configuration query
    dataset_audit.py  Dataset readiness audit
    experiment_execution.py  DAG traversal and dispatch
    experiment_planning.py   DAG construction and validation
    ports.py          Repository and adapter interfaces
    reporting.py      Result freeze, tables, figures
    result_audit.py   Frozen-result validation
    stage_handlers.py All 11 stage handlers (~3400 lines)
    statistical_analysis.py  BCa, Wilcoxon, paired-seed analysis
    threshold_construction.py  Threshold estimator orchestration
  composition/        Application wiring (root.py)
  config/             Configuration resolution, validation, models
  domain/             Immutable scientific value objects and contracts
  infrastructure/     Framework adapters (PyTorch, Flower, Polars, SciPy, Parquet)
  interfaces/         CLI (click)
  orchestration/      Dagster integration (optional)
  planning/           Experiment DAG identity and expansion
```

## Pipeline stages (11 StageKind values)

| Stage | Handler | Status |
|---|---|---|
| PREFLIGHT | PreflightStageHandler | registered |
| DATASET_MATERIALIZATION | DatasetMaterializationStageHandler | registered |
| MODEL_TRAINING | ModelTrainingStageHandler | registered |
| COHORT_CHECKPOINT_SELECTION | CohortCheckpointSelectionStageHandler | registered |
| SCORE_GENERATION | ScoreGenerationStageHandler | registered |
| CALIBRATION_SUBSAMPLING | CalibrationSubsamplingStageHandler | registered |
| THRESHOLD_CONSTRUCTION | ThresholdConstructionStageHandler | registered |
| OPERATING_POINT_EVALUATION | OperatingPointEvaluationStageHandler | registered |
| STATISTICAL_ANALYSIS | StatisticalAnalysisStageHandler | registered |
| RESULT_FREEZE | ResultFreezeStageHandler | registered |
| REPORT_GENERATION | ReportGenerationStageHandler | registered |

## Artifact kinds (20 ArtifactKind values)

`resolved_config`, `materialized_dataset`, `split_manifest`, `partition_manifest`,
`dataset_readiness`, `preprocessing_evidence`, `model_checkpoint`,
`personalized_model_checkpoint`, `checkpoint_selection`, `calibration_scores`,
`future_recalibration_scores`, `calibration_subset`, `test_scores`, `thresholds`,
`threshold_diagnostics`, `client_metrics`, `statistical_summary`, `result_freeze`,
`result_report`, `report`

## CLI

```
datp-core config validate|explain-drift|fingerprint
datp-core catalogue describe
datp-core dataset audit DATASET_ID
datp-core experiment plan|run -c EXPERIMENT
datp-core results query SQL
```

## Experiment catalogue

23 experiments defined in `configs/experiments.yaml` covering:
confirmatory, sensitivity, mechanism, calibration-robustness, comparator,
external-validation, stress-test, and temporal categories.

14 threshold policies defined in `configs/protocols.yaml`.

## Datasets

| Dataset | Clients | Type | Regime |
|---|---|---|---|
| N-BaIoT | 9 | physical devices | A (confirmatory), C (heterogeneity) |
| CICIoT2023 | 63 | file-defined pseudo-clients | B-a (applicability boundary) |
| Edge-IIoTset | 10 (static) / 9 (temporal) | sensor-group folders | D (external validation) |

## Quality gates

- Ruff: all checks pass
- Formatting: all files formatted
- Pyright: 0 errors, 0 warnings
- Import-linter: 2/2 contracts kept
- Tests: 360+ passing

## Scientific authority

The canonical scientific contract is `docs/roadmap/SCIENTIFIC_SOURCE_OF_TRUTH.md`.
All implementation, configuration, and tests must conform to it.

## Architecture documentation

`docs/Architecture/` contains design documentation. Some files describe aspirational
target-state architecture that diverges from the current implementation. The file
tree and type catalogue above are authoritative for the current state.

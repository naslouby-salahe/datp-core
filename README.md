# DATP-Core

**Device-Aware Threshold Personalization: A Controlled Threshold-Calibration Study for Non-IID Federated IoT Anomaly Detection.**

Status: `COMPLETE EXCEPT EXPERIMENT EXECUTION`

## Package structure

```
src/datp_core/
  core/            Bottom-layer scientific value objects, identifiers, and typed registries
                    (imports nothing else in datp_core)
  contracts/       Resolved protocol-level record types shared across configuration, analysis,
                    and reporting (imports only core/ and third-party schema libraries)
  config/          Authored-YAML schema, resolution, fingerprints, and the composition-root
                    validator (schema/, resolve/, project.py, loading.py, fingerprints.py)
  data/            Dataset adapters (N-BaIoT, CICIoT2023, Edge-IIoTset), split manifests, and
                    materialization (adapters/, contracts.py, manifests.py, sources.py)
  experiments/     Experiment definitions, sweeps, planning, identity, and execution
  learning/        Model definition, federated/personalization training, checkpoints, and scoring
  thresholding/    Threshold policy models, calibration, quantile/grouped/conformal/shrinkage
                    estimators
  evaluation/      Confusion-matrix, operating-point, AUROC, dispersion, and score-distribution
                    evaluation
  analysis/        Paired/association/stability/coverage/temporal/resource analyses, typed
                    results, and dispatch
  reporting/       Result freezing, table rendering, figure rendering, and report-package
                    generation
  artifacts/       Artifact identity, persistence, serialization, and provenance
  pipeline/        Stage/job models and DAG execution shared by every feature package
  app.py           Composition root assembling every feature package's use cases and stage
                    handlers -- the sole module permitted to import concrete infrastructure
                    across package boundaries
  cli.py           Typer CLI routing commands to explicit application use cases
```

Import direction across these packages is enforced by `importlinter.ini` (8 contracts): `core`
imports nothing else in `datp_core`; `contracts` imports only `core`; the config-independent model modules
(`experiments.models`, `data.contracts`, `learning.models`, `thresholding.models`,
`evaluation.models`, `analysis.results`, `analysis.statistics`, `artifacts.models`) never import
`config.project`, `app`, or `cli`; only `cli.py` imports `app.py`; `analysis` never imports
`reporting`; `data`/`learning`/`thresholding`/`evaluation` never import `analysis`/`reporting`;
`flwr` is not a dependency anywhere in the package; and `data.contracts`/`experiments.models`
never import each other, even indirectly (the one place two feature packages' execution-tier
modules legitimately cross into each other's pure-data tier today).

There is no `orchestration/`, `application/`, `domain/`, `infrastructure/`, `interfaces/`,
`composition/`, or `planning/` package -- an earlier horizontal-layer architecture was replaced by
the feature-oriented tree above.

## Pipeline stages (11 StageKind values)

| Stage | Handler | Status |
|---|---|---|
| PREFLIGHT | PreflightStageHandler | registered |
| DATASET_MATERIALIZATION | DatasetMaterializationStageHandler | registered |
| MODEL_TRAINING | ModelTrainingStageHandler | registered |
| CHECKPOINT_SELECTION | CohortCheckpointSelectionStageHandler | registered |
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
datp-core config validate|explain-drift|explain-scientific-drift|explain-execution-drift|fingerprint
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
- Import-linter: 8/8 contracts kept
- Tests: 358 passing, 0 skipped

## Scientific authority

The canonical scientific contract is `docs/roadmap/SCIENTIFIC_SOURCE_OF_TRUTH.md`.
All implementation, configuration, and tests must conform to it.

## Architecture documentation

`docs/Architecture/` contains design documentation. Some files describe aspirational
target-state architecture that diverges from the current implementation. The file
tree and type catalogue above are authoritative for the current state.

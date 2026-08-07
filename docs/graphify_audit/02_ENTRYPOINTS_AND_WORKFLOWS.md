# 02 — Entrypoints and Workflows

## CLI Entrypoints (src/datp_core/cli/app.py)

| Command | Function | Arguments | Delegates To |
|---------|----------|-----------|-------------|
| `validate [EXPERIMENT_ID]` | `validate_command` | Optional ExperimentId | `validate_programme()` |
| `plan [EXPERIMENT_ID]` | `plan_command` | Optional ExperimentId | `build_programme_plan()` |
| `preprocess [DATASET_ID]` | `preprocess_command` | Optional DatasetId, --overwrite | `preprocess_datasets()` |
| `smoke [EXPERIMENT_ID]` | `smoke_command` | Optional ExperimentId, --overwrite | `run_smoke()` |
| `report [EXPERIMENT_ID]` | `report_command` | Optional ExperimentId, --overwrite | `generate_report()` |
| `status [EXPERIMENT_ID]` | `status_command` | Optional ExperimentId | `programme_status()` |
| `run experiment <ID>` | `experiment_command` | ExperimentId, --overwrite | `run_experiment()` |
| `run campaign` | `campaign_command` | --overwrite | `run_campaign()` |
| `anchor reproduce` | `reproduce_command` | --overwrite | `reproduce_anchor()` |
| `anchor verify` | `verify_command` | — | `verify_anchor_programme()` |
| `anchor status` | `status_command` | — | `anchor_status()` |

## Experiment Registry

### Experiments WITH registered workflows (7 of 24):

| ExperimentId | Role | Population | Anchor Gated |
|-------------|------|-----------|--------------|
| SHARED_VS_LOCAL_CONFIRMATION | CONFIRMATORY | NBAIOT_NATURAL_DEVICES | YES |
| FAMILY_AND_GROUPED_GRANULARITY | MECHANISM | NBAIOT_NATURAL_DEVICES | YES |
| FEDPROX_ABSORPTION_STRESS_TEST | TRAINING_STRESS_TEST | NBAIOT_NATURAL_DEVICES | YES |
| DITTO_ABSORPTION_STRESS_TEST | TRAINING_STRESS_TEST | NBAIOT_NATURAL_DEVICES | YES |
| EDGE_BENIGN_EQUITY_VALIDATION | EXTERNAL_VALIDATION | EDGE_SENSOR_GROUPS | NO |
| CICIOT_FILE_CLIENT_BOUNDARY | APPLICABILITY_BOUNDARY | CICIOT_FILE_CLIENTS | NO |
| EDGE_ONE_SHOT_RECALIBRATION | TEMPORAL_BOUNDARY | EDGE_TEMPORAL_GROUPS | NO |

### Experiments WITHOUT registered workflows (17 of 24):

| ExperimentId | Role | Status |
|-------------|------|--------|
| HISTORICAL_DATP_REPRODUCTION | ANCHOR_REPRODUCTION | Separate anchor path |
| SHARED_CONSTRUCTION_SENSITIVITY | SUPPORTIVE | DECLARED only |
| QUANTILE_SENSITIVITY | SUPPORTIVE | DECLARED only |
| CONTROLLED_HETEROGENEITY_SWEEP | MECHANISM | DECLARED only |
| PER_CLIENT_SCORE_GEOMETRY | MECHANISM | DECLARED only |
| HETEROGENEITY_BENEFIT_ASSOCIATION | MECHANISM | DECLARED only |
| THRESHOLD_MOVEMENT_TRADEOFF | MECHANISM | DECLARED only |
| CALIBRATION_SIZE_ABLATION | SUPPORTIVE | DECLARED only |
| FIXED_SHRINKAGE_CURVE | SUPPORTIVE | DECLARED only |
| SIZE_AWARE_SHRINKAGE | SUPPORTIVE | DECLARED only |
| LOCAL_CONFORMAL_COVERAGE | SUPPORTIVE | DECLARED only |
| FEDERATED_BENIGN_STATISTICS_COMPARISON | THRESHOLD_VARIANT | DECLARED only |
| FEDERATED_QUANTILE_ESTIMATION | THRESHOLD_VARIANT | DECLARED only |
| FIXED_COEFFICIENT_STATISTICS_SENSITIVITY | THRESHOLD_VARIANT | DECLARED only |
| ALERT_BURDEN_TRANSLATION | OPERATIONAL_TRANSLATION | SUPPRESSED |
| GROUP_MEDIAN_SUPPLEMENT | EXPLORATORY | DECLARED only |
| OPTIONAL_EQUITY_INDICES | EXPLORATORY | DECLARED only |

## Workflow Dispatch Architecture

```
CLI app.py
  └─> pipeline/workflows/__init__.py (public API)
        ├─> validate_programme() → protocols/validation.py
        ├─> build_programme_plan() → pipeline/planning.py
        ├─> preprocess_datasets() → datasets/service.py
        ├─> run_smoke() → campaign.py → _dispatch_experiment()
        ├─> run_experiment() → campaign.py → _dispatch_experiment()
        ├─> run_campaign() → campaign.py (validates, preprocesses, anchor, all experiments)
        ├─> generate_report() → campaign.py → _EXPERIMENT_REPORT_HANDLERS
        └─> programme_status() → campaign.py

campaign.py _EXPERIMENT_DISPATCH_HANDLERS:
  SHARED_VS_LOCAL_CONFIRMATION → confirmatory.run_confirmatory_seed()
  FAMILY_AND_GROUPED_GRANULARITY → confirmatory.run_family_grouped_mechanism_seed()
  EDGE_BENIGN_EQUITY_VALIDATION → external.run_external_validation_seed()
  CICIOT_FILE_CLIENT_BOUNDARY → external.run_ciciot_boundary_seed()
  FEDPROX_ABSORPTION_STRESS_TEST → personalization.run_fedprox_grid_campaign()
  DITTO_ABSORPTION_STRESS_TEST → personalization.run_ditto_stress_test_seed()
  EDGE_ONE_SHOT_RECALIBRATION → temporal.run_temporal_seed()

campaign.py _EXPERIMENT_REPORT_HANDLERS:
  SHARED_VS_LOCAL_CONFIRMATION → confirmatory.analyze_confirmatory_campaign()
  FAMILY_AND_GROUPED_GRANULARITY → confirmatory (via _report_confirmatory_family)
  EDGE_BENIGN_EQUITY_VALIDATION → external.analyze_external_validation_campaign()
  CICIOT_FILE_CLIENT_BOUNDARY → external.analyze_ciciot_boundary_campaign()
  FEDPROX_ABSORPTION_STRESS_TEST → personalization (via _report_fedprox_absorption)
  DITTO_ABSORPTION_STRESS_TEST → personalization.run_ditto_absorption_campaign()
  EDGE_ONE_SHOT_RECALIBRATION → temporal.run_temporal_campaign()
```

## Execution Flow (campaign mode)

```
run_campaign()
  1. validate_programme()
  2. preprocess_datasets(overwrite=False)
  3. reproduce_anchor(overwrite=overwrite)
  4. verify_anchor_programme()
  5. For each registered experiment (in order):
     a. run_experiment()
        - _enforce_anchor_gate() if not smoke
        - _dispatch_experiment() → handler(seeds, output_root, overwrite)
     b. generate_report(experiment_id)
  6. Write campaign COMPLETE marker
  7. generate_report(None) → campaign-level report
```

## Key Finding: 17 Unregistered Experiments

17 of 24 declared experiments have no registered workflow. They are declared in `EXPERIMENTS` and validate/plan correctly, but cannot be executed. Classification:

- **Intentionally suppressed**: ALERT_BURDEN_TRANSLATION (no rate evidence)
- **Separate anchor path**: HISTORICAL_DATP_REPRODUCTION
- **Declared but not yet implemented (15)**: All supportive, mechanism, threshold-variant, and exploratory experiments

These 15 experiments are journal-required but have no execution path. The validate command reports them as `unregistered_declared`.

### Seed Cohort Selection

- Confirmatory population (NBAIOT_NATURAL_DEVICES, NBAIOT_DIRICHLET_CLIENTS): 10 seeds
- Bounded-evidence populations (EDGE_SENSOR_GROUPS, EDGE_TEMPORAL_GROUPS, CICIOT_FILE_CLIENTS): smaller cohort
- Smoke: first seed only

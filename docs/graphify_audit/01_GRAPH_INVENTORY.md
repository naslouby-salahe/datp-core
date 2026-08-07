# 01 — Graph Inventory

Built from graphify queries and direct source inspection. Graphify graph exists at `graphify-out/graph.json`.

## Package Structure

```
src/datp_core/
├── __init__.py
├── analysis/           # Statistical analysis, contrasts, mechanisms
│   ├── contrasts.py
│   ├── descriptive.py
│   ├── mechanisms.py
│   ├── preparation.py
│   ├── scientific_decision.py
│   └── temporal.py
├── anchor/             # Historical reproduction gate
│   ├── comparison.py
│   ├── gate.py
│   ├── models.py
│   └── reproduction.py
├── calibration/        # Benign calibration, eligibility
│   ├── eligibility.py
│   ├── models.py
│   ├── sampling.py
│   └── service.py
├── cli/                # Typer CLI
│   ├── anchor.py
│   ├── app.py
│   ├── execution.py
│   └── validation.py
├── datasets/           # Dataset materialization, capabilities
│   ├── canonical_cache.py
│   ├── capabilities.py
│   ├── contracts.py
│   ├── materialization.py
│   ├── materialization_lifecycle.py
│   ├── paths.py
│   ├── publication.py
│   ├── registry.py
│   ├── service.py
│   └── partitioning/
│       ├── construction.py
│       └── contracts.py
├── domain/             # Enums, errors, contracts, value objects
│   ├── contracts.py
│   ├── enums.py
│   ├── errors.py
│   ├── provenance.py
│   └── values/
│       ├── base.py
│       ├── checksums.py
│       ├── counts.py
│       ├── identifiers.py
│       └── ratios.py
├── evaluation/         # Evaluation metrics, confusion, evidence
│   ├── client_metrics.py
│   ├── communication.py
│   ├── conformal_coverage.py
│   ├── confusion.py
│   ├── federated/
│   │   ├── contracts.py
│   │   └── publication.py
│   ├── fixed_score/
│   │   ├── construction.py
│   │   ├── contracts.py
│   │   └── validation.py
│   ├── metric_semantics.py
│   ├── models.py
│   ├── operational.py
│   ├── population_metrics.py
│   ├── threshold_estimation.py
│   ├── threshold_evidence.py
│   └── traffic_rates.py
├── learning/           # Model definitions, training
│   ├── autoencoder.py
│   └── federated/
│       ├── checkpoints/
│       │   └── selection.py
│       ├── models.py
│       └── training.py
├── pipeline/           # Orchestration, planning, execution
│   ├── checkpoints/
│   │   └── service.py
│   ├── coordinates.py
│   ├── decision/
│   │   ├── calibration.py
│   │   ├── centralized.py
│   │   ├── evidence.py
│   │   └── federated.py
│   ├── execution/
│   │   ├── checkpoints.py
│   │   ├── context.py
│   │   ├── engine.py
│   │   ├── evidence.py
│   │   ├── layout.py
│   │   ├── matched_reference.py
│   │   ├── models.py
│   │   ├── score_generation.py
│   │   └── workspace.py
│   ├── planning.py
│   ├── publication/
│   │   ├── layout.py
│   │   ├── models.py
│   │   └── service.py
│   ├── scoring/
│   │   └── models.py
│   ├── training/
│   │   └── federated.py
│   └── workflows/
│       ├── anchor.py
│       ├── campaign.py
│       ├── centralized.py
│       ├── confirmatory.py
│       ├── execution.py
│       ├── external.py
│       ├── personalization.py
│       ├── personalization_scoring.py
│       └── temporal.py
├── preprocessing/      # Data normalization, scaling
│   ├── centralized.py
│   ├── ciciot_file_clients.py
│   ├── client_partitions.py
│   ├── contracts.py
│   ├── federated.py
│   ├── models.py
│   ├── paths.py
│   ├── persisted_artifacts.py
│   ├── publication.py
│   ├── service.py
│   ├── state.py
│   └── validation.py
├── protocols/          # Typed protocol declarations
│   ├── anchor.py
│   ├── calibration.py
│   ├── checkpoints.py
│   ├── experiments.py
│   ├── graph.py
│   ├── inference.py
│   ├── metrics.py
│   ├── populations.py
│   ├── seeds.py
│   ├── splits.py
│   ├── statistics.py
│   ├── temporal.py
│   ├── traffic_rates.py
│   ├── training.py
│   └── validation.py
├── reporting/          # Publication artifacts
│   ├── export.py
│   ├── figures.py
│   ├── tables.py
│   └── validation.py
├── runtime/            # Determinism, logging, config, filesystem
│   ├── compute.py
│   ├── configuration.py
│   ├── determinism.py
│   ├── filesystem.py
│   └── logging.py
└── thresholding/       # Threshold construction, dispatch
    ├── assignments.py
    ├── dispatch.py
    ├── identities.py
    ├── methods/
    │   ├── cluster.py
    │   ├── conformal.py
    │   ├── family.py
    │   ├── federated_statistics.py
    │   ├── local.py
    │   ├── shared.py
    │   └── shrinkage.py
    ├── models.py
    ├── publication.py
    └── quantiles.py
```

## Key Dependency Flows

### CLI → Workflow → Execution
```
cli/app.py → pipeline/workflows/__init__.py → campaign.py → dispatch handler → execution.py → engine.py → workspace.py
```

### Experiment Declaration → Planning
```
protocols/experiments.py (EXPERIMENTS tuple) → pipeline/planning.py (expand_experiment_plan) → execution/models.py (build_campaign) → execution/engine.py (execute_campaign)
```

### Threshold Dispatch
```
thresholding/dispatch.py (dispatch_federated_threshold) → thresholding/methods/{shared,local,family,cluster,shrinkage,conformal,federated_statistics}.py
```

### Evaluation
```
evaluation/federated/contracts.py → evaluation/client_metrics.py → evaluation/population_metrics.py → evaluation/fixed_score/construction.py
```

### Analysis
```
analysis/contrasts.py → analysis/descriptive.py → analysis/mechanisms.py → analysis/scientific_decision.py
```

## Enum Inventory

| Enum | Members | File |
|------|---------|------|
| DatasetId | 3 | domain/enums.py |
| PopulationId | 5 | domain/enums.py |
| PopulationIdentityKind | 5 | domain/enums.py |
| ExperimentId | 24 | domain/enums.py |
| EvidenceRole | 11 | domain/enums.py |
| ExperimentReadiness | 5 | domain/enums.py |
| ProgrammeStatus | 11 | domain/enums.py |
| TrainingModelId | 4 | domain/enums.py |
| FederatedThresholdMethod | 10 | domain/enums.py |
| CentralizedThresholdMethod | 1 | domain/enums.py |
| MetricId | 33 | domain/enums.py |
| AvailabilityStatus | 6 | domain/enums.py |
| StageOperationId | 19 | domain/enums.py |
| TemporalState | 3 | domain/enums.py |
| PipelineStage | 13 | pipeline/execution/models.py |
| ExecutionRecipeId | 2 | pipeline/execution/models.py |
| ... | ... | ... |

## Value Objects

| Type | Wraps | File |
|------|-------|------|
| Seed | int | domain/values/counts.py |
| RowCount | int | domain/values/counts.py |
| ClientCount | int | domain/values/counts.py |
| RoundNumber | int | domain/values/counts.py |
| BatchSize | int | domain/values/counts.py |
| ClusterIndex | int | domain/values/counts.py |
| ByteCount | int | domain/values/counts.py |
| Checksum | str | domain/values/checksums.py |
| Quantile | float | domain/values/ratios.py |
| MetricValue | float | domain/values/ratios.py |
| ConfidenceLevel | float | domain/values/ratios.py |
| DirichletConcentration | float | domain/values/ratios.py |
| ModelCoefficientValue | float | domain/values/ratios.py |
| FeatureNameSequence | tuple[str,...] | domain/values/identifiers.py |
| CaptureTimestampColumn | str | domain/values/identifiers.py |

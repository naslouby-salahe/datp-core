# TARGET_ARCHITECTURE.md

## Drift Audit A — roadmap responsibility → current implementation location

(Performed before any target design. Source: `ROADMAP_EXTRACTION.md` + `CURRENT_ARCHITECTURE.md`.)

| Roadmap responsibility | Current implementation | Notes |
|---|---|---|
| Scientific identity/scope (fixed-detector ladder, AUROC-as-control-only) | Implicit across `domain/evaluation.py` (`assert_auroc_invariant`), `application/analysis_stages.py` | No code violation found; enforced by convention across stage handlers, not a single guarded module. Target: `evaluation/` owns the AUROC-invariant assertion explicitly. |
| Dataset definitions (N-BaIoT 9 clients, CICIoT2023 63 pseudo-clients, Edge-IIoTset 10/9 clients) | `infrastructure/datasets/{nbaiot,ciciot2023,edge_iiotset}.py`, `config/models/dataset_config.py`, `config/dataset_resolution.py`, `domain/datasets.py`, `configs/datasets/*.yaml` | Client counts are authored per-dataset in `configs/datasets/*.yaml`, resolved into `domain.datasets.ResolvedDataset`. Correctly config-driven already; must preserve exactly through migration. |
| Client eligibility (`n_k>=100`) | `config/models/experiment_config.py::EligibilityGateConfig`, `application/stage_protocol.py::evaluate_readiness_gates` | Gate evaluation logic sits in a "dumping ground" module (`stage_protocol.py`) — target: move to `datasets/readiness.py` or `experiments/` per ownership section 8.3. |
| Experiment catalogue / evidence roles / sweeps | `config/models/experiment_config.py`, `config/experiment_resolution.py`, `domain/catalogue.py`, `planning/expansion.py` | Spans config+domain+planning; target `experiments/` package per section 6. |
| Training profiles (FedAvg/FedProx/Ditto, seeds, rounds) | `config/models/protocol_config.py` (`TrainingProfileConfig`, `FederationStrategyConfig`), `infrastructure/learning/pytorch_adapter.py`, `application/learning_stages.py` | Round/mu/seed grids config-driven; algorithm mechanics in `pytorch_adapter.py` (649-line mixed file, needs splitting per section 8.4). |
| Checkpoint rules (anchor convergence, journal grid, forbidden selectors) | `domain/checkpoints.py` (pure algorithms), `application/learning_stages.py::CohortCheckpointSelectionStageHandler` | Correctly split: pure selection algorithm in domain, orchestration in application. Preserve this split in `learning/checkpoints.py`. |
| Threshold policy families (B0-B4, shrinkage, conformal, B-FedStatsBenign) | **3 independent layers**: `config/models/protocol_config.py` (12 Pydantic configs) → `config/protocol_resolution.py` (12-entry resolver dispatch) → `domain/thresholding.py` (12-member record union) → `infrastructure/thresholding/estimators.py` (12-branch estimator dispatch) | Biggest consolidation target — see §9.3 of CURRENT_ARCHITECTURE.md. Target: one coherent `thresholding/` package structuring all 3 executable layers (config models stay in `configuration/`, but resolution/record/estimator converge under `thresholding/`). |
| Seed cohorts / deterministic seed derivation | `config/models/protocol_config.py::SeedCohortConfig`, 3 independent reimplementations of the derivation formula (`pytorch_adapter._derive_seed`, `nbaiot.derive_partition_seed`, `calibration_subsampling._subsample_seed`) | Must consolidate into one canonical function — candidate home: `pipeline/` shared determinism helper reused by `learning/`, `datasets/`, `thresholding/`. This is a genuine duplication risk to scientific reproducibility, not just style. |
| Split rules (standard vs. temporal chronological) | `domain/splits.py` (validation), `infrastructure/datasets/{nbaiot,edge_iiotset}.py` (per-adapter split logic) | Correctly split at record-validation level; per-adapter split *algorithms* differ intentionally (chronological-gapped vs. chronological-with-rollover) — not a false duplication, preserve dataset-specific semantics per section 8.3. |
| Calibration/test separation | Enforced structurally via `domain/splits.py::SplitMembership`, never violated by any code path found in audit | No drift found. |
| Evaluation metrics (CV(FPR), metric-status enum) | `domain/evaluation.py` | Correctly placed already — good example per Part-1 audit. `cv_instability_threshold` **hardcoded invented value** at `application/analysis_stages.py:496` (`0.10 * (1.0 - quantile)`) — roadmap flags this exact item as unresolved/must-not-invent (SoT §17 item 20, §1.4). **This is pre-existing scientific-configuration debt, not something this architecture refactor will silently "fix."** Will preserve exact current runtime behavior during migration (moving the call site into `evaluation/`), and flag prominently in `TYPE_AND_CONFIG_AUDIT.md` as requiring a separate roadmap-authorized resolution — not invented anew during this refactor. |
| Statistical procedures (BCa, Wilcoxon, Holm, Spearman) | `application/statistical_analysis.py`, `domain/statistics.py`, `application/stage_protocol.py::apply_holm_correction` | Correct primitive/glue split (domain vs application) already exists — preserve pattern, relocate both sides into `analysis/`. |
| Reporting rules / result freeze | `application/reporting.py` (mixes freeze validation + matplotlib rendering) | Needs splitting into `reporting/freezing.py` (scientific/provenance) vs `reporting/figures.py`+`reporting/tables.py` (presentation) per section 8.8. |
| Artifact provenance chain | `infrastructure/artifacts/{atomic_commit,manifest_codec,model_store}.py` (mechanics, well-centralized) + path/provenance construction scattered ~19x across `application/*.py` | Target: centralize path-naming + provenance capture (git revision, environment identity) into `artifacts/paths.py` + `artifacts/provenance.py`, not left as copy-pasted strings in stage handlers. |
| Deterministic execution / capability restrictions (GPU required, no silent downgrade) | `config/models/runtime_config.py`, `config/runtime_settings.py` | Correctly config-driven; preserve exactly. |
| Suppressed experiments / claim boundaries | Enforced narratively via which experiments exist in `configs/experiments.yaml` + resolver rejection of retired policy IDs (`protocol_config.py`'s `model_validator` rejecting `b5`/`b3lgs`) | No code drift found — this validator must be preserved verbatim in `thresholding/` or `configuration/validation.py`. |

**Drift Audit A conclusion**: no evidence of the architecture migration needing to *change* any scientific formula, threshold, or decision rule — the one exception is the pre-existing `cv_instability_threshold` invented-value debt, which is out-of-scope to fix here and will be preserved byte-for-byte while relocated. All other roadmap contracts map cleanly onto existing (if architecturally scattered) code. The migration's job is purely to relocate/consolidate ownership, not to alter values.

---

## Target package tree

```text
src/datp_core/
├── __init__.py
├── bootstrap.py
├── cli.py
│
├── configuration/
│   ├── __init__.py
│   ├── models.py            # merged: config/models/{_base,dataset_config,experiment_config,protocol_config,runtime_config}.py
│   ├── loading.py            # config/yaml_loader.py (renamed)
│   ├── resolution.py         # config/resolver.py minus validation-cycle; orchestrates dataset/experiment/protocol/runtime resolution
│   ├── dataset_resolution.py # config/dataset_resolution.py (kept separate: 509 lines, genuinely dataset-specific)
│   ├── experiment_resolution.py # config/experiment_resolution.py minus analysis-kind dispatch (moves to experiments/)
│   ├── protocol_resolution.py   # config/protocol_resolution.py minus threshold-policy dispatch (moves to thresholding/) and minus analysis/report bits
│   ├── validation.py         # config/validation.py, cycle broken (see below)
│   ├── fingerprints.py       # config/converter.py + fingerprint orchestration extracted from resolver.py
│   └── project.py            # ResolvedProjectConfiguration assembly (final immutable record), from config/resolver.py
│
├── experiments/
│   ├── __init__.py
│   ├── models.py             # domain/catalogue.py split: population/experiment/sweep records only (training/analysis/eligibility records move out)
│   ├── catalogue.py          # experiment catalogue construction/lookup helpers (new, thin — currently implicit in resolver)
│   ├── sweeps.py             # sweep-value extraction: application/scoring_support.py::calibration_sample_counts + config experiment_resolution sweep bits
│   ├── planning.py           # planning/expansion.py (decomposed from one 340-line fn into per-substage helpers) + planning/validation.py
│   ├── identity.py           # planning/identity.py split: the experiment/job-DAG-identity slice
│   └── execution.py          # application/experiment_execution.py
│
├── datasets/
│   ├── __init__.py
│   ├── models.py             # domain/datasets.py
│   ├── discovery.py          # infrastructure/datasets/source_inventory.py
│   ├── materialization.py    # application/data_stages.py::DatasetMaterializationStageHandler (thinned) + application/ports.py (DatasetMaterializer/SourceInventory Protocols now owned here, breaking the app↔infra cycle)
│   ├── readiness.py          # application/dataset_audit.py + application/stage_protocol.py::evaluate_readiness_gates
│   ├── common.py             # infrastructure/datasets/csv_source.py + infrastructure/datasets/split_manifest.py (genuinely shared across all 3 adapters)
│   ├── nbaiot.py             # infrastructure/datasets/nbaiot.py
│   ├── ciciot2023.py         # infrastructure/datasets/ciciot2023.py
│   └── edge_iiotset.py       # infrastructure/datasets/edge_iiotset.py (split strategy + fitting stay dataset-specific per section 8.3 — normalization *fitting* moves here from infrastructure/tables/parquet_io.py, generic I/O stays as a pipeline-level helper)
│
├── learning/
│   ├── __init__.py
│   ├── models.py              # domain/catalogue.py's training/model/optimizer/batching/checkpoint records
│   ├── autoencoder.py         # infrastructure/learning/pytorch_adapter.py: DynamicDenseAutoencoder + seeding/device selection only
│   ├── federated.py           # infrastructure/learning/pytorch_adapter.py: federated_train_autoencoder, fedprox_objective, _weighted_average_state
│   ├── personalization.py     # infrastructure/learning/pytorch_adapter.py: ditto_train_autoencoder, DittoCheckpoint/DittoTrainingResult
│   ├── checkpoints.py         # domain/checkpoints.py (pure algorithms) + application/learning_stages.py::CohortCheckpointSelectionStageHandler (thinned)
│   ├── training.py            # application/learning_stages.py::ModelTrainingStageHandler (thinned orchestration only)
│   └── scoring.py             # application/learning_stages.py::ScoreGenerationStageHandler + module-level _score_split/_load_checkpoint_model + infrastructure/learning/pytorch_adapter.py's score_materialized_split/score_personalized_materialized_split
│
├── thresholding/
│   ├── __init__.py
│   ├── models.py              # domain/thresholding.py (BenignCalibrationScores, ThresholdRecord, ThresholdSet, 12-member policy union)
│   ├── calibration.py         # application/threshold_stages.py::CalibrationSubsamplingStageHandler + infrastructure/tables/calibration_subsampling.py (thinned; seed derivation moves to shared determinism helper)
│   ├── quantiles.py           # infrastructure/thresholding/estimators.py: shared-mean/pooled/weighted/local-quantile/family-mean estimator methods (B0/B1/B2/B3 family)
│   ├── grouped.py             # infrastructure/thresholding/estimators.py: cluster (B4) estimator method + KMeans call
│   ├── conformal.py           # infrastructure/thresholding/estimators.py: split-conformal (B2-conf) estimator method
│   ├── shrinkage_and_federated.py # infrastructure/thresholding/estimators.py: shrinkage + federated-matched/fixed (B-FedStatsBenign) methods — kept together since both are "combination" policies over already-computed local/shared thresholds
│   └── construction.py        # application/threshold_construction.py + infrastructure/thresholding/base.py (ThresholdEstimator protocol) + application/threshold_stages.py::ThresholdConstructionStageHandler (thinned)
│
├── evaluation/
│   ├── __init__.py
│   ├── models.py               # domain/evaluation.py (MetricStatus, ClientConfusionMatrix, FprDispersion, MetricValue, MetricResultRecord)
│   ├── operating_points.py     # infrastructure/tables/polars_engine.py::compute_operating_point_metrics + application/threshold_stages.py::OperatingPointEvaluationStageHandler (thinned) + the one shared _ineligible_client_metrics (deduplicated from learning_stages.py/threshold_stages.py)
│   ├── predictive_metrics.py   # infrastructure/tables/polars_engine.py::compute_client_auroc + infrastructure/learning/sklearn_adapter.py::compute_roc_auc/AurocStatus/ClientAuroc (AUROC-specific; sklearn confined here)
│   ├── dispersion.py           # domain/evaluation.py::calculate_fpr_dispersion, calculate_pairwise_js_divergence, assert_auroc_invariant (kept in models.py) OR here if models.py stays pure-data — resolved during implementation: dispersion math functions live here, records stay in models.py
│   └── distributions.py        # application/scoring_support.py::client_score_distributions, threshold_tradeoff, calibration_variance_terms, _empirical_cdf, _cdf_position, _metric_delta
│
├── analysis/
│   ├── __init__.py
│   ├── models.py                # domain/catalogue.py's 14 analysis-kind records + AnalysisKind enum (typed result hierarchy per section 12.2)
│   ├── paired.py                # application/analysis_stages.py::_analyze_paired + _analyze_association (paired threshold + metric association)
│   ├── association.py           # application/analysis_stages.py::_analyze_association (split out if paired.py grows too large; decided during implementation based on actual line count)
│   ├── stability.py             # application/analysis_stages.py::_analyze_threshold_stability + _analyze_cluster_stability + infrastructure/learning/sklearn_adapter.py::compute_adjusted_rand_index
│   ├── coverage.py               # application/analysis_stages.py::_analyze_conformal_coverage + application/scoring_support.py::conformal_seed_coverage
│   ├── temporal.py               # application/analysis_stages.py::_analyze_temporal_recovery + _analyze_recovery_fraction + _analyze_absorption + _analyze_anchor_equivalence
│   ├── resources.py              # application/scoring_support.py::threshold_exchange_cost, _field_bytes (communication-cost / resource-cost analysis)
│   └── execution.py              # application/analysis_stages.py::StatisticalAnalysisStageHandler (thinned to pure dispatch, no inline math) + application/statistical_analysis.py::StatisticalAnalysisUseCase + application/stage_protocol.py::apply_holm_correction + domain/statistics.py content
│
├── reporting/
│   ├── __init__.py
│   ├── models.py                # domain/protocol_contracts.py's ReportProfileRecord/ReportDefaults (the ~2 actually-consumed records; rest of protocol_contracts.py's dead records are deleted, not migrated — see MIGRATION_MAP)
│   ├── freezing.py               # application/reporting.py::freeze_result_family, ResultFreezeError + application/reporting_stages.py::ResultFreezeStageHandler (thinned)
│   ├── tables.py                 # application/reporting.py::_render_table, _markdown_table, _latex_table, _table_value
│   ├── figures.py                # application/reporting.py::_render_figure (matplotlib)
│   └── generation.py             # application/reporting.py::render_frozen_report + application/reporting_stages.py::ReportGenerationStageHandler (thinned)
│
├── artifacts/
│   ├── __init__.py
│   ├── models.py                 # domain/artifacts.py
│   ├── identity.py                # planning/identity.py's artifact-id-construction slice (ArtifactKey/ArtifactId string formatting)
│   ├── paths.py                   # NEW — centralizes the ~19x duplicated f"runs/{run_id}/{job_id}" relative-path convention currently scattered across application/*.py stage handlers
│   ├── repository.py               # infrastructure/artifacts/atomic_commit.py (AtomicArtifactRepository)
│   ├── serialization.py            # infrastructure/artifacts/manifest_codec.py + infrastructure/artifacts/model_store.py (SafeTensors — becomes the ONLY sanctioned SafeTensors call site, fixing the bypass in learning_stages.py)
│   └── provenance.py                # NEW — centralizes git_revision (from application/stage_protocol.py) + environment-identity capture (currently threaded as a plain string param)
│
└── pipeline/
    ├── __init__.py
    ├── identifiers.py              # domain/identifiers.py verbatim (all typed ID classes — genuinely shared by every feature, including configuration itself)
    ├── values.py                   # domain/values.py verbatim (value-objects + TypedDomainRegistry + JSON-freezing utilities — confirmed by grep to be consumed across config/resolver.py, config/runtime_settings.py, config/dataset_resolution.py, and domain/{datasets,thresholding,catalogue}.py, i.e. genuinely shared, not configuration-owned)
    ├── fingerprints.py             # domain/fingerprints.py minus its two configuration-specific entry points: Fingerprint, Checksum, CanonicalProjection, FingerprintPayload, canonicalize_value, compute_payload_checksum, compute_file_checksum (generic hash/canonicalization primitives used by artifacts, datasets, configuration alike)
    ├── models.py                   # domain/outcomes.py (StageKind, JobExecutionStatus, StageJobContext, StageJob, StageJobOutcome) + planning/graph.py (PlanningGraph)
    ├── stages.py                   # application/stage_protocol.py::StageHandler Protocol + commit_artifact/artifact_parents (thinned — git/holm/gates/partition logic moved to their owning features per section 8.10)
    ├── handler.py                  # thin per-stage handler base/shared execution helpers only (no git, no stats, no gates — those move to artifacts/provenance.py, analysis/execution.py, datasets/readiness.py, experiments/planning.py respectively)
    └── runner.py                    # NEW — the actual DAG-execution loop currently embedded in application/experiment_execution.py::ExecuteExperimentUseCase, extracted as the pipeline's execution primitive; experiments/execution.py becomes a thin caller of pipeline/runner.py
```

**Deviation #13**: `pipeline/{identifiers,values,fingerprints}.py` split out from a single `models.py`, contrary to the section-6 baseline's implied single file. Justified because these are three independently-cohesive, independently-testable concept families (typed IDs; constrained scalars+registry+JSON-freezing; hash/canonicalization primitives) that happen to all sit at the same foundational dependency layer — cramming them into one file would recreate exactly the "grab-bag module" anti-pattern flagged in `domain/values.py`'s current audit finding (§2 of CURRENT_ARCHITECTURE.md), just renamed. Splitting here is a debloat, not a proliferation of micro-modules, since each resulting file is still substantial (100-230 lines) and single-purpose.

**Deviation #14**: `configuration/fingerprints.py` retains only `compute_scientific_fingerprint`/`compute_execution_fingerprint` (thin, config-resolution-specific wrappers), not the full old `domain/fingerprints.py`. The `Fingerprint`/`Checksum` types and generic hashing primitives move to `pipeline/fingerprints.py` because `artifacts/`, `datasets/discovery.py` (source-inventory fingerprinting), and `configuration/` all need them independently — placing the base types inside `configuration/` would force every other feature package to depend on configuration for a basic value type, inverting the intended dependency direction (features depend on configuration's resolved *values*, not on configuration for foundational *types*).

**Deviation #15**: `config/runtime_settings.py` splits into `configuration/loading.py` (env-driven `RuntimeBootstrapSettings` + `resolve_config_root` — genuinely "loading" bootstrap config) and `configuration/runtime_resolution.py` (NEW, path-authority resolution + all the `*Record` classes + `resolve_runtime_configuration()` — genuinely "resolving one authored document," the same axis `dataset_resolution.py`/`experiment_resolution.py`/`protocol_resolution.py` already use for runtime.yaml's three siblings). Confirmed during implementation that the original file conflated two responsibilities under one name.

**Deviation #16 (important correction, made while reading `domain/catalogue.py`)**: the 14 `*AnalysisRecord` classes (`PairedThresholdAnalysisRecord` etc.) plus `AnalysisKind` move to **`experiments/models.py`**, not `analysis/models.py` as the original target tree sketch assumed. On inspection these are catalogue-level analysis **specifications** (what analysis to run, resolved 1:1 from `AuthoredExperimentConfig.analyses`), referenced directly by `ExperimentRecord.analyses: tuple[AnalysisRecord, ...]` — not analysis **results**. Keeping them with `ExperimentRecord` avoids a manufactured circular dependency (an earlier draft tried a bottom-of-file import from `analysis.models` back into `experiments.models`, which was itself circular since `ClusterStabilityAnalysisRecord.run_requirement` needs `experiments.models.RunRequirement`). `analysis/models.py` (built properly in Phase 7) instead owns the *new* typed result hierarchy required by section 12.2 — a hierarchy that does not exist under any name in the current codebase (today's stage handler returns bare `dict[str, object]` per the CURRENT_ARCHITECTURE.md finding) — plus `StatisticalProfileRecord` (the resolved BCa/bootstrap/Wilcoxon configuration contract, needed by `analysis/execution.py`).

**Deviation #17 (debloat, confirmed dead code)**: `domain/catalogue.py::ResolvedCatalogue` is **deleted, not migrated**. Grep across the entire repo (`src/` and `tests/`) shows zero consumers — its registries (`populations`, `experiments`, `training_profiles`, `checkpoint_profiles`, `seed_cohorts`) duplicate what `ResolvedProjectConfiguration` (→ `configuration/project.py`) already holds directly as top-level fields. This is exactly the "no duplicate record remains" / "no dead module remains" case sections 11/16 require eliminating.

**Deviation #18**: four small record clusters from `domain/catalogue.py` that don't belong to any one obvious package were placed by tracing their actual consumer, not by their old file location: `EligibilityFallbackRecord`/`EligibilityPolicyRecord`/`NormalizationStrategyRecord` → `datasets/models.py` (referenced by `ResolvedDataset.eligibility_policy_id` and `DatasetMaterialization.normalization_strategy`); `QuantileEstimatorRecord` → `thresholding/models.py` (referenced by every threshold policy's `quantile_estimator` field); `MetricBundleRecord` → `evaluation/models.py` (referenced by `PopulationRecord.metric_bundle_id`).

## Deviations from the section-6 baseline (with cohesion-based reasons)

1. **`evaluation/dispersion.py` vs folding into `models.py`** — left as an open decision resolved during implementation, not upfront, because whether `calculate_fpr_dispersion` etc. count as "models" (pure data) or "calculations" depends on their actual complexity once isolated; documented above as a conditional, not a guess.
2. **`analysis/association.py` may merge into `paired.py`** — both operate on paired/associative statistics over the same input shape; kept as a documented maybe rather than forcing a split that duplicates imports if the combined file stays under ~300 lines.
3. **`thresholding/shrinkage_and_federated.py`** combines two roadmap-distinct families (local-global shrinkage and `B-FedStatsBenign`/fixed-coefficient) into one file rather than two, because both are "combination-over-existing-thresholds" policies sharing helper math (weighted pooling), and the section-6 baseline doesn't list a `thresholding/` file for shrinkage separately from `conformal.py`/`grouped.py` — this is a merge justified by shared implementation, not a rename of the old god-class.
4. **`artifacts/paths.py` and `artifacts/provenance.py` are NEW files**, not in any current module — justified because path-naming and provenance capture are currently scattered ~19x/2x respectively across `application/*.py`, a duplication CURRENT_ARCHITECTURE.md flags explicitly (§4.12/9.9); centralizing them is a debloat, not scope creep.
5. **`pipeline/runner.py` is NEW**, extracting the DAG-walk loop currently inlined in `application/experiment_execution.py`, because `experiments/execution.py` (the feature-level orchestrator) and `pipeline/runner.py` (the generic execute-in-topological-order primitive) are different responsibilities per section 8.10/8.2 — experiments own *what* to run, pipeline owns *how* a DAG of stage jobs gets walked and failures propagated.
6. **`experiments/planning.py`** merges `planning/expansion.py` and `planning/validation.py` into one file rather than keeping them separate, since both operate on the same `PlanningGraph` construction step and section 6's baseline lists both under one `planning.py` file for `experiments/`.
7. **`config/dataset_resolution.py`, `experiment_resolution.py`, `protocol_resolution.py`** are kept as separate files under `configuration/` (matching current names) rather than merged into `resolution.py`, because each is independently substantial (509/288/375 lines) and each maps 1:1 to one authored YAML document — splitting by source document is a legitimate axis distinct from the target-feature split that happens to their *dispatch* sub-logic (which does move out, per the drift-audit notes above).
8. **No dedicated `bootstrap.py` split** — `composition/root.py` (201 lines) becomes `bootstrap.py` verbatim in responsibility (sole composition authority per section 8.11); not split further since 201 lines for wiring ~10 feature packages is proportionate, not oversized.
9. **CORRECTED during implementation** (was wrong in the original draft): `domain/protocol_contracts.py`'s records are **NOT dead code and are NOT deleted**. Verified by grep: every one of its ~26 classes is held as a field on `ResolvedProjectConfiguration` (`config/resolver.py`), which is unstructured whole for the scientific fingerprint — per the file's own docstring, these blocks are "never dropped... scientific-identity relevant blocks participate in the scientific fingerprint." Only `ReportProfileRecord` and `CommunicationEstimationContractRecord` have a consumer *outside* the config layer (`application/reporting.py`, `application/scoring_support.py` respectively) — the other ~24 are resolved-but-not-yet-execution-consumed, which is a scientific-fingerprint-integrity concern, not a dead-code one. All records migrate, distributed by concept to their owning package: `evaluation/models.py` gets `MetricFormulaRecord`/`CrossClientAggregationRecord`/`ThresholdEstimationMetricsRecord`/`JsDivergenceRecord`/`HeterogeneityDiagnosticsRecord`/`ClusterDiagnosticsRecord`/`PrecisionPolicyRecord`/`MetricDefinitionsRecord`/`EvaluationResultContractRecord`; `artifacts/models.py` gets `ArtifactFingerprintsRecord`/`ArtifactIdentityRecord`; `analysis/models.py` gets `FieldEncodingRecord`/`ThresholdExchangeEntryRecord`/`ThresholdExchangeRecord`/`ModelExchangeRecord`/`CheckpointStorageRecord`/`CommunicationEstimationContractRecord`/`BenignDecisionRateRecord`/`OperationalInputsRecord`/`NestedReplicatePolicyRecord`/`ResultTypeRecord`; `thresholding/models.py` gets `ThresholdPolicyDefaultsRecord`; `reporting/models.py` (NEW) gets `ReportColumnRecord`/`ReportProfileRecord`/`ReportDefaultsRecord`; `configuration/project.py` gets `SeedNamespaceRecord`/`ProtocolDeterminismRecord` (protocols.yaml's own seed/determinism contract, a configuration-authority concern with no other feature owner, distinct from runtime.yaml's determinism already in `configuration/runtime_resolution.py`).
   (`domain/catalogue.py::ResolvedCatalogue` from deviation #17 remains the correctly-identified dead-code deletion — that one truly has zero consumers anywhere, including in `resolver.py`.)
10. **`infrastructure/federation/flower_adapter.py` and the `flwr` dependency are DELETED**, not migrated — confirmed dead code (§9.6), no production caller, duplicates `learning/federated.py`'s hand-rolled FedAvg loop.
11. **`infrastructure/learning/sklearn_adapter.py::scale_features()` is DELETED** — confirmed zero consumers.
12. **`infrastructure/querying/audit_service.py` (`DuckDbAuditService`)** — disposition depends on a cross-check with `interfaces/cli/app.py` (not yet audited in this pass for whether a CLI command calls it). Tentatively migrates to `artifacts/repository.py` (it queries committed Parquet artifacts) pending that check during Phase 8 implementation; if confirmed truly dead, it will be deleted instead and this deviation note updated.

## Package ownership / dependency contracts (section 7 requirement, condensed — full detail during implementation)

For every package: **allowed deps** = configuration models + domain-level shared identifiers/value-objects (`pipeline/models.py`, `artifacts/models.py`) + stdlib/its own concrete library. **Prohibited deps** = `cli.py`, `bootstrap.py`, any other feature package's internals (only its `models.py`/public functions), pipeline stage-handler internals from another feature.

| Package | Owns | Forbidden from importing |
|---|---|---|
| `configuration/` | authored models, loading, resolution, validation, fingerprints | `pipeline`, `experiments`, `datasets`, `learning`, `thresholding`, `evaluation`, `analysis`, `reporting`, `artifacts` (configuration is upstream of all features) |
| `experiments/` | experiment/sweep/plan/identity/execution-graph | concrete infra adapters (torch/polars/duckdb/pyarrow); `bootstrap`, `cli` |
| `datasets/` | dataset contracts, discovery, materialization, readiness | `learning`, `thresholding`, `evaluation`, `analysis`, `reporting` internals |
| `learning/` | model def, federated/personalization training, checkpoints, scoring | `thresholding`, `evaluation`, `analysis`, `reporting`, `artifacts` internals (only via `pipeline`/`artifacts.models`) |
| `thresholding/` | policy models, calibration, quantile/grouped/conformal/shrinkage estimators | `learning`, `evaluation`, `analysis`, `reporting` internals |
| `evaluation/` | confusion/operating-point/AUROC/dispersion/distributions | `analysis`, `reporting` internals |
| `analysis/` | all 14 analysis families, typed results, statistical procedures, dispatch | `reporting`, `cli`, `bootstrap`; must not import stage-handler modules from `pipeline` beyond the `StageHandler` Protocol |
| `reporting/` | freeze, tables, figures, generation | stage handlers from any other feature; consumes only typed `analysis/models.py` results |
| `artifacts/` | identity, paths, repository, serialization, provenance | scientific/feature calculation modules (only `pipeline/models.py`) |
| `pipeline/` | stage kinds/jobs/outcomes, handler protocol, runner | concrete adapters (torch/polars/duckdb/pyarrow/safetensors); no scientific formulas |
| `bootstrap.py` | wires everything | nothing forbidden — sole exception |
| `cli.py` | argument parsing, presentation | concrete infra directly (goes through `bootstrap`) |

## Circular-dependency resolution (mandatory before migration starts)

**`config/resolver.py ⇄ config/validation.py`** → becomes: `configuration/resolution.py::resolve_project_configuration()` returns the assembled (not-yet-validated) candidate; a new top-level `configuration/project.py::build_project_configuration()` calls `resolution.resolve_project_configuration()` then `validation.validate_all_configurations()` and only then freezes/returns the final `ResolvedProjectConfiguration`. Neither `resolution.py` nor `validation.py` imports the other; `project.py` imports both. This matches section 8.1's mandated one-directional flow exactly (`load → resolve → assemble candidate → validate → project → fingerprint → construct final`).

**`application.ports` (app↔infra cycle)** → `DatasetMaterializer`/`SourceInventory` Protocols move into `datasets/materialization.py` (owned by the feature that both the "orchestration" and "adapter" sides now both live inside); no cross-package cycle possible since both sides are the same package.

## Test tree target (mirrors production 1:1, per section 15)

```text
tests/
├── configuration/
├── experiments/
├── datasets/
├── learning/
├── thresholding/
├── evaluation/
├── analysis/
├── reporting/
├── artifacts/
├── pipeline/
└── integration/        # cross-feature integration + conformance/dependency-boundary tests (replaces tests/conformance/)
```

`tests/scientific/` content (drift/catalogue/thresholding golden-value tests) distributes into the matching feature test directories (`tests/configuration/` for drift/fingerprint tests, `tests/thresholding/` for estimator golden tests) since "scientific" was a cross-cutting label, not a feature — each test's *subject* determines its new home, not its old label.

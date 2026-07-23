# MIGRATION_MAP.md

Every current production file (88) and test file (73) with exactly one final disposition. Status column tracks progress; starts "planned" for all, updated to "done" as migration proceeds (see STATE.md for the authoritative current-phase pointer).

Legend — Action: RETAIN (same responsibility, new location) / RENAME / MOVE / MERGE / SPLIT / DELETE.

## `application/` (14 files)

| Current module | Final module | Action | Reason | Tests affected | Status |
|---|---|---|---|---|---|
| `application/__init__.py` | `experiments/__init__.py` etc. (dissolved) | DELETE | empty layer marker, package itself removed | none | planned |
| `application/analysis_stages.py` | `analysis/execution.py` (dispatch only) + `analysis/{paired,association,stability,coverage,temporal}.py` (math) | SPLIT | 1298-line stage handler mixing orchestration + real statistics; decompose per analysis family | 4 files (see below) | planned |
| `application/configuration.py` | `configuration/project.py` (use-case functions folded into public API) | MERGE | small use-case wrappers belong with the resolution/validation orchestration they call | `test_configuration_drift_explanations.py` | planned |
| `application/data_stages.py` | `datasets/materialization.py` | MOVE (thinned) | thin stage orchestration; dataset-specific logic already in adapters | `test_dataset_materialization_reuse.py`, `test_preflight_stage_commits_artifact.py` | planned |
| `application/dataset_audit.py` | `datasets/readiness.py` | MOVE | audit + readiness are dataset ownership per section 8.3 | `test_dataset_readiness.py` | planned |
| `application/experiment_execution.py` | `experiments/execution.py` (thin) + `pipeline/runner.py` (DAG walk extracted) | SPLIT | separates "what to run" (experiments) from "how a DAG executes" (pipeline) per section 8.10 | `test_execution_suppresses_unavailable_dependencies.py` | planned |
| `application/learning_stages.py` | `learning/training.py` + `learning/checkpoints.py` + `learning/scoring.py` | SPLIT | 3 unrelated stage handlers bundled; each becomes its own thin orchestration file | `test_model_training_stage_handler.py`, `test_cohort_checkpoint_selection_stage_handler.py`, `test_score_generation_stage_handler.py` | planned |
| `application/ports.py` | `datasets/materialization.py` (Protocols folded in) | MERGE | resolves the app↔infra cycle; port + adapter now same package | none currently — add direct tests | planned |
| `application/reporting.py` | `reporting/freezing.py` + `reporting/tables.py` + `reporting/figures.py` + `reporting/generation.py` | SPLIT | mixes scientific freeze-validation with presentation rendering — 4 distinct responsibilities | `test_result_freeze_reporting.py` | planned |
| `application/reporting_stages.py` | `reporting/freezing.py`::stage handler + `reporting/generation.py`::stage handler (thinned) | MERGE into split targets | thin wrappers, fold into the modules they wrap | none currently — add direct tests | planned |
| `application/scoring_support.py` | `experiments/sweeps.py` (calibration_sample_counts, score_context) + `analysis/coverage.py` (conformal_seed_coverage) + `evaluation/distributions.py` (client_score_distributions, threshold_tradeoff, calibration_variance_terms) + `analysis/resources.py` (threshold_exchange_cost) | SPLIT | explicit dumping ground (6 unrelated concerns) — each moves to its true owning feature | `test_calibration_subsampling_stage_handler.py`, `test_recovery_fraction_analysis.py`, `test_threshold_and_evaluation_stage_handlers.py`, `test_conformal_and_distribution_analysis.py`, `tests/scientific/thresholding/test_configured_threshold_estimators.py` | planned |
| `application/stage_protocol.py` | `pipeline/stages.py` (Protocol + commit_artifact/artifact_parents) + `artifacts/provenance.py` (git_revision) + `analysis/execution.py` (apply_holm_correction) + `datasets/readiness.py` (evaluate_readiness_gates) + `experiments/planning.py` (resolve_partition_contract) | SPLIT | explicit dumping ground (5 unrelated concerns) | exercised transitively by many stage-handler tests; add direct tests per destination | planned |
| `application/statistical_analysis.py` | `analysis/execution.py` | MOVE | BCa/Wilcoxon/Spearman/regression belongs with analysis dispatch | `test_bca_degeneracy.py`, `test_statistical_analysis_uses_composed_port.py` | planned |
| `application/threshold_construction.py` | `thresholding/construction.py` | MOVE | dispatch to injected estimator registry — thresholding ownership | `tests/scientific/thresholding/test_configured_threshold_estimators.py` | planned |
| `application/threshold_stages.py` | `thresholding/calibration.py` + `thresholding/construction.py` + `evaluation/operating_points.py` | SPLIT | 3 unrelated stage handlers; `_ineligible_client_metrics` deduplicated into `evaluation/operating_points.py` | `test_threshold_and_evaluation_stage_handlers.py`, `test_calibration_subsampling_stage_handler.py`, `tests/unit/infrastructure/tables/test_polars_operating_point_metrics.py` | planned |

## `domain/` (15 files)

| Current module | Final module | Action | Reason | Tests affected | Status |
|---|---|---|---|---|---|
| `domain/__init__.py` | dissolved | DELETE | package removed | none | planned |
| `domain/artifacts.py` | `artifacts/models.py` | MOVE | artifact identity/lifecycle owned by artifacts feature | 14 files reference it — update imports only | planned |
| `domain/catalogue.py` | `experiments/models.py` (population/experiment/sweep/evidence-role/**14 analysis-kind specs + AnalysisKind**, corrected from original plan — see TARGET_ARCHITECTURE deviation #16) + `learning/models.py` (training/model/optimizer/batching/checkpoint) + `datasets/models.py` (eligibility/normalization) + `thresholding/models.py` (quantile estimator) + `evaluation/models.py` (metric bundle); `ResolvedCatalogue` **DELETED** (confirmed dead, deviation #17) | SPLIT + DELETE | 690-line module with 5+ independent concept clusters — split by actual consumer, not by old co-location | `test_resolved_configuration_is_immutable.py` + many application-layer tests importing specific records | done |
| `domain/checkpoints.py` | `learning/checkpoints.py` | MOVE | pure checkpoint-selection algorithms | `test_anchor_checkpoint_selection.py` | planned |
| `domain/datasets.py` | `datasets/models.py` | MOVE (kept together — see TARGET note: 3 sub-domains but all genuinely "dataset" records, not split further) | | `test_dataset_readiness.py`, `test_source_inventory.py` | planned |
| `domain/drift.py` | `configuration/validation.py` (or `project.py`) | MOVE | drift diffing is a configuration-authority concern | none direct — add test | planned |
| `domain/evaluation.py` | `evaluation/models.py` (+ dispersion math, see TARGET note) | MOVE | correctly-placed stats stay in evaluation feature | `test_evaluation_metrics.py` | planned |
| `domain/fingerprints.py` | `configuration/fingerprints.py` | MOVE | canonical fingerprinting is configuration-authority responsibility | 9 references — update imports | planned |
| `domain/identifiers.py` | `pipeline/models.py` (shared identifiers, most widely used — lives at the shared base level pipeline sits on) | MOVE | 42 test references; genuinely shared across every feature — placed in `pipeline/models.py` since section 9's dependency direction puts pipeline below all features | 42 references — update imports | planned |
| `domain/outcomes.py` | `pipeline/models.py` | MERGE | StageKind/StageJob/StageJobOutcome are pipeline's own models | 15 references — update imports | planned |
| `domain/protocol_contracts.py` | `reporting/models.py` (ReportProfileRecord only) + `analysis/models.py` (CommunicationEstimationContractRecord only); **remaining ~18 classes DELETED** | SPLIT + DELETE | admitted dead dumping ground; only 2 classes have any consumer | none — confirmed zero test references | planned |
| `domain/run_identity.py` | `experiments/identity.py` | MOVE | run-id derivation is part of experiment/job identity | none direct — add test | planned |
| `domain/splits.py` | `datasets/models.py` | MERGE | split manifest is a dataset record | `test_split_manifest.py` | planned |
| `domain/statistics.py` | `analysis/execution.py` (or a small `analysis/models.py` slice for the pure records) | MOVE | statistical primitives belong with analysis | `test_statistics.py` | planned |
| `domain/thresholding.py` | `thresholding/models.py` | MOVE | policy records belong to thresholding feature | `test_threshold_policy_records.py` + heavy application-layer use | planned |
| `domain/values.py` | SPLIT: value-objects → `pipeline/models.py`; `TypedDomainRegistry` → `pipeline/models.py` (or delete if only used for the one estimator registry — confirm during implementation); JSON-freezing utils → `configuration/fingerprints.py` (only consumer is fingerprinting) | SPLIT | grab-bag of 3 unrelated families | `test_scientific_value_objects.py` + 7 others | planned |

## `planning/` (4 files)

| Current module | Final module | Action | Reason | Tests affected | Status |
|---|---|---|---|---|---|
| `planning/__init__.py` | dissolved | DELETE | package removed | none | planned |
| `planning/expansion.py` | `experiments/planning.py` | MOVE (decomposed) | single 340-line function broken into per-substage helpers during move | `test_complete_catalogue_plans_without_score_leakage.py` | planned |
| `planning/graph.py` | `pipeline/models.py` | MOVE | `PlanningGraph` is a generic DAG primitive, pipeline-level | `test_graph_transformations_preserve_context.py` (transitive) | planned |
| `planning/validation.py` | `experiments/planning.py` | MERGE | operates on the same `PlanningGraph` construction step as expansion | transitive via `test_identity_builder_determinism.py` | planned |
| `planning/identity.py` | `experiments/identity.py` (job/plan identity) + per-feature slices where a feature owns its own ID formatting (`learning/identity` helpers folded into `learning/checkpoints.py` etc. as needed) — primary mass stays in `experiments/identity.py` since it's the sole consumer-facing entry point | MOVE (kept together initially; split only if implementation reveals a clean per-feature seam) | 561-line god-class; natural fault line per feature, but consolidate-first to avoid breaking the single canonical identity authority mid-migration | `test_identity_builder_determinism.py` | planned |

## `interfaces/` (4 files)

| Current module | Final module | Action | Reason | Tests affected | Status |
|---|---|---|---|---|---|
| `interfaces/__init__.py`, `interfaces/cli/__init__.py` | dissolved | DELETE | package removed | none | planned |
| `interfaces/cli/app.py` | `cli.py` | MOVE | CLI parsing owned by top-level `cli.py` per section 8.11 | `test_cli_commands.py` | planned |
| `interfaces/cli/formatters.py` | `cli.py` (merged — no reuse case beyond CLI presentation) | MERGE | section 8.11: "do not keep a separate package for one small CLI formatter unless meaningful reuse" — none found | transitive via `test_cli_commands.py` | planned |

## `composition/` (2 files)

| Current module | Final module | Action | Reason | Tests affected | Status |
|---|---|---|---|---|---|
| `composition/__init__.py` | dissolved | DELETE | package removed | none | planned |
| `composition/root.py` | `bootstrap.py` | RENAME | sole composition authority per section 8.11 | none dedicated — add `tests/integration/test_bootstrap_wiring.py` | planned |

## `config/` (10 files + `models/` 5 files)

| Current module | Final module | Action | Reason | Tests affected | Status |
|---|---|---|---|---|---|
| `config/__init__.py`, `config/models/__init__.py` | dissolved | DELETE | package removed | none | planned |
| `config/converter.py` | `configuration/fingerprints.py` | MERGE | cattrs converter singleton feeds fingerprinting | `tests/scientific/drift/*` (3 files) | planned |
| `config/dataset_resolution.py` | `configuration/dataset_resolution.py` | RETAIN (rename package prefix only) | independently substantial (509 lines), 1:1 with dataset YAML doc | via `test_configuration_authority_boundary.py` + dataset/drift tests | planned |
| `config/experiment_resolution.py` | `configuration/experiment_resolution.py` (records/sweep resolution stays) + `analysis/models.py`/`experiments/models.py` (the 13-branch `_resolve_analysis` dispatch relocates to feature-owned resolution — see note) | SPLIT | analysis-kind dispatch is analysis-feature dispatch table embedded in config; the config-side YAML→record transform stays in configuration, kind-specific record construction moves with its owning feature | via `test_configuration_authority_boundary.py`, `test_experiment_catalogue_field_disposition.py` | planned |
| `config/protocol_resolution.py` | `configuration/protocol_resolution.py` (metric-def/artifact-identity/comms/report resolution stays) + `thresholding/construction.py` (12-family `_resolve_threshold_policy` dispatch relocates) | SPLIT | threshold-policy dispatch is thresholding-feature dispatch table embedded in config | via `test_configuration_authority_boundary.py`, model tests | planned |
| `config/resolver.py` | `configuration/resolution.py` (resolution logic, cycle broken) + `configuration/project.py` (`ResolvedProjectConfiguration` assembly + validation orchestration) | SPLIT | breaks the resolver⇄validation cycle per section 8.1's one-directional flow; dead `communication_estimation` field dropped (see TYPE_AND_CONFIG_AUDIT) | 15+ test files — see full list in CURRENT_ARCHITECTURE §7 | planned |
| `config/runtime_settings.py` | `configuration/loading.py` (bootstrap settings + config-root resolution) + `configuration/runtime_resolution.py` (NEW — path-authority + all Record classes + resolve_runtime_configuration, corrected split per deviation #15) | SPLIT | bootstrap-settings loading vs. one-document resolution are different concerns, same axis as the dataset/experiment/protocol resolution siblings | `test_resolver_golden_identity.py`, conformance tests | done |
| `config/validation.py` | `configuration/validation.py` | MOVE (cycle broken — becomes pure function taking resolved candidate, called only from `configuration/project.py`) | | exercised transitively everywhere `resolve_project_configuration` is called | planned |
| `config/yaml_loader.py` | `configuration/loading.py` | MERGE | strict YAML→Pydantic loading is the loading responsibility | `test_hidden_defaults_and_duplicates.py`, model tests | planned |
| `config/models/_base.py` | `configuration/models.py` | MERGE | shared Pydantic bases | `test_strict_base.py` | planned |
| `config/models/dataset_config.py` | `configuration/models.py` | MERGE | authored dataset schema | `test_strict_base.py`, `test_hidden_defaults_and_duplicates.py` | planned |
| `config/models/experiment_config.py` | `configuration/models.py` | MERGE | authored experiment schema | `test_hidden_defaults_and_duplicates.py`, `test_strict_base.py`, `test_experiment_catalogue_field_disposition.py` | planned |
| `config/models/protocol_config.py` | `configuration/models.py` | MERGE | authored protocol schema (815 lines — `configuration/models.py` will be large; acceptable since it's one coherent "authored schema" responsibility per section 6, not a mixed one) | `test_strict_base.py`, `test_protocol_contract_blocks.py`, `test_statistical_profile_schema.py`, `test_scientific_guard_validation.py`, `test_hidden_defaults_and_duplicates.py` | planned |
| `config/models/runtime_config.py` | `configuration/models.py` | MERGE | authored runtime schema | `test_strict_base.py`, `test_hidden_defaults_and_duplicates.py` | planned |

## `infrastructure/` (all subpackages, 41 files incl. composition/config already listed above — remainder below)

| Current module | Final module | Action | Reason | Tests affected | Status |
|---|---|---|---|---|---|
| `infrastructure/__init__.py` | dissolved | DELETE | package removed | none | planned |
| `infrastructure/artifacts/__init__.py` | dissolved | DELETE | | none | planned |
| `infrastructure/artifacts/atomic_commit.py` | `artifacts/repository.py` | MOVE | | `test_atomic_transaction_engine.py`, `test_atomic_artifact_repository.py` | planned |
| `infrastructure/artifacts/manifest_codec.py` | `artifacts/serialization.py` | MOVE | | `test_manifest_codec_strictness.py` | planned |
| `infrastructure/artifacts/model_store.py` | `artifacts/serialization.py` | MERGE | becomes the ONLY sanctioned SafeTensors call site (fixes bypass in learning_stages.py) | `test_safetensors_atomic_commit.py` | planned |
| `infrastructure/datasets/__init__.py` | dissolved | DELETE | | none | planned |
| `infrastructure/datasets/adapter_registry.py` | `datasets/materialization.py` | MERGE | registry is materialization ownership | `test_adapter_registry.py` | planned |
| `infrastructure/datasets/csv_source.py` | `datasets/common.py` | MOVE | genuinely shared across all 3 adapters | `test_numeric_csv_source_preserves_rejections.py`, `test_labeled_numeric_csv_source.py` | planned |
| `infrastructure/datasets/source_inventory.py` | `datasets/discovery.py` | MOVE | | `test_source_inventory.py` | planned |
| `infrastructure/datasets/split_manifest.py` | `datasets/common.py` | MERGE | shared split-evidence codec | `test_parquet_split_manifest.py` | planned |
| `infrastructure/datasets/ciciot2023.py` | `datasets/ciciot2023.py` | MOVE | | `ciciot2023/test_merged_identity_and_label.py`, `test_global_deduplication_and_split.py`, integration test | planned |
| `infrastructure/datasets/edge_iiotset.py` | `datasets/edge_iiotset.py` | MOVE (normalization-fitting logic that currently lives in `infrastructure/tables/parquet_io.py` consolidates here where it's dataset-specific) | | `test_edge_iiotset_source.py` | planned |
| `infrastructure/datasets/nbaiot.py` | `datasets/nbaiot.py` | MOVE (partition-seed derivation switches to the new shared determinism helper — see below) | | `nbaiot/test_parquet_encoding.py`, `test_path_identity_and_labels.py`, integration tests | planned |
| `infrastructure/federation/__init__.py`, `infrastructure/federation/flower_adapter.py` | — | DELETE | confirmed dead code; `flwr` dependency removed from `pyproject.toml` too | `test_strategy_uses_resolved_participation.py` DELETED (tests only the dead module) | planned |
| `infrastructure/learning/__init__.py` | dissolved | DELETE | | none | planned |
| `infrastructure/learning/pytorch_adapter.py` | `learning/autoencoder.py` (model+seeding+device) + `learning/federated.py` (FedAvg/FedProx) + `learning/personalization.py` (Ditto) + `learning/scoring.py` (score_materialized_split/score_personalized_materialized_split) | SPLIT | 649-line file mixing 5 concerns — the clearest "training+checkpoint+scoring bundled" instance in the audit | `test_fedprox_objective.py`, `test_training_data_loader.py` | planned |
| `infrastructure/learning/sklearn_adapter.py` | `evaluation/predictive_metrics.py` (AurocStatus/ClientAuroc/compute_roc_auc) + `analysis/stability.py` (compute_adjusted_rand_index); `scale_features()` DELETED (dead) | SPLIT + partial DELETE | AUROC belongs to evaluation, ARI belongs to cluster-stability analysis | none direct — exercised via `test_polars_operating_point_metrics.py`, `test_association_and_cluster_stability_analysis.py` | planned |
| `infrastructure/querying/__init__.py` | dissolved | DELETE | | none | planned |
| `infrastructure/querying/audit_service.py` | `artifacts/repository.py` (tentative — pending CLI cross-check, see TARGET_ARCHITECTURE deviation #12) | MOVE (tentative) | queries committed artifacts; disposition confirmed during Phase 8 | none currently — add test regardless of final home | planned |
| `infrastructure/runtime/__init__.py` | dissolved | DELETE | | none | planned |
| `infrastructure/runtime/logging.py` | `bootstrap.py` (or a tiny `pipeline/` logging helper if reused beyond bootstrap — decide during implementation; default: bootstrap owns process-wide logging config) | MOVE | single-purpose, process-level concern | `test_structured_logging_rejects_unknown_values.py` | planned |
| `infrastructure/tables/__init__.py` | dissolved | DELETE | | none | planned |
| `infrastructure/tables/calibration_subsampling.py` | `thresholding/calibration.py` | MOVE (seed derivation switches to shared determinism helper) | | `test_calibration_subsampling.py` | planned |
| `infrastructure/tables/parquet_io.py` | generic I/O → `datasets/common.py`; `normalize_materialized_parquet` + helpers → `datasets/edge_iiotset.py`/`datasets/nbaiot.py` or a shared `datasets/materialization.py` fitting helper if used by >1 adapter (confirm during implementation) | SPLIT | mild dumping ground: generic I/O vs. dataset-normalization-fitting are different concerns | `test_parquet_normalization.py` | planned |
| `infrastructure/tables/polars_engine.py` | `evaluation/operating_points.py` (compute_operating_point_metrics) + `evaluation/predictive_metrics.py` (compute_client_auroc) | SPLIT | operating-point metrics vs AUROC-specific delegation | `test_polars_operating_point_metrics.py` | planned |
| `infrastructure/tables/schemas.py` | `pipeline/frames.py` (NEW, confirmed during implementation — separate from `pipeline/models.py` since these are Pandera DataFrame contracts, a distinct concern from job/stage-outcome models; used by learning/scoring.py, thresholding/, and evaluation/ alike) | MOVE | currently zero direct tests despite being safety-critical — **add direct unit tests as part of this migration**, not just relocate | none currently — new tests required | done |
| `infrastructure/thresholding/__init__.py` | dissolved | DELETE | | none | planned |
| `infrastructure/thresholding/base.py` | `thresholding/construction.py` | MERGE | `ThresholdEstimator` protocol is the construction contract | referenced by `tests/scientific/thresholding/test_configured_threshold_estimators.py` | planned |
| `infrastructure/thresholding/estimators.py` | `thresholding/quantiles.py` (B0/B1/B2/B3 methods) + `thresholding/grouped.py` (B4/cluster) + `thresholding/conformal.py` (B2-conf) + `thresholding/shrinkage_and_federated.py` (shrinkage + B-FedStatsBenign) | SPLIT | one class implementing all 12 policy families behind an isinstance chain — split per family group; **add unit-level tests per file** (currently only `tests/scientific/` covers this, no fast per-policy isolation) | `test_configured_threshold_estimators.py` (redistributed/supplemented) | planned |

## Tests requiring rewrite (not just move) — conformance suite

| Current test | Disposition | Reason |
|---|---|---|
| `tests/conformance/test_project_structure.py` | REWRITE → `tests/integration/test_package_structure.py` | `_EXPECTED_PACKAGES` hard-codes the 7 old layer packages; must assert the new 10-feature-package + bootstrap/cli tree instead |
| `tests/conformance/test_application_port_dependency.py` | REWRITE → `tests/integration/test_dependency_boundaries.py` | forbids `application/` importing specific old infra modules; must become import-linter-style boundary tests for the new package contracts (section 9's table) |
| `tests/conformance/test_configuration_authority_boundary.py` | REWRITE → `tests/configuration/test_authority_boundary.py` | update to new `configuration/` module paths, same intent (config remains authoritative) |
| `tests/conformance/test_experiment_catalogue_field_disposition.py` | REWRITE → `tests/experiments/test_catalogue_field_disposition.py` | update import paths |
| `tests/conformance/test_executable_invariants.py` | REWRITE → `tests/integration/test_executable_invariants.py` | update import paths, same intent |
| `tests/conformance/test_no_hidden_defaults.py` | REWRITE → `tests/configuration/test_no_hidden_defaults.py` | update import paths, same intent |
| `tests/conftest.py` | RETAIN at `tests/conftest.py` | shared fixtures, update imports inside as needed |

## Tests: straightforward moves (import-path update + directory move only, same intent)

All remaining 66 test files move 1:1 alongside their production module per the tables above (e.g. `tests/unit/domain/test_threshold_policy_records.py` → `tests/thresholding/test_threshold_policy_records.py`; `tests/unit/application/test_model_training_stage_handler.py` → `tests/learning/test_training_stage_handler.py`; `tests/unit/infrastructure/thresholding/...` doesn't exist yet — **new unit tests to add**, see below). Full 1:1 list intentionally omitted here (redundant with the production tables above, which already list "Tests affected" per module) — each test's new path is `tests/<feature>/test_<name>.py` where `<feature>` matches the destination package of the code it tests, dropping the `unit/`, `infrastructure/`, `application/`, `domain/`, `planning/`, `scientific/`, `conformance/` prefixes.

`tests/unit/application/_statistical_analysis_fixtures.py`, `tests/unit/application/_synthetic_training_fixtures.py` → move to `tests/analysis/_fixtures.py` / `tests/learning/_fixtures.py` respectively; convert from dict-based fixture factories to typed builders per section 15.2 during the test-migration phase (not part of a mechanical move).

## New tests required (gaps identified by the audit, must exist before final validation)

- `tests/artifacts/test_repository_wiring.py` or equivalent — direct test for `composition/root.py`→`bootstrap.py` wiring (currently zero direct coverage).
- Direct unit tests for `pipeline/stages.py` (currently `application/stage_protocol.py` has none by name).
- Direct unit tests for `datasets/materialization.py`'s port Protocols (currently `application/ports.py` has none).
- Direct unit tests for `reporting/generation.py`'s stage handlers (currently `application/reporting_stages.py` has none).
- Per-policy-family unit tests for `thresholding/{quantiles,grouped,conformal,shrinkage_and_federated}.py` (currently only `tests/scientific/thresholding/test_configured_threshold_estimators.py` covers the whole 12-family estimator, no fast isolation).
- Direct unit tests for the frame-contract module inheriting `infrastructure/tables/schemas.py` (currently zero tests despite 18 call sites).
- Direct unit test for `configuration/validation.py` constructing a deliberately-invalid config and asserting specific `ValidationReport` errors (currently only exercised transitively).
- Direct unit test for `configuration/loading.py`'s path-authority symlink-loop/broken-symlink/escape branches (currently untested).
- A single shared-determinism-helper test covering the consolidated seed-derivation function (replacing 3 independent implicit coverages).

# CURRENT_ARCHITECTURE.md

Status: Both audit passes complete (Part 1: `application/`, `domain/`, `planning/`, `interfaces/`; Part 2: `composition/`, `config/`, `infrastructure/`). Reconciled cross-cutting summary at the very end.

---

## 1. `src/datp_core/application/` (14 files, ~5,340 lines)

| File | Lines | Responsibility |
|---|---|---|
| `__init__.py` | 0 | empty marker |
| `analysis_stages.py` | 1298 | `StatisticalAnalysisStageHandler` — dispatches + **computes** all 14 analysis kinds inline (real stats embedded in a stage handler) |
| `configuration.py` | 101 | config validation/drift-explanation/fingerprint use cases |
| `data_stages.py` | 322 | `PreflightStageHandler`, `DatasetMaterializationStageHandler` |
| `dataset_audit.py` | 431 | source-tree audit + post-materialization readiness |
| `experiment_execution.py` | 85 | `ExecuteExperimentUseCase` — DAG expand/validate/topo-sort/drive |
| `learning_stages.py` | 953 | 3 bundled stage handlers: training (FedAvg/FedProx/Ditto), 3-variant checkpoint selection, scoring |
| `ports.py` | 95 | Protocol ports (`DatasetMaterializer`, `SourceInventory`, etc.) — **no test references it by name**; root of the app↔infra cycle below |
| `reporting.py` | 344 | mixes result-freeze validation (scientific) with matplotlib rendering (presentation) — two responsibilities |
| `reporting_stages.py` | 127 | thin stage wrappers — **untested by name** |
| `scoring_support.py` | 316 | **explicit dumping ground** (per its own docstring): context derivation, sweep extraction, generic stat helpers, conformal coverage, score-distribution/CDF, comms-cost estimation — 6 unrelated concerns |
| `stage_protocol.py` | 160 | **explicit dumping ground**: `StageHandler` Protocol + artifact-commit plumbing + git/VCS shell-out (`git_revision`) + Holm correction + dataset-eligibility gates + partition-seed derivation — 5 unrelated concerns, **untested by name** |
| `statistical_analysis.py` | 169 | BCa/percentile bootstrap, Wilcoxon, Spearman, regression w/ leverage diagnostics |
| `threshold_construction.py` | 65 | `ConstructThresholdsUseCase` — dispatch to injected estimator registry |
| `threshold_stages.py` | 397 | 3 stage handlers: calibration subsampling, threshold construction, operating-point evaluation |

**Confirmed duplicate**: `_ineligible_client_metrics` is byte-for-byte duplicated in `learning_stages.py:920-941` and `threshold_stages.py:374-397` (latter has a redundant local `import polars as pl` at line 375 despite module-top import at line 8).

**Confirmed circular dependency (package-level)**: `application/data_stages.py` imports `infrastructure.datasets.{adapter_registry,source_inventory,split_manifest}`, while `infrastructure/datasets/{adapter_registry,nbaiot,ciciot2023,edge_iiotset}.py` import `DatasetMaterializer`/`SourceInventory` from `application.ports` (top-level, not `TYPE_CHECKING`-guarded). Only doesn't crash today because concrete registry construction happens lazily via the composition root — any static import-order change could break it. Must resolve by having the new `datasets/` feature package own both the port protocols and the adapters (no back-reference to a separate `application` layer).

**Stage handlers with real scientific computation inline** (violates "thin orchestration"):
- `analysis_stages.py`: `_analyze_threshold_stability` (variance/attainment-error math), `_analyze_cluster_stability` (dispersion aggregation), `_analyze_temporal_recovery` (drift/recovery-ratio + band classification), `_analyze_quantile_estimation` (exceedance/attainment-error).
- `scoring_support.py`: `conformal_seed_coverage`, `client_score_distributions`, `calibration_variance_terms`, `threshold_exchange_cost` — pure statistical/estimation functions living in "application support" rather than domain/feature math.
- `stage_protocol.py::apply_holm_correction` — real statistical procedure invoked directly from `analysis_stages.py.execute()`.

**Config service-locator pattern**: `ResolvedProjectConfiguration` threaded into nearly every stage handler ctor, then deep-indexed far from the top level — e.g. `analysis_stages.py` reaches `self._config.metric_definitions.cross_client_aggregation.cv_fpr`, `self._config.communication_estimation_contract`, `self._config.protocol_determinism.seed_namespaces[...]`; `learning_stages.py` reaches `self._config.training_profiles.get(...)`, `self._config.runtime.active_execution_profile.device_policy`. Classic service-locator anti-pattern.

**`dict[str, object]` internal contracts (not I/O boundaries)**: `analysis_stages.py` threads `list[dict[str, object]]` between `_analyze_*` methods (`.get("seed_differences")`, `cast(list[float], result[...])`); `scoring_support.py::seed_ratio_result`/`conformal_seed_coverage` return `dict[str, object]`; `reporting.py` pulls apart `Mapping[str, object]` records by string key in `_render_table`/`_render_figure`.

**Untested-by-name modules**: `ports.py`, `stage_protocol.py`, `reporting_stages.py` — none referenced by class/module name in any test (unit/integration/conformance/scientific), despite being load-bearing cross-cutting modules.

## 2. `src/datp_core/domain/` (15 files, ~3,187 lines)

Zero upward dependencies — every file imports only other `domain.*` modules. Legitimate base layer.

| File | Lines | Responsibility |
|---|---|---|
| `__init__.py` | 3 | docstring |
| `artifacts.py` | 190 | artifact identity/lifecycle/format enums + `ArtifactRepository` Protocol |
| `catalogue.py` | 690 | **oversized**: 4 concept clusters — training/model-infra records, eligibility/metric-bundle records, all 14 analysis-kind records + `AnalysisKind` enum, sweep/population/experiment records |
| `checkpoints.py` | 80 | 3 pure checkpoint-selection algorithms |
| `datasets.py` | 379 | **oversized**: source-layout/inspection + per-setup client-construction + field-schema/encoding — 3 sub-domains |
| `drift.py` | 58 | `diff_canonical_projections` — **no direct test** |
| `evaluation.py` | 232 | operating-point models: `MetricStatus`, `ClientConfusionMatrix`, `FprDispersion`, JS-divergence — good example of stats correctly placed in domain. Uses relative import (`.identifiers`) — inconsistent with rest of package |
| `fingerprints.py` | 131 | BLAKE2b fingerprinting |
| `identifiers.py` | 102 | all typed ID classes — most depended-upon module (42 test references) |
| `outcomes.py` | 119 | `StageKind`, `JobExecutionStatus`, `StageJobContext` (19-field context — candidate to split into composable sub-contexts), `StageJob`, `StageJobOutcome`. Relative imports (`.artifacts`, `.identifiers`) |
| `protocol_contracts.py` | 294 | **explicit dumping ground, admitted in its own docstring** ("no current downstream consumer"): metric-definitions, artifact-identity, comms-estimation, operational-inputs, report-profiles, determinism/threshold-policy-defaults records — ~20 classes, only 2 consumed anywhere (`ReportProfileRecord`, `CommunicationEstimationContractRecord`), **no test references it at all** |
| `run_identity.py` | 7 | `execution_run_id` — single pure fn, no direct test |
| `splits.py` | 180 | `SplitMembership`, `SplitManifest` w/ temporal future-leakage validation |
| `statistics.py` | 107 | `holm_adjust_p_values`, BCa/rank-biserial/regression records — correct split: primitive here, app-facing glue (`apply_holm_correction`) in `stage_protocol.py`. **Preserve this split pattern**, don't re-merge |
| `thresholding.py` | 370 | `ThresholdRecord`/`ThresholdSet`, 12-member `ThresholdPolicyRecord` union |
| `values.py` | 224 | **grab-bag**: constrained scalar value-objects + generic `TypedDomainRegistry[K,V]` (DI/lookup, unrelated to "values") + JSON-freezing utilities (`deep_freeze`/`FrozenJson`/`as_*_mapping`) — 3 unrelated families |

## 3. `src/datp_core/planning/` (4 files, ~1,040 lines)

| File | Lines | Responsibility |
|---|---|---|
| `__init__.py` | 0 | empty |
| `expansion.py` | 393 | `expand_experiment_jobs` — single ~340-line function, 6+ nested `product()` levels expanding seeds/conditions/mu/ditto-weight/calibration-subset/eval-sweep into a `PlanningGraph`. Monolithic; candidate to decompose per experiment/materialization/training/scoring/threshold/evaluation sub-stage |
| `graph.py` | 86 | `PlanningGraph` — thin NetworkX wrapper. No direct test (only transitive) |
| `validation.py` | 85 | `ExecutionPlanValidator`/`PlanValidationResult` — DAG + artifact-producer + stage-input-contract checks |
| `identity.py` | 561 | `IdentityBuilder` — single god-class, 30+ static methods, sole authority for every `JobId`/`ArtifactId`/`ArtifactKey` string. Not fake modularization (real load-bearing logic) but natural fault line to split per feature package (experiments/, learning/, thresholding/, evaluation/, analysis/, reporting/) |

## 4. `src/datp_core/interfaces/` (4 files, 207 lines)

| File | Lines | Responsibility |
|---|---|---|
| `__init__.py` / `cli/__init__.py` | 1/1 | docstring markers |
| `cli/app.py` | 165 | Typer CLI routing to application use cases via composition root. **Local-import inconsistency**: lines 129-130 import `planning.expansion`/`planning.validation` inside `experiment_plan()` while every other dependency is module-top — no cycle justifies this, looks like an oversight |
| `cli/formatters.py` | 40 | Rich renderers `print_catalogue_summary`, `print_planning_dag` — no direct test |

## 5. Systemic / cross-cutting issues (application+domain+planning+interfaces scope)

- **Oversized/mixed-responsibility**: `analysis_stages.py` (1298), `learning_stages.py` (953), `domain/catalogue.py` (690), `planning/identity.py` (561, justified god-class), `dataset_audit.py` (431), `threshold_stages.py` (397), `planning/expansion.py` (393, one 340-line fn), `domain/datasets.py` (379), `domain/protocol_contracts.py` (294).
- **Fake modularization**: none beyond expected empty/docstring `__init__.py` markers.
- **Duplicate helpers**: `_ineligible_client_metrics` (see above). No duplicate enums/dataclasses found in this scope beyond adjacent-but-distinct status enums (`MetricStatus` vs `ConformalAttainabilityStatus` — different domains, not duplicates).
- **Circular import**: confirmed `application.data_stages` ↔ `infrastructure.datasets.*` via `application.ports` (see above).
- **Local imports hiding nothing suspicious except**: `interfaces/cli/app.py:129-130` (no actual cycle risk, just inconsistent style) and `application/threshold_stages.py:375` (redundant, not cycle-related).
- **Stage handlers with embedded scientific computation**: see above (`analysis_stages.py`, `scoring_support.py`, `stage_protocol.py::apply_holm_correction`).
- **Config service-locator usage**: pervasive across `analysis_stages.py`, `learning_stages.py`, `threshold_stages.py`, `data_stages.py`, `stage_protocol.py`.
- **`dict[str,object]`/`dict[str,Any]` internal contracts**: `analysis_stages.py` inter-method plumbing, `scoring_support.py` return values, `reporting.py` rendering internals.
- **Dead/effectively-unconsumed code**: `domain/protocol_contracts.py` (~18 of ~20 classes unconsumed, zero test references).
- **Miscellaneous dumping grounds (explicit)**: `application/stage_protocol.py`, `application/scoring_support.py`, `domain/protocol_contracts.py`, `domain/values.py`.
- **Conformance tests hard-coding the OLD layer architecture** (must be rewritten, not merely deleted-around): `tests/conformance/test_project_structure.py` (`_EXPECTED_PACKAGES` tuple lists `application, composition, config, domain, infrastructure, interfaces, planning`), `tests/conformance/test_application_port_dependency.py` (forbids `application/` importing specific concrete infra modules — encodes the old boundary, needs a new boundary test for the new package set).

## 6. `src/datp_core/composition/` (2 files, 202 lines)

| File | Lines | Responsibility |
|---|---|---|
| `__init__.py` | 1 | docstring |
| `root.py` | 201 | **The single composition root.** Builds `ConfigOnlyApplication`/`DatpApplication` from resolved config. Imports across `application` (10 modules, ~20 names), `config.resolver`, `domain.{datasets,identifiers,values}`, `infrastructure.{artifacts,datasets,querying,thresholding}` (8 names). By far the largest fan-in of any file in the codebase — the intended single point allowed to cross every feature boundary. **No dedicated unit test directory** (`tests/unit/composition/` doesn't exist) — wiring logic (e.g. "does `build_application` fail closed on bad config") is only exercised transitively. |

## 7. `src/datp_core/config/` (10 files + `models/` subpackage, ~3,790 + ~1,410 = ~5,200 lines)

| File | Lines | Responsibility |
|---|---|---|
| `converter.py` | 66 | shared `cattrs.Converter` singleton for fingerprint unstructuring. Module-global mutable singleton (stateless/idempotent, low risk) |
| `dataset_resolution.py` | 509 | **mixed-responsibility**: every authored-dataset sub-schema transform (identity scheme → labels → endpoint identity → categorical encoding → field schema → source layout → source contract → client construction → `resolve_datasets`) in one file — natural split point per `datasets/` sub-concern |
| `experiment_resolution.py` | 288 | authored experiment/analysis/sweep → domain records + experiment scientific-fingerprint projection. **Naming violation**: its real public API (`_resolve_analysis`, `_resolve_sweep`, `_experiment_scientific_projection`) is underscore-prefixed yet imported directly by `resolver.py` — signals "private" to tooling while actually being cross-module public API. `_resolve_analysis` is a 13-branch dispatch, one per analysis kind — this *is* the `analysis/`/`evaluation/` feature's dispatch table, currently embedded in config |
| `protocol_resolution.py` | 375 | resolver-side mirror of `protocol_config.py`'s policy-family mixing: `_resolve_threshold_policy` dispatches all 12 threshold-policy families in one table, plus unrelated metric-definition/artifact-identity/comms-estimation/report-profile resolution — spans at least 4 future packages (`thresholding/`, `evaluation/`, `reporting/`, `artifacts/`) |
| `resolver.py` | 836 | **largest file in `config/`.** Defines `ResolvedProjectConfiguration` (40-field god object) + the entire staged resolution pipeline. **Confirmed circular import**: line 831 does `from datp_core.config.validation import ProjectConfigurationValidator` inside `resolve_project_configuration()` (deferred, function-body) because `validation.py` imports `resolver.py` at module scope — the **only** local/deferred import found anywhere in these 41 files, and a genuine resolver⇄validation cycle that must be broken explicitly (e.g. validation becomes a pure function invoked by a caller above both, not called from within resolution itself). Also has a **dead field**: `communication_estimation: Mapping[str, object] | None` (line 149) is written (line 813) but never read anywhere else in `src/` — the one untyped internal-contract escape hatch in an otherwise fully-typed record |
| `runtime_settings.py` | 337 | bootstrap settings, path-authority resolution (symlink/escape policy), resolved runtime config. Security-sensitive `PathAuthorityError` branches (symlink loops, broken symlinks, repo-root escape) have **no direct unit test** |
| `validation.py` | 250 | cross-document validation of resolved config. Other half of the resolver⇄validation cycle (module-scope import of `resolver.py`). **No dedicated unit test** constructing a deliberately-invalid config and asserting `ValidationReport.errors` in isolation |
| `yaml_loader.py` | 114 | strict PyYAML→Pydantic loading, duplicate-key detection, typed `ConfigurationError` |
| `models/_base.py` | 32 | `StrictFrozenConfigModel`/`SchemaVersionOneConfigModel` — shared Pydantic bases, genuinely load-bearing |
| `models/dataset_config.py` | 256 | ~20 Pydantic models for one dataset YAML doc |
| `models/experiment_config.py` | 210 | Pydantic models for `experiments.yaml`. `AnalysisSpecConfig` is a deliberate ~60-field "superset" model with no per-kind subclassing — kind-specific typing lives only downstream in the resolver |
| `models/protocol_config.py` | 815 | **largest single file in scope.** 49 model classes for the entire `protocols.yaml`: architecture/optimizer/batching/determinism/checkpoints/training/federation/eligibility/normalization/quantile-estimators/**12 threshold-policy configs**/metric-bundles/statistical-profiles/result-types/report-profiles/artifact-identity/comms-estimation. This is the authored-schema counterpart of 6+ future feature packages in one file — the single largest mixed-responsibility instance in the whole audit |
| `models/runtime_config.py` | 95 | Pydantic models for `runtime.yaml` |

## 8. `src/datp_core/infrastructure/` (41 files total across subpackages, ~8,564 LOC incl. config/composition)

### `infrastructure/artifacts/`
- `atomic_commit.py` (217) — sole filelock-protected, fsync+atomic-rename artifact-commit engine; well-factored, no duplication.
- `manifest_codec.py` (133) — sole `msgspec` strict JSON codec for `ArtifactManifest`.
- `model_store.py` (66) — SafeTensors persistence wrappers. **Bypassed abstraction**: `application/learning_stages.py` (out of this audit's direct scope, confirmed by grep) imports `safetensors.torch.load/save` **directly** 4 times instead of calling these wrappers — duplicate concrete-library integration.
- **Provenance/path construction is NOT centralized here**: relative-path strings (`f"runs/{run_id}/{job_id}"`) are independently re-formatted at ~19 call sites across `application/*.py`; git-revision lookup lives in `application/stage_protocol.py`, not in `infrastructure/artifacts/`. When `artifacts/` becomes its own package, path-naming and provenance capture should move into it.

### `infrastructure/datasets/`
- `adapter_registry.py` (36) — `AdapterKind → DatasetMaterializer` registry.
- `csv_source.py` (148) — streaming strict CSV validation, never silently drops rows.
- `source_inventory.py` (132) — deterministic ordered source-file inventory + fingerprint.
- `split_manifest.py` (67) — Parquet split-evidence read/encode.
- `ciciot2023.py` (422) — adapter: pseudo-client identity, SQLite dedup, seeded split, Parquet materialization. Explicitly forbidden from `application/` import by conformance test (confirms port-only access pattern).
- `edge_iiotset.py` (660, **largest dataset adapter**) — mixes source parsing, two independent split strategies (random vs. chronological-with-rollover), vocabulary/normalization *fitting* (a preprocessing concern), and Parquet encoding — 4 concerns in one file.
- `nbaiot.py` (595) — path-derived identity, chronological-gapped split, Dirichlet partitioning, deterministic partition-seed derivation (3rd independent reimplementation of the seed-derivation formula — see below), Parquet streaming.

### `infrastructure/federation/`
- `flower_adapter.py` (32) — **DEAD CODE**. Wraps `flwr.server.strategy.FedAvg`; the *only* file in the whole audited scope importing `flwr`; used nowhere except its own unit test. The real FedAvg/FedProx/Ditto loop is hand-implemented in `pytorch_adapter.py` with zero Flower dependency. Delete this subpackage (and the `flwr` dependency) during the migration, or explicitly justify keeping it — current state is orphaned.

### `infrastructure/learning/`
- `pytorch_adapter.py` (649, **largest infrastructure file**) — the complete PyTorch stack: seeding, autoencoder architecture, manual FedAvg/FedProx training loop + checkpoint scheduling, Ditto training loop + checkpoint scheduling, shared + personalized scoring, device selection. Exactly the "training + checkpoint selection + scoring bundled together" anti-pattern the task brief warns about — top candidate for splitting into seeding/device, model definition, FedAvg/FedProx training, Ditto training, checkpoint capture, scoring. No `domain`/`application`/`config` imports at all (self-contained ML mechanics) — but the round-loop/checkpoint-scheduling logic itself has **no dedicated unit test**, only indirect coverage via application-layer stage-handler tests.
- `sklearn_adapter.py` (49) — per-client AUROC + adjusted Rand index. Uses stdlib `@dataclass` instead of the codebase's universal `attrs @define` — convention inconsistency. `scale_features()` has **no consumer anywhere** — likely dead.

### `infrastructure/querying/`
- `audit_service.py` (40) — read-only DuckDB audit service. Constructor takes the **entire** `ResolvedProjectConfiguration` god object just to read one `Path` — config-service-locator pattern again. **Zero unit tests anywhere** call `execute_query`/`audit_metrics_completeness`; only reference is `composition/root.py` wiring + the conformance test asserting `application/` doesn't import it directly. Candidate dead/under-integrated feature — cross-check against CLI (`interfaces/`) before deciding its fate.

### `infrastructure/runtime/`
- `logging.py` (50) — `structlog` configuration, clean single-purpose module.

### `infrastructure/tables/`
- `calibration_subsampling.py` (69) — deterministic nested subsampling via seeded permutation. `_subsample_seed` is the **3rd independent reimplementation** of the blake2b seed-derivation formula (see below).
- `parquet_io.py` (195) — mixes generic Parquet I/O helpers with dataset-normalization-**fitting** business logic (~100 of 195 lines) — mild dumping-ground pattern; the normalization-fitting half belongs with `datasets/`/`learning/` preprocessing, not generic I/O.
- `polars_engine.py` (124) — per-client confusion-matrix metrics + AUROC delegation. Cross-subpackage import `tables → learning` (`sklearn_adapter`) — needs an explicit decision when these split into separate feature packages (`evaluation/` computing metrics vs. `learning/` owning sklearn).
- `schemas.py` (83) — Pandera schema contracts for calibration/test-score/threshold/per-client-metric frames. **Zero direct unit tests anywhere**, despite being a heavily-used (18 call sites across 3 application files), safety-critical validation boundary — the single clearest "untested but load-bearing" module in the entire audit.

### `infrastructure/thresholding/`
- `base.py` (34) — `ThresholdEstimator` Protocol + `ThresholdConstructionRequest`. Has a loosely-typed `family_map: dict[str, str] | None` field — narrow escape hatch, candidate for a typed value object if family-taxonomy handling grows.
- `estimators.py` (377) — `ConfiguredThresholdEstimator`, one class implementing **all 12** threshold-policy-family algorithms behind an `isinstance` dispatch chain (shared-mean, pooled, weighted, local-quantile, family-mean, cluster/KMeans, split-conformal, shrinkage, calibration-fallback, federated-matched-exceedance, federated-fixed-coefficient). This is the estimator-layer mirror of `protocol_config.py`'s 12 config classes and `protocol_resolution.py`'s 12-entry dispatch — **the same 12-policy-family concept is independently represented at 3 layers**. **No `tests/unit/infrastructure/thresholding/` directory exists** — validated only by `tests/scientific/thresholding/test_configured_threshold_estimators.py`, no fast unit-level per-policy isolation.

## 9. Reconciled cross-cutting findings (both audit passes)

### 9.1 The one real circular dependency
`config/resolver.py:831` (deferred, function-body) ⇄ `config/validation.py:10` (module-scope). This is the **only** circular-import risk confirmed by direct grep of local/deferred imports across all ~88 files (the `application.data_stages ↔ infrastructure.datasets.*` relationship via `application.ports` in Part 1 is a package-level dependency-direction violation, not a same-process import cycle, since it's mediated by lazy composition-root construction — but it must still be resolved the same way: neither side should import concrete implementations of the other).

### 9.2 God object / service-locator pattern
`ResolvedProjectConfiguration` (40 fields, `config/resolver.py`) is threaded whole into nearly every use case, stage handler, and infra service in `composition/root.py`, rather than each consumer receiving a narrow typed projection. Confirmed extreme case: `DuckDbAuditService` takes the entire config just to read one `Path`. This is the single biggest structural obstacle to decomposing `config/` into `configuration/` + per-feature packages — each new feature package needs its own narrow resolved read-model.

### 9.3 The "12 threshold policy families" are represented independently at 3 layers
`config/models/protocol_config.py` (12 Pydantic config classes) → `config/protocol_resolution.py` (12-entry resolver dispatch) → `infrastructure/thresholding/estimators.py` (12-branch `isinstance` estimator dispatch). All three must move into `thresholding/` together and should be reconciled into one coherent per-family structure (e.g. one file/class pair per family or family-group) rather than three independently-maintained 12-way dispatches.

### 9.4 Duplicate scientific helpers (confirmed exact/near-exact duplication)
- `_ineligible_client_metrics`: byte-for-byte duplicate in `application/learning_stages.py:920-941` and `application/threshold_stages.py:374-397`.
- Seed-derivation formula (blake2b digest of pipe-joined `name=value` components, mod 2³²) independently reimplemented **three times**: `infrastructure/learning/pytorch_adapter.py::_derive_seed`, `infrastructure/datasets/nbaiot.py::derive_partition_seed`, `infrastructure/tables/calibration_subsampling.py::_subsample_seed` — scientifically sensitive (determinism guarantees depend on exact formula) and currently unguarded against drift. Needs one canonical shared implementation.
- `*MaterializationPayload` attrs records (`CICIoT2023MaterializationPayload`, `EdgeIIoTsetMaterializationPayload`, `NBaIoTMaterializationPayload`) are structurally identical (`staged_path`, `row_count`, `preprocessing_evidence`, `partition_evidence`) — collapse to one shared record.

### 9.5 Explicit "dumping ground" modules (both passes combined)
`application/stage_protocol.py`, `application/scoring_support.py`, `domain/protocol_contracts.py`, `domain/values.py` (Part 1); `config/dataset_resolution.py`, `config/protocol_resolution.py`, `infrastructure/tables/parquet_io.py` (mild — normalization-fitting bundled with generic I/O) (Part 2).

### 9.6 Dead / orphaned code (confirmed by grep, both passes)
- `domain/protocol_contracts.py` — ~18 of ~20 record classes have no consumer, zero test references.
- `infrastructure/federation/flower_adapter.py` — entire subpackage + `flwr` dependency orphaned.
- `config/resolver.py::ResolvedProjectConfiguration.communication_estimation` field — written, never read.
- `infrastructure/learning/sklearn_adapter.py::scale_features()` — no consumer.
- `infrastructure/querying/audit_service.py` — no test, unclear caller; cross-check against `interfaces/cli` before deciding fate.

### 9.7 Untested-but-load-bearing modules (confirmed, both passes)
`application/ports.py`, `application/stage_protocol.py`, `application/reporting_stages.py` (Part 1); `infrastructure/tables/schemas.py` (heavily used, safety-critical, zero direct tests — single clearest instance in the whole audit), `infrastructure/thresholding/estimators.py` (no unit-level tests, only `tests/scientific/`), `composition/root.py` (no `tests/unit/composition/` at all), `config/validation.py` and `config/runtime_settings.py`'s security-sensitive path-authority branches (Part 2).

### 9.8 Conformance tests that hard-code the OLD architecture (must be rewritten, not just routed around)
`tests/conformance/test_project_structure.py` (`_EXPECTED_PACKAGES` lists the 7 old layer packages), `tests/conformance/test_application_port_dependency.py` (forbids `application/` importing specific concrete infra modules — encodes the old boundary; `_FORBIDDEN_INFRASTRUCTURE_IMPORTS` explicitly names `infrastructure.datasets.{ciciot2023,nbaiot}` etc.), `tests/conformance/test_configuration_authority_boundary.py`, `tests/conformance/test_experiment_catalogue_field_disposition.py`, `tests/conformance/test_executable_invariants.py`, `tests/conformance/test_no_hidden_defaults.py` — all reference old package paths and must be redesigned as import-boundary tests for the new package set (Section 9 of the task spec).

### 9.9 Concrete library placement (compliance check against "no concrete infra outside infrastructure/")
PyTorch/SafeTensors leak into `application/learning_stages.py` directly (bypassing `pytorch_adapter.py`/`model_store.py` wrappers) — the one confirmed violation. All other concrete libraries (Polars partially excepted, since Polars `DataFrame` is used as the de facto interchange type between stage handlers and infra — needs an explicit architectural decision for the new `pipeline/`/feature boundary) are correctly confined to `infrastructure/`.

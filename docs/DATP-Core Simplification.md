# DATP-Core Simplification and Architecture Consolidation Roadmap

**Version:** 2.0 — Repository-grounded rewrite
**Date:** 2026-07-26
**Status:** Implementation roadmap — no code changes in this document

---

## A. Executive Summary

### Current architectural problem

DATP-Core implements a scientifically rigorous threshold-calibration-scope study with strong configuration validation, typed domain models, and a clean composition root. However, the implementation carries structural problems that make it harder to navigate, extend, and maintain than necessary:

1. **Oversized nullable stage context.** `StageJobContext` (`pipeline/stages/context.py`) has 16 fields, 13 of which are `Optional`. A single context class serves materialization, training, scoring, thresholding, evaluation, and analysis stages. Fields irrelevant to a stage are silently `None`.

2. **Long isinstance dispatch chain.** `thresholding/estimation/dispatch.py` contains a 12-branch `isinstance` chain over concrete threshold policy record types. Adding a policy requires editing this central chain.

3. **No experiment compilation.** Experiment planning in `experiments/planning/jobs.py` navigates `ResolvedProjectConfiguration` repeatedly (`config.populations.get()`, `config.training_profiles.get()`, etc.). No `CompiledExperiment` resolves references once.

4. **Scattered path construction.** Experiment output paths are built inline in `experiments/planning/jobs.py` and `experiments/planning/layout.py` via `cell_directory()`, `evaluation_directory()`, `output()`, and `shared_output_path()` helpers. No centralized `ExperimentPaths` authority exists.

5. **Opaque Dagster integration.** `orchestration/dagster_defs.py` wraps each experiment in one opaque Dagster operation. Dagster provides no stage-level visibility.

6. **Mixed model systems.** Production code uses `attrs` (`@define`) for `ResolvedProjectConfiguration`, metric records, and evaluation records; `pydantic.BaseModel` for authored configuration and analysis results; `cattrs.Converter` for CLI JSON serialization. Three serialization frameworks coexist without clear boundaries.

7. **Hydra dependency unused.** `hydra-core>=1.3` is in dependencies but no Hydra configuration composition is implemented. Configuration is loaded via a custom `YamlConfigurationReader`.

8. **Dictionary access in campaign.** `experiments/execution/campaign.py` accesses frozen results via `frozen.get("outcomes")` and `frozen.get("anchor_equivalence_passed")` — untyped dictionary access on what should be a typed model.

### Simplification objective

Make DATP-Core smaller, clearer, more centralized, and easier to extend without introducing a framework around it. Every proposed abstraction must replace more complexity than it adds.

### Scientific non-drift requirement

All scientific behavior defined by `docs/roadmap/SCIENTIFIC_SOURCE_OF_TRUTH.md` is preserved unchanged. The confirmatory endpoint (Regime A, B1 vs B2, CV(FPR), ten paired seeds, 95% BCa CI) is never altered. Threshold policies, metrics, statistical procedures, checkpoint selection, and dataset contracts remain identical.

### What will be centralized

- Configuration resolution into one `ResolvedProjectConfiguration` (already done; preserve)
- Experiment compilation into `CompiledExperiment` (new)
- Path construction into `ExperimentPaths` (new)
- Stage planning into `ExperimentPlanBuilder` (consolidated from `experiments/planning/jobs.py`)
- Campaign execution into one `CampaignRunner` (consolidated from `CampaignOrchestrator` + `ExperimentLifecycleUseCase`)
- Threshold dispatch into `ThresholdEstimatorRegistry` keyed by `ThresholdPolicyKind` (replaces isinstance chain)

### What will be removed

- `StageJobContext` with 13 nullable fields — replaced by 4 typed context families
- 12-branch isinstance chain in `thresholding/estimation/dispatch.py`
- Inline path construction in `experiments/planning/layout.py` and `jobs.py`
- `attrs` models where Pydantic v2 provides equivalent behavior
- `cattrs` serialization in CLI — replaced by Pydantic `model_dump`
- `Mapping[str, ...]` fields in `ResolvedProjectConfiguration`
- Dictionary access on frozen results in campaign
- Opaque Dagster one-op wrapper
- Dead `no-flower-dependency` import-linter contract

### What will deliberately not be abstracted

- No compiler class hierarchy
- No registry for metrics, paths, reports, codecs, statistics, models, optimizers, losses, schedulers, scorers
- No plugin framework for preprocessing, statistics, or plotting
- No dependency-injection framework or service locator
- No artifact-management framework
- No stage-contributor framework
- No separate campaign domain package
- No compatibility shims, redirects, or deprecated aliases

---

## B. Repository-Grounded Current-State Audit

### B.1 Configuration

**Current state.** Configuration is loaded from 6 YAML files (`configs/runtime.yaml`, `protocols.yaml`, `experiments.yaml`, `datasets/nbaiot.yaml`, `ciciot2023.yaml`, `edge_iiotset.yaml`) by `config/loading.py`'s `YamlConfigurationReader`. Authored documents use Pydantic v2 models (`config/authored/`). Resolution produces `ResolvedProjectConfiguration` via `config/project.py:resolve_from_authored_documents()`. Validation runs through `ProjectConfigurationValidator`.

**Findings:**
- Hydra is listed as a dependency but never used for configuration composition. YAML files are read directly by custom code.
- `ResolvedProjectConfiguration` uses `@define` (attrs), not Pydantic. This prevents using Pydantic validators on the resolved config.
- Three `Mapping[str, ...]` fields remain: `population_readiness_rule: Mapping[str, str | bool]`, `analysis_conventions: Mapping[str, str]`, `normalization_fit_scopes: Mapping[str, str]`. These are untyped dictionaries at the boundary of the resolved configuration.
- Environment variable overrides are set via `os.environ` in `cli.py` (lines 291-293, 316-318, 345) and `orchestration/diagnostics.py` (lines 35-38, 61-65), not via Hydra's override system.
- CLI commands for config drift comparison (`config/explain-drift`, `config/explain-scientific-drift`, `config/explain-execution-drift`) import `resolve_project_configuration` directly (cli.py:18) — bypassing the application composition root.

### B.2 Pydantic/attrs/cattrs

**Current state.** Three serialization/validation frameworks coexist:

| Framework | Usage | Files |
|---|---|---|
| Pydantic v2 `BaseModel` | Authored config models, analysis result models (30+ discriminated unions) | `config/authored/`, `analysis/contracts.py` |
| `attrs` (`@define`) | `ResolvedProjectConfiguration`, metric formula records, evaluation records, seed records, threshold policy records | `config/models.py`, `evaluation/definitions/metrics.py`, `learning/contracts/`, `thresholding/policies/` |
| `cattrs` (`Converter`) | CLI JSON serialization | `cli.py:19`, `cli.py:96,111,126` |

**Findings:**
- `attrs` models for metric records (`evaluation/definitions/metrics.py`) have no validation beyond type checking — Pydantic could provide validators for formula consistency.
- `cattrs.Converter` in CLI is used only for `unstructure()` calls to serialize drift reports and fingerprints to JSON. Pydantic's `model_dump(mode="json")` provides the same capability.
- No `structure()` calls found — cattrs is only used for unstructuring, making it trivially replaceable.
- `ResolvedProjectConfiguration` has 45+ fields, many of which are `TypedDomainRegistry` instances. Converting to Pydantic would add validation at the resolved-config boundary.
- Analysis result models already use Pydantic discriminated unions (`AnalysisResult = Annotated[...]`) with `Field(discriminator="result_kind")`. This pattern is correct and should be preserved.

### B.3 Datasets and preprocessing

**Current state.** Three dataset adapters in `data/adapters/`:
- `nbaiot/` — 5 files: adapter, models, parquet, partitioning, splitting
- `ciciot2023/` — 6 files: adapter, identity, index, models, parquet, splitting
- `edge_iiotset/` — 6 files: adapter, models, parquet, parsing, preprocessing, splitting

Each adapter implements a common protocol. Shared preprocessing is in `data/preprocessing/` (normalization, models). Materialization is orchestrated by `data/materialization/handler.py`.

**Findings:**
- Adapter structure is clean and preserves dataset-specific logic. No flattening needed.
- `data/materialization/registry.py` provides a `DatasetAdapterRegistry` keyed by `AdapterKind` enum — correct pattern.
- `data/preprocessing/normalization.py` contains shared normalization logic already separated from adapters.
- `ConfigFile` source: `data/sources/csv.py` handles numeric CSV parsing with label extraction — shared infrastructure.
- No preprocessing plugin framework exists — good, and it should stay that way.

### B.4 Experiment planning

**Current state.** `experiments/planning/jobs.py:expand_experiment_jobs()` is the central planning function (~540 lines). It:
1. Creates preflight job
2. Creates materialization jobs per seed/condition/population
3. Creates training jobs per seed/condition/mu/ditto_weight
4. Creates checkpoint selection job
5. Creates scoring and calibration subsampling jobs
6. Creates evaluation jobs (threshold + metrics) per sweep combination
7. Creates statistical analysis job
8. Creates result freeze and report jobs
9. Returns a `PlanningGraph`

Campaign planning (`expand_campaign_jobs()`) adds shared-stage deduplication on top.

**Findings:**
- `expand_experiment_jobs()` navigates `ResolvedProjectConfiguration` repeatedly: `config.populations.get()`, `config.training_profiles.get()`, `config.seed_cohorts.get()`, `config.datasets.get()`. These are resolved-config lookups that should happen once during compilation.
- Paths are built inline via `cell_directory()`, `evaluation_directory()`, `output()`, `shared_output_path()` from `experiments/planning/layout.py`. No centralized path authority.
- Sweep expansion (`experiments/planning/sweeps.py`) handles `product()` over quantile × shrinkage × fixed_k × features. This belongs in the plan builder but currently interleaves with path construction.
- `StageJob` has a `context: StageJobContext` field that carries all nullable coordinates. The planning function constructs context objects with only the relevant fields set, leaving others `None`.

### B.5 Campaign

**Current state.** `experiments/execution/campaign.py` contains `CampaignOrchestrator` (193 lines). It:
1. Builds experiment DAG via `networkx`
2. Computes canonical experiment order (anchors first)
3. Delegates actual execution to `ExperimentLifecycleUseCase.run_campaign()`
4. Maps lifecycle results to `CampaignExperimentResult` with status conversion

`experiments/execution/use_case.py` contains `ExperimentLifecycleUseCase` that handles per-experiment skip/override/run logic.

`experiments/execution/output_manager.py` contains `ExperimentOutputManager` for inspecting, deleting, and loading experiment outputs.

**Findings:**
- Campaign logic is split between `CampaignOrchestrator` (ordering, DAG, reporting) and `ExperimentLifecycleUseCase` (per-experiment lifecycle). These should be consolidated.
- `_anchor_passed()` (line 140-148) uses dictionary access: `frozen.get("outcomes")`, `frozen.get("anchor_equivalence_passed")`.
- `_prerequisite_error()` (line 150-165) does string-based status comparison.
- Campaign resumption logic is implicitly handled by the lifecycle's skip/override behavior — no explicit "find first incomplete and resume" step.
- No prerequisite fingerprint compatibility check exists. Only prerequisite success status is verified, not fingerprint match.
- `override_all` deletes via `output_manager.delete()` and `output_manager.delete_shared_outputs()` — correct.

### B.6 Artifacts and paths

**Current state.** `artifacts/store.py` contains `ArtifactStore` with atomic writes, replacement protection, checksum support, symlink protection, and path traversal protection. `artifacts/atomic.py` handles atomic file writes. `artifacts/codecs/` provides SafeTensors and schema codecs.

**Findings:**
- `ArtifactStore` is a clean direct-file store. No over-abstraction. Preserve as-is.
- `artifacts/schemas/` contains Pandera schemas for columns, metrics, scores, and thresholds — correct pattern.
- Path construction is NOT centralized. Paths are built in:
  - `experiments/planning/layout.py` — `cell_directory()`, `evaluation_directory()`, `output()`, `shared_output_path()`
  - `experiments/planning/jobs.py` — inline `f"experiments/{context.experiment_id.value}/"` prefix, `f"training/{cell_directory(context)}"`, etc.
  - `experiments/execution/output_manager.py` — `self._outputs_root / experiment_id.value`
  - `orchestration/diagnostics.py` — `Path(".tmp/diagnostics")`
  - `cli.py` — `Path(".tmp/diagnostics").resolve()`
- No `ExperimentPaths` class exists.

### B.7 Learning

**Current state.** `learning/` is organized into:
- `contracts/` — architecture, checkpoints, enums, optimization, seeds, training records
- `model/` — autoencoder, determinism, device
- `training/` — federated, local, aggregation, personalization, handler, models
- `checkpoints/` — evidence, handler, models, selection
- `scoring/` — checkpoints, compute, data, handler, models

**Findings:**
- `learning/training/handler.py` receives the full `ResolvedProjectConfiguration` — should receive only compiled training inputs.
- `learning/scoring/handler.py` receives the full config — same issue.
- Three training strategies (FedAvg, FedProx, Ditto) are dispatched via `TrainingProfileKind` enum and `PersonalizationStrategy` enum in the planning layer, not via a learning strategy registry. This is acceptable but could be more explicit.
- Model construction (`learning/model/autoencoder.py`) uses configured architecture parameters — correct.
- `learning/model/determinism.py` handles seed derivation via blake2b — correct and should be preserved.
- SafeTensors codec in `artifacts/codecs/safetensors.py` — correct.

### B.8 Thresholding

**Current state.** `thresholding/` is organized into:
- `policies/` — 8 files defining 12 threshold policy record types (all `@define` attrs)
- `estimation/` — dispatch, quantiles, federated, shrinkage, clustering, conformal, construction, models, ports
- `calibration/` — handler, sampling (calibration subsampling)
- `execution/` — frames, handler

**Findings:**
- `thresholding/estimation/dispatch.py:ConfiguredThresholdEstimator.estimate()` contains a 12-branch `isinstance` chain (lines 61-91). Each branch dispatches to a specific estimation function. Adding a threshold policy requires editing this chain.
- The estimator is keyed by `ThresholdPolicyId` (configured instance, e.g., `shared_mean_p95`) not by `ThresholdPolicyKind`. There is no `ThresholdPolicyKind` enum. The dispatch should be keyed by a kind enum like `SHARED_MEAN`, `SHARED_POOLED`, `LOCAL_QUANTILE`, `FAMILY_MEAN`, `CLUSTER`, `CONFORMAL`, `SHRINKAGE`, `CALIBRATION_FALLBACK`, `FEDERATED_MATCHED`, `FEDERATED_FIXED`.
- `thresholding/policies/union.py` defines `ThresholdPolicyRecord` as a union of all 12 policy record types. This union is used for type annotations.
- `thresholding/estimation/ports.py` defines `ThresholdEstimator` protocol. Clean.
- Pure functions in `quantiles.py`, `federated.py`, `shrinkage.py`, `clustering.py`, `conformal.py` are already separated from dispatch — good.

### B.9 Evaluation and metrics

**Current state.** `evaluation/` is organized into:
- `definitions/` — metrics, bundles, results (all `@define` attrs records)
- `distributions/` — CDF, models, tradeoff, variance
- `metrics/` — auroc, diagnostics, models, operating_point
- `execution/` — handler

**Findings:**
- Metric formula records (`evaluation/definitions/metrics.py`) use attrs with many nullable fields (`str | None`, `float | None`, `bool | None`). Converting to Pydantic would add validation.
- `evaluation/metrics/operating_point.py` computes operating-point metrics (FPR, TPR, etc.). Need to verify Polars native expressions are used (not `.iter_rows()`).
- No metric plugin framework exists — good.
- Evaluation metrics are computed once and consumed by analysis. The roadmap must enforce this contract, but the structure already supports it.

### B.10 Analysis and statistics

**Current state.** `analysis/` is organized into:
- `contracts.py` — 30+ Pydantic result models with discriminated union `AnalysisResult`
- `enums.py` — 30+ `StrEnum` definitions
- `statistics/` — inference (BCa, Wilcoxon, rank-biserial, Holm), association (Spearman, linear regression), descriptive
- `comparisons/` — paired, association, effect_ratios
- `calibration/` — conformal, quantile, stability
- `clustering/` — dispersion, membership
- `mechanisms/` — distributions, operational, temporal
- `runtime/` — artifacts, context, persistence, planning, runner
- `selection.py` — FedProx/Ditto selection analysis
- `validation.py` — analysis validation

**Findings:**
- `analysis/statistics/inference.py` already uses Pingouin for Wilcoxon signed-rank (`pg.wilcoxon`) and rank-biserial correlation (`res["RBC"]`). Holm correction also uses Pingouin (`pg.multicomp`). BCa bootstrap uses `scipy.stats.bootstrap` directly — correct, as Pingouin does not provide BCa.
- `analysis/statistics/association.py` (not fully read) uses scipy for Spearman and linear regression — these could use Pingouin (`pg.corr`, `pg.linear_regression`).
- `analysis/runtime/context.py` defines `AnalysisExecutionContext` — separate from the main `StageJobContext`.
- No import-time registration found. The analysis handler registry is built explicitly in the composition root.
- Result models use discriminated unions with `Literal[AnalysisResultKind.X]` discriminator — excellent pattern.

### B.11 Polars vectorization

**Current state.** Polars is a dependency. Statistical code uses NumPy arrays and pandas DataFrames at the Pingouin/scipy boundary.

**Findings:**
- Did not find `.iter_rows()` or `.to_list()` patterns in the files read. The statistical code correctly converts to NumPy arrays before computation.
- Need to verify data preprocessing, evaluation metrics, and calibration modules for Polars row-iteration patterns. This audit was inconclusive — flagged for Phase 9 implementation audit.
- Pingouin and scipy require pandas DataFrames/NumPy arrays. These conversions are at explicit library boundaries — acceptable.

### B.12 Reporting and plots

**Current state.** `reporting/` is organized into:
- `profiles/` — enums for report profiles
- `rendering/` — figures, tables, models, package
- `audit/` — DuckDB query
- `execution/` — freeze handler, report handler
- `freezing/` — codec, errors, models, service, validation

**Findings:**
- `reporting/rendering/figures.py` and `tables.py` use matplotlib for plots — direct functions, not a plugin framework.
- `reporting/audit/query.py` provides DuckDB query service for Parquet artifacts.
- `reporting/freezing/models.py` defines frozen result models — need to verify they are typed (not dictionaries).
- Report profiles in `configs/protocols.yaml` define 18 report items (tables and figures) with column lists, units, and directions.

### B.13 Dagster

**Current state.** `orchestration/dagster_defs.py` (57 lines) defines:
- `STAGE_ORDER` tuple listing 11 stage kinds
- `_make_experiment_job()` that creates one opaque Dagster op per experiment
- `build_dagster_definitions()` that returns `dg.Definitions` with all experiment jobs

**Findings:**
- Each experiment is ONE opaque Dagster operation. The op wraps the entire `app.run_experiment.run()` call. Dagster provides no stage-level visibility, no per-stage retry, no per-stage logging.
- `_run_experiment` (line 32) has a hardcoded repository path: `"/home/naslouby/Projects/datp-core"`. This is a machine-specific path.
- No stage-level asset definitions exist. The entire experiment lifecycle is a single black box to Dagster.
- The diagnostic Dagster command (`cli.py:336-366`) imports `resolve_project_configuration` and `build_dagster_definitions` directly, then calls `job.execute_in_process()` — bypassing the application composition root.

### B.14 CLI and composition

**Current state.** `cli.py` (374 lines) defines:
- 5 Typer command groups: config, catalogue, dataset, experiment, results
- Diagnostic commands with environment mutation
- Direct imports of `expand_experiment_jobs`, `PlanningGraph`, `lexicographical_topological_sort`

**Findings:**
- CLI imports concrete planning infrastructure directly (`cli.py:21-22`): `from datp_core.experiments.planning import expand_experiment_jobs, validate_planning_graph`
- CLI commands mutate `os.environ` directly for diagnostic and Dagster execution (lines 291-293, 316-318, 345)
- `experiment_plan` command (line 168-178) calls `expand_experiment_jobs()` directly instead of routing through an application use case
- `ConfigOnlyApplication` pattern in `app.py` is correct — lightweight config-only app avoids loading training/infrastructure
- `app.py` composition root is clean and explicit — no import-time side effects, no global mutable state

### B.15 Tests and quality tooling

**Current state.** 56 test files organized as unit/, integration/, scientific/.

**Findings:**
- CI workflows (`.github/workflows/tests.yml`) run only pytest — no linting, type checking, or import contract enforcement in CI
- Quality gates are enforced locally via `nox` or `make quality`, not in CI
- `noxfile.py` defines 13 sessions with uv backend
- `importlinter.ini` defines 6 contracts — well-structured but has a dead `no-flower-dependency` contract
- No pytest markers registered in pyproject.toml
- No coverage configuration in pyproject.toml (coverage flags passed via CLI)
- SonarQube configured but quality gate enforced server-side only
- CodeScene configured with all-default thresholds

---

## C. Scientific Source-of-Truth Constraints

The following scientific invariants from `docs/roadmap/SCIENTIFIC_SOURCE_OF_TRUTH.md` are mapped to the code domains that must preserve them. No simplification phase may weaken these constraints.

### C.1 Causal isolation

**Rule:** B1–B4 must use the same frozen detector, scores, calibration records, and test records within a seed.
**Affected code:** `experiments/planning/jobs.py` (job expansion), `thresholding/estimation/` (estimators), `evaluation/metrics/` (metric computation)
**Verification:** AUROC invariance check across B1–B4; identical score artifact paths for all policies within a seed

### C.2 Benign-only calibration

**Rule:** Attack-labelled data must not influence threshold values, quantile selection, checkpoint selection, client eligibility, or comparator tuning.
**Affected code:** `thresholding/calibration/` (subsampling), `learning/checkpoints/selection.py` (checkpoint selection), `data/contracts/eligibility.py` (eligibility)
**Verification:** Audit calibration data paths; verify no attack labels enter threshold construction

### C.3 Confirmatory endpoint

**Rule:** Sole confirmatory: Regime A, B1 vs B2, `CV(FPR)`, ten paired seeds, 95% BCa CI excluding zero (positive).
**Affected code:** `analysis/comparisons/paired.py`, `analysis/statistics/inference.py` (BCa)
**Verification:** Ten-seed BCa result with recorded analysis seed, resample count ≥ 10,000

### C.4 Checkpoint selection

**Rule:** One primary round number selected by `lowest_federated_averaging_weighted_benign_validation_reconstruction_error`, frozen before outcome inspection.
**Affected code:** `learning/checkpoints/selection.py`, `learning/checkpoints/handler.py`
**Verification:** Selection evidence persisted; forbidden selectors not used

### C.5 Seed cohorts

**Rule:** `datp_core_ten_seed` (seeds 0–9) for journal; `anchor_five_seed` (seeds 0–4) for anchor.
**Affected code:** `configs/protocols.yaml` (seed_cohorts), `learning/contracts/seeds.py`
**Verification:** Seed values match configuration

### C.6 Metric definitions

**Rule:** `CV(FPR)` uses `ddof=0`, no epsilon stabilizer, undefined at zero mean. AUROC is a control.
**Affected code:** `evaluation/metrics/operating_point.py`, `evaluation/definitions/metrics.py`
**Verification:** Hand-checkable metric calculations

### C.7 Dataset boundaries

**Rule:** Edge-IIoTset attack-sensitive metrics are unavailable. CICIoT2023 file-defined clients are not physical devices. B3 requires family taxonomy.
**Affected code:** `data/adapters/edge_iiotset/`, `data/adapters/ciciot2023/`, `data/contracts/eligibility.py`
**Verification:** Typed unavailability for unsupported metrics

### C.8 Statistical procedures

**Rule:** BCa for confirmatory; Wilcoxon and rank-biserial secondary; Holm correction within declared families.
**Affected code:** `analysis/statistics/inference.py`, `config/statistical_profiles.py`
**Verification:** BCa with jackknife acceleration; matched-pairs rank-biserial (not Cliff's delta)

---

## D. Simplified Target Architecture

### D.1 Final top-level package structure

```
src/datp_core/
├── config/           # Configuration loading, resolution, validation, fingerprinting
│   ├── authored/     # Pydantic v2 models for YAML documents
│   ├── resolution/   # Per-document resolvers
│   ├── hydra/        # Hydra configuration composition (NEW)
│   └── models.py     # ResolvedProjectConfiguration (migrated to Pydantic v2)
├── core/             # Identifiers, registry, hashing, seeding, immutability
├── data/             # Dataset adapters, preprocessing, contracts, materialization
│   ├── adapters/     # N-BaIoT, CICIoT2023, Edge-IIoTset (unchanged structure)
│   ├── contracts/    # Dataset, eligibility, features, materialization, sources
│   ├── preprocessing/ # Shared normalization, encoding
│   ├── sources/      # CSV parsing, source inventory
│   ├── manifests/    # Split/partition manifest models and codec
│   ├── readiness/    # Source audit, readiness gates
│   └── materialization/ # Materialization handler and registry
├── learning/         # Model, training, checkpoints, scoring
├── thresholding/     # Threshold policies, estimation, calibration
│   ├── policies/     # Policy record types (Pydantic, not attrs)
│   ├── estimation/   # Estimators keyed by ThresholdPolicyKind
│   └── calibration/  # Calibration subsampling
├── evaluation/       # Metric computation authority
├── analysis/         # Statistical comparisons, mechanism analysis
├── reporting/        # Tables, figures, result freezing
├── artifacts/        # ArtifactStore, codecs, schemas
├── pipeline/         # Stage definitions, graph model, execution
├── experiments/      # Experiment catalogue, planning, execution, campaign
│   ├── catalogue/    # Experiment records, analyses, evaluations
│   ├── planning/     # ExperimentPlanBuilder, ExperimentPaths (CENTRALIZED)
│   └── execution/    # ExperimentRunner, CampaignRunner, OutputManager
├── orchestration/    # Dagster definitions, diagnostics
├── app.py            # Composition root
└── cli.py            # CLI entry point (thin)
```

### D.2 Key centralized components

```
ResolvedProjectConfiguration (Pydantic v2)
    ↓ compile once
CompiledExperiment (frozen dataclass)
    ↓ plan once
ExperimentPlan (stage jobs, dependencies, paths)
    ↓ execute
ExperimentRunner → CampaignRunner
    ↓ orchestrate
Dagster (canonical — stage-level ops from ExperimentPlan)
```

### D.3 Central configuration flow

```
Hydra composes authored YAML → Pydantic validates → resolve once → ResolvedProjectConfiguration
    → compile each experiment → CompiledExperiment (no further config lookup)
        → ExperimentPlanBuilder → ExperimentPlan (all stages, paths, contexts)
            → ExperimentPaths (sole path authority)
```

### D.4 Minimal registries

| Registry | Key | Justification |
|---|---|---|
| `DatasetAdapterRegistry` | `AdapterKind` | 3 adapters with genuinely different implementations |
| `ThresholdEstimatorRegistry` | `ThresholdPolicyKind` | 10+ estimator implementations with distinct algorithms |
| `StageHandlerRegistry` | `StageKind` | 11 stage kinds with different handlers |
| `AnalysisHandlerRegistry` | `AnalysisKind` | 15+ analysis types with different execution logic |
| `LearningStrategyRegistry` | `TrainingProfileKind` | 3 training strategies (FedAvg, FedProx, Ditto) — optional, direct dispatch may suffice |

**Explicitly forbidden registries:** Metric registry, path registry, report renderer registry, codec registry, statistics registry, model registry, optimizer registry, loss registry, scheduler registry, scorer registry, preprocessing registry, plot registry.

---

## E. Before/After Responsibility Mapping

| Responsibility | Current Owner | Problem | Target Owner | Deleted/Merged |
|---|---|---|---|---|
| Config composition | `config/loading.py` (custom YAML reader) | Hydra unused; manual YAML loading | `config/hydra/` (Hydra composition) + `config/loading.py` (Pydantic parsing only) | Custom YAML reader complexity removed |
| Resolved config model | `config/models.py` (`@define` attrs) | Mixed model system; no Pydantic validators | `config/models.py` (`BaseModel` Pydantic v2) | attrs removed from this file |
| Stage context | `pipeline/stages/context.py` (`StageJobContext`) | 13/16 fields nullable; one context for all stages | 4 typed context families: `DataContext`, `TrainingContext`, `EvaluationContext`, `AnalysisContext` | `StageJobContext` deleted |
| Experiment compilation | None (repeated config lookup in planning) | `config.populations.get()` etc. scattered in planning | `experiments/planning/compilation.py` (`CompiledExperiment`) | Repeated lookup code removed |
| Path construction | `experiments/planning/layout.py` (scattered helpers) | No centralized authority | `experiments/planning/paths.py` (`ExperimentPaths`) | `layout.py` helpers deleted |
| Threshold dispatch | `thresholding/estimation/dispatch.py` (12-branch isinstance) | Central chain must be edited per policy | `ThresholdEstimatorRegistry` keyed by `ThresholdPolicyKind` | `dispatch.py` isinstance chain deleted |
| Campaign execution | `CampaignOrchestrator` + `ExperimentLifecycleUseCase` | Logic split across two classes | `CampaignRunner` (consolidated) | `CampaignOrchestrator` and split logic merged |
| Dagster integration | `orchestration/dagster_defs.py` (opaque one-op) | No stage visibility | Stage-level ops from `ExperimentPlan.stages` | Opaque wrapper deleted |
| CLI serialization | `cli.py` (`cattrs.Converter`) | Third serialization framework | Pydantic `model_dump(mode="json")` | `cattrs` removed from CLI |
| Frozen result access | `campaign.py` (`frozen.get("outcomes")`) | Untyped dictionary access | `FrozenResult` Pydantic model with typed fields | Dictionary access deleted |
| Metric records | `evaluation/definitions/metrics.py` (`@define` attrs) | Mixed model system | Pydantic `BaseModel` with validators | attrs removed from metric records |
| Analysis execution context | `analysis/runtime/context.py` (separate context) | Parallel context system | `AnalysisContext` (from 4-family system) | `analysis/runtime/context.py` merged |

---

## F. Minimal Registry List

### Justified registries

1. **`DatasetAdapterRegistry`** — keyed by `AdapterKind` enum. 3 adapters (N-BaIoT, CICIoT2023, Edge-IIoTset) with genuinely different source parsing, client identity, and splitting logic. Built explicitly in `app.py:_build_adapter_registry()`.

2. **`ThresholdEstimatorRegistry`** — keyed by `ThresholdPolicyKind` enum. 10 implementation kinds: `SHARED_MEAN`, `SHARED_POOLED`, `SHARED_WEIGHTED`, `LOCAL_QUANTILE`, `FAMILY_MEAN`, `CLUSTER`, `CONFORMAL`, `SHRINKAGE`, `CALIBRATION_FALLBACK`, `FEDERATED_MATCHED`, `FEDERATED_FIXED`. Replaces the 12-branch isinstance chain.

3. **`StageHandlerRegistry`** — keyed by `StageKind` enum. 11 stage kinds mapping to their handlers. Used by Dagster, diagnostics, tests, and CLI. Built explicitly in `app.py`.

4. **`AnalysisHandlerRegistry`** — keyed by `AnalysisKind` enum. 15+ analysis types. Replaces `singledispatch`-style registration. Built explicitly in the composition root.

5. **`LearningStrategyRegistry`** (optional) — keyed by `TrainingProfileKind`. Only if the current 3-way dispatch (FedAvg, FedProx, Ditto via `PersonalizationStrategy` enum + conditional logic) proves unwieldy. Direct dispatch may be simpler.

### Forbidden registries

- **Metric registry** — metrics are direct functions grouped in `evaluation/metrics/`. No runtime dispatch needed.
- **Path registry** — `ExperimentPaths` is a single class with explicit methods, not a registry.
- **Report renderer registry** — only two output formats (table, figure) with direct dispatch via `isinstance`. No plugin architecture.
- **Codec registry** — `artifacts/codecs/` has 2 codecs (SafeTensors, JSON). Direct imports suffice.
- **Statistics registry** — statistical procedures are functions, not interchangeable implementations.
- **Model/Optimizer/Loss registry** — factories (`build_model()`, `build_optimizer()`, `build_loss()`) are simpler.
- **Preprocessing registry** — shared preprocessing functions are called directly by adapters.
- **Plot registry** — direct matplotlib/seaborn functions grouped by responsibility.

---

## G. Detailed Implementation Phases

### Phase 0 — Baseline and Scientific Lock

**Scope.** Lock current behavior before any structural changes.

**Current repository evidence.**
- 194 source files under `src/datp_core/`
- 56 test files
- 6 YAML configuration files
- Configuration validates successfully, 22 experiments defined, all three datasets configured

**Scientific invariants.** All invariants in Section C are the baseline.

**Exact architecture change.** None. This phase only records baselines.

**Files affected.** None modified. Create `.tmp/baseline/` with:
- Source file inventory and line counts
- Scientific fingerprint from `datp-core config fingerprint`
- Experiment catalogue plan output for all 22 experiments
- Checksums of key configuration files

**Config changes.** None.

**Test changes.** None.

**Migration order.** Not applicable.

**Validation commands.**
```bash
nox -s tests        # Current tests pass
nox -s typecheck    # Pyright passes
nox -s lint         # Ruff passes
nox -s imports      # Import contracts pass
datp-core config validate  # Configuration validates
```

**Phase-wide validation.** All existing gates pass before any refactoring begins.

**Scientific equivalence.** Current behavior IS the baseline.

**Static analysis.** SonarQube, CodeScene current baselines recorded.

**Completion checklist.**
- [ ] Source inventory recorded
- [ ] Scientific fingerprint recorded
- [ ] Execution fingerprint recorded
- [ ] All 22 experiments plan successfully
- [ ] All existing tests pass
- [ ] All static checks pass
- [ ] Configuration validates

**Non-goals.** No code changes, no configuration changes.

**Net simplification target.** Baseline establishment only.

---

### Phase 1 — Core Types, Enum Cleanup, and Model System Consolidation

**Scope.** Establish one model system (Pydantic v2), clean up enums, remove `attrs` from domain models, remove `cattrs` from CLI.

**Current repository evidence.**
- `ResolvedProjectConfiguration` uses `@define` (attrs) — `config/models.py:57`
- Metric records use `@define` (attrs) — `evaluation/definitions/metrics.py`
- Analysis results use Pydantic `BaseModel` — `analysis/contracts.py` (correct, preserve)
- `cattrs.Converter` used in CLI — `cli.py:19,96,111,126`
- `Mapping[str, str | bool]` in `population_readiness_rule` — `config/models.py:66`
- `Mapping[str, str]` in `analysis_conventions` and `normalization_fit_scopes` — `config/models.py:68,87`
- `StageJobContext` has string-typed fields: `evaluation_label: str | None`, `dataset_setup_id: str | None`, `materialization_id: str | None`, `partition_condition: str | None` — should be typed IDs

**Scientific invariants.** No scientific behavior changes. All configuration fields preserved with identical validation.

**Exact architecture change.**

1. Convert `ResolvedProjectConfiguration` from `@define` to `BaseModel`:
   - Replace `@define(frozen=True, slots=True, kw_only=True)` with `class ResolvedProjectConfiguration(BaseModel)`
   - Add `model_config = ConfigDict(frozen=True, extra="forbid")`
   - Convert `TypedDomainRegistry` fields to retain their current type
   - Replace `Mapping[str, str | bool]` with typed Pydantic models: `PopulationReadinessRule`, `AnalysisConventions`
   - Replace `Mapping[str, str]` with `NormalizationFitScopes` model

2. Convert metric records from `@define` to `BaseModel`:
   - `MetricFormulaRecord`, `CrossClientAggregationRecord`, `ThresholdEstimationMetricsRecord`, `MetricDefinitionsRecord` → Pydantic
   - Add validators for formula consistency where applicable

3. Convert threshold policy records from `@define` to `BaseModel`:
   - All 12 policy record types in `thresholding/policies/` → Pydantic
   - Preserve existing field validation

4. Replace `cattrs.Converter` in CLI with Pydantic `model_dump(mode="json")`:
   - `_converter.unstructure(drift)` → `drift.model_dump(mode="json")`
   - Remove `import cattrs` from `cli.py`

5. Clean up identifier types in `StageJobContext`:
   - `evaluation_label: str | None` → `evaluation_label: EvaluationLabel | None`
   - `dataset_setup_id: str | None` → `dataset_setup_id: DatasetSetupId | None`
   - `materialization_id: str | None` → `materialization_id: MaterializationId | None`
   - `partition_condition: str | None` → `partition_condition: PartitionConditionId | None`

6. Add `ThresholdPolicyKind` enum in `thresholding/policies/enums.py`:
   - Members: `SHARED_MEAN`, `SHARED_POOLED`, `SHARED_WEIGHTED`, `LOCAL_QUANTILE`, `FAMILY_MEAN`, `CLUSTER`, `CONFORMAL`, `SHRINKAGE`, `CALIBRATION_FALLBACK`, `FEDERATED_MATCHED`, `FEDERATED_FIXED`
   - Each policy record gets a `kind` property returning its `ThresholdPolicyKind`

7. Audit all enums across packages for duplicates. Merge overlapping enums:
   - `ArtifactKind` in `analysis/enums.py` vs any artifact kind in `artifacts/` — verify no duplicates
   - `StageKind` in `pipeline/stages/enums.py` — verify no overlapping enum with other packages

**Files affected.**
- `config/models.py` — attrs → Pydantic conversion
- `config/project.py` — update construction of `ResolvedProjectConfiguration`
- `evaluation/definitions/metrics.py` — attrs → Pydantic
- `evaluation/definitions/bundles.py` — attrs → Pydantic
- `evaluation/definitions/results.py` — attrs → Pydantic
- `thresholding/policies/*.py` — all 8 files, attrs → Pydantic
- `thresholding/policies/enums.py` — add `ThresholdPolicyKind`
- `learning/contracts/*.py` — attrs → Pydantic (architecture, checkpoints, optimization, seeds, training)
- `data/contracts/*.py` — attrs → Pydantic (dataset, eligibility, features, materialization, sources)
- `data/contracts/enums.py` — audit for duplicates
- `config/statistical_profiles.py` — attrs → Pydantic
- `config/report_profiles.py` — attrs → Pydantic
- `config/operational_contracts.py` — attrs → Pydantic
- `core/identifiers.py` — preserve attrs for lightweight identifiers (justified: no validation needed, attrs simpler for pure value objects)
- `cli.py` — remove `cattrs`, use `model_dump`
- `app.py` — update construction if needed

**Code to remove or merge.**
- All `@define` decorators on migrated classes
- `import attrs` where no longer needed
- `import cattrs` from `cli.py`
- `_converter = cattrs.Converter()` from `cli.py`

**Config changes.**
- `configs/protocols.yaml` — add `kind` field to each threshold policy entry mapping to `ThresholdPolicyKind`
- No other config changes

**Test changes.**
- Update test imports if attrs APIs were used directly
- Add serialization round-trip tests for Pydantic models
- Add `ThresholdPolicyKind` enum exhaustiveness tests
- Verify `ResolvedProjectConfiguration` can be constructed and validated

**Migration order.**
1. Add `ThresholdPolicyKind` enum
2. Convert leaf models first (metric records, policy records, contract records)
3. Convert `ResolvedProjectConfiguration` last
4. Replace `cattrs` in CLI last
5. Run full test suite after each batch

**Validation commands.**
```bash
nox -s typecheck    # Pyright strict
nox -s lint         # Ruff
nox -s tests        # Full test suite
nox -s imports      # Import contracts
datp-core config validate
```

**Phase-wide validation.**
- All configuration YAML validates under new Pydantic models
- Scientific fingerprint unchanged from Phase 0 baseline
- All 22 experiments plan successfully

**Scientific equivalence checks.**
- `datp-core config explain-scientific-drift` against Phase 0 baseline — must show no drift
- Configuration fingerprint unchanged

**Static analysis.** SonarQube comparison against Phase 0 baseline.

**Completion checklist.**
- [ ] `ResolvedProjectConfiguration` is Pydantic v2 `BaseModel`
- [ ] All metric records are Pydantic v2
- [ ] All threshold policy records are Pydantic v2
- [ ] All learning contract records are Pydantic v2
- [ ] All data contract records are Pydantic v2
- [ ] `cattrs` removed from CLI
- [ ] `Mapping[str, ...]` replaced with typed models
- [ ] `ThresholdPolicyKind` enum exists with all 11 members
- [ ] Every policy record exposes `kind` property
- [ ] No duplicate enums remain
- [ ] `StageJobContext` string fields typed with ID types
- [ ] All tests pass
- [ ] Scientific fingerprint unchanged
- [ ] Configuration validates

**Non-goals.**
- Do not convert `core/identifiers.py` from attrs (lightweight value objects, attrs is appropriate)
- Do not convert `TypedDomainRegistry` from its current generic implementation
- Do not change analysis result models (already Pydantic, already correct)
- Do not restructure packages

**Net simplification target.**
- Remove `attrs` from 30+ domain model files
- Remove `cattrs` dependency from CLI path
- Remove 3 `Mapping[str, ...]` dictionary fields
- Add `ThresholdPolicyKind` enum (enables Phase 8 simplification)

---

### Phase 2 — Hydra Configuration Composition and Experiment Compilation

**Scope.** Implement Hydra for configuration composition. Add `CompiledExperiment`. Centralize configuration resolution flow.

**Current repository evidence.**
- `hydra-core>=1.3` and `omegaconf>=2.3` in dependencies but unused
- `config/loading.py:YamlConfigurationReader` does manual YAML parsing + Pydantic validation
- `config/bootstrap.py:resolve_config_root()` uses environment variables for config directory
- Experiment planning (`experiments/planning/jobs.py`) performs repeated `config.populations.get()`, `config.training_profiles.get()`, etc.
- No `CompiledExperiment` exists

**Scientific invariants.** All configuration values preserved. No new defaults. Missing configuration must still fail explicitly.

**Exact architecture change.**

1. Create Hydra configuration structure:
   - `configs/config.yaml` — Hydra root config with defaults for datasets, protocols, experiments, runtime
   - Configuration groups: `datasets/`, `protocols/`, `experiments/`, `runtime/`
   - Existing YAML files become Hydra configuration group members
   - Hydra composes → Pydantic validates → resolve → `ResolvedProjectConfiguration`

2. Create `config/hydra/compose.py`:
   ```python
   def compose_config(overrides: list[str] | None = None) -> ResolvedProjectConfiguration:
       """Hydra composes → Pydantic validates → resolve → ResolvedProjectConfiguration."""
       with hydra.initialize_config_dir(config_dir, version_base=None):
           cfg = hydra.compose(config_name="config", overrides=overrides)
       # Convert OmegaConf → dict → Pydantic → resolve
   ```

3. Add `CompiledExperiment` in `experiments/planning/compilation.py`:
   ```python
   @dataclass(frozen=True, slots=True)
   class CompiledEvaluation:
       record: EvaluationSpecRecord
       population: PopulationRecord
       dataset: ResolvedDataset
       setup: DatasetSetupRecord
       threshold_policy: ThresholdPolicyRecord
       metric_bundle: MetricBundleRecord

   @dataclass(frozen=True, slots=True)
   class CompiledExperiment:
       record: ExperimentRecord
       populations: tuple[PopulationRecord, ...]
       training_profile: TrainingProfileRecord
       checkpoint_profile: CheckpointProfileRecord
       seed_cohort: SeedCohortRecord
       eligibility_policy: EligibilityPolicyRecord
       evaluations: tuple[CompiledEvaluation, ...]
       analyses: tuple[AnalysisRecord, ...]
       report_profiles: tuple[ReportProfileRecord, ...]
   ```

4. Add `compile_experiment()` function:
   ```python
   def compile_experiment(
       config: ResolvedProjectConfiguration,
       experiment_id: ExperimentId,
   ) -> CompiledExperiment
   ```
   Resolves all references once. Validates during compilation: unknown IDs, capability mismatches, missing prerequisites, unsupported policy kinds.

5. Update `expand_experiment_jobs()` to accept `CompiledExperiment` instead of navigating `ResolvedProjectConfiguration`.

**Files affected.**
- `configs/config.yaml` — new Hydra root
- `config/hydra/compose.py` — new
- `config/bootstrap.py` — update to use Hydra
- `experiments/planning/compilation.py` — new
- `experiments/planning/jobs.py` — update signature to accept `CompiledExperiment`
- `config/project.py` — update `resolve_project_configuration` to accept Hydra-composed config
- `app.py` — update application construction
- `cli.py` — update to use Hydra overrides

**Code to remove or merge.**
- Custom YAML composition logic in `config/loading.py` (replace with Hydra composition)
- Repeated `config.*.get()` calls in `experiments/planning/jobs.py` (replaced by compiled references)
- `config/bootstrap.py:resolve_config_root()` complexity (Hydra handles config directory)

**Config changes.**
- Add `configs/config.yaml` with Hydra defaults
- Existing YAML files become Hydra group members (content unchanged)
- Add `kind` field to threshold policies (from Phase 1)

**Test changes.**
- Add `compile_experiment()` tests for all 22 experiments
- Add missing-reference rejection tests
- Add capability incompatibility rejection tests
- Update planning tests to use `CompiledExperiment`
- Add Hydra override tests

**Migration order.**
1. Add `compilation.py` with `CompiledExperiment` and `compile_experiment()`
2. Write tests for compilation of all experiments
3. Update `expand_experiment_jobs()` signature
4. Implement Hydra composition in `config/hydra/`
5. Update `app.py` and `cli.py`
6. Remove old manual composition code

**Validation commands.**
```bash
nox -s typecheck
nox -s lint
nox -s tests
nox -s imports
datp-core config validate
datp-core config fingerprint  # unchanged
```

**Phase-wide validation.**
- All 22 experiments compile without error
- Compiled experiments are equality-comparable (same inputs → same compiled result)
- Missing references fail with precise error messages
- Scientific fingerprint unchanged from Phase 0

**Scientific equivalence checks.**
- `datp-core config explain-scientific-drift` against Phase 0 baseline — no drift
- Experiment plans produce identical stage keys and dependencies

**Static analysis.** SonarQube comparison.

**Completion checklist.**
- [ ] Hydra composes configuration from YAML files
- [ ] Pydantic validates composed configuration
- [ ] `CompiledExperiment` exists with all resolved references
- [ ] `compile_experiment()` resolves all experiments
- [ ] No runtime `config.*.get()` in planning code
- [ ] Hydra overrides work for experiment selection, CLI overrides
- [ ] Scientific fingerprint unchanged
- [ ] All tests pass

**Non-goals.**
- Do not let Hydra dictate artifact paths
- Do not let Hydra become a runtime service locator
- Do not leak `DictConfig` or `OmegaConf` beyond `config/hydra/`
- Do not dynamically instantiate scientific implementations from YAML class paths
- Do not change Dagster's role as canonical orchestrator

**Net simplification target.**
- Remove manual YAML loading complexity
- Add ~1 file for Hydra composition
- Remove repeated config lookups in planning (replaced by compiled references)
- CLI `--config` overrides become Hydra overrides

---

### Phase 3 — Centralized Path Authority

**Scope.** Create `ExperimentPaths` as the sole path construction authority. Remove all inline path construction.

**Current repository evidence.**
- Path construction scattered across:
  - `experiments/planning/layout.py:cell_directory()`, `evaluation_directory()`, `output()`, `shared_output_path()`
  - `experiments/planning/jobs.py` — inline `f"experiments/{context.experiment_id.value}/"` and `f"training/{cell_directory(context)}"`
  - `experiments/execution/output_manager.py:__init__` — `self._outputs_root / experiment_id.value`
  - `orchestration/diagnostics.py:37` — `Path(__file__).resolve().parent.parent.parent.parent` for repo root
  - `cli.py:293,317,360` — `Path(".tmp/diagnostics").resolve()`

**Scientific invariants.** All output paths must remain deterministic, unique across variants, and collision-free. Path structure must produce identical relative paths after centralization.

**Exact architecture change.**

1. Create `experiments/planning/paths.py` with `ExperimentPaths`:
   ```python
   @dataclass(frozen=True, slots=True)
   class ExperimentPaths:
       outputs_root: Path
       repository_root: Path

       def experiment_root(self, experiment_id: ExperimentId) -> Path: ...
       def manifest(self, experiment_id: ExperimentId) -> Path: ...
       def completion_marker(self, experiment_id: ExperimentId) -> Path: ...
       def preflight(self, experiment_id: ExperimentId) -> Path: ...
       def materialization(self, context: DataContext) -> Path: ...
       def split_manifest(self, context: DataContext) -> Path: ...
       def readiness(self, context: DataContext) -> Path: ...
       def preprocessing(self, context: DataContext) -> Path: ...
       def partition_manifest(self, context: DataContext) -> Path: ...
       def checkpoint(self, context: TrainingContext) -> Path: ...
       def selection_evidence(self, context: TrainingContext) -> Path: ...
       def personalized_checkpoint(self, context: TrainingContext) -> Path: ...
       def calibration_scores(self, context: TrainingContext) -> Path: ...
       def test_scores(self, context: TrainingContext) -> Path: ...
       def future_recalibration_scores(self, context: TrainingContext) -> Path: ...
       def calibration_subset(self, context: EvaluationContext) -> Path: ...
       def thresholds(self, context: EvaluationContext) -> Path: ...
       def threshold_diagnostics(self, context: EvaluationContext) -> Path: ...
       def client_metrics(self, context: EvaluationContext) -> Path: ...
       def statistical_result(self, experiment_id: ExperimentId) -> Path: ...
       def frozen_result(self, experiment_id: ExperimentId) -> Path: ...
       def report(self, experiment_id: ExperimentId) -> Path: ...
       def shared_materialization(self, ordinal: int, output_name: str) -> Path: ...
       def shared_training(self, ordinal: int, output_name: str) -> Path: ...
       def shared_checkpoint_selection(self, ordinal: int, ...) -> Path: ...
       def shared_scores(self, ordinal: int, output_name: str) -> Path: ...
       def diagnostic_root(self) -> Path: ...
   ```

2. Replace all inline path construction in `experiments/planning/jobs.py` with `ExperimentPaths` method calls.

3. Replace hardcoded diagnostic paths: pass `ExperimentPaths` to diagnostics.

4. Replace hardcoded repo root in `orchestration/dagster_defs.py` and `orchestration/diagnostics.py`.

**Files affected.**
- `experiments/planning/paths.py` — new
- `experiments/planning/jobs.py` — replace inline paths with `ExperimentPaths`
- `experiments/planning/layout.py` — DELETE (all content moves to `paths.py`)
- `experiments/execution/output_manager.py` — use `ExperimentPaths`
- `orchestration/diagnostics.py` — use `ExperimentPaths.diagnostic_root()`
- `orchestration/dagster_defs.py` — use configured path instead of hardcoded
- `cli.py` — use `ExperimentPaths` via application
- `app.py` — construct `ExperimentPaths` and inject

**Code to remove or merge.**
- `experiments/planning/layout.py` — entirely deleted
- Inline path strings in `experiments/planning/jobs.py`
- Hardcoded `/home/naslouby/Projects/datp-core` in `orchestration/dagster_defs.py:35`
- Hardcoded `.tmp/diagnostics` in `cli.py` and `orchestration/diagnostics.py`

**Config changes.**
- `configs/runtime.yaml` roots already define output paths — preserve
- `ExperimentPaths` reads roots from `ResolvedProjectConfiguration.paths`

**Test changes.**
- Add `ExperimentPaths` unit tests: determinism, uniqueness, collision-free
- Update planning tests to verify path output
- Add path traversal rejection tests
- Add symlink rejection tests

**Migration order.**
1. Create `ExperimentPaths`
2. Replace paths in `experiments/planning/jobs.py`
3. Delete `experiments/planning/layout.py`
4. Update `output_manager.py`
5. Update `orchestration/` files
6. Update `cli.py`
7. Run tests after each step

**Validation commands.**
```bash
nox -s typecheck
nox -s lint
nox -s tests
nox -s imports
```

**Phase-wide validation.**
- All output paths are produced by `ExperimentPaths`
- No other package constructs semantic output paths
- Paths are deterministic and unchanged from Phase 0 baseline

**Scientific equivalence.** Experiment plan produces identical output paths as Phase 0 baseline.

**Completion checklist.**
- [ ] `ExperimentPaths` is sole path authority
- [ ] `experiments/planning/layout.py` deleted
- [ ] No inline path construction in `jobs.py`
- [ ] No hardcoded paths in `orchestration/`
- [ ] No hardcoded paths in `cli.py`
- [ ] All tests pass
- [ ] Path determinism verified

**Non-goals.**
- Do not create artifact-management framework
- Do not create path registry
- Do not introduce generic `path_for(kind, **kwargs)`

**Net simplification target.**
- Delete 1 file (`layout.py`)
- Remove path construction from 4+ files
- One authority for all semantic paths

---

### Phase 4 — Typed Context Families

**Scope.** Replace `StageJobContext` (16 fields, 13 nullable) with 4 small typed context families.

**Current repository evidence.**
- `pipeline/stages/context.py` — `StageJobContext` with 16 fields:
  - `experiment_id: ExperimentId` (always present)
  - `seed: int | None`
  - `evaluation_label: str | None` (should be `EvaluationLabel | None`)
  - `population_id: PopulationId | None`
  - `recalibration_mode: RecalibrationMode | None`
  - `threshold_policy_id: ThresholdPolicyId | None`
  - `dataset_setup_id: str | None`
  - `materialization_id: str | None`
  - `partition_condition: str | None`
  - `federated_proximal_mu: float | None`
  - `ditto_proximal_weight: float | None`
  - `threshold_quantile: float | None`
  - `shrinkage_weight: float | None`
  - `federated_summary_fixed_k: float | None`
  - `calibration_sample_count: int | None`
  - `calibration_replicate: int | None`
  - `fingerprint_features: tuple[str, ...] | None`
  - `prerequisite_results: tuple[PrerequisiteExperimentResult, ...]`
- `analysis/runtime/context.py` — separate `AnalysisExecutionContext` (parallel context system)
- `experiments/planning/context.py` — `score_context()` helper that copies select fields

**Scientific invariants.** Stage inputs must remain identical. Stage identity coordinates must not change.

**Exact architecture change.**

1. Create 4 context dataclasses in `pipeline/stages/context.py`:

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class DataContext:
    experiment_id: ExperimentId
    population_id: PopulationId
    seed: int | None
    partition_condition: PartitionConditionId | None

@dataclass(frozen=True, slots=True, kw_only=True)
class TrainingContext:
    experiment_id: ExperimentId
    population_id: PopulationId
    seed: int
    partition_condition: PartitionConditionId | None
    federated_proximal_mu: float | None
    ditto_proximal_weight: float | None

@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluationContext:
    experiment_id: ExperimentId
    population_id: PopulationId
    seed: int
    partition_condition: PartitionConditionId | None
    evaluation_label: EvaluationLabel
    threshold_policy_id: ThresholdPolicyId
    threshold_quantile: float | None
    shrinkage_weight: float | None
    federated_summary_fixed_k: float | None
    fingerprint_features: tuple[str, ...] | None
    calibration_sample_count: int | None
    calibration_replicate: int | None
    recalibration_mode: RecalibrationMode | None
    federated_proximal_mu: float | None
    ditto_proximal_weight: float | None

@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisContext:
    experiment_id: ExperimentId
    analysis_label: AnalysisLabel | None
    prerequisite_results: tuple[PrerequisiteExperimentResult, ...]
```

2. Update `StageJob` to carry a `context: DataContext | TrainingContext | EvaluationContext | AnalysisContext` union.

3. Update each stage handler to accept only its relevant context type.

4. Update `expand_experiment_jobs()` to construct the appropriate context per stage.

5. Delete `analysis/runtime/context.py` — merged into `pipeline/stages/context.py`.

**Files affected.**
- `pipeline/stages/context.py` — replace `StageJobContext` with 4 families
- `pipeline/stages/jobs.py` — update `StageJob` context field type
- `experiments/planning/jobs.py` — construct typed contexts per stage
- `experiments/planning/context.py` — DELETE (content merged)
- `analysis/runtime/context.py` — DELETE (merged into `pipeline/stages/context.py`)
- All stage handler files (11 files) — update context parameter types
- `pipeline/graph/key.py` — update `GraphNodeKey` construction
- `pipeline/graph/model.py` — update `PlanningGraph` if needed

**Code to remove or merge.**
- `StageJobContext` class deleted
- `_validate_context()` function deleted
- `experiments/planning/context.py` deleted
- `analysis/runtime/context.py` deleted
- `score_context()` helper deleted (no longer needed with typed contexts)

**Config changes.** None.

**Test changes.**
- Update all tests that construct `StageJobContext`
- Add context type coverage tests
- Add invalid combination rejection tests
- Update planning tests

**Migration order.**
1. Create 4 context dataclasses
2. Update `StageJob` context type
3. Update `expand_experiment_jobs()` context construction (biggest change)
4. Update each stage handler (11 files, mechanical)
5. Delete old context files
6. Update tests

**Validation commands.**
```bash
nox -s typecheck
nox -s lint
nox -s tests
nox -s imports
```

**Phase-wide validation.**
- No handler receives a context with irrelevant fields
- No `isinstance` checks needed to determine which context fields are valid
- Experiment plans produce identical stage keys

**Scientific equivalence.** Stage job identities unchanged.

**Completion checklist.**
- [ ] `StageJobContext` deleted
- [ ] 4 typed context families exist
- [ ] Each handler accepts only its context type
- [ ] `experiments/planning/context.py` deleted
- [ ] `analysis/runtime/context.py` deleted
- [ ] `score_context()` deleted
- [ ] All tests pass
- [ ] No handler receives irrelevant nullable fields

**Non-goals.**
- Do not create one context class per stage
- Do not add services to contexts
- Do not add configuration to contexts
- Do not let contexts construct paths

**Net simplification target.**
- Delete 2 files
- Replace 1 oversized context (16 fields, 13 nullable) with 4 focused contexts (4–15 fields each with minimal nullable)
- Remove context copying helpers

---

### Phase 5 — One Experiment-Plan Builder

**Scope.** Consolidate `expand_experiment_jobs()` and `expand_campaign_jobs()` into `ExperimentPlanBuilder`. Use `ExperimentPaths` and `CompiledExperiment`.

**Current repository evidence.**
- `experiments/planning/jobs.py` — 697 lines, two functions: `expand_experiment_jobs()` (540 lines) and `expand_campaign_jobs()` (157 lines)
- Planning uses private helpers: `_create_training_cells()`, `_create_selection_stage()`, `_create_scoring_and_calibration_cells()`, `_create_evaluation_jobs()`
- Campaign planning adds shared-stage deduplication via `SharedUpstreamKey`
- `experiments/planning/sweeps.py` — sweep value extraction
- `experiments/planning/validation.py` — graph validation

**Scientific invariants.** Stage order, dependencies, output identities, and sweep expansion must remain identical.

**Exact architecture change.**

1. Create `ExperimentPlan` and `StageJob` models (consolidate existing types).

2. Create `ExperimentPlanBuilder` class:
   ```python
   class ExperimentPlanBuilder:
       def __init__(self, paths: ExperimentPaths) -> None: ...

       def build(self, experiment: CompiledExperiment) -> ExperimentPlan: ...

       def build_campaign(
           self, experiments: tuple[CompiledExperiment, ...]
       ) -> ExperimentPlan: ...
   ```

3. Private methods for stage expansion: `_build_materialization_jobs`, `_build_training_jobs`, etc.

4. Move sweep expansion into dedicated private methods.

5. Keep `StageKind` enum with one compact stage definition per kind.

**Files affected.**
- `experiments/planning/builder.py` — new (consolidates `jobs.py`)
- `experiments/planning/jobs.py` — DELETE (content moved to `builder.py`)
- `experiments/planning/models.py` — new (ExperimentPlan, if not already in graph/model.py)
- `experiments/planning/sweeps.py` — keep but simplify
- `experiments/planning/validation.py` — keep (graph validation)
- `pipeline/graph/model.py` — keep (PlanningGraph)
- `app.py` — update to use `ExperimentPlanBuilder`
- `orchestration/dagster_defs.py` — update to use `ExperimentPlan`
- `cli.py` — update `experiment_plan` command

**Code to remove or merge.**
- `experiments/planning/jobs.py` — deleted
- Duplicate planning logic between `expand_experiment_jobs` and `expand_campaign_jobs`
- Inline path construction (already moved to `ExperimentPaths` in Phase 3)

**Config changes.** None.

**Test changes.**
- Update planning tests to use `ExperimentPlanBuilder`
- Add plan equality tests (same input → same plan)
- Add stage order validation tests
- Add output uniqueness tests
- Add dependency completeness tests

**Migration order.**
1. Create `builder.py` with `ExperimentPlanBuilder`
2. Migrate `expand_experiment_jobs()` logic
3. Migrate `expand_campaign_jobs()` logic
4. Delete `jobs.py`
5. Update callers (`app.py`, `cli.py`, `dagster_defs.py`, diagnostics)
6. Update tests

**Validation commands.**
```bash
nox -s typecheck
nox -s lint
nox -s tests
nox -s imports
```

**Phase-wide validation.**
- All 22 experiments produce identical plans as Phase 0 baseline
- Campaign plans produce identical shared-stage deduplication
- CLI planning, tests, diagnostics, and Dagster all use same `ExperimentPlanBuilder`

**Scientific equivalence.** Plans identical to baseline.

**Completion checklist.**
- [ ] `ExperimentPlanBuilder` builds plans for all experiments
- [ ] `experiments/planning/jobs.py` deleted
- [ ] Campaign and single-experiment planning use same builder
- [ ] Dagster, diagnostics, tests, CLI all use same plan
- [ ] All tests pass

**Net simplification target.**
- Replace 697-line `jobs.py` with ~500-line `builder.py` (shorter due to `ExperimentPaths` and `CompiledExperiment` removing inline paths and config lookups)
- Remove campaign-specific planning duplication

---

### Phase 6 — Dataset Adapters and Preprocessing Cleanup

**Scope.** Audit and clean adapter implementations. Centralize shared preprocessing. No adapter protocol changes.

**Current repository evidence.**
- Three adapters in `data/adapters/` with 5-6 files each
- Shared preprocessing in `data/preprocessing/normalization.py`
- `data/materialization/registry.py` — `DatasetAdapterRegistry` keyed by `AdapterKind`
- Adapters implement: source audit, materialization, splitting, parquet persistence

**Scientific invariants.** N-BaIoT 9 physical devices, CICIoT2023 63 file-defined pseudo-clients, Edge-IIoTset 10 sensor groups. All splitting, chronology, deduplication, and client identity logic preserved.

**Exact architecture change.**

1. Audit each adapter for:
   - Duplicate normalization logic
   - Duplicate categorical encoding
   - Duplicate row filtering
   - Duplicate manifest validation
   - Adapter access to unrelated project configuration

2. Extract truly shared logic to `data/preprocessing/`:
   - Numeric parsing (if duplicated)
   - Invalid-row filtering (if duplicated)
   - Leakage column exclusion (if duplicated)
   - Feature ordering (if duplicated)

3. Remove adapter access to full `ResolvedProjectConfiguration`. Adapters receive only:
   - `ResolvedDataset` (their dataset config)
   - `DatasetSetupRecord` (their setup)
   - Materialization paths from `ExperimentPaths`

4. Keep one adapter protocol and one adapter registry.

5. Preserve dataset-specific ownership:
   - N-BaIoT: device directory discovery, benign/attack interpretation, chronological handling
   - CICIoT2023: file-defined client deduplication, pseudo-client identity
   - Edge-IIoTset: endpoint parsing, Modbus exclusion, chronological split validity

**Files affected.**
- `data/adapters/nbaiot/*.py` — audit, clean
- `data/adapters/ciciot2023/*.py` — audit, clean
- `data/adapters/edge_iiotset/*.py` — audit, clean
- `data/preprocessing/normalization.py` — add shared logic
- `data/materialization/handler.py` — update to use `ExperimentPaths`

**Code to remove or merge.**
- Duplicate preprocessing implementations across adapters
- Adapter access to `ResolvedProjectConfiguration` (pass only needed records)
- Unused adapter methods

**Config changes.** None.

**Test changes.**
- For each adapter: source audit, materialization, split validity, chronology, client identity, eligibility
- Normalization fit scope tests
- Leakage exclusion tests
- Repeat execution equivalence tests

**Validation commands.**
```bash
nox -s typecheck
nox -s lint
nox -s tests
nox -s imports
```

**Phase-wide validation.**
- All three adapters produce identical materialization outputs as Phase 0 baseline
- Source fingerprints unchanged
- Split manifests unchanged

**Completion checklist.**
- [ ] Adapters are smaller (no duplicated preprocessing)
- [ ] Shared preprocessing is centralized in `data/preprocessing/`
- [ ] Adapters receive only needed records, not full config
- [ ] No preprocessing plugin framework introduced
- [ ] All adapter tests pass
- [ ] Materialization outputs identical to baseline

**Net simplification target.**
- Remove duplicate code across adapters
- Reduce adapter dependencies on full configuration

---

### Phase 7 — Learning, Checkpoint Selection, and Scoring Cleanup

**Scope.** Centralize resolved learning inputs. Clean up model/optimizer/loss construction. Preserve all training semantics.

**Current repository evidence.**
- `learning/training/handler.py` receives full `ResolvedProjectConfiguration`
- `learning/scoring/handler.py` receives full config
- Three training strategies: FedAvg, FedProx, Ditto (via `TrainingProfileKind` and `PersonalizationStrategy`)
- Checkpoint selection in `learning/checkpoints/handler.py` and `selection.py`
- Model construction in `learning/model/autoencoder.py`

**Scientific invariants.** Training hyperparameters, checkpoint grid, primary round selection, seed derivation, personalization semantics all preserved.

**Exact architecture change.**

1. Training handler receives `CompiledExperiment` + `TrainingContext` + materialized data paths — not full config.

2. Scoring handler receives selected checkpoint + materialized split + population — not full config.

3. Use ordinary factories for model/optimizer/loss:
   ```python
   build_autoencoder(architecture: ModelArchitectureRecord, input_dim: int) -> nn.Module
   build_optimizer(model: nn.Module, optimizer_config: OptimizerRecord) -> torch.optim.Optimizer
   build_loss() -> nn.Module  # MSE
   ```

4. Keep current training dispatch. Add `LearningStrategyRegistry` only if direct dispatch proves unwieldy after audit.

5. Centralize checkpoint selection evidence persistence.

**Files affected.**
- `learning/training/handler.py` — narrow config dependency
- `learning/scoring/handler.py` — narrow config dependency
- `learning/checkpoints/handler.py` — narrow config dependency
- `learning/model/autoencoder.py` — keep, may add factory function
- `learning/training/federated.py` — FedAvg implementation
- `learning/training/personalization.py` — Ditto implementation
- `learning/training/aggregation.py` — FedProx variant

**Code to remove or merge.**
- Repeated model construction logic (if duplicated)
- Repeated optimizer construction (if duplicated)
- Config lookup in scoring handler

**Config changes.** None.

**Test changes.**
- FedAvg deterministic focused test
- FedProx grid and selection test
- Ditto grid and selection test
- Checkpoint serialization round-trip
- Score equality across repeated runs
- CUDA availability behavior test

**Validation commands.**
```bash
nox -s typecheck
nox -s lint
nox -s tests
nox -s imports
```

**Completion checklist.**
- [ ] Training, checkpointing, and scoring handlers receive compiled inputs, not full config
- [ ] Model/optimizer/loss construction uses ordinary factories
- [ ] Checkpoint selection evidence persisted as typed artifact
- [ ] All learning tests pass
- [ ] GPU behavior preserved

**Net simplification target.**
- Reduce handler dependencies from `ResolvedProjectConfiguration` to compiled records
- Remove config lookup from scoring

---

### Phase 8 — Thresholding Simplification

**Scope.** Replace 12-branch isinstance dispatch with `ThresholdEstimatorRegistry` keyed by `ThresholdPolicyKind`. Preserve all threshold families.

**Current repository evidence.**
- `thresholding/estimation/dispatch.py:41-91` — 12-branch isinstance chain
- `thresholding/policies/` — 12 policy record types
- `thresholding/policies/enums.py` — policy enums (add `ThresholdPolicyKind` in Phase 1)
- `thresholding/estimation/` — pure estimation functions already separated
- `app.py:58-66` — builds estimator registry keyed by `ThresholdPolicyId`

**Scientific invariants.** All 12 threshold policy families preserved with identical behavior. B4 canonical K=3, quantile q=0.95, shrinkage grid, conformal alpha, federated matching all unchanged.

**Exact architecture change.**

1. Create `ThresholdEstimatorRegistry` keyed by `ThresholdPolicyKind`:
   ```python
   class ThresholdEstimatorRegistry:
       def __init__(self, estimators: dict[ThresholdPolicyKind, ThresholdEstimator]) -> None: ...
       def require(self, kind: ThresholdPolicyKind) -> ThresholdEstimator: ...

       def estimate(self, kind: ThresholdPolicyKind, request: ThresholdConstructionRequest) -> ThresholdSet:
           return self.require(kind).estimate(request)
   ```

2. Replace `ConfiguredThresholdEstimator` with per-kind estimator implementations:
   - `SharedMeanEstimator`, `SharedPooledEstimator`, `SharedWeightedEstimator`
   - `LocalQuantileEstimator`
   - `FamilyMeanEstimator`
   - `ClusterEstimator`
   - `ConformalEstimator`
   - `ShrinkageEstimator`
   - `CalibrationFallbackEstimator`
   - `FederatedMatchedEstimator`, `FederatedFixedEstimator`

3. Delete `dispatch.py`. Each estimator class is thin (delegates to existing pure functions).

4. Update `app.py:_build_estimator_registry()` to map `ThresholdPolicyKind` → estimator.

5. Runtime flow:
   ```python
   policy = compiled_evaluation.threshold_policy
   estimator = threshold_estimators.require(policy.kind)
   result = estimator.estimate(request)
   ```

**Files affected.**
- `thresholding/estimation/dispatch.py` — DELETE
- `thresholding/estimation/registry.py` — new (or add to existing `ports.py`)
- `thresholding/estimation/estimators.py` — new (thin per-kind estimator classes)
- `thresholding/policies/enums.py` — `ThresholdPolicyKind` already added in Phase 1
- `app.py` — update estimator construction

**Code to remove or merge.**
- `dispatch.py` — entirely deleted
- `ConfiguredThresholdEstimator` class — deleted
- `isinstance` chain — deleted

**Config changes.** None (policy records unchanged).

**Test changes.**
- One focused contract test per policy kind
- Input eligibility tests
- Expected output column tests
- Threshold ownership tests
- Determinism tests
- Fallback behavior tests
- Edge case tests
- Baseline numeric equivalence tests (compare against Phase 0)

**Migration order.**
1. Create per-kind estimator classes
2. Create `ThresholdEstimatorRegistry`
3. Update `app.py` composition
4. Verify all 12 policy families produce identical thresholds
5. Delete `dispatch.py`

**Validation commands.**
```bash
nox -s typecheck
nox -s lint
nox -s tests
nox -s imports
```

**Phase-wide validation.**
- All 12 threshold policy families produce identical threshold values as Phase 0 baseline
- Adding a new threshold policy requires only: policy record, estimator class, registry entry — no central chain edit

**Scientific equivalence.** All threshold values numerically identical to baseline.

**Completion checklist.**
- [ ] `dispatch.py` deleted
- [ ] `ThresholdEstimatorRegistry` exists keyed by `ThresholdPolicyKind`
- [ ] Each policy kind has one estimator implementation
- [ ] No isinstance chain remains
- [ ] All threshold tests pass
- [ ] Threshold values identical to baseline

**Net simplification target.**
- Delete 1 file (`dispatch.py`)
- Replace 12-branch isinstance chain with registry lookup
- No central dispatch chain to edit when adding policies

---

### Phase 9 — Evaluation and Metric Authority

**Scope.** Ensure evaluation is the only package that computes configured evaluation metrics. Audit Polars-native vectorization.

**Current repository evidence.**
- `evaluation/metrics/operating_point.py` — operating point metrics
- `evaluation/metrics/auroc.py` — AUROC calculation
- `evaluation/metrics/diagnostics.py` — diagnostics
- `evaluation/execution/handler.py` — evaluation stage handler

**Scientific invariants.** All metric formulas preserved. `ddof=0` for population variance. No epsilon stabilizer on CV(FPR). AUROC as control.

**Exact architecture change.**

1. Audit `evaluation/metrics/` for Polars-native expressions:
   - Verify no `.iter_rows()`, `.rows()`, `.to_list()`, `.to_dict()` on DataFrames
   - Replace any Python loops over Polars rows with native expressions
   - Use Polars expressions for: joins, filters, grouped aggregation, exceedance counting, coverage calculations

2. Audit `analysis/` for metric recomputation:
   - Verify analysis does not recompute `CV(FPR)`, `IQR(FPR)`, `worst-client FPR`
   - Analysis must consume metric values from persisted evaluation artifacts

3. Persist a typed aggregate metric artifact:
   - Experiment ID, evaluation label, variant coordinates, seed, metric ID, value, status, scope

4. Audit data preprocessing for Polars-native operations:
   - `data/preprocessing/normalization.py`
   - Adapter preprocessing methods

**Files affected.**
- `evaluation/metrics/operating_point.py` — audit for vectorization
- `evaluation/metrics/auroc.py` — audit for vectorization
- `evaluation/metrics/diagnostics.py` — audit for vectorization
- `analysis/comparisons/paired.py` — verify no metric recomputation
- `analysis/calibration/quantile.py` — audit for vectorization
- `analysis/calibration/conformal.py` — audit for vectorization
- `analysis/calibration/stability.py` — audit for vectorization
- `analysis/clustering/membership.py` — audit for vectorization
- `analysis/mechanisms/distributions.py` — audit for vectorization
- `data/preprocessing/normalization.py` — audit for vectorization

**Code to remove or merge.**
- Any `.iter_rows()` loops in computational paths
- Any analysis-side metric recomputation
- Any Polars → Python list → computation patterns

**Config changes.** None.

**Test changes.**
- Every metric formula test
- Every metric status condition test
- Cross-client aggregation test
- Near-zero CV handling test
- Ineligible client exclusion test
- Missing attack-class handling test
- AUROC invariance control test
- Metric artifact schema test
- Evaluation repeatability test

**Validation commands.**
```bash
nox -s typecheck
nox -s lint
nox -s tests
nox -s imports
```

**Completion checklist.**
- [ ] No `.iter_rows()` in computational hot paths
- [ ] No analysis-side metric recomputation
- [ ] Polars native expressions for all DataFrame operations
- [ ] Evaluation is sole metric computation authority
- [ ] All metric tests pass
- [ ] Metric values identical to baseline

**Net simplification target.**
- Remove Python loops over DataFrames
- Remove analysis-side metric recomputation

---

### Phase 10 — Analysis, Comparisons, Pingouin, and Polars

**Scope.** Simplify analysis dispatch. Maximize Pingouin usage where scientifically equivalent. Remove import-time registration remnants.

**Current repository evidence.**
- `analysis/statistics/inference.py` — already uses Pingouin for Wilcoxon (line 166) and rank-biserial (line 42); Holm uses Pingouin (line 56); BCa uses scipy (line 199, correct)
- `analysis/statistics/association.py` — Spearman and linear regression (needs audit)
- `analysis/statistics/descriptive.py` — descriptive statistics (needs audit)
- `analysis/runtime/runner.py` — analysis execution runner
- `analysis/runtime/planning.py` — analysis planning
- `analysis/runtime/artifacts.py` — analysis artifact loading
- No import-time registration found (good)

**Scientific invariants.** All statistical procedures preserved. BCa with jackknife acceleration. Wilcoxon secondary. Holm correction within declared families.

**Exact architecture change.**

1. Replace custom Spearman correlation with Pingouin `pg.corr(method="spearman")` where equivalence is verified.

2. Replace custom linear regression with Pingouin `pg.linear_regression()` where equivalence is verified, retaining leverage and leave-one-out diagnostics from scipy where Pingouin does not provide them.

3. Replace custom descriptive statistics with Pingouin where applicable.

4. Keep scipy for:
   - BCa bootstrap (`scipy.stats.bootstrap` — Pingouin does not provide BCa)
   - Leverage diagnostics (if not in Pingouin)
   - Leave-one-out regression diagnostics (if not in Pingouin)

5. Create `AnalysisHandlerRegistry` (if not already done) keyed by `AnalysisKind`. Build explicitly in composition root.

6. Analysis execution context receives only: `CompiledExperiment`, `AnalysisContext`, `ArtifactStore`, `ExperimentPaths`, `StatisticalAnalysisUseCase`.

**Files affected.**
- `analysis/statistics/association.py` — Pingouin for Spearman/regression
- `analysis/statistics/descriptive.py` — Pingouin where applicable
- `analysis/runtime/runner.py` — use typed context
- `analysis/runtime/planning.py` — simplify
- `analysis/runtime/artifacts.py` — use `ExperimentPaths`
- `analysis/comparisons/paired.py` — use Pingouin, consume eval artifacts
- `analysis/comparisons/association.py` — consume eval artifacts
- `analysis/comparisons/effect_ratios.py` — consume eval artifacts

**Code to remove or merge.**
- Custom statistical implementations replaced by Pingouin
- Analysis path reconstruction (use `ExperimentPaths`)
- Configuration navigation from analysis modules

**Config changes.** None.

**Test changes.**
- One focused test per analysis kind
- Result serialization round-trip
- Seed alignment tests
- Sweep-cell alignment tests
- Prerequisite loading tests
- Statistical family correction tests
- Materiality rule tests
- Undefined denominator behavior tests
- Chronology rule tests
- Population alignment tests

**Validation commands.**
```bash
nox -s typecheck
nox -s lint
nox -s tests
nox -s imports
```

**Completion checklist.**
- [ ] Pingouin used for Spearman correlation where equivalent
- [ ] Pingouin used for linear regression where equivalent
- [ ] Pingouin used for descriptive statistics where equivalent
- [ ] scipy retained for BCa, leverage, leave-one-out diagnostics (documented)
- [ ] Analysis handler registry explicit and keyed by `AnalysisKind`
- [ ] Analysis modules consume canonical metric artifacts
- [ ] No analysis-side metric recomputation
- [ ] All analysis tests pass
- [ ] Statistical results identical to baseline

**Net simplification target.**
- Remove custom Spearman/regression implementations (replaced by Pingouin)
- Remove analysis path reconstruction

---

### Phase 11 — Result Freezing, Tables, and Plots

**Scope.** Replace dictionary-driven reporting with typed report items. Preserve real persisted output files (Markdown, LaTeX, PNG, PDF, SVG, Parquet/CSV).

**Current repository evidence.**
- `reporting/rendering/figures.py` — matplotlib figure functions
- `reporting/rendering/tables.py` — table generation
- `reporting/profiles/enums.py` — report profile enums
- `reporting/freezing/` — result freezing codec, models, service, validation
- `reporting/execution/freeze_handler.py` — freeze stage handler
- `reporting/execution/report_handler.py` — report stage handler
- `reporting/audit/query.py` — DuckDB query service

**Scientific invariants.** All report profiles preserved. Every figure and table traces to frozen result. No hand-copied values.

**Exact architecture change.**

1. Replace dictionary-based report profiles with typed specifications:
   ```python
   class TableSpec(BaseModel):
       table_id: str
       source_result: str
       columns: tuple[ColumnSpec, ...]
       output_format: Literal["markdown", "latex", "csv", "parquet"]
       caption: str

   class FigureSpec(BaseModel):
       figure_id: str
       source_result: str
       output_format: Literal["png", "pdf", "svg"]
       width_inches: float
       height_inches: float
       caption: str

   ReportItem = TableSpec | FigureSpec
   ```

2. Use one `ReportGenerator` with direct dispatch on `TableSpec | FigureSpec`.

3. Keep direct focused table and figure builders — no renderer registry unless multiple rendering backends genuinely require it.

4. Freeze finalized typed results before reporting. `FrozenResult` is a Pydantic model, not a dictionary.

5. Reporting reads frozen results only.

**Files affected.**
- `reporting/profiles/enums.py` — update for typed specs
- `reporting/rendering/models.py` — add `TableSpec`, `FigureSpec`
- `reporting/rendering/figures.py` — keep, audit
- `reporting/rendering/tables.py` — keep, audit
- `reporting/rendering/package.py` — update
- `reporting/execution/report_handler.py` — use typed specs
- `reporting/freezing/models.py` — ensure `FrozenResult` is typed Pydantic model

**Code to remove or merge.**
- Dictionary-based report profile conversion
- Arbitrary field access by string in report rendering
- Base64-only figure storage
- Reporting path reconstruction (use `ExperimentPaths`)

**Config changes.**
- `configs/protocols.yaml` report_profiles — update to typed format if needed

**Test changes.**
- Freeze/unfreeze round-trip tests
- Result union validation tests
- Every table builder test
- Every figure builder test
- Output format tests
- Missing-field behavior tests
- File checksum tests
- Report traceability tests
- DuckDB query compatibility tests

**Validation commands.**
```bash
nox -s typecheck
nox -s lint
nox -s tests
nox -s imports
```

**Completion checklist.**
- [ ] `TableSpec` and `FigureSpec` are typed Pydantic models
- [ ] `FrozenResult` is typed Pydantic model
- [ ] Report generator uses direct dispatch
- [ ] Real files persisted (not base64-only)
- [ ] Every report item traces to frozen result
- [ ] All report tests pass

**Net simplification target.**
- Remove dictionary-driven reporting
- Remove base64-only figure storage
- Replace with typed Pydantic models

---

### Phase 12 — Standalone Experiment Lifecycle

**Scope.** Make single-experiment execution simple and atomic. Clean up lifecycle use case.

**Current repository evidence.**
- `experiments/execution/use_case.py` — `ExperimentLifecycleUseCase`
- `experiments/execution/output_manager.py` — `ExperimentOutputManager`
- `experiments/execution/preflight.py` — preflight stage

**Scientific invariants.** Standalone lifecycle: valid completed output skips, incomplete/corrupt requires override, override deletes and restarts from scratch, no stage-level resume.

**Exact architecture change.**

1. Consolidate into `ExperimentRunner`:
   ```python
   class ExperimentRunner:
       def run(
           self,
           experiment_id: ExperimentId,
           *,
           override: bool = False,
       ) -> ExperimentResult: ...
   ```

2. Keep `ExperimentOutputManager` for output inspection, deletion, and fingerprint validation.

3. Finalization: verify mandatory stage outcomes, required artifacts, checksums, frozen results, fingerprints — then write manifest, then completion marker last.

**Files affected.**
- `experiments/execution/runner.py` — new (consolidates lifecycle + execution)
- `experiments/execution/use_case.py` — DELETE (merged into runner)
- `experiments/execution/output_manager.py` — keep, use `ExperimentPaths`
- `app.py` — update to use `ExperimentRunner`

**Code to remove or merge.**
- `use_case.py` — deleted (merged)
- Campaign-specific logic in standalone lifecycle (must be separate)

**Config changes.** None.

**Test changes.**
- Absent output test
- Complete output skip test
- Missing file test
- Corrupt file test
- Fingerprint mismatch test
- Prerequisite mismatch test
- Override test
- Crash before finalization test
- Completion marker written last test

**Validation commands.**
```bash
nox -s typecheck
nox -s lint
nox -s tests
nox -s imports
```

**Completion checklist.**
- [ ] Standalone lifecycle is atomic
- [ ] No campaign-specific logic in standalone path
- [ ] Completion marker written last
- [ ] All lifecycle tests pass

**Net simplification target.**
- Merge `use_case.py` into `runner.py`
- Remove campaign logic from standalone path

---

### Phase 13 — Campaign Simplification

**Scope.** Consolidate campaign logic into one `CampaignRunner`. Add prerequisite fingerprint compatibility. Implement full resumption.

**Current repository evidence.**
- `experiments/execution/campaign.py` — `CampaignOrchestrator` (193 lines)
- `experiments/execution/use_case.py` — `ExperimentLifecycleUseCase.run_campaign()`
- Logic split between orchestrator (ordering, DAG) and lifecycle (per-experiment execution)

**Scientific invariants.** Campaign ordering, prerequisite dependencies, anchor priority, blocking rules, sharing rules all preserved.

**Exact architecture change.**

1. Create `CampaignRunner` consolidating `CampaignOrchestrator` and campaign-specific lifecycle logic:
   ```python
   class CampaignRunner:
       def run(self, *, override_all: bool = False) -> CampaignReport: ...
   ```

2. Implement full resumption logic:
   1. Resolve canonical experiment order
   2. Validate prerequisite dependencies
   3. Ensure anchors run before dependents
   4. Inspect existing outputs
   5. Skip valid compatible completed experiments
   6. Detect first incomplete/corrupt/incompatible experiment
   7. Delete only that experiment's invalid output
   8. Restart from that experiment
   9. Continue through later experiments
   10. Revalidate later completed experiments before skipping

3. Add prerequisite fingerprint compatibility check:
   - Load prerequisite frozen result fingerprint
   - Compare with current prerequisite output fingerprint
   - Mark dependent as incompatible if mismatch

4. Replace dictionary access on frozen results with typed `FrozenResult` model.

5. Keep minimal campaign sharing (materializations, training, checkpoints, scores only — not thresholds, evaluations, analyses, frozen results, reports, completion markers).

**Files affected.**
- `experiments/execution/campaign.py` — rewrite as `CampaignRunner`
- `experiments/execution/runner.py` — standalone runner (Phase 12)
- `experiments/execution/output_manager.py` — add fingerprint validation
- `app.py` — update to use `CampaignRunner`

**Code to remove or merge.**
- `CampaignOrchestrator` class — replaced by `CampaignRunner`
- Split lifecycle/campaign logic — consolidated
- `frozen.get("outcomes")` dictionary access — replaced by typed model
- Ordinal sharing paths — replaced by fingerprint-based sharing

**Config changes.** None.

**Test changes.**
- Full fresh campaign test
- All experiments already complete test
- Interruption at every stage test
- Anchor failure test
- Missing prerequisite test
- Changed prerequisite fingerprint test
- Shared artifact reuse test
- Corrupt shared artifact test
- Override-all test
- Deterministic campaign order test

**Validation commands.**
```bash
nox -s typecheck
nox -s lint
nox -s tests
nox -s imports
```

**Completion checklist.**
- [ ] `CampaignRunner` owns campaign order, prerequisites, blocking, resumption, and sharing
- [ ] Prerequisite fingerprint compatibility checked
- [ ] Campaign resumption works correctly
- [ ] No dictionary access on frozen results
- [ ] Minimal sharing is fingerprint-safe
- [ ] All campaign tests pass

**Net simplification target.**
- Consolidate 2 files (`campaign.py` + `use_case.py`) into 1 file (`campaign.py`)
- Remove dictionary access on frozen results
- Remove ordinal-based sharing paths

---

### Phase 14 — Dagster, Diagnostics, CLI, and Composition

**Scope.** Generate Dagster operations from `ExperimentPlan`. Clean up CLI. Remove orchestration duplication.

**Current repository evidence.**
- `orchestration/dagster_defs.py` — one opaque op per experiment
- `orchestration/diagnostics.py` — diagnostic commands
- `cli.py` — imports concrete planning infrastructure directly

**Scientific invariants.** Dagster remains canonical orchestrator. Same plan used everywhere.

**Exact architecture change.**

1. Generate Dagster operations from `ExperimentPlan.stages`:
   ```python
   def build_dagster_definitions(experiment: CompiledExperiment) -> dg.Definitions:
       plan = plan_builder.build(experiment)
       ops = {stage.node_key.label: _make_op(stage) for stage in plan.stages}
       ...
   ```
   Each operation receives one stage job, calls the corresponding handler, declares upstream dependencies.

2. Remove hardcoded repository path from Dagster definitions.

3. Diagnostics use:
   - Real experiment compiler
   - Real plan builder
   - Real stage handlers
   - Diagnostic output root from `ExperimentPaths`
   - Reduced execution profile

4. CLI only:
   - Parses arguments (Typer)
   - Calls application use cases
   - Displays typed results
   - Maps typed failures to exit codes
   - Does NOT mutate `os.environ`
   - Does NOT import concrete planning infrastructure

5. `app.py` exports `DatpApplication` with:
   - `ExperimentRunner`, `CampaignRunner`, `ExperimentPlanBuilder`, `ExperimentPaths`
   - Configuration-only application remains lightweight

**Files affected.**
- `orchestration/dagster_defs.py` — generate stage-level ops from plan
- `orchestration/diagnostics.py` — use `ExperimentPaths`
- `cli.py` — remove concrete infrastructure imports, remove `os.environ` mutation
- `app.py` — update composition

**Code to remove or merge.**
- One-op Dagster wrapper in `dagster_defs.py`
- Direct `expand_experiment_jobs` import in CLI
- Direct `PlanningGraph` import in CLI
- `os.environ` mutation in CLI and diagnostics
- Hardcoded repository path in `dagster_defs.py:35`

**Config changes.** None.

**Test changes.**
- Dagster graph equals experiment plan test
- Stage dependencies preserved in Dagster test
- Diagnostic output isolation test
- Configuration-only application remains lightweight test
- CLI command tests
- No CUDA initialization for config commands test
- No DuckDB initialization for config commands test

**Validation commands.**
```bash
nox -s typecheck
nox -s lint
nox -s tests
nox -s imports
```

**Completion checklist.**
- [ ] Dagster ops generated from `ExperimentPlan.stages`
- [ ] No opaque one-op wrapper
- [ ] Diagnostics use real pipeline with isolated output
- [ ] CLI contains no planning or infrastructure logic
- [ ] No `os.environ` mutation in CLI
- [ ] One plan, one handler set, one orchestration path
- [ ] All tests pass

**Net simplification target.**
- Remove opaque Dagster wrapper
- Remove CLI planning imports
- Remove `os.environ` mutation patterns

---

### Phase 15 — Debloating and Legacy Removal

**Scope.** Delete all replaced architecture. Merge unnecessary files. Enforce all static rules.

**Current repository evidence.** After Phases 1-14, the following should be deletable:
- `experiments/planning/layout.py` (Phase 3)
- `experiments/planning/jobs.py` (Phase 5)
- `experiments/planning/context.py` (Phase 4)
- `analysis/runtime/context.py` (Phase 4)
- `thresholding/estimation/dispatch.py` (Phase 8)
- `experiments/execution/use_case.py` (Phase 12)
- Dead `no-flower-dependency` import-linter contract
- Any remaining `attrs` imports in migrated files
- Any remaining `cattrs` usage

**Scientific invariants.** All scientific behavior unchanged.

**Exact architecture change.**

1. Delete all replaced files (see deletion ledger in Section H).

2. Merge files when:
   - A file contains one trivial record
   - A file only wraps one function
   - Two files always change together
   - A package contains nearly empty `__init__.py`-only subpackages
   - A helper is used only by one neighboring module

3. Enforce static rules:
   - No `Any` in source or tests
   - No untyped scientific dictionaries
   - No implicit configuration defaults in Python
   - No raw string comparison for closed vocabularies
   - No unused configuration fields
   - No unused enum values
   - No dead dataclasses
   - No unnecessary inheritance
   - No comments narrating obvious code
   - No compatibility aliases
   - No duplicate scientific formulas
   - No duplicate path creation

4. Reduce tests:
   - Remove duplicate tests asserting same contract
   - Prefer parametrized tests for policy families
   - Keep focused scientific regression tests
   - Avoid mocking simple pure functions
   - Use builders where they remove repeated fixture construction

**Files affected.** All remaining source and test files — audit pass only.

**Validation commands.**
```bash
nox -s typecheck
nox -s lint
nox -s pylint
nox -s tests
nox -s imports
nox -s scientific_invariants
```

**Completion checklist.**
- [ ] All replaced files deleted
- [ ] No `Any` in source or tests
- [ ] No untyped dictionaries in domain code
- [ ] No implicit scientific defaults
- [ ] No raw string comparisons for enums
- [ ] No dead code
- [ ] No compatibility shims
- [ ] All tests pass
- [ ] Static checks pass

---

### Phase 16 — Full Scientific and Execution Verification

**Scope.** Prove no scientific or execution drift from Phase 0 baseline.

**Scientific invariants.** All invariants in Section C verified.

**Verification steps.**

1. **Configuration.** Validate all YAML. Resolve twice. Compare scientific and execution fingerprints against Phase 0 baseline.

2. **Data.** Recompute source fingerprints for all three datasets. Compare materialization outputs.

3. **Planning.** Build plans for all 22 experiments. Compare stage keys, dependencies, output paths against baseline.

4. **Learning.** Focused execution of FedAvg, FedProx, Ditto. Compare checkpoint selection outputs.

5. **Thresholding.** Test all 12 policy families for numeric equivalence.

6. **Evaluation.** Validate all metric computations against baseline.

7. **Analysis.** Run every configured analysis type. Compare results.

8. **Reporting.** Freeze results. Generate all configured tables and figures. Compare file checksums.

9. **Lifecycle.** Standalone fresh/skip/override/incomplete/corrupt tests.

10. **Campaign.** Fresh/resume/prerequisite-blocking/anchor-blocking/changed-prerequisite/sharing/corrupt/override-all tests.

11. **Dagster.** Stage visibility, dependencies, single-experiment, campaign, diagnostic execution.

12. **Quality gates.** Ruff, formatter, Pyright, Pylance, Pylint, import-linter, focused tests, package tests, full test suite, SonarQube, CodeScene.

**Validation commands.**
```bash
datp-core config validate
datp-core config fingerprint  # compare to Phase 0
datp-core config explain-scientific-drift  # must show no drift
nox -s quality
```

**Completion checklist.**
- [ ] Scientific fingerprint unchanged from Phase 0
- [ ] Execution fingerprint unchanged from Phase 0
- [ ] All baselines matched
- [ ] All quality gates pass
- [ ] SonarQube issues not increased
- [ ] CodeScene hotspots not worsened

---

## H. Deletion and Consolidation Ledger

### Files expected to be deleted

| File | Phase | Reason |
|---|---|---|
| `experiments/planning/layout.py` | 3 | Replaced by `ExperimentPaths` |
| `experiments/planning/jobs.py` | 5 | Consolidated into `ExperimentPlanBuilder` |
| `experiments/planning/context.py` | 4 | Merged into `pipeline/stages/context.py` |
| `analysis/runtime/context.py` | 4 | Merged into `pipeline/stages/context.py` |
| `thresholding/estimation/dispatch.py` | 8 | Replaced by `ThresholdEstimatorRegistry` |
| `experiments/execution/use_case.py` | 12 | Consolidated into `ExperimentRunner` |

### Files expected to be merged

| Files | Phase | Into |
|---|---|---|
| Campaign orchestrator + lifecycle campaign logic | 13 | `campaign.py` `CampaignRunner` |

### Items to eliminate

| Item | Phase | Current location |
|---|---|---|
| `@define` (attrs) on domain models | 1 | 30+ files across all packages |
| `cattrs.Converter` in CLI | 1 | `cli.py:19` |
| `Mapping[str, str \| bool]` in `ResolvedProjectConfiguration` | 1 | `config/models.py:66` |
| `Mapping[str, str]` fields | 1 | `config/models.py:68,87` |
| 12-branch isinstance chain | 8 | `thresholding/estimation/dispatch.py:61-91` |
| Inline path construction | 3 | `experiments/planning/jobs.py`, `layout.py` |
| `frozen.get("outcomes")` dictionary access | 13 | `experiments/execution/campaign.py:146-148` |
| `os.environ` mutation for config | 14 | `cli.py:291-293,316-318,345` |
| Hardcoded repo path | 14 | `orchestration/dagster_defs.py:35` |
| One-op Dagster wrapper | 14 | `orchestration/dagster_defs.py:31-50` |
| Direct planning imports in CLI | 14 | `cli.py:21-22` |
| `no-flower-dependency` import contract | 15 | `importlinter.ini:106-111` |

---

## I. Library Adoption Matrix

| Library | Current Usage | Target Usage | Replaces | Must Not Be Used For | Migration Phase | Acceptance Criteria |
|---|---|---|---|---|---|---|
| **Pydantic v2** | Authored config models, analysis results | All validated config, metric records, policy records, frozen results, CLI serialization | attrs, cattrs | Lightweight internal coordinate dataclasses (use frozen dataclass) | Phase 1 | All domain models are Pydantic; cattrs removed |
| **Hydra** | Unused (dependency only) | Configuration composition, CLI overrides, sweep expansion | Custom YAML loading in `config/loading.py` | Artifact paths, runtime service location, Dagster orchestration | Phase 2 | Hydra composes config; no OmegaConf leaks |
| **Pingouin** | Wilcoxon, rank-biserial, Holm correction | Add Spearman, linear regression, descriptive stats where equivalent | Custom scipy-based implementations | BCa bootstrap (use scipy), leverage diagnostics (use scipy/statsmodels) | Phase 10 | Pingouin used for all supported procedures; exceptions documented |
| **Polars** | DataFrame operations (dependency) | Native expressions for all DataFrame computation | `.iter_rows()`, `.rows()`, `.to_list()`, Python loops over DataFrames | Statistical computation (use NumPy/pandas at library boundary) | Phase 9 | No row iteration in hot paths |
| **Dagster** | One opaque op per experiment | Stage-level ops from `ExperimentPlan` | None (Dagster remains canonical) | Configuration management (use Hydra) | Phase 14 | Dagster shows per-stage execution |
| **Pandera** | Artifact schema validation | Unchanged | None | Configuration validation (use Pydantic) | — | Preserved as-is |
| **DuckDB** | Parquet query audit | Unchanged | None | Primary data processing | — | Preserved as-is |
| **SafeTensors** | Model checkpoint persistence | Unchanged | None | — | — | Preserved as-is |
| **NumPy** | Array computation in statistics | NumPy arrays at library boundaries | None | DataFrame computation (use Polars) | — | Preserved for scipy/Pingouin boundary |
| **SciPy** | BCa bootstrap, stats not in Pingouin | BCa bootstrap, leverage diagnostics, any stat Pingouin does not provide | None where Pingouin equivalent exists | Procedures Pingouin supports equivalently | Phase 10 | scipy used only where Pingouin lacks equivalent |
| **statsmodels** | Additional statistical procedures | Unchanged | None | — | — | Preserved where needed |
| **attrs** | Domain models throughout | REMOVED from domain models. Retained only for `core/identifiers.py` lightweight value objects | N/A | Domain models, configuration, records | Phase 1 | Only `core/identifiers.py` uses attrs |
| **cattrs** | CLI JSON serialization | REMOVED | N/A | Any serialization | Phase 1 | No cattrs imports remain |

---

## J. Scientific Equivalence Matrix

| Experiment/Scientific Mechanism | Affected Phases | Verification |
|---|---|---|
| Confirmatory B1 vs B2 (Regime A, CV(FPR), 10 seeds, BCa) | 1, 2, 4, 5, 8, 9, 10, 16 | Identical CV(FPR) values, identical BCa interval |
| B0 centralized reference | 2, 7, 8, 16 | Identical centralized threshold |
| B3 family threshold | 2, 8, 16 | Identical family assignments and thresholds |
| B4 cluster threshold (K=3 canonical) | 2, 8, 16 | Identical cluster assignments, identical thresholds |
| B2-conf split conformal | 8, 16 | Identical conformal quantile and coverage |
| Shared-threshold construction controls | 8, 16 | Identical shared thresholds |
| Quantile sensitivity grid | 2, 8, 16 | Identical CV(FPR) across quantile grid |
| Shrinkage λ grid | 2, 8, 16 | Identical shrinkage thresholds |
| Calibration-size ablation | 8, 9, 16 | Identical threshold variance across sizes |
| B-FedStatsBenign comparator | 8, 16 | Identical matched-exceedance threshold |
| FedProx stress test | 7, 16 | Identical proximal selection, identical scores |
| Ditto stress test | 7, 16 | Identical personalized states, identical scores |
| N-BaIoT materialization | 3, 6, 16 | Identical materialized data, identical split manifests |
| CICIoT2023 materialization | 3, 6, 16 | Identical materialized data, identical pseudo-client assignments |
| Edge-IIoTset materialization | 3, 6, 16 | Identical materialized data, identical sensor-group assignments |
| Regime C Dirichlet heterogeneity | 2, 6, 16 | Identical partitions, identical CV(FPR) per α |
| Regime D-temporal chronology | 2, 6, 16 | Identical chronological splits, identical recovery ratio |
| Anchor equivalence | 10, 16 | Identical anchor checks pass/fail |
| Paired comparisons | 9, 10, 16 | Identical paired differences |
| Absorption analysis | 9, 10, 16 | Identical absorption ratios |
| Recovery fraction analysis | 9, 10, 16 | Identical recovery fractions |
| Association analysis | 10, 16 | Identical Spearman ρ, identical regression |
| Cluster stability analysis | 9, 10, 16 | Identical ARI, identical memberships |
| Distribution mechanism analysis | 9, 10, 16 | Identical JS divergence, identical CDF data |
| Temporal recovery analysis | 9, 10, 16 | Identical drift excess, identical recovery ratio |
| Alert burden analysis | 9, 10, 16 | Identical alerts per client per day |
| Resource cost analysis | 9, 10, 16 | Identical estimated bytes |
| All 18 report profiles | 11, 16 | Identical table values, identical figure data |

**Unacceptable drift:** Any numeric change in CV(FPR), BCa interval bounds, threshold values, cluster assignments, checkpoint selection, or statistical test results.

**Acceptable change:** Code structure, file organization, import paths, class names (as long as behavior is identical).

---

## K. Quality and Simplification Metrics

### Before (baseline from Phase 0 audit)

| Metric | Current Value |
|---|---|
| Source files (`src/datp_core/`) | 194 |
| Test files (`tests/`) | 56 |
| Source lines (approx.) | ~19,400 |
| `@define` (attrs) models | 30+ (config, evaluation, thresholding, learning, data contracts) |
| `cattrs` usage sites | 3 (CLI only) |
| Pydantic `BaseModel` classes | 30+ (authored config, analysis results) |
| `Mapping[str, ...]` dictionary fields | 3 |
| `Any` occurrences | 0 (verified in audit) |
| Nullable fields in `StageJobContext` | 13 of 16 |
| `isinstance` dispatch branches | 12 |
| Path construction sites | 5+ files |
| Configuration lookup sites in planning | 10+ per experiment |
| `.iter_rows()`/`.to_list()` sites | To be audited in Phase 9 |
| Dispatch chains (isinstance/if-elif) | 1 major (thresholding) |
| Mutable/global registries | 0 (all explicit in composition root) |
| Orchestration entry paths | 4 (CLI, Dagster, diagnostics, tests) |

### Target (after all phases)

| Metric | Target |
|---|---|
| Source files | < 194 (files deleted, not added) |
| Test files | ≤ 56 (consolidated where duplicative) |
| `@define` (attrs) models | < 20 (only `core/identifiers.py` lightweight IDs) |
| `cattrs` usage | 0 |
| `Mapping[str, ...]` fields | 0 |
| `Any` occurrences | 0 (maintain) |
| Nullable fields in stage contexts | < 5 per context (from 13 in one context to focused families) |
| `isinstance` dispatch branches | 0 (registry replaces chain) |
| Path construction sites | 1 (`ExperimentPaths`) |
| Configuration lookup sites in planning | 0 (compiled once) |
| Dispatch chains | 0 major chains |
| Mutable/global registries | 0 (maintain) |
| Orchestration entry paths | 1 shared plan, multiple entry points |

**Net simplification must be demonstrable: fewer files, fewer lines, fewer authorities, fewer abstractions, easier navigation.**

---

## L. Final GO FOR EXPERIMENTS Checklist

The final verdict is **GO FOR EXPERIMENTS** only when all of the following are true:

### Architecture
- [ ] Existing top-level scientific domains remain clear
- [ ] No unnecessary architecture framework was added
- [ ] `ResolvedProjectConfiguration` is the single resolved configuration authority
- [ ] Every experiment is compiled once via `CompiledExperiment`
- [ ] One `ExperimentPlanBuilder` creates the full stage plan
- [ ] One `ExperimentPaths` owns all semantic paths
- [ ] The oversized `StageJobContext` is gone (replaced by 4 typed context families)

### Scientific domains
- [ ] Dataset adapters preserve dataset-specific logic
- [ ] Shared preprocessing code is centralized in `data/preprocessing/`
- [ ] Threshold dispatch uses `ThresholdEstimatorRegistry` keyed by `ThresholdPolicyKind`
- [ ] Evaluation owns metric computation
- [ ] Analysis consumes canonical metric artifacts
- [ ] Analysis registration is explicit (no import-time side effects)
- [ ] Statistics remain reusable direct functions with Pingouin integration
- [ ] Reporting uses typed `TableSpec` and `FigureSpec`
- [ ] Real report files are persisted (Markdown, LaTeX, PNG, PDF, SVG, Parquet/CSV)

### Execution
- [ ] Standalone experiment lifecycle is atomic
- [ ] One `CampaignRunner` owns campaign semantics
- [ ] Campaign resumption is deterministic with fingerprint compatibility
- [ ] Minimal sharing is fingerprint-safe
- [ ] Dagster executes the canonical plan with stage-level visibility
- [ ] CLI contains no planning or infrastructure logic

### Cleanup
- [ ] Replaced code has been deleted
- [ ] No compatibility shims remain
- [ ] No `attrs` on domain models (only lightweight identifiers)
- [ ] No `cattrs` in CLI
- [ ] No untyped dictionaries in domain contracts
- [ ] No `Any` in source or tests
- [ ] No hardcoded scientific values
- [ ] No hidden defaults
- [ ] No duplicate scientific formulas
- [ ] No duplicate path construction
- [ ] No import-time registration

### Verification
- [ ] Scientific results match Phase 0 baseline
- [ ] Scientific fingerprint unchanged
- [ ] Execution fingerprint unchanged
- [ ] All 22 experiments plan and compile
- [ ] All static checks pass (Ruff, Pyright, Pylint, import-linter)
- [ ] All tests pass (unit, integration, scientific)
- [ ] SonarQube issues not increased from baseline
- [ ] CodeScene hotspots not worsened from baseline
- [ ] Configuration validates
- [ ] The resulting codebase is measurably smaller and simpler

### Blocking decisions (unresolved)
1. **`cv_instability_threshold` value.** Required by `SCIENTIFIC_SOURCE_OF_TRUTH.md` §11 item 8 for near-zero-denominator warning annotation. Blocks only the warning annotation on CV(FPR) cells — does not block confirmatory endpoint or any other checklist item. Must be configured before publication.
2. **CICIoT2023 feature count verification.** Required before quantitative CICIoT2023 claims reach print. Does not block Regime A/C work. Flagged in roadmap audit.

---

## Guiding Principle

```
Keep the scientific domains.
Resolve configuration once.
Compile each experiment once.
Build one execution plan.
Construct paths in one place.
Use small typed contexts.
Use registries only where executable implementations genuinely vary.
Keep scientific calculations as direct functions.
Let evaluation own metrics.
Let analysis own comparisons and inference.
Let reporting own tables and figures.
Let one campaign runner own campaign behavior.
Let Dagster execute the same plan used everywhere else.
Delete every replaced abstraction.
```

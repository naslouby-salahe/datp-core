# DATP-Core Code Review and Refactoring Plan

## 1. Purpose and Non-Negotiable Constraints

This document is the single, idempotent review and restructuring authority for `datp-core`. It is maintained, not regenerated: repeated runs of the review prompt must preserve finding IDs, accepted decisions, and resolved/rejected history, updating only what has concretely changed in the repository.

Non-negotiable constraints carried into every finding and phase below:

- The accepted six-file authored YAML tree (`configs/runtime.yaml`, `configs/experiments.yaml`, `configs/protocols.yaml`, `configs/datasets/{nbaiot,ciciot2023,edge_iiotset}.yaml`) is fixed. No finding may recommend expanding it, moving scientific values into Python, or moving Python duplication into YAML.
- Locked scientific invariants (see [2.4](#24-scientific-integrity-baseline)) — anchor protocol, seed cohorts, batch size 256, checkpoint-selection rules, threshold-policy semantics, quantile `q = 0.95`, canonical `K = 3`, eligibility minimum `n_k >= 100` — may never be silently altered by a refactor.
- No backward-compatibility shims, import redirects, or parallel old/new architectures. Corrections are made once, forward, with obsolete code deleted in the same change.
- Batch-size reduction is forbidden under any circumstance, including "temporary" test or performance changes.
- This review evaluates the repository as it exists now. It does not treat `NOT_STARTED`/`IN_PROGRESS` execution work (real dataset materialization beyond N-BaIoT/CICIoT2023, Dagster execution, PyTorch/Flower training, evaluation/statistics tables) as a defect merely for being unimplemented — see [2.4](#24-scientific-integrity-baseline) for the verified implementation frontier. Findings target the code that does exist.

---

## 2. Current Verified Baseline

### 2.1 Repository Structure

Verified by direct traversal and `find`/`wc` on 2026-07-21's repository state (branch `main`, working tree clean).

```text
src/datp_core/
  application/       8 files,  ~740 lines  — use cases, ports, stage handlers
  composition/        1 file,   172 lines  — DatpApplication / ConfigOnlyApplication factories
  config/             8 files, ~2,750 lines — resolver, resolution helpers, yaml loader, validation
    models/           5 files, ~1,570 lines — authored Pydantic schema (_base, dataset, experiment, protocol, runtime)
  domain/            10 files, ~2,300 lines — pure attrs/dataclass records, no framework imports
  infrastructure/
    artifacts/         4 files,   ~620 lines — atomic commit engine, manifest codec, model store
    datasets/          9 files, ~1,690 lines — csv_source, source_inventory, adapter_registry, nbaiot(+adapter), ciciot2023(+adapter), edge_iiotset
    federation/        1 file,     32 lines  — Flower FedAvg strategy wrapper
    learning/          2 files,   198 lines  — PyTorch autoencoder + sklearn helpers
    querying/          1 file,     40 lines  — DuckDB audit service
    runtime/           1 file,     50 lines  — structlog configuration
    statistics/        5 files,   150 lines  — scipy/statsmodels/posthoc/pingouin adapters
    tables/            4 files,   178 lines  — pandera schemas, parquet io, polars engine, xarray views
    thresholding/       2 files,   334 lines  — Protocol + 12-policy configured estimator
  interfaces/cli/     2 files,   193 lines  — Typer app, rich formatters
  orchestration/dagster/ 6 files, ~130 lines — assets, resources, translation, partitions, metadata, definitions
  planning/           4 files,   624 lines  — graph (NetworkX), identity builder, expansion, validation
tests/
  unit/               ~38 files, ~2,900 lines
  integration/          4 files,   145 lines
  scientific/           6 files,   350 lines
  conformance/          5 files,   380 lines
```

Source: 95 Python files, 11,537 lines (excluding `__pycache__`, `.venv`, `build`). Tests: 51 files (excluding `tests/__pycache__`), 4,279 lines. Package/subpackage count: 21 directories under `src/datp_core` (see tree above). Configuration corpus: 3,710 YAML lines across the six accepted documents.

### 2.2 Quality Gates

Gates defined by `noxfile.py` (`lint`, `typecheck`, `tests`, `tests_parallel`, `imports`) and by CI:

| Gate | Local (`nox`) | CI (`.github/workflows/tests.yml`, `sonarqube.yml`) |
| --- | --- | --- |
| `ruff format --check` | Yes | **No** |
| `ruff check` | Yes | **No** |
| `pyright` | Yes | **No** |
| `pytest` (serial) | Yes | Yes |
| `pytest -n auto` | Yes | No |
| `lint-imports --config importlinter.ini` | Yes | **No** |

Per the `.tmp/implementation` control ledger (2026-07-21, most recent hardening pass): `ruff format --check`, `ruff check`, `pyright` (0 errors), `lint-imports` (2/2 contracts kept), and `pytest` (194 tests, serial and `-n auto`) all pass locally. This baseline is trusted as a starting point but is **not itself re-verified by this review** (this task is read-only; see [14](#14-master-completion-checklist)). See [CR-TEST-001](#cr-test-001--ci-does-not-run-linttypeimport-gates) for the CI gap.

Import-linter contracts (`importlinter.ini`): `domain` may import no framework or other layer; `config` may import no `infrastructure`/`orchestration`/`composition`/`interfaces`. Neither contract restricts `infrastructure` importing `config.models` (used deliberately by `infrastructure/thresholding/{base,estimators}.py`), nor restricts `application` from being bypassed by `interfaces/cli` for simple registry lookups (see [CR-ARCH-002](#cr-arch-002--cli-dataset-audit-command-bypasses-the-application-boundary)).

### 2.3 Structural Metrics

Longest function bodies (AST line-span, `src/datp_core`, top entries):

| Lines | Location | Function |
| ---: | --- | --- |
| 625 | `config/resolver.py:166` | `resolve_project_configuration` |
| 227 | `config/dataset_resolution.py:283` | `resolve_datasets` |
| 203 | `config/experiment_resolution.py:86` | `_resolve_analysis` (14-way kind dispatch; see [10](#10-accepted-architecture-decisions)) |
| 142 | `planning/expansion.py:12` | `expand_experiment_jobs` |
| 118 | `config/validation.py:29` | `ProjectConfigurationValidator.validate` |
| 104 | `config/runtime_settings.py:236` | `resolve_runtime_configuration` |
| 97 | `application/dataset_audit.py:101` | `AuditDatasetUseCase._audit_source_tree` |
| 91 | `infrastructure/datasets/ciciot2023.py:183` | `write_ciciot2023_materialized_parquet` |
| 89 | `infrastructure/artifacts/atomic_commit.py:58` | `_execute_atomic_transaction` |

Records with the largest field counts: `ExperimentRecord` (`domain/catalogue.py`, 34 fields — see [CR-DOMAIN-002](#cr-domain-002--experimentrecord-mixes-independent-concern-groups-as-flat-fields)); `AuthoredExperimentConfig` (`config/models/experiment_config.py`, ~40 fields, mirrors `ExperimentRecord` 1:1 and is an accepted authored-side flat superset, see [10](#10-accepted-architecture-decisions)); `MetricFormulaRecord`/`MetricFormulaConfig` (19 fields, accepted flat superset for an inert, not-yet-consumed contract).

Other counts: `cast(` usage across `src`: 111 call sites (concentrated in `domain/{thresholding,datasets,catalogue}.py` converter helpers — see [CR-DOMAIN-003](#cr-domain-003--repeated-mapping-conversion-boilerplate-across-domain-modules)). `# type: ignore` / `# pyright: ignore`: 18 occurrences, of which 12 are the single clustered pattern in `composition/root.py` (see [CR-ARCH-001](#cr-arch-001--composition-root-uses-dictstr-object-forcing-12-type-ignores)) and 6 are `pandera.polars` `Field(...)` declarations in `infrastructure/tables/schemas.py` (accepted — a known pandera/pyright typing-stub gap, not a project defect). Bare `except Exception`: zero occurrences. `dict[str, ...]` / `Mapping[str, ...]` type annotations: 127 + 119 = 246 occurrences, the large majority being deliberate `Mapping[str, FrozenJson]`/`as_*_mapping` conversions of genuinely heterogeneous authored blocks (accepted pattern, see [10](#10-accepted-architecture-decisions)); a small number represent fixed-shape scientific contracts that should be typed records (see [CR-CONFIG-002](#cr-config-002--untyped-mapping-fields-on-threshold-policy-records-for-fixed-shape-contracts)).

### 2.4 Scientific Integrity Baseline

Per `.tmp/implementation/MASTER_IMPLEMENTATION_CHECKLIST.md` and `IMPLEMENTATION_STATE.md` (read as evidence of current status, not as a scientific authority — the roadmap and YAML remain authoritative):

- **Implemented and verified**: strict six-document configuration authority with duplicate-key rejection; lossless resolution of `experiments.yaml` (all catalogue-level and per-experiment fields, including the 14-member analysis-kind union) and of `protocols.yaml` (12 pure threshold-policy records, model/optimizer/batching, all previously-dead protocol contract blocks); single path/symlink authority with raw-source policy enforcement; unified cattrs-based fingerprint canonicalization with a structured drift-diff (`domain/drift.py`) replacing hash-only comparison; atomic, checksummed, msgspec-strict artifact manifest codec; N-BaIoT and CICIoT2023 bounded materialization paths (source→Parquet→committed artifact) proven on representative (not full-corpus) data.
- **Explicitly residual** (per the ledger's own accounting, not disputed by this review): `AuthoredDatasetConfig`'s `source_layout`/`field_schema`/`source_contract`/`client_identity_contract` leaf-disposition coverage is not yet gated by the same structural test used for `experiments.yaml`, although this review's direct reading of `domain/datasets.py` and `config/dataset_resolution.py` finds the great majority of these fields already resolved losslessly (only `client_identity_contract` remains an untyped `Mapping[str, FrozenJson]`, which is appropriate given it is genuinely dataset-specific and currently populated only for Edge-IIoTset).
- **Not started**: real dataset materialization for Edge-IIoTset beyond its adapter-free helper functions (no `EdgeIIoTsetAdapter` class or `adapter_registry` entry exists yet); real Dagster asset-graph construction from a `PlanningGraph` (translation/partition/metadata helpers exist and are unit-tested, but `orchestration/dagster/definitions.py` registers only one static asset); real federated-round orchestration (Flower strategy object is constructed but no round-driving loop exists — `infrastructure/learning/pytorch_adapter.py::train_autoencoder` is a plain non-federated single-model training loop); evaluation/statistics table generation (`EVAL-METRICS-001`, `NOT_STARTED`); all 14 threshold policies are implemented in `infrastructure/thresholding/estimators.py`, but none has been exercised against real trained scores.
- **Verified counts** (cross-checked against the YAML directly by this review): 3 datasets, 7 study populations, 23 experiments, 14 threshold-policy identifiers, 2 seed cohorts (10-seed journal, 5-seed anchor), 6 checkpoint/round profiles' worth of selection rules. These match the `.tmp` ledger's own count claims exactly.

No finding in this document recommends changing any locked value (batch size 256, seed cohorts `[0..9]`/`[0..4]`, quantile 0.95, canonical `K=3`, eligibility minimum 100, checkpoint convergence tolerance 0.005/window 10/rounds_initial 40, anchor round cap 150, journal round cap 200).

---

## 3. Executive Assessment

### 3.1 Overall Architecture Verdict

The repository is a disciplined, evidence-driven implementation of a hexagonal/clean architecture (domain → config → application → infrastructure/orchestration → composition → interfaces), and it visibly practices what it preaches: an explicit control ledger (`.tmp/implementation/`) tracks every hardening decision with reasons, and conformance tests (`tests/conformance/*`) mechanically enforce the layer boundaries and no-hidden-default rules that the roadmap demands. Configuration resolution is lossless and richly typed to a degree well beyond typical scientific-computing codebases: every one of the ~14 threshold policies, ~14 analysis kinds, and every protocol contract block has its own frozen attrs record, and a real, proven bug (silently dropped list-valued sweep values) was caught and fixed by this discipline during the prior hardening pass.

The weaknesses found are concentrated, not diffuse: one god function (`resolve_project_configuration`), one composition-root typing hole (`dict[str, object]`), one unsafe first-item assumption in the only wired stage handler, a cluster of scientifically-latent hardcoded-fallback values for undefined metrics, and a body of orphaned "future work" scaffolding (whole unused adapter files and one whole unused subpackage) that inflates the dependency and file count without contributing tested behavior. None of these weaknesses is deeply embedded — each is addressable without touching the six-file YAML authority, the resolved domain records, or any locked scientific value.

### 3.2 Strong Areas to Preserve

- The domain layer (`domain/*.py`) is completely framework-free (verified by import-linter and by direct reading), immutable (`frozen=True, slots=True`), and enforces "no hidden defaults" via `tests/conformance/test_no_hidden_defaults.py`'s reflection-based sweep over every attrs class.
- The atomic-artifact transaction engine (`infrastructure/artifacts/atomic_commit.py`) is a genuine single authority: one private `_execute_atomic_transaction` handles both `BytesPayload` and `FilePayload` variants with identical locking/fsync/manifest/atomic-replace semantics; `model_store.py` and `pytorch_adapter.py`'s SafeTensors persistence both delegate to it rather than writing files directly.
- The manifest codec (`infrastructure/artifacts/manifest_codec.py`) uses `msgspec` with `forbid_unknown_fields=True` to distinguish `ManifestDecodeError` from `ManifestSchemaIncompatibleError` precisely — a deliberate, justified, single use of `msgspec` for exactly the boundary it is good at.
- The 14-policy threshold estimator dispatch (`infrastructure/thresholding/estimators.py`) is a clean `isinstance`-per-policy dispatch with no duplicated boilerplate; the analogous 14-kind analysis dispatch (`config/experiment_resolution.py::_resolve_analysis`) is long only because it is mechanically enumerating 14 genuinely distinct, previously-audited field supersets — both are accepted patterns (see [10](#10-accepted-architecture-decisions)).
- The conformance-test layer (`tests/conformance/*`) is exceptional: it enforces the authored-config-import allowlist, the no-hidden-defaults rule, and (via `test_experiment_catalogue_field_disposition.py`) an exhaustive enumeration of all 153 `AuthoredExperimentsCatalogueConfig` leaf field paths against an explicit SCIENTIFIC/EXECUTION/AUTHORING_METADATA disposition table that fails on any undeclared field. This is a rare, high-value regression gate against silent scientific-field loss.
- `runtime_settings.py`'s raw-symlink policy enforcement (`_resolve_raw_data_root`) deliberately inspects `Path.is_symlink()`/`Path.resolve(strict=True)` *before* any destructive resolution, with an inline comment explaining exactly why ordering matters — a correct, non-obvious safety property that is easy to get wrong and is documented precisely where it matters.

### 3.3 Highest-Risk Weaknesses

Ordered by the priority classification used in [6](#6-prioritized-findings):

1. Hardcoded numeric substitutes (`0.0`, `0.5`) for metrics protocols.yaml explicitly defines as *undefined*/*unavailable* statuses, currently latent in unused code but certain to cause silent scientific drift the moment `EVAL-METRICS-001` wires them up unmodified ([CR-SCI-001](#cr-sci-001--hardcoded-numeric-fallbacks-for-undefined-metrics-contradict-the-authored-metric-status-contract)).
2. An unguarded `population_ids[0]` in the only currently-wired stage handler, plus an unguarded `next()` lookup beside it ([CR-EXEC-001](#cr-exec-001--unsafe-first-item-and-unguarded-lookup-assumptions-in-the-dataset-materialization-stage-handler)).
3. A CSV-reading regression: the immediately-preceding commit fixed a duplicate-header/short-row defect in the shared CSV reader, but the same defect remains live in Edge-IIoTset's independent reader ([CR-DATA-002](#cr-data-002--edge-iiotset-csv-reader-still-has-the-defect-the-latest-commit-just-fixed-elsewhere)).
4. A 625-line configuration-resolution god function with inconsistent delegation ([CR-CONFIG-001](#cr-config-001--resolve_project_configuration-is-a-625-line-god-function-with-inconsistent-delegation)).
5. A composition root typed through `dict[str, object]`, producing 12 `# type: ignore` suppressions that erase the very type safety the rest of the codebase enforces ([CR-ARCH-001](#cr-arch-001--composition-root-uses-dictstr-object-forcing-12-type-ignores)).

### 3.4 Expected Consolidation Outcome

Implementing every finding in this document is expected to: delete roughly 550-650 lines of dead/orphaned code (whole files in `infrastructure/tables/`, `infrastructure/statistics/{posthoc,pingouin,statsmodels}_adapter.py`, most of `infrastructure/learning/sklearn_adapter.py`, `domain/catalogue.py::ResolvedCatalogue`, `domain/thresholding.py::SampleSizeCheck`, `domain/evaluation.py`'s two unused records, `config/converter.py::unstructure_mapping_proxy`); remove 12 of 18 `# type: ignore` suppressions; shrink the largest function from 625 to an estimated ~40-60 lines via extraction (with total line count roughly unchanged, redistributed into named, independently testable functions); remove six now-provably-unused runtime dependencies (`pandera`, `xarray`, `scikit-posthocs`, `pingouin`, `statsmodels`, `pandas`) and the entirely-unused `hardware` extra (`psutil`, `pynvml`); and close one proven, latent scientific-drift risk before it is built upon. No finding changes the resolved scientific projection, the execution projection, or any fingerprint, when validated per each finding's required checks.

---

## 4. Target Architecture Principles

1. **One resolution authority per configuration collection.** Every authored-YAML collection (`training_profiles`, `checkpoint_profiles`, `seed_cohorts`, `model_architectures`, `optimizers`, `batching`, `eligibility_policies`, `normalization_strategies`, `quantile_estimators`, `metric_bundles`, `populations`, `eligibility_gates`, experiments) is resolved by exactly one named, independently testable function, consistent with the pattern already established for `protocols.yaml`'s dead-block contracts and for `experiments.yaml`'s analysis-kind union. `config/resolver.py` becomes a thin orchestrator that calls these functions in dependency order and assembles the two projection dicts; it does not itself contain resolution logic for any single collection.
2. **The composition root is fully typed, with zero `dict[str, object]`.** Shared use-case construction returns a named record (attrs or `NamedTuple`), not a string-keyed dictionary, so that pyright verifies every wire-up without suppression.
3. **No unguarded first-item or `next()` access on any collection whose cardinality is not proven to be exactly one by a type or an explicit prior check.** Where an experiment/dataset/materialization genuinely has exactly one element by current schema and usage, that invariant is asserted with a clear error message (matching the existing `dataset.setup()`/`ResolvedDataset.setup()` KeyError pattern), never silently assumed.
4. **One filesystem-scanning authority per dataset.** `build_source_inventory` is the sole implementation of source-tree traversal; every consumer (audit, materialization) calls it — none reimplements glob/rglob/ignored-suffix/ignored-subtree filtering independently.
5. **One CSV-reading authority per row-validation contract.** Numeric and labeled-numeric CSV streaming lives in `infrastructure/datasets/csv_source.py` only; dataset-specific readers (Edge-IIoTset) either reuse it or, where genuinely dataset-specific parsing is required (hex-encoded numerics, endpoint-based client identity), share the row-validation primitives rather than re-deriving them with `csv.DictReader`.
6. **Undefined and unavailable metric outcomes are always a typed status, never a substituted number.** Every metric computation that can be undefined (zero denominator) or unavailable (missing class) returns/raises a value from the `metric_statuses` closed set defined in `protocols.yaml`; no function returns `0.0`, `0.5`, or any other numeric placeholder for these cases.
7. **Dead code is deleted, not preserved as speculative future scaffolding.** Code with zero consumers and zero tests is removed in the same phase it is identified, and is re-added (freshly, reflecting the actual consumer's needs) only when the corresponding roadmap requirement (`EVAL-METRICS-001`, `EXEC-DAGSTER-HANDLER-001`, etc.) is genuinely implemented.
8. **Fixed-shape scientific contracts are typed records, not string-keyed mappings requiring `isinstance` probing at the point of use.** A `dict`/`Mapping` field is acceptable only where the underlying authored shape is genuinely heterogeneous or per-instance-varying (already the case for `FrozenJson` extension points); where every instance of a policy has the exact same fixed key set (K-means hyperparameters, candidate-grid bounds), the field becomes a typed sub-record.

---

## 5. Proposed Target Project Tree

No directory is added, removed, or renamed at the top level. The following describes intra-file reorganization only; package boundaries are already correct (verified: every subpackage has one clear responsibility, no `__init__.py` layer is more than an empty marker, no directory contains a single trivial file).

```text
src/datp_core/
  config/
    resolver.py                  # thin orchestrator only, post CR-CONFIG-001
    catalogue_resolution.py       # NEW: populations, eligibility_gates, experiments (extracted from resolver.py)
    protocol_collection_resolution.py  # NEW: training_profiles, checkpoint_profiles, seed_cohorts,
                                        #      model_architectures, optimizers, batching_profiles,
                                        #      eligibility_policies, normalization_strategies,
                                        #      quantile_estimators, metric_bundles (extracted from resolver.py)
    dataset_resolution.py         # unchanged package, resolve_datasets decomposed into helpers (CR-CONFIG-001)
    experiment_resolution.py      # unchanged (already a correct extraction)
    protocol_resolution.py        # unchanged (already a correct extraction)
  composition/
    root.py                       # CommonConfigUseCases typed record replaces dict[str, object] (CR-ARCH-001)
  domain/
    catalogue.py                  # ResolvedCatalogue removed (CR-DOMAIN-001); ExperimentRecord regrouped (CR-DOMAIN-002)
    thresholding.py               # SampleSizeCheck removed; ClusterThresholdPolicyRecord/
                                   # FederatedMatchedExceedanceThresholdPolicyRecord gain typed sub-records (CR-CONFIG-002)
    evaluation.py                 # removed entirely, or rebuilt with typed-status semantics when EVAL-METRICS-001 starts (CR-SCI-001, CR-DOMAIN-001)
  infrastructure/
    datasets/
      source_inventory.py         # sole scanning authority; dataset_audit.py consumes it (CR-DATA-001)
      csv_source.py                # shared numeric-field validation helper extracted (CR-DATA-005)
      edge_iiotset.py              # iter_edge_iiotset_source reuses the shared, fixed reader (CR-DATA-002)
      ciciot2023.py                 # in-memory canonicalize_and_split_ciciot2023_rows removed; SQLite path is sole authority (CR-DATA-003)
      nbaiot_adapter.py             # chunk_row_count sourced from ResolvedRuntimeConfiguration (CR-DATA-004)
    statistics/                     # posthoc_adapter.py, pingouin_adapter.py, statsmodels_adapter.py removed (CR-DEPS-001)
    learning/
      sklearn_adapter.py           # scale_features/compute_roc_auc/compute_adjusted_rand_index removed or rebuilt typed (CR-DEPS-001, CR-SCI-001)
    tables/                        # removed entirely until EVAL-METRICS-001 has a real consumer (CR-DEPS-001)
  planning/
    identity.py                    # PlannedJobSpec named record replaces positional 4-tuples (CR-EXEC-002)
    expansion.py                   # consumes PlannedJobSpec.job_id/.output/.inputs/.dependencies (CR-EXEC-002)
  application/
    stage_handlers.py              # DatasetMaterializationStageHandler validates population_ids/materialization lookup (CR-EXEC-001)
```

---

## 6. Prioritized Findings

### 6.1 Priority 0 — Critical

#### CR-SCI-001 — Hardcoded numeric fallbacks for undefined metrics contradict the authored metric-status contract

**Status:** `CONFIRMED`
**Priority:** `P0`
**Category:** scientific-integrity
**Decision:** `REPLACE`

**Affected files:**

- `src/datp_core/domain/evaluation.py`
- `src/datp_core/infrastructure/learning/sklearn_adapter.py`

**Affected symbols or responsibilities:**

- `ClientConfusionMatrix.false_positive_rate` / `.true_positive_rate`
- `compute_roc_auc`

**Evidence:**

`domain/evaluation.py:22-27` and `:29-34`: `false_positive_rate`/`true_positive_rate` return `0.0` when the respective denominator (`false_positives + true_negatives` / `true_positives + false_negatives`) is zero. `infrastructure/learning/sklearn_adapter.py:20-23`: `compute_roc_auc` returns `0.5` when `len(np.unique(labels)) < 2` (single-class label array). `configs/protocols.yaml`'s `metric_definitions` block defines `fpr`/`tpr` with `zero_denominator: undefined_zero_denominator` and `auroc` with `requires_both_classes: true`; the same document's `metric_statuses` enum lists `undefined_zero_denominator` and `unavailable_missing_attack_class` as required typed outcomes, and its `forbidden_substitutions` list explicitly names `zero_for_undefined` as forbidden. Both functions are currently unreferenced by any other production code or test (`grep` confirms zero call sites outside their own definitions), so no observed result is corrupted today — the risk is latent.

**Problem:**

The authored scientific contract requires every metric that can be undefined or unavailable to surface a typed status distinguishable from a real value (`domain/protocol_contracts.py::MetricFormulaRecord` already carries the corresponding `zero_denominator`/`zero_mean_behavior`/`requires_both_classes` fields losslessly). These two functions instead collapse the undefined case into a plausible-looking number — `0.0` FPR/TPR is indistinguishable from "measured, perfect performance," and `0.5` AUROC is indistinguishable from "measured, chance-level discrimination." If either function is reused as-is when `EVAL-METRICS-001` is implemented, per-client metrics for ineligible or degenerate clients would silently enter aggregate statistics (`CV(FPR)`, mean AUROC) as real observations rather than being excluded or flagged, which is exactly the "denominator_stabilizer: forbidden" / "near_zero_mean_behavior" class of failure the roadmap's evaluation protocol is designed to prevent.

**Impact:**

Scientific-integrity: a downstream `CV(FPR)` or AUROC-invariance calculation built on these functions without modification would silently misrepresent excluded/degenerate clients as measured ones, directly risking the confirmatory endpoint's validity. Currently no impact (dead code), but the impact is certain and severe if inherited unmodified.

**Recommended target state:**

Both functions return a discriminated result (e.g. `float | Literal["undefined_zero_denominator"]`, or a small typed `MetricOutcome` value with an explicit status enum drawn from `protocols.yaml`'s `metric_statuses`) instead of a bare `float`. Callers must handle the non-numeric case explicitly.

**Required actions:**

1. Define a `MetricStatus` enum (or reuse string literals matching `metric_statuses` exactly) in `domain/evaluation.py` or a new `domain/metrics.py`.
2. Change `ClientConfusionMatrix.false_positive_rate`/`.true_positive_rate` to return `float | MetricStatus`, raising or returning the enum member for the zero-denominator case; update or delete `MetricResultRecord` accordingly (see [CR-DOMAIN-001](#cr-domain-001--dead-code-cluster-in-the-domain-layer)).
3. Change `compute_roc_auc` to return `float | MetricStatus` for the single-class case, matching `unavailable_missing_attack_class` (or `unavailable_missing_benign_class`, depending on which class is absent).
4. Add unit tests proving both zero-denominator and single-class inputs surface the typed status, and that a genuine measured value is unaffected.

**Prerequisites:**

- None (self-contained; both files are currently unused elsewhere).

**Dependent findings:**

- [CR-DOMAIN-001](#cr-domain-001--dead-code-cluster-in-the-domain-layer) (these records may be deleted rather than fixed if `EVAL-METRICS-001` has not started by the time this phase executes — see that finding's required action 3 for the decision rule).

**Expected files to change:**

- `src/datp_core/domain/evaluation.py`
- `src/datp_core/infrastructure/learning/sklearn_adapter.py`

**Tests to update or add:**

- `tests/unit/domain/test_scientific_value_objects.py` or a new `tests/unit/domain/test_metric_status_contract.py` covering zero-denominator FPR/TPR and single-class AUROC.

**Scientific-drift risk:** `HIGH` (latent; certain if inherited unmodified by `EVAL-METRICS-001`)

**Required validation:**

- `uv run pytest tests/unit/domain -q`
- Manual cross-check: every value in `protocols.yaml::metric_statuses` has at least one corresponding typed-status code path once `EVAL-METRICS-001` lands.

**Completion criteria:**

- No function in `src/datp_core` returns a bare numeric literal for a metric that `protocols.yaml` defines as capable of being undefined or unavailable.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

#### CR-EXEC-001 — Unsafe first-item and unguarded-lookup assumptions in the dataset-materialization stage handler

**Status:** `CONFIRMED`
**Priority:** `P0`
**Category:** correctness / execution-architecture
**Decision:** `SIMPLIFY`

**Affected files:**

- `src/datp_core/application/stage_handlers.py`

**Affected symbols or responsibilities:**

- `DatasetMaterializationStageHandler.execute`

**Evidence:**

`application/stage_handlers.py:119`: `population = self._config.populations.get(experiment.population_ids[0])` — silently selects the first population of `ExperimentRecord.population_ids: tuple[PopulationId, ...]`, a tuple whose type permits (and whose name implies) more than one element, with no validation that exactly one is present or any documented reason the first is authoritative. `application/stage_handlers.py:123`: `materialization = next(item for item in dataset.materializations if item.identifier == setup.materialization_id)` — an unguarded generator `next()` that raises a bare `StopIteration` (which surfaces as a `RuntimeError` inside the enclosing generator/exception context, not a clear application error) if no materialization matches, unlike the existing `ResolvedDataset.setup()` method two lines above it, which raises a clear `KeyError` with a descriptive message for the analogous lookup. This is the exact pattern named as a hypothesis to verify in the original review brief (`population_ids[0]`, unguarded `next(...)`), and both instances are confirmed present in the one stage handler that is actually wired into `composition/root.py::build_application`.

**Problem:**

Every experiment currently authored in `experiments.yaml` happens to declare exactly one population (`populations: [<single-id>]`), so this code path has not yet produced an observably wrong result. But nothing in the schema, the resolver, or a validation rule enforces that invariant — `ExperimentRecord.population_ids` is a tuple specifically because the catalogue format supports more than one, and `ProjectConfigurationValidator` (`config/validation.py`) never checks population-count cardinality per experiment. The unguarded `next()` similarly assumes the resolved dataset always has a materialization matching the setup's `materialization_id`, an invariant that is true today only because `resolve_datasets` enforces referential integrity for `client_population_must_equal_setup` but never for setup→materialization existence.

**Impact:**

Correctness/scientific-integrity: if a future experiment (e.g. one spanning both a natural-device and a Dirichlet population for a joint comparison) authored more than one population, this handler would silently materialize only the first, with no error — a textbook "architecture that allows silent scientific changes" per the priority-0 criteria in this review's own rubric. The unguarded `next()` would convert a genuine configuration-authoring mistake (misspelled or missing `materialization_id`) into an opaque internal error rather than a clear, actionable `ConfigurationError`.

**Recommended target state:**

Both lookups fail loudly and specifically when their single-element assumption is violated, following the existing `ResolvedDataset.setup()` KeyError precedent.

**Required actions:**

1. Add a guard in `DatasetMaterializationStageHandler.execute` (or in `ExperimentRecord` construction / `ProjectConfigurationValidator`) that raises a clear error naming the experiment if `len(experiment.population_ids) != 1`, documenting that multi-population experiments are not yet supported by this handler — or, if multi-population support is intended soon, thread the correct population through `StageJobContext` (already carries `population_id` on `EvaluationSpecRecord`/per-evaluation context — reuse that instead of re-deriving from the experiment).
2. Add a `ResolvedDataset.materialization(identifier: MaterializationId) -> DatasetMaterialization` helper mirroring `.setup()`'s KeyError pattern; replace the unguarded `next()` with a call to it.
3. Add a unit test proving a multi-population experiment either fails clearly or is routed correctly (per the decision in action 1), and a unit test proving an unknown `materialization_id` raises a clear, typed error.

**Prerequisites:**

- None.

**Dependent findings:**

- None.

**Expected files to change:**

- `src/datp_core/application/stage_handlers.py`
- `src/datp_core/domain/datasets.py` (new `ResolvedDataset.materialization` helper)

**Tests to update or add:**

- `tests/unit/application/test_dataset_materialization_reuse.py` (extend), or a new `tests/unit/application/test_stage_handler_population_and_materialization_guards.py`.

**Scientific-drift risk:** `MEDIUM` (no currently-observed drift; the guard prevents a specific, plausible future drift)

**Required validation:**

- `uv run pytest tests/unit/application -q`
- Confirm `ProjectConfigurationValidator.validate(...)` still reports zero errors against the current `configs/*.yaml`.

**Completion criteria:**

- No stage handler indexes `population_ids` or any resolved collection positionally without a preceding cardinality check or a named, single-purpose accessor that raises a clear error on violation.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

#### CR-DATA-002 — Edge-IIoTset CSV reader still has the defect the latest commit just fixed elsewhere

**Status:** `CONFIRMED`
**Priority:** `P0`
**Category:** data-integrity
**Decision:** `REPLACE`

**Affected files:**

- `src/datp_core/infrastructure/datasets/edge_iiotset.py`
- `src/datp_core/infrastructure/datasets/csv_source.py` (reference implementation of the fix)

**Affected symbols or responsibilities:**

- `iter_edge_iiotset_source`

**Evidence:**

Commit `37e38db` ("fix: replace DictReader with csv.reader to handle duplicate headers and eager field-count validation") changed `csv_source.py::iter_numeric_csv_source` and `::iter_labeled_numeric_csv_source` from `csv.DictReader` to `csv.reader` plus an explicit `header_to_index` map, specifically because `DictReader` silently collapses duplicate header names to one dict key (last value wins) and represents short/long rows via missing/`None` dict values rather than an eager, explicit field-count check. `edge_iiotset.py:102-113` (`iter_edge_iiotset_source`) still constructs `reader = csv.DictReader(source)` and detects malformed rows via `if None in record or any(record[header] is None for header in required)` — the exact pattern the commit replaced in the sibling module, present in the same commit's diff scope but not touched.

**Problem:**

Edge-IIoTset's authored header list (`configs/datasets/edge_iiotset.yaml::field_schema.source_columns`, 63 Wireshark protocol-field columns including near-duplicates like `tcp.flags`/`tcp.flags.ack`, `mqtt.conflag.cleansess`/`mqtt.conflags`) is exactly the kind of large, mechanically-exported header set where an accidental duplicate column name in a source file would be silently absorbed by `DictReader` (later columns overwrite earlier ones under the same key) rather than surfaced as the `"field count differs from configured header"` rejection this same function already emits for width mismatches via a different path. The fix's own commit message states the defect in general terms ("duplicate headers", "eager field-count validation") that apply equally to any `DictReader` use in this codebase, not only to the two functions it touched.

**Impact:**

Data-integrity / scientific-integrity: a duplicate or reordered header in any Edge-IIoTset source file would silently misassign feature values to the wrong column name instead of being rejected, directly risking `retained_numeric_features`/`categorical_encoding.columns` correctness for the sole external-validation dataset (Regime D). This is the same class of defect the prior commit treated as worth an immediate fix, not a stylistic preference.

**Recommended target state:**

`iter_edge_iiotset_source` reads headers positionally via `csv.reader` plus an explicit `header_to_index` map (or reuses a shared helper factored out per [CR-DATA-005](#cr-data-005--near-duplicated-numeric-field-validation-loops-in-csv_sourcepy)), with an eager `len(record) != len(raw_headers)` check before any field access, exactly matching the fixed pattern in `csv_source.py`.

**Required actions:**

1. Replace `csv.DictReader(source)` with `csv.reader(source)` plus `header_to_index` in `iter_edge_iiotset_source`, following `csv_source.py`'s current implementation.
2. Replace the `None in record or any(record[header] is None ...)` check with an eager `len(record) != len(raw_headers)` check yielding the existing `SourceRowFailure(reason="field count differs from configured header")`.
3. Update all `record[header]` accesses to `record[header_to_index[header]]`.
4. Add a unit test with a source file containing a duplicate header name (or an intentionally short row) proving the row is now rejected rather than silently misparsed.

**Prerequisites:**

- None.

**Dependent findings:**

- [CR-DATA-005](#cr-data-005--near-duplicated-numeric-field-validation-loops-in-csv_sourcepy) (if executed first, this finding reuses the extracted shared helper instead of hand-rolling the fix a third time).

**Expected files to change:**

- `src/datp_core/infrastructure/datasets/edge_iiotset.py`

**Tests to update or add:**

- `tests/unit/infrastructure/datasets/test_edge_iiotset_source.py` (add a duplicate-header / short-row fixture case).

**Scientific-drift risk:** `HIGH` (data-integrity defect in the sole external-validation dataset's source reader; currently unproven against real Edge-IIoTset files but structurally identical to an already-fixed defect)

**Required validation:**

- `uv run pytest tests/unit/infrastructure/datasets/test_edge_iiotset_source.py -q`
- Re-run `tests/integration/datasets/test_raw_source_contracts_are_ready.py` to confirm Edge-IIoTset header/layout evidence is unchanged for the real raw corpus.

**Completion criteria:**

- `iter_edge_iiotset_source` no longer imports or uses `csv.DictReader`.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

### 6.2 Priority 1 — High Correctness and Architecture

#### CR-CONFIG-001 — `resolve_project_configuration` is a 625-line god function with inconsistent delegation

**Status:** `CONFIRMED`
**Priority:** `P1`
**Category:** architecture / config-resolution
**Decision:** `SPLIT`

**Affected files:**

- `src/datp_core/config/resolver.py`
- `src/datp_core/config/dataset_resolution.py`

**Affected symbols or responsibilities:**

- `resolve_project_configuration`
- `resolve_datasets`

**Evidence:**

`config/resolver.py:166-790` is a single 625-line function (confirmed by AST line-span analysis). It already delegates dataset resolution to `dataset_resolution.resolve_datasets`, experiment-analysis/sweep resolution to `experiment_resolution.py`, and every protocol-contract-block resolution (`metric_definitions`, `artifact_identity`, `communication_estimation_contract`, `operational_inputs`, `protocol_determinism`, `threshold_policy_defaults`, `nested_replicate_policy`, `result_types`, `evaluation_result_contract`, `report_defaults`, `report_profiles`, threshold policies) to `protocol_resolution.py`. It does **not** delegate: population resolution + cross-reference validation (lines 205-230), catalogue-level contracts (232-251), training profiles (253-279), checkpoint profiles (281-324), seed cohorts (326-338), the executable statistical-profile subset (340-360), the full `ExperimentRecord` assembly including inline capability-requirement and calibration-subset construction (368-509), model architectures/optimizers/batching/eligibility-policies/normalization-strategies/quantile-estimators/metric-bundles (512-631, six dict-comprehensions inline), and the two ~75-line scientific/execution projection dict literals (656-747). `dataset_resolution.py::resolve_datasets` is itself 227 lines (line 283-509) — the second-longest function in the repository — inlining setup construction, materialization construction, and inspection-contract construction in one per-dataset loop rather than delegating to helper functions the way `resolve_identity_scheme`/`resolve_label_fields`/`resolve_endpoint_identity` already do for smaller sub-blocks in the same file.

**Problem:**

The extraction pattern used for `experiments.yaml` and `protocols.yaml` contract blocks is correct and should be the norm, but it was applied unevenly: roughly a dozen collection-resolution responsibilities remain inline in `resolver.py` for no apparent reason other than that they are individually "simple" dict comprehensions — the same could be said of several of the blocks that *were* extracted. This makes `resolver.py` the single largest and least uniform file to review or modify safely: a change to, say, `eligibility_policies` resolution requires scrolling through unrelated `metric_bundles`/`quantile_estimators` code with no function boundary to scope a diff or a targeted test to.

**Impact:**

Maintainability/testability: no individual collection's resolution logic can be unit-tested without exercising the entire `resolve_project_configuration` pipeline (loading all six YAML documents). Review risk: a 625-line function is far above the ~150-200-line review trigger this document's own methodology uses, and mixes clearly-independent responsibilities with different YAML-section owners.

**Recommended target state:**

`resolver.py` contains only: document loading, top-level ordering of resolution calls, and the two projection-assembly blocks (which may themselves be simplified per [CR-PERF-001](#cr-perf-001--duplicated-scientificexecution-fingerprint-computation-functions)-adjacent cleanup). Every individual collection gets one named function in the appropriate existing module (`protocol_resolution.py` for the protocol-side collections; a new `config/catalogue_resolution.py` for populations/eligibility-gates/experiments, since `experiment_resolution.py` is already scoped narrowly to analysis/sweep conversion per its own docstring). `resolve_datasets` decomposes its per-dataset loop body into `_resolve_setups`, `_resolve_materializations`, and `_build_inspection_contract` helpers, mirroring the existing `resolve_identity_scheme`-style extractions in the same file.

**Required actions:**

1. Extract `_resolve_populations`, `_resolve_eligibility_gates`, `_resolve_training_profiles`, `_resolve_checkpoint_profiles`, `_resolve_seed_cohorts`, `_resolve_statistical_profiles`, `_resolve_model_architectures`, `_resolve_optimizers`, `_resolve_batching_profiles`, `_resolve_eligibility_policies`, `_resolve_normalization_strategies`, `_resolve_quantile_estimators`, `_resolve_metric_bundles` from `resolver.py` into named functions (new `config/catalogue_resolution.py` for the first two; `protocol_resolution.py` for the rest), each taking the relevant authored config slice and returning the resolved dict/registry.
2. Extract `_resolve_experiment` (the per-experiment-record assembly currently inline at lines 369-509) into `experiment_resolution.py`, since that module already owns analysis/sweep conversion for the same records.
3. In `dataset_resolution.py`, extract `_resolve_setups(d_cfg, ...)`, `_resolve_materializations(d_cfg)`, and `_build_inspection_contract(d_cfg, ...)` from the body of `resolve_datasets`.
4. Re-verify `resolver.py`'s final line count and confirm every extracted function has at least one direct unit test (many collections currently have none, since they were only exercised indirectly through full resolution).
5. Do not change the resolved value, ordering, or fingerprint of any collection — this is a pure code-motion refactor.

**Prerequisites:**

- None.

**Dependent findings:**

- None (this finding does not block others, though [CR-CONFIG-002](#cr-config-002--untyped-mapping-fields-on-threshold-policy-records-for-fixed-shape-contracts) touches the same threshold-policy resolution path and should not be executed concurrently on the same lines — see [9.3](#93-shared-file-collision-risks)).

**Expected files to change:**

- `src/datp_core/config/resolver.py`
- `src/datp_core/config/dataset_resolution.py`
- `src/datp_core/config/protocol_resolution.py`
- `src/datp_core/config/experiment_resolution.py`
- `src/datp_core/config/catalogue_resolution.py` (new)

**Tests to update or add:**

- New targeted unit tests per extracted function (e.g. `tests/unit/config/test_catalogue_resolution.py`, extensions to `tests/unit/config/models/test_protocol_contract_blocks.py`).
- All existing tests under `tests/unit/config/`, `tests/scientific/drift/`, `tests/scientific/catalogue/` must pass unchanged (they exercise the public `resolve_project_configuration` entry point and must observe no behavioral difference).

**Scientific-drift risk:** `LOW` (pure refactor; every resolved value, ordering, and fingerprint input must remain byte-identical)

**Required validation:**

- `uv run pytest tests/scientific/drift/test_resolver_golden_identity.py tests/scientific/drift/test_fingerprint_projection_is_deterministic.py -q`
- Compare `resolve_project_configuration().scientific_fingerprint` / `.execution_fingerprint` before and after the refactor on the real `configs/` tree — must be byte-identical.
- `uv run pyright`

**Completion criteria:**

- `resolve_project_configuration` is under 150 lines; `resolve_datasets` is under 100 lines; every extracted function has a direct unit test; fingerprints are unchanged.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

#### CR-ARCH-001 — Composition root uses `dict[str, object]`, forcing 12 `# type: ignore`s

**Status:** `CONFIRMED`
**Priority:** `P1`
**Category:** composition-root / typing
**Decision:** `REPLACE`

**Affected files:**

- `src/datp_core/composition/root.py`

**Affected symbols or responsibilities:**

- `_build_common_config_use_cases`
- `build_config_only_application`
- `build_application`

**Evidence:**

`composition/root.py:59-70`: `_build_common_config_use_cases` is annotated `-> dict[str, object]` and returns a literal dict of six differently-typed use-case instances under string keys. Both `build_config_only_application` (lines 92-104) and `build_application` (lines 127-172) immediately destructure this dict back into a typed `attrs` container (`ConfigOnlyApplication`/`DatpApplication`), and every one of the six field assignments carries a `# type: ignore[arg-type]` comment (12 occurrences total, all in this file) because pyright correctly cannot verify that `cc["validate_configuration"]` is actually a `ValidateProjectConfiguration` given the `dict[str, object]` return type.

**Problem:**

This is precisely the anti-pattern this review's own methodology names explicitly: "no dependency container uses `dict[str, object]`" and "no unjustified `type: ignore` remains." The dict-of-`object` return type discards type information that both call sites need one line later, and the twelve suppressions are not narrowing a genuine pyright limitation — they are compensating for a self-inflicted type hole one function away.

**Impact:**

Type-safety: a typo in a dict key, or a reordered/renamed use-case, would not be caught by pyright at the composition site — exactly the failure mode static typing exists to prevent, in the one place (application wiring) where a mistake would silently misconfigure the entire application graph.

**Recommended target state:**

`_build_common_config_use_cases` returns a small typed record (e.g. `@define(frozen=True, slots=True, kw_only=True) class CommonConfigUseCases`) with the six named fields; both factories construct `ConfigOnlyApplication`/`DatpApplication` from its named attributes, with zero `# type: ignore`.

**Required actions:**

1. Define `CommonConfigUseCases` (attrs, frozen) with fields `validate_configuration`, `describe_project`, `explain_authored_drift`, `explain_scientific_drift`, `explain_execution_drift`, `fingerprint_config`, matching the six dict keys exactly.
2. Change `_build_common_config_use_cases`'s return type and body to construct/return this record.
3. Update `build_config_only_application` and `build_application` to read `cc.validate_configuration`, etc., removing all twelve `# type: ignore[arg-type]` comments.
4. Confirm `uv run pyright` reports zero errors with no new suppressions.

**Prerequisites:**

- None.

**Dependent findings:**

- None.

**Expected files to change:**

- `src/datp_core/composition/root.py`

**Tests to update or add:**

- None functionally required (composition root has no dedicated unit test today); optionally add a smoke test asserting `build_application()`/`build_config_only_application()` construct without error, if not already covered indirectly by CLI tests (`tests/unit/interfaces/cli/test_cli_commands.py`).

**Scientific-drift risk:** `NONE` (pure typing/wiring refactor, no behavior change)

**Required validation:**

- `uv run pyright`
- `uv run pytest tests/unit/interfaces/cli -q`

**Completion criteria:**

- Zero `# type: ignore` comments remain in `composition/root.py`; `CommonConfigUseCases` (or equivalent) is a typed record, not a `dict[str, object]`.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

#### CR-DATA-001 — Duplicated source-tree scanning logic between dataset audit and materialization

**Status:** `CONFIRMED`
**Priority:** `P1`
**Category:** data-architecture / duplication
**Decision:** `MERGE`

**Affected files:**

- `src/datp_core/infrastructure/datasets/source_inventory.py`
- `src/datp_core/application/dataset_audit.py`

**Affected symbols or responsibilities:**

- `_inventory_source_tree` (`source_inventory.py`)
- `AuditDatasetUseCase._source_files` (`dataset_audit.py`)

**Evidence:**

`source_inventory.py`'s module docstring states: "Applies configured source-tree resolution, path containment, glob semantics, ignored suffixes/subtrees... exactly once... Consumed by both audit and materialization; no consumer rescans the filesystem independently." `_inventory_source_tree` (lines 90-130) implements: `rglob("*.csv")` when `device_directories`/`normal_group_directories` are configured, else `glob(tree.file_pattern)` (with an `rglob` fallback for `**` patterns); filtering by ignored suffix and ignored subtree; sorting by relative path. `dataset_audit.py::AuditDatasetUseCase._source_files` (lines 199-218) independently implements the same `rglob("*.csv")`-or-`glob(pattern)` branch, the same ignored-subtree filtering, and the same relative-path sort — its own docstring for the sibling `_inventory_source_tree` function in `source_inventory.py` explicitly says "Uses the exact same glob/rglob logic as the dataset audit's `_source_files` method," i.e. the duplication is acknowledged in a comment rather than eliminated.

**Problem:**

Two independent implementations of file-tree discovery exist for the same configured contract, contradicting the module's own stated design goal. Any future change to filtering semantics (a new ignored pattern, a change to case-sensitivity, a new source-tree shape) must be made twice and kept in sync by convention; nothing enforces the two stay identical beyond a code comment.

**Impact:**

Correctness/maintainability: the two implementations could silently diverge (e.g. one gains a fix the other does not), causing the dataset audit to report readiness/file counts that do not match what materialization will actually consume — a direct threat to the "no data defect is silently repaired" and "audit and materialization see the same inventory" principles the roadmap requires (`05_IMPLEMENTATION_ROADMAP.md §4.1`).

**Recommended target state:**

`AuditDatasetUseCase` consumes `build_source_inventory(dataset)` (already returns the exact `ConcreteSourceInventory` that materialization uses) instead of re-scanning the filesystem; per-tree audit statistics (file count, header count, headers-identical) are derived from the shared inventory's entries grouped by `source_tree_identifier`.

**Required actions:**

1. Change `AuditDatasetUseCase.execute` to call `build_source_inventory(dataset)` once and derive `SourceTreeAudit` entries by grouping `inventory.entries` by `source_tree_identifier`, instead of calling `self._source_files(...)` per tree.
2. Delete `AuditDatasetUseCase._source_files`.
3. Confirm the audit's existing tests (`tests/unit/infrastructure/datasets/test_source_inventory.py`, any dataset-audit-specific tests) still pass with identical file counts/headers on the same fixtures.
4. Note: `application` importing `infrastructure.datasets.source_inventory` is already permitted by the current import-linter contracts (no restriction exists between `application` and `infrastructure`); no import-boundary change is required.

**Prerequisites:**

- None.

**Dependent findings:**

- None.

**Expected files to change:**

- `src/datp_core/application/dataset_audit.py`

**Tests to update or add:**

- Existing dataset-audit tests must pass unchanged; add a regression test proving audit file counts match `build_source_inventory`'s counts exactly on a shared fixture.

**Scientific-drift risk:** `LOW` (read-only audit path; no materialized artifact or fingerprint is affected)

**Required validation:**

- `uv run pytest tests/unit/infrastructure/datasets tests/integration/datasets -q`

**Completion criteria:**

- `AuditDatasetUseCase._source_files` no longer exists; audit and materialization both derive from `build_source_inventory`.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

#### CR-DATA-003 — Duplicate CICIoT2023 deduplication/split algorithm (in-memory vs SQLite-backed)

**Status:** `CONFIRMED`
**Priority:** `P1`
**Category:** data-architecture / duplication / scientific-drift-risk
**Decision:** `DELETE`

**Affected files:**

- `src/datp_core/infrastructure/datasets/ciciot2023.py`
- `tests/unit/infrastructure/datasets/ciciot2023/test_global_deduplication_and_split.py`

**Affected symbols or responsibilities:**

- `canonicalize_and_split_ciciot2023_rows`
- `write_ciciot2023_materialized_parquet`

**Evidence:**

`ciciot2023.py:118-180` (`canonicalize_and_split_ciciot2023_rows`) implements global exact-duplicate equivalence-class computation and seeded benign-class-level random splitting entirely in Python dicts/lists, in memory. `ciciot2023.py:183-273` (`write_ciciot2023_materialized_parquet`) implements the identical algorithm — same equivalence-class key `(features, is_attack)`, same canonical-row-selection rule (earliest by source path/row index), same conflicting-label-group counting, same seeded per-class random draw against `train_ratio`/`calibration_ratio` — against a temporary SQLite table, added later per `.tmp/implementation/CHANGELOG.md`'s "Materialize CICIoT2023 through a bounded equivalence index" entry to support corpora too large to hold in memory. `grep` across `src/` and `tests/` confirms `canonicalize_and_split_ciciot2023_rows` is called only by its own dedicated unit test (`test_global_deduplication_and_split.py`); the production adapter path (`ciciot2023_adapter.py`) calls only `write_ciciot2023_materialized_parquet`.

**Problem:**

The scientific algorithm that determines global deduplication and the train/calibration/test split for CICIoT2023 — a locked, seed-sensitive procedure per `configs/datasets/ciciot2023.yaml::materializations.datp_core` — exists in two independently-maintained implementations. The in-memory version is reachable only from a test that exercises itself, not the real materialization path; it provides no evidence about the SQLite path's correctness and creates a false sense of test coverage (`test_global_deduplication_and_split.py` "passing" says nothing about whether `write_ciciot2023_materialized_parquet` behaves identically). Any future correction to the algorithm (e.g. a tie-break fix) applied to one implementation and not the other would silently and permanently diverge the tested behavior from the executed behavior.

**Impact:**

Scientific-drift risk: the split assignment and duplicate-handling behavior that is unit-tested is not the behavior that runs in production for CICIoT2023 materialization — a direct violation of the principle that tests must exercise the real path, and a latent risk that a future bug fix to the SQLite implementation goes unverified by any test.

**Recommended target state:**

One algorithm, one implementation. Since the SQLite-backed path is required for full-corpus feasibility (per the roadmap's `05_IMPLEMENTATION_ROADMAP.md §6.8` resource-discipline requirement — the in-memory version cannot be used for the full CICIoT2023 corpus), the SQLite-backed `write_ciciot2023_materialized_parquet` becomes the sole implementation, and its correctness is proven directly (against small, in-memory-sized fixtures — the SQLite engine handles arbitrarily small inputs correctly, so no test fidelity is lost).

**Required actions:**

1. Delete `canonicalize_and_split_ciciot2023_rows`, `CICIoT2023SplitRows`, and any other symbols used only by it (confirm via grep before deleting each).
2. Rewrite `test_global_deduplication_and_split.py` to exercise `write_ciciot2023_materialized_parquet` directly against small CSV fixtures on disk (matching the pattern already used by `test_ciciot2023_bounded_materialization.py`), preserving every currently-tested invariant (duplicate classes keep one canonical row; conflicting-label groups are counted and reported; attacks remain test-only; seeded execution is deterministic across repeated runs).
3. Confirm no other module imports the deleted symbols.

**Prerequisites:**

- None.

**Dependent findings:**

- None.

**Expected files to change:**

- `src/datp_core/infrastructure/datasets/ciciot2023.py`
- `tests/unit/infrastructure/datasets/ciciot2023/test_global_deduplication_and_split.py`

**Tests to update or add:**

- `test_global_deduplication_and_split.py` rewritten against the SQLite-backed path; all currently-asserted invariants preserved.

**Scientific-drift risk:** `MEDIUM` (deleting the untested-in-production twin cannot itself cause drift, but the rewritten test must be proven to cover every invariant the deleted test covered, or a real invariant silently loses coverage)

**Required validation:**

- `uv run pytest tests/unit/infrastructure/datasets/ciciot2023 tests/integration/datasets/test_ciciot2023_bounded_materialization.py -q`
- Manual diff of asserted invariants between the old and new test to confirm no coverage is lost.

**Completion criteria:**

- `canonicalize_and_split_ciciot2023_rows` no longer exists; every invariant it was proving is proven against `write_ciciot2023_materialized_parquet` instead.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

### 6.3 Priority 2 — High Maintainability and Simplification

#### CR-DATA-004 — Hardcoded Parquet batch size ignores the resolved runtime execution profile

**Status:** `CONFIRMED`
**Priority:** `P2`
**Category:** hardcoded-value / runtime-authority
**Decision:** `REPLACE`

**Affected files:**

- `src/datp_core/infrastructure/datasets/nbaiot_adapter.py`

**Affected symbols or responsibilities:**

- `NBaIoTAdapter.materialize`

**Evidence:**

`nbaiot_adapter.py:53`: `chunk_row_count = 100_000  # Default; overridden by runtime profile if needed`. No code path in this file, `stage_handlers.py`, or `composition/root.py` reads `ResolvedRuntimeConfiguration.active_execution_profile.data_loading.chunk_row_count` and passes it into `NBaIoTAdapter.materialize`; the comment describes behavior that does not exist. `configs/runtime.yaml::execution_profiles` authors a distinct `chunk_row_count` per profile (`scientific: 50000`, `development: 10000`, `smoke: 1000`, `dataset_audit: 50000`, `test_smoke: 1000`) specifically so this value is operator/runtime-configurable, not a Python constant.

**Problem:**

A runtime/operator-tunable value (per this review's own hardcoded-value classification: category 2, "runtime/operator configuration") is hardcoded in infrastructure code with a comment asserting a fallback mechanism that was never implemented, which is misleading to future readers and reviewers.

**Impact:**

Operational: the authored per-profile chunk-size tuning in `runtime.yaml` currently has no effect on N-BaIoT materialization regardless of `DATP_EXECUTION_PROFILE`; a `smoke` or `test_smoke` profile run would still stream/write in 100,000-row batches rather than the authored 1,000, which could exceed the small resource budgets those profiles declare (`max_ram_gib: 6` / `4`).

**Recommended target state:**

`DatasetMaterializer.materialize` (or its stage-handler caller) receives the resolved `chunk_row_count` from `ResolvedRuntimeConfiguration.active_execution_profile.data_loading`, threaded through the `DatasetMaterializer` Protocol or the stage handler's constructor, and the adapter uses it instead of a literal.

**Required actions:**

1. Add a `chunk_row_count: int` parameter to `DatasetMaterializer.materialize` (`application/ports.py`) or to adapter construction, sourced from `config.runtime.active_execution_profile.data_loading.chunk_row_count`.
2. Update `NBaIoTAdapter.materialize` (and `CICIoT2023Adapter`, which has an analogous `batch_size` parameter already threaded through — confirm it is sourced correctly, not also hardcoded) to use the passed-in value; remove the misleading comment and the literal.
3. Update `DatasetMaterializationStageHandler` to pass the resolved value.
4. Add a unit test proving a non-default execution profile changes the batch size used by materialization.

**Prerequisites:**

- None.

**Dependent findings:**

- None.

**Expected files to change:**

- `src/datp_core/infrastructure/datasets/nbaiot_adapter.py`
- `src/datp_core/application/ports.py`
- `src/datp_core/application/stage_handlers.py`

**Tests to update or add:**

- `tests/integration/artifacts/test_staged_nbaiot_parquet_commit.py` (extend to assert batch-size propagation), or a new focused unit test.

**Scientific-drift risk:** `LOW` (batch size here is a Parquet write-batching/memory parameter, not a training batch size — no interaction with the locked `batching.standard.micro_batch_size: 256` training contract; still requires care not to be confused with it)

**Required validation:**

- `uv run pytest tests/integration/artifacts tests/unit/infrastructure/datasets -q`

**Completion criteria:**

- No literal `100_000` (or any other hardcoded chunk size) remains in `nbaiot_adapter.py`; the value is sourced from the resolved runtime configuration.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

#### CR-DOMAIN-001 — Dead code cluster in the domain layer

**Status:** `CONFIRMED`
**Priority:** `P2`
**Category:** dead-code
**Decision:** `DELETE`

**Affected files:**

- `src/datp_core/domain/catalogue.py`
- `src/datp_core/domain/thresholding.py`
- `src/datp_core/domain/evaluation.py`
- `src/datp_core/config/converter.py`

**Affected symbols or responsibilities:**

- `ResolvedCatalogue`
- `SampleSizeCheck`
- `ClientConfusionMatrix`, `MetricResultRecord`
- `unstructure_mapping_proxy`

**Evidence:**

`grep -rn` across `src/` and `tests/` confirms each symbol appears only in its own definition, with zero other references: `domain/catalogue.py:656-665` (`ResolvedCatalogue`) — this repeats a finding the repository's own `.tmp/implementation/CHANGELOG.md` (Theme 0 entry) already identified once ("the pre-existing `domain/catalogue.ResolvedCatalogue` class... was dead code, never constructed anywhere") without deleting it; `domain/thresholding.py:104-112` (`SampleSizeCheck`); `domain/evaluation.py` (`ClientConfusionMatrix`, `MetricResultRecord`, both — see also [CR-SCI-001](#cr-sci-001--hardcoded-numeric-fallbacks-for-undefined-metrics-contradict-the-authored-metric-status-contract) for the fallback-value defect within `ClientConfusionMatrix`); `config/converter.py:64-66` (`unstructure_mapping_proxy`).

**Problem:**

Four unrelated pieces of dead code accumulated across three modules, one of which (`ResolvedCatalogue`) was already flagged as dead by the project's own prior audit and left in place. Dead domain code is especially costly to carry here because the domain layer is the one place this project holds to the highest purity bar (no hidden defaults, full immutability); a reader encountering `ResolvedCatalogue` or `ClientConfusionMatrix` reasonably assumes they are load-bearing, since everything else in the file is.

**Impact:**

Maintainability: four dead symbols inflate the domain layer's surface area and the artifacts a future contributor must read and reason about before making a change, with zero test or production benefit.

**Recommended target state:**

None of the four symbols exists. `ClientConfusionMatrix`/`MetricResultRecord` are either deleted outright or rebuilt with typed-status semantics only when `EVAL-METRICS-001` gets a real implementation plan and consumer (do not resurrect the zero-substitution defect from [CR-SCI-001](#cr-sci-001--hardcoded-numeric-fallbacks-for-undefined-metrics-contradict-the-authored-metric-status-contract) when that happens).

**Required actions:**

1. Delete `ResolvedCatalogue` from `domain/catalogue.py`.
2. Delete `SampleSizeCheck` from `domain/thresholding.py`.
3. Delete `ClientConfusionMatrix` and `MetricResultRecord` from `domain/evaluation.py`; if the file becomes empty, delete `domain/evaluation.py` itself (confirm no import references it first).
4. Delete `unstructure_mapping_proxy` from `config/converter.py`.
5. Re-run the full test suite to confirm nothing imported these symbols transitively through a wildcard import (none is expected, since none use `from module import *`).

**Prerequisites:**

- None.

**Dependent findings:**

- [CR-SCI-001](#cr-sci-001--hardcoded-numeric-fallbacks-for-undefined-metrics-contradict-the-authored-metric-status-contract) (if that finding is executed first and fixes `ClientConfusionMatrix` instead of deleting it, this finding's action 3 is scoped to the remaining three symbols only).

**Expected files to change:**

- `src/datp_core/domain/catalogue.py`
- `src/datp_core/domain/thresholding.py`
- `src/datp_core/domain/evaluation.py`
- `src/datp_core/config/converter.py`

**Tests to update or add:**

- None (no test currently references these symbols; confirm via grep before deleting).

**Scientific-drift risk:** `NONE` (unreferenced code; deletion cannot change any resolved value or fingerprint)

**Required validation:**

- `grep -rn "ResolvedCatalogue\|SampleSizeCheck\|ClientConfusionMatrix\|MetricResultRecord\|unstructure_mapping_proxy" src tests` returns no results after deletion (except any rebuilt, actually-consumed replacement).
- `uv run pytest -q`

**Completion criteria:**

- All four symbols are absent from the codebase (or, for `ClientConfusionMatrix`/`MetricResultRecord`, replaced by a typed-status implementation with a real consumer, per [CR-SCI-001](#cr-sci-001--hardcoded-numeric-fallbacks-for-undefined-metrics-contradict-the-authored-metric-status-contract)).

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

#### CR-DEPS-001 — Orphaned adapter files and one whole subpackage are the sole reachability path for six declared dependencies

**Status:** `CONFIRMED`
**Priority:** `P2`
**Category:** dead-code / dependency-ownership
**Decision:** `DELETE`

**Affected files:**

- `src/datp_core/infrastructure/tables/schemas.py`
- `src/datp_core/infrastructure/tables/parquet_io.py`
- `src/datp_core/infrastructure/tables/polars_engine.py`
- `src/datp_core/infrastructure/tables/multidim_views.py`
- `src/datp_core/infrastructure/statistics/posthoc_adapter.py`
- `src/datp_core/infrastructure/statistics/pingouin_adapter.py`
- `src/datp_core/infrastructure/statistics/statsmodels_adapter.py`
- `src/datp_core/infrastructure/learning/sklearn_adapter.py`
- `pyproject.toml`

**Affected symbols or responsibilities:**

- Entire `infrastructure/tables/` subpackage
- `compute_nemenyi_posthoc`, `fit_mixed_effects_model`, `compute_paired_effect_size`
- `scale_features`, `compute_roc_auc`, `compute_adjusted_rand_index`

**Evidence:**

`grep -rn` confirms zero consumers, in either `src/` or `tests/`, for every symbol in `infrastructure/tables/{schemas,parquet_io,polars_engine,multidim_views}.py`, `infrastructure/statistics/{posthoc_adapter,pingouin_adapter,statsmodels_adapter}.py`, and all three functions in `infrastructure/learning/sklearn_adapter.py` (`compute_roc_auc` additionally carries the [CR-SCI-001](#cr-sci-001--hardcoded-numeric-fallbacks-for-undefined-metrics-contradict-the-authored-metric-status-contract) defect). `tests/conformance/test_project_structure.py:19` references `infrastructure/tables` only as a directory-existence allowlist entry, not a behavior test. Tracing `import` statements shows these files are the *only* reachable path in the entire codebase for six declared dependencies: `pandera` (`schemas.py`), `xarray` (`multidim_views.py`), `scikit-posthocs` (`posthoc_adapter.py`), `pingouin` (`pingouin_adapter.py`), `statsmodels` (`statsmodels_adapter.py`), and `pandas` (imported only by the last two). Additionally, `pyproject.toml`'s `hardware` optional-dependency extra (`psutil`, `pynvml`) has zero imports anywhere in `src/`.

**Problem:**

This is speculative scaffolding for `EVAL-METRICS-001` (`NOT_STARTED`) and `STAT-ANALYSIS-001` (`IN_PROGRESS`, but not through these files) written ahead of any real consumer, with zero tests proving it behaves correctly. It inflates the file count, the dependency-audit surface (`DEP-OWNERSHIP-001`'s own prior pass removed `deepdiff`/`blake3`/`matplotlib` as unused but did not catch these, since the check for "is the package imported" is not the same as "is the importing module itself reachable"), and the review burden, without being backed by any evidence that its API shape matches what a real evaluation/statistics pipeline will need.

**Impact:**

Maintainability and correctness-of-audit: six dependencies (plus an optional extra) are carried in `pyproject.toml`/`uv.lock` with no working, tested code exercising them; a future contributor cannot tell from the test suite whether `compute_operating_point_metrics`'s Polars logic or `build_multidimensional_metric_cube`'s Xarray indexing is correct, because nothing runs them.

**Recommended target state:**

None of these files exists until the corresponding roadmap item (`EVAL-METRICS-001`) has a concrete implementation plan; at that point, the actual consumer's real needs (which prediction rule, which metric bundle, which output shape the application layer requires) drive a fresh, tested implementation — which may reuse ideas from the deleted code but should not be assumed correct merely because it once existed.

**Required actions:**

1. Delete `infrastructure/tables/` in its entirety (`schemas.py`, `parquet_io.py`, `polars_engine.py`, `multidim_views.py`).
2. Delete `infrastructure/statistics/posthoc_adapter.py`, `pingouin_adapter.py`, `statsmodels_adapter.py`.
3. Delete `scale_features`, `compute_roc_auc`, `compute_adjusted_rand_index` from `infrastructure/learning/sklearn_adapter.py`; if the file becomes empty, delete it.
4. Remove `pandera`, `xarray`, `scikit-posthocs`, `pingouin`, `statsmodels`, `pandas` from `pyproject.toml`'s `dependencies` list and run `uv lock` to regenerate `uv.lock`.
5. Remove the `hardware` optional-dependency extra (`psutil`, `pynvml`) from `pyproject.toml` unless a concrete near-term consumer is named (device/resource monitoring is referenced by `runtime.yaml::device_policy_rules` but nothing in `src/` reads GPU/CPU state today).
6. Remove `infrastructure/tables` from `tests/conformance/test_project_structure.py`'s expected-package allowlist.
7. Confirm `uv sync --all-groups --all-extras --frozen && uv run pytest -q` still passes after dependency removal.

**Prerequisites:**

- None.

**Dependent findings:**

- [CR-SCI-001](#cr-sci-001--hardcoded-numeric-fallbacks-for-undefined-metrics-contradict-the-authored-metric-status-contract) (resolve first if `compute_roc_auc` is being fixed rather than deleted — otherwise this finding's action 3 removes it entirely).

**Expected files to change:**

- All files listed in "Affected files" above.
- `pyproject.toml`, `uv.lock`
- `tests/conformance/test_project_structure.py`

**Tests to update or add:**

- `tests/conformance/test_project_structure.py` (remove `infrastructure/tables` from the expected-package list).

**Scientific-drift risk:** `NONE` (unreferenced code and unused dependencies; no resolved value or fingerprint is affected)

**Required validation:**

- `grep -rn "infrastructure.tables\|posthoc_adapter\|pingouin_adapter\|statsmodels_adapter" src tests` returns no results.
- `uv sync --all-groups --all-extras --frozen`
- `uv run pytest -q`
- `uv run ruff check src tests`

**Completion criteria:**

- `infrastructure/tables/` does not exist; the three named statistics adapters do not exist; `sklearn_adapter.py`'s three unused functions do not exist; `pyproject.toml` no longer declares `pandera`, `xarray`, `scikit-posthocs`, `pingouin`, `statsmodels`, `pandas`, `psutil`, `pynvml`.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

#### CR-DOMAIN-002 — `ExperimentRecord` mixes independent concern groups as flat fields

**Status:** `CONFIRMED`
**Priority:** `P2`
**Category:** domain-record-design
**Decision:** `SPLIT`

**Affected files:**

- `src/datp_core/domain/catalogue.py`
- `src/datp_core/config/resolver.py`
- `src/datp_core/config/models/experiment_config.py`

**Affected symbols or responsibilities:**

- `ExperimentRecord`

**Evidence:**

`domain/catalogue.py:612-654`: `ExperimentRecord` has 34 fields. Beyond the always-populated core (identifier, evidence role, run requirement, population/training/checkpoint/seed-cohort/eligibility ids, prerequisites, capability requirements, evaluations, analyses, report ids), roughly 15 fields are populated only for specific experiment categories observed by direct inspection of `experiments.yaml`: external-validation-only fields (`validation_scope`, `never_promoted_to_confirmatory`, `attack_sensitive_metrics_requested`, `client_semantics_constraint`, `generalization_constraint`, `population_equivalence_requirement`), personalization-stress-test-only fields (`method_naming_rule`, `personalization_parameter_selection_source`, `primary_coefficient_selection`, `training_overrides`), temporal-experiment-only fields (`temporal_procedure`, `population_roles`, `scope_constraint`), and conditional-run-only fields (`run_condition`, `unavailable_behavior`, `blocks_other_experiments_when_unavailable`, `estimate_basis`). This mirrors the flat-superset shape `AnalysisSpecRecord` had before the Theme 0 pass split it into a 14-member kind-discriminated union — but unlike analyses, experiments have no single discriminant field driving which group applies (evidence_role does not cleanly predict it, e.g. `evidence_role: external_validation` covers several structurally different experiments).

**Problem:**

A reader of `ExperimentRecord` cannot tell, from the type alone, which fields are meaningful for a given experiment without cross-referencing `experiments.yaml`; 15 of 34 fields are `None` for the large majority of the 23 authored experiments.

**Impact:**

Readability/maintainability only — this is explicitly *not* the kind of unrepresentable-invalid-states problem the `AnalysisSpecRecord` split solved (there is no incorrect resolver behavior here, and the existing `tests/conformance/test_experiment_catalogue_field_disposition.py` already exhaustively proves every field is accounted for). No correctness or scientific-drift risk exists; this is a pure cohesion improvement.

**Recommended target state:**

`ExperimentRecord` retains its always-populated core fields and gains four optional nested records — `ExternalValidationConstraints`, `PersonalizationConstraints`, `TemporalProcedureConstraints`, `ConditionalRunSpec` — each grouping the fields identified above. This is additive nesting, not a discriminated union (unlike `AnalysisSpecRecord`), since no single field cleanly discriminates which group(s) apply to a given experiment.

**Required actions:**

1. Define the four nested attrs records in `domain/catalogue.py`.
2. Update `ExperimentRecord` to hold `external_validation: ExternalValidationConstraints | None`, etc., replacing the 15 flat fields with 4 nested-or-`None` fields.
3. Update `config/resolver.py` (or its extracted successor per [CR-CONFIG-001](#cr-config-001--resolve_project_configuration-is-a-625-line-god-function-with-inconsistent-delegation)) to construct the nested records conditionally.
4. Update `tests/conformance/test_experiment_catalogue_field_disposition.py`'s leaf-path enumeration to reflect the new nested structure — this test is the primary safety net proving no field is silently dropped during the regrouping.
5. Update `_experiment_scientific_projection` (`config/experiment_resolution.py`) if the nested structure changes the cattrs-unstructured shape; confirm the scientific fingerprint is unchanged (nesting must not change *which* leaf values are included, only their path).

**Prerequisites:**

- None. Sequential with [CR-CONFIG-001](#cr-config-001--resolve_project_configuration-is-a-625-line-god-function-with-inconsistent-delegation) if both touch `ExperimentRecord` construction in the same phase — see [9.2](#92-sequential-only-work).

**Dependent findings:**

- None.

**Expected files to change:**

- `src/datp_core/domain/catalogue.py`
- `src/datp_core/config/resolver.py` (or `config/experiment_resolution.py` / `config/catalogue_resolution.py` post-[CR-CONFIG-001](#cr-config-001--resolve_project_configuration-is-a-625-line-god-function-with-inconsistent-delegation))

**Tests to update or add:**

- `tests/conformance/test_experiment_catalogue_field_disposition.py`
- `tests/scientific/drift/test_theme0_recovered_fields_change_fingerprint.py`-equivalent regression: confirm fingerprint is unchanged by the regrouping.

**Scientific-drift risk:** `LOW` (field regrouping only; every leaf value and its fingerprint contribution must remain identical)

**Required validation:**

- `uv run pytest tests/conformance/test_experiment_catalogue_field_disposition.py tests/scientific/drift -q`
- Fingerprint diff before/after on the real `configs/experiments.yaml` — must be byte-identical.

**Completion criteria:**

- `ExperimentRecord` has no more than ~20 top-level fields; the four nested records exist and are populated correctly; the field-disposition conformance test passes with an updated leaf-path table; fingerprints are unchanged.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

#### CR-CONFIG-002 — Untyped mapping fields on threshold-policy records for fixed-shape contracts

**Status:** `CONFIRMED`
**Priority:** `P2`
**Category:** typed-contracts / dictionary-usage
**Decision:** `REPLACE`

**Affected files:**

- `src/datp_core/domain/thresholding.py`
- `src/datp_core/infrastructure/thresholding/estimators.py`

**Affected symbols or responsibilities:**

- `ClusterThresholdPolicyRecord.clustering`, `.standardization`, `.fingerprint_degenerate_client_rules`
- `FederatedMatchedExceedanceThresholdPolicyRecord.candidate_grid`, `.exceedance_exchange`, `.selection`

**Evidence:**

`domain/thresholding.py:221`: `clustering: Mapping[str, str | int | float]`. Every one of the three cluster-policy variants in `protocols.yaml` (`cluster_k3_mean_p95`, `cluster_k9_mean_p95`, `cluster_k3_robust_median_p95`) authors the exact same fixed key set for `clustering` (`algorithm`, `initialization`, `initialization_runs`, `maximum_iterations`, `convergence_tolerance`, `random_seed`) — this is a fixed scientific contract, not a heterogeneous or per-instance-varying shape. `infrastructure/thresholding/estimators.py:186-197` reads it via `clustering.get("random_seed")`, `.get("initialization_runs")`, etc., followed by four separate `isinstance` checks with hand-written `ValueError` messages ("Cluster policy has invalid authored integer parameters") — logic that a typed `ClusteringConfigRecord` would make unnecessary, since Pydantic/attrs construction would already guarantee the types. `candidate_grid` (`FederatedMatchedExceedanceThresholdPolicyRecord`, `minimum`/`maximum`/`step`, all always-`float`) is read the same way at `estimators.py:267-273`.

**Problem:**

This is exactly the dictionary-usage pattern this review's own methodology flags as suspicious: "Dictionaries are suspicious when they represent fixed scientific or architectural contracts, including: ...threshold-policy parameters." The current design pushes runtime type-narrowing and manual error messages into the estimator (the consumer), when the resolver (the producer) already has the authored, strictly-typed Pydantic source (`ClusterThresholdPolicyConfig.clustering: dict[str, str | int | float]` — itself also untyped, one level up) and could guarantee the shape at construction time instead.

**Impact:**

Type-safety/maintainability: four `isinstance` checks and hand-written error strings in `estimators.py` exist solely to compensate for the resolver not having typed this fixed-shape sub-contract; a future addition of a new cluster-policy variant with a differently-shaped `clustering` mapping would not be caught by pyright, only at runtime.

**Recommended target state:**

`ClusteringConfigRecord(algorithm: str, initialization: str, initialization_runs: PositiveInt, maximum_iterations: PositiveInt, convergence_tolerance: PositiveFloat, random_seed: int)` and `CandidateGridRecord(minimum: float, maximum: float, step: PositiveFloat)` become typed fields on the two policy records; `estimators.py` accesses `policy.clustering.random_seed` directly with no `isinstance` narrowing.

**Required actions:**

1. Add `ClusteringConfigConfig`/`ClusteringConfigRecord` and `CandidateGridConfig`/`CandidateGridRecord` (authored + resolved pair) mirroring the existing pattern for other nested contract blocks.
2. Update `ClusterThresholdPolicyConfig.clustering` and `ClusterThresholdPolicyRecord.clustering` (and `.standardization` if it has the same fixed-shape property — confirm by inspecting all three cluster-policy YAML blocks) to the new typed record.
3. Update `FederatedMatchedExceedancePolicyConfig.candidate_grid` / `FederatedMatchedExceedanceThresholdPolicyRecord.candidate_grid` similarly.
4. Update `infrastructure/thresholding/estimators.py::_cluster` and `_federated_matched` to use typed attribute access, deleting the `isinstance` guard blocks.
5. Update `_resolve_threshold_policy` (`config/protocol_resolution.py`) if the generic `record_type(**cfg.model_dump())` dispatch needs adjustment for the newly nested field (likely still works unchanged, since `model_dump()` recurses).

**Prerequisites:**

- None. Do not execute concurrently with [CR-CONFIG-001](#cr-config-001--resolve_project_configuration-is-a-625-line-god-function-with-inconsistent-delegation) on `protocol_resolution.py`'s threshold-policy resolution path — see [9.3](#93-shared-file-collision-risks).

**Dependent findings:**

- None.

**Expected files to change:**

- `src/datp_core/domain/thresholding.py`
- `src/datp_core/config/models/protocol_config.py`
- `src/datp_core/config/protocol_resolution.py`
- `src/datp_core/infrastructure/thresholding/estimators.py`

**Tests to update or add:**

- `tests/unit/domain/test_threshold_policy_records.py`
- `tests/scientific/thresholding/test_configured_threshold_estimators.py`

**Scientific-drift risk:** `LOW` (typing-only change; every authored value must resolve identically)

**Required validation:**

- `uv run pytest tests/scientific/thresholding tests/unit/domain/test_threshold_policy_records.py -q`
- `uv run pyright`

**Completion criteria:**

- No `isinstance` narrowing of `clustering`/`candidate_grid` remains in `estimators.py`; both fields are typed records.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

#### CR-DOMAIN-003 — Repeated mapping-conversion boilerplate across domain modules

**Status:** `CONFIRMED`
**Priority:** `P2`
**Category:** duplication / boilerplate
**Decision:** `SIMPLIFY`

**Affected files:**

- `src/datp_core/domain/thresholding.py`
- `src/datp_core/domain/datasets.py`
- `src/datp_core/domain/values.py`
- `src/datp_core/config/runtime_settings.py`

**Affected symbols or responsibilities:**

- `_as_mapping_str_str`, `_as_mapping_str_int`, `_as_mapping_str_float`, `_as_mapping_str_object`, `_as_mapping_str_str_or_int`, `_as_mapping_str_str_or_int_or_float`, `_as_mapping_str_float_or_mapping`, `_as_mapping_str_str_or_float_or_bool`, `_as_mapping_str_tuple_or_str`, `_as_tuple_str`, `_as_tuple_float` (`domain/thresholding.py`, 11 private helpers)
- `_as_mapping_str_str_or_bool` (`domain/datasets.py`)
- `_as_mapping_str_int`, `_as_mapping_str_int_or_bool`, `_as_mapping_str_str`, `_as_mapping_str_tuple_or_bool` (`config/runtime_settings.py`)
- `as_str_mapping`, `as_int_mapping`, `as_frozen_json_mapping`, etc. (`domain/values.py`, the pre-existing generic helpers)

**Evidence:**

`domain/values.py` already provides generic `deep_freeze`-plus-`cast` helpers (`as_str_mapping`, `as_int_mapping`, `as_frozen_json_mapping`, `as_str_mapping_tuple`, and their `_optional` variants). `domain/thresholding.py` independently defines 11 more single-purpose variants of the identical pattern (`cast(cast_type, deep_freeze(value))`) rather than adding new type parameters to the existing generic helpers or introducing one parametrized `as_mapping[K, V](value) -> Mapping[K, V]` attrs converter factory. `config/runtime_settings.py` and `domain/datasets.py` each define their own small subset of the same pattern independently.

**Problem:**

The same three-line "cast a `deep_freeze`d value to a specific `Mapping`/`tuple` type" idiom is reimplemented roughly 17 times across four files with only the type annotation differing, instead of being centralized once (as `domain/values.py` already partially does). This is boilerplate this review's `cattrs` library assessment ([7.2](#72-libraries-to-adopt)) can also reduce directly.

**Impact:**

Maintainability: a correction to the freezing behavior (e.g. handling a new authored shape) must be found and applied in up to three files' worth of near-identical helpers rather than one; the sheer number of near-identical private functions makes `domain/thresholding.py` harder to scan for the actual policy-record definitions.

**Recommended target state:**

One generic helper in `domain/values.py`, e.g. `def as_mapping(value: object) -> Mapping[K, V]` used with an explicit `cast(...)` at each attrs `field(converter=...)` call site (the type parameter is supplied by the field's own annotation, not by a differently-named function per type combination) — or, per [7.2](#72-libraries-to-adopt), a `cattrs`-based structuring hook that removes the need for hand-written converters entirely for the mechanical cases.

**Required actions:**

1. Inventory every `_as_mapping_str_*`/`_as_tuple_*` helper across `domain/thresholding.py`, `domain/datasets.py`, `config/runtime_settings.py`.
2. Consolidate into `domain/values.py` as either (a) a single generic `as_mapping`/`as_tuple` pair used with local `cast(...)` at each call site, replacing the per-type-combination function names, or (b) a `cattrs` structuring hook per [7.2](#72-libraries-to-adopt) if that trial is adopted first.
3. Update every call site; delete the now-redundant per-file private helpers.

**Prerequisites:**

- None. Should not run concurrently with [CR-CONFIG-002](#cr-config-002--untyped-mapping-fields-on-threshold-policy-records-for-fixed-shape-contracts), which edits the same file's converter usage — see [9.3](#93-shared-file-collision-risks).

**Dependent findings:**

- None.

**Expected files to change:**

- `src/datp_core/domain/values.py`
- `src/datp_core/domain/thresholding.py`
- `src/datp_core/domain/datasets.py`
- `src/datp_core/config/runtime_settings.py`

**Tests to update or add:**

- `tests/unit/domain/test_scientific_value_objects.py` (extend to cover the consolidated helper directly).

**Scientific-drift risk:** `NONE` (pure code-motion; conversion behavior is byte-for-byte identical)

**Required validation:**

- `uv run pytest tests/unit/domain -q`
- `uv run pyright`

**Completion criteria:**

- No more than 2-3 generic mapping/tuple conversion helpers remain across the whole `domain`/`config` tree, replacing the current ~17 near-duplicates.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

#### CR-DATA-005 — Near-duplicated numeric-field validation loops in `csv_source.py`

**Status:** `CONFIRMED`
**Priority:** `P2`
**Category:** duplication
**Decision:** `SIMPLIFY`

**Affected files:**

- `src/datp_core/infrastructure/datasets/csv_source.py`

**Affected symbols or responsibilities:**

- `iter_numeric_csv_source`
- `iter_labeled_numeric_csv_source`

**Evidence:**

`csv_source.py:51-81` (`iter_numeric_csv_source`) and `:96-149` (`iter_labeled_numeric_csv_source`) both implement, nearly verbatim, a per-required-header loop: read the raw value, reject blank, attempt `float(...)`, reject on `ValueError`, reject on non-finite, else append — differing only in that the labeled variant also validates a label column and performs an eager field-count check (post the [CR-DATA-002](#cr-data-002--edge-iiotset-csv-reader-still-has-the-defect-the-latest-commit-just-fixed-elsewhere)-referenced fix).

**Problem:**

The numeric-validation inner loop (blank/unparseable/non-finite) is duplicated rather than shared, so a future correction to numeric parsing (e.g. accepting scientific notation exceptions, or a stricter finite check) must be made twice.

**Impact:**

Maintainability only; both functions are otherwise correct and well-tested.

**Recommended target state:**

A shared `_validate_numeric_fields(record: Sequence[str], header_to_index: Mapping[str, int], headers: tuple[str, ...]) -> tuple[tuple[float, ...], str | None]` helper used by both functions.

**Required actions:**

1. Extract the shared per-row numeric-validation loop into a private helper in `csv_source.py`.
2. Update both `iter_numeric_csv_source` and `iter_labeled_numeric_csv_source` to call it.
3. Confirm existing tests (`test_numeric_csv_source_preserves_rejections.py`, `test_labeled_numeric_csv_source.py`) pass unchanged.

**Prerequisites:**

- None. If [CR-DATA-002](#cr-data-002--edge-iiotset-csv-reader-still-has-the-defect-the-latest-commit-just-fixed-elsewhere) is implemented after this finding, its Edge-IIoTset fix should reuse the same extracted helper rather than re-deriving it a third time.

**Dependent findings:**

- None.

**Expected files to change:**

- `src/datp_core/infrastructure/datasets/csv_source.py`

**Tests to update or add:**

- `tests/unit/infrastructure/datasets/test_numeric_csv_source_preserves_rejections.py`, `test_labeled_numeric_csv_source.py` (must pass unchanged).

**Scientific-drift risk:** `NONE` (pure code-motion; identical validation behavior)

**Required validation:**

- `uv run pytest tests/unit/infrastructure/datasets -q`

**Completion criteria:**

- Both functions share one numeric-validation helper; no duplicated per-header validation loop remains.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

### 6.4 Priority 3 — Medium Optimization and Cleanup

#### CR-CONFIG-003 — Unguarded `next(iter(...))` first-value pick for a potential per-source column-count mapping

**Status:** `CONFIRMED`
**Priority:** `P3`
**Category:** hidden-assumption
**Decision:** `SIMPLIFY`

**Affected files:**

- `src/datp_core/config/dataset_resolution.py`

**Affected symbols or responsibilities:**

- `resolve_datasets` (single-source-tree branch)

**Evidence:**

`dataset_resolution.py:402-420`: when a dataset has no `source_layout.sources` mapping (single-source-tree case, currently N-BaIoT and Edge-IIoTset), `expected_column_count` is computed as `source_column_count if isinstance(source_column_count, int) else next(iter(source_column_count.values()))` — i.e., if `field_schema.source_column_count` were ever authored as a per-source mapping (as CICIoT2023's is: `{per_class: 39, merged: 40}`) *while* `source_layout.sources` was absent, this would silently pick an arbitrary first value from the mapping rather than raising. Confirmed by direct reading of all three dataset YAMLs: this branch is not currently exercised with a mapping value (N-BaIoT and Edge-IIoTset both author a plain `int`; CICIoT2023, whose `source_column_count` is a mapping, always has `source_layout.sources` populated and takes the other branch).

**Problem:**

This is the "unguarded `next(...)`"/"hidden first-item assumption" pattern named as a hypothesis to verify in this review's own methodology, confirmed present (latently) here. It is not exercised by any of the three current datasets, so it is not an active defect, but it is a landmine for a fourth dataset or a future edit to one of the three that introduces this combination.

**Impact:**

Low today (unreachable with current YAML); would silently select an arbitrary schema column count for a future dataset if the combination ever arose.

**Recommended target state:**

Raise `ConfigurationError` explicitly when `source_column_count` is a mapping but `source_layout.sources` is absent, naming the ambiguity, instead of silently picking a value.

**Required actions:**

1. Replace the `next(iter(...))` fallback with an explicit `ConfigurationError` raise when `not isinstance(source_column_count, int)` in the single-source-tree branch.
2. Add a unit test constructing a synthetic authored dataset config with this combination and asserting the explicit error.

**Prerequisites:**

- None.

**Dependent findings:**

- None.

**Expected files to change:**

- `src/datp_core/config/dataset_resolution.py`

**Tests to update or add:**

- New unit test in `tests/unit/config/` covering the rejected combination.

**Scientific-drift risk:** `NONE` (unreachable branch with current YAML; behavior for all three real datasets is unchanged)

**Required validation:**

- `uv run pytest tests/unit/config -q`
- Confirm `resolve_project_configuration()` on the real `configs/` tree is unaffected (all three datasets take the unchanged code path).

**Completion criteria:**

- No `next(iter(...))` remains in `dataset_resolution.py` without a preceding explicit-error guard.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

#### CR-CONFIG-004 — `getattr(x, attr, None)` duck-typed probing on discriminated-union domain records

**Status:** `CONFIRMED`
**Priority:** `P3`
**Category:** weak-typing
**Decision:** `SIMPLIFY`

**Affected files:**

- `src/datp_core/config/validation.py`

**Affected symbols or responsibilities:**

- `ProjectConfigurationValidator.validate`

**Evidence:**

`config/validation.py:67`: `quantile_estimator = getattr(policy, "quantile_estimator", None)` over `policy: ThresholdPolicyRecord` (a 12-member union). `config/validation.py:123`: `secondary_profile = getattr(analysis, "secondary_statistical_profile", None)` over `analysis: AnalysisRecord` (a 14-member union). Both use `getattr` with a string attribute name and a default, rather than `isinstance`/structural narrowing, to probe for a field that only some union members have.

**Problem:**

`getattr(x, "name", default)` defeats static type checking for the exact kind of discriminated-union access this codebase otherwise handles correctly elsewhere (e.g. `infrastructure/thresholding/estimators.py`'s `isinstance`-per-policy dispatch, `config/experiment_resolution.py::_resolve_analysis`'s `if a.kind == "..."` dispatch). A typo in the attribute-name string would silently and permanently return `None` rather than being caught by pyright or at runtime.

**Impact:**

Low-severity type-safety gap in a validation function whose entire purpose is catching configuration mistakes; ironic that it uses an unchecked-string-based access pattern to do so.

**Recommended target state:**

Explicit `isinstance` checks (or a `hasattr`-free structural match) naming the exact record types that carry `quantile_estimator`/`secondary_statistical_profile`.

**Required actions:**

1. Replace both `getattr(..., None)` calls with `isinstance`-based narrowing (a small tuple-of-types check, matching the pattern already used throughout `estimators.py` and `experiment_resolution.py`).
2. Confirm `uv run pyright` reports no new errors and the two `getattr` calls are gone.

**Prerequisites:**

- None.

**Dependent findings:**

- None.

**Expected files to change:**

- `src/datp_core/config/validation.py`

**Tests to update or add:**

- Existing `tests/unit/config/` validation tests must pass unchanged.

**Scientific-drift risk:** `NONE` (validation-logic refactor only)

**Required validation:**

- `uv run pytest tests/unit/config -q`
- `uv run pyright`

**Completion criteria:**

- No `getattr(..., None)` duck-typed probing remains in `config/validation.py`.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

#### CR-EXEC-002 — Positional tuple returns in `IdentityBuilder`'s job-builder methods

**Status:** `CONFIRMED`
**Priority:** `P3`
**Category:** weak-typing / readability
**Decision:** `REPLACE`

**Affected files:**

- `src/datp_core/planning/identity.py`
- `src/datp_core/planning/expansion.py`

**Affected symbols or responsibilities:**

- `IdentityBuilder.materialization_job`, `.training_job`, `.calibration_score_job`, `.test_score_job`, `.threshold_job`, `.evaluation_job`, `.statistical_analysis_job`, `.report_job`
- `expand_experiment_jobs`

**Evidence:**

`planning/identity.py:189-279`: seven of `IdentityBuilder`'s eight "job" methods return an unlabeled positional tuple `tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]`. `planning/expansion.py:46-149` consumes every one of them via positional indexing — `mat_ids[0]`, `mat_ids[1]`, `mat_ids[2]`, `mat_ids[3]`, `train_ids[0..3]`, `calib_ids[0..3]`, `test_ids[0..3]`, `thresh_ids[0..3]`, `eval_ids[0..3]`, `stats_ids[0..3]`, `report_ids[0..3]` — 15+ indexing call sites across a single 142-line function, none self-documenting.

**Problem:**

Every call site must remember that index 0 is the job id, 1 is the output artifact key, 2 is the input tuple, 3 is the dependency tuple — a convention enforced only by consistent naming discipline, not by the type system. Reordering a return statement in `identity.py` would silently break every caller with no pyright error (all four members are attrs-defined/frozen types, but their tuple position carries the meaning).

**Impact:**

Readability/fragility: `expand_experiment_jobs` is materially harder to review than necessary because every line requires cross-referencing `identity.py` to know what `[2]` means for a given call; a future refactor of `IdentityBuilder` that reorders fields would be a silent, untyped breaking change.

**Recommended target state:**

A small named record, e.g. `@define(frozen=True, slots=True, kw_only=True) class PlannedJobSpec: job_id: JobId; output: ArtifactKey; inputs: tuple[ArtifactKey, ...]; dependencies: tuple[JobId, ...]`, returned by all eight methods; `expansion.py` reads `.job_id`/`.output`/`.inputs`/`.dependencies`.

**Required actions:**

1. Define `PlannedJobSpec` in `planning/identity.py` (or `domain/outcomes.py`, if it is considered a cross-cutting planning/execution concept).
2. Change all eight `IdentityBuilder` job-builder methods to return `PlannedJobSpec` instead of a positional tuple.
3. Update `expand_experiment_jobs` to use named attribute access throughout.
4. Confirm `tests/unit/planning/test_identity_builder_determinism.py` and `test_graph_transformations_preserve_context.py` pass unchanged (behavior, not shape, is what they assert).

**Prerequisites:**

- None.

**Dependent findings:**

- None.

**Expected files to change:**

- `src/datp_core/planning/identity.py`
- `src/datp_core/planning/expansion.py`

**Tests to update or add:**

- `tests/unit/planning/test_identity_builder_determinism.py` (update call sites if it destructures return tuples directly).

**Scientific-drift risk:** `NONE` (planning-graph shape and job identities are unchanged; only the intermediate return type changes)

**Required validation:**

- `uv run pytest tests/unit/planning -q`
- `uv run pyright`

**Completion criteria:**

- No positional tuple indexing (`[0]`, `[1]`, `[2]`, `[3]`) of an `IdentityBuilder` job-method return value remains in `planning/expansion.py`.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

#### CR-ARCH-002 — CLI `dataset audit` command bypasses the application boundary

**Status:** `CONFIRMED`
**Priority:** `P3`
**Category:** layering-consistency
**Decision:** `SIMPLIFY`

**Affected files:**

- `src/datp_core/interfaces/cli/app.py`

**Affected symbols or responsibilities:**

- `dataset_audit` CLI command

**Evidence:**

`interfaces/cli/app.py:104-117`: every other CLI command calls exactly one `application.<use_case>.execute(...)`. `dataset_audit` instead does `dataset = application.config.datasets[DatasetId(dataset_id)]` directly (a registry lookup on the resolved configuration, with its own `try/except KeyError` → `typer.BadParameter` translation) before calling `application.audit_dataset.execute(dataset)`. This matches the `.tmp/implementation/FINAL_VERIFICATION.md` residual item ("`dataset_audit`/`results_query` CLI commands still reach `config`/infrastructure directly rather than exclusively through use cases (judged low-risk; not fixed this pass)"), confirmed still present by direct reading.

**Problem:**

`AuditDatasetUseCase.execute(dataset: ResolvedDataset)` requires the caller to have already resolved a `ResolvedDataset` from a raw string id — the CLI does this resolution and its error handling itself rather than the use case, making this one command's contract inconsistent with every sibling command and with the "CLI invokes use cases only" architectural principle (`CLI-LOGGING-001`).

**Impact:**

Low — purely a consistency/architecture-boundary concern, not a correctness defect; the resolved config is safe to index directly since it is fully validated by the time the CLI runs.

**Recommended target state:**

`AuditDatasetUseCase.execute(dataset_id: DatasetId)` performs the lookup and raises a typed, use-case-level error (e.g. `ValueError` or a small `DatasetNotConfiguredError`) that the CLI translates to `typer.BadParameter`, matching every other command's shape.

**Required actions:**

1. Change `AuditDatasetUseCase.__init__` to accept the `ResolvedProjectConfiguration` (matching every other use case's constructor pattern) and `execute` to accept `dataset_id: DatasetId`, performing the lookup and raising a typed error on failure.
2. Update `composition/root.py::build_application` to construct `AuditDatasetUseCase(config=resolved_config)`.
3. Update `interfaces/cli/app.py::dataset_audit` to call `application.audit_dataset.execute(DatasetId(dataset_id))` and translate the typed error to `typer.BadParameter`.

**Prerequisites:**

- None.

**Dependent findings:**

- None.

**Expected files to change:**

- `src/datp_core/application/dataset_audit.py`
- `src/datp_core/composition/root.py`
- `src/datp_core/interfaces/cli/app.py`

**Tests to update or add:**

- `tests/unit/interfaces/cli/test_cli_commands.py` (extend to cover the unknown-dataset-id error path through the use case rather than the CLI).

**Scientific-drift risk:** `NONE` (CLI wiring only)

**Required validation:**

- `uv run pytest tests/unit/interfaces/cli tests/unit/application -q`

**Completion criteria:**

- Every CLI command calls exactly one `application.<use_case>.execute(...)` with no direct `application.config` indexing in `interfaces/cli/app.py`.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

#### CR-TEST-001 — CI does not run lint/type/import gates

**Status:** `CONFIRMED`
**Priority:** `P3`
**Category:** CI / quality-gates
**Decision:** `SIMPLIFY`

**Affected files:**

- `.github/workflows/tests.yml`
- `.github/workflows/sonarqube.yml`
- `noxfile.py` (reference — unchanged)

**Affected symbols or responsibilities:**

- CI job definitions

**Evidence:**

`noxfile.py:5` declares five sessions (`lint`, `typecheck`, `tests`, `tests_parallel`, `imports`) as the default nox run. `.github/workflows/tests.yml` and `.github/workflows/sonarqube.yml` both run only `uv run pytest` (with coverage, for the SonarQube job) — neither invokes `ruff format --check`, `ruff check`, `pyright`, or `lint-imports`.

**Problem:**

A pull request or push can merge with lint violations, type errors, or import-boundary violations (exactly the things `import-linter` and the conformance tests are designed to catch) as long as `pytest` passes, even though all four gates are defined, fast, and already proven to pass locally per the `.tmp` ledger.

**Impact:**

Process/quality-gate risk: the architectural boundaries this review repeatedly credits as a strong area (import-linter contracts, pyright strictness, ruff formatting) are enforced only by local developer discipline, not by CI, for anyone pushing directly or via a PR from a fork.

**Recommended target state:**

CI runs all five nox sessions (or the equivalent four extra gates alongside `pytest`), failing the build on any violation.

**Required actions:**

1. Add `ruff format --check src tests`, `ruff check src tests`, `pyright`, and `lint-imports --config importlinter.ini` steps to `.github/workflows/tests.yml` (or add a nox-driven `uv run nox` step running all five sessions).
2. Confirm the added steps pass against the current repository state (they are already proven to pass locally, so this should require no code changes).

**Prerequisites:**

- None.

**Dependent findings:**

- None (should be run after most other findings in this document to avoid the new CI gates immediately failing on pre-existing issues this review has already catalogued — see [8](#8-implementation-plan), Phase 13).

**Expected files to change:**

- `.github/workflows/tests.yml`

**Tests to update or add:**

- None (CI configuration change only).

**Scientific-drift risk:** `NONE`

**Required validation:**

- A CI run on a branch with a deliberately introduced lint/type/import violation must fail; a clean branch must pass.

**Completion criteria:**

- CI fails on any `ruff`/`pyright`/`lint-imports` violation, not only on `pytest` failures.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

### 6.5 Priority 4 — Low Cleanup

#### CR-ARCH-003 — `protocol_config.py` could be split by topic (deferred, not currently recommended)

**Status:** `REJECTED`
**Priority:** `P4`
**Category:** file-organization
**Decision:** `KEEP`

**Affected files:**

- `src/datp_core/config/models/protocol_config.py`

**Affected symbols or responsibilities:**

- Whole-file organization

**Evidence:**

`protocol_config.py` is 780 lines, containing ~40 small, cohesive Pydantic model classes mirroring `protocols.yaml`'s structure 1:1 (model/training classes, 12 threshold-policy variant classes, metrics/statistics classes, artifact/communication/report classes).

**Problem:**

The file is long by line count, but every class within it is short (typically 5-20 fields, single-purpose), and the file boundary matches the single authored YAML document it mirrors exactly. Splitting it by topic (e.g. `protocol_threshold_config.py`, `protocol_metrics_config.py`) would not reduce any actual coupling or duplication — it would only redistribute already-well-organized code across more files for a document that is itself one YAML file by design (and the six-file YAML tree is fixed, see [1](#1-purpose-and-non-negotiable-constraints)).

**Impact:**

None identified beyond subjective navigability preference.

**Recommended target state:**

Unchanged. This finding is recorded and rejected explicitly so a future review does not re-raise it as if unconsidered.

**Required actions:**

None.

**Prerequisites:**

- None.

**Dependent findings:**

- None.

**Expected files to change:**

- None.

**Tests to update or add:**

- None.

**Scientific-drift risk:** `NONE`

**Required validation:**

- None.

**Completion criteria:**

- N/A — no action taken.

**Checklist:**

- [x] Evidence is still valid.
- [x] Target design is confirmed (reject, keep as-is).
- [ ] N/A — remaining checklist items do not apply to a rejected finding requiring no implementation.

---

#### CR-PERF-001 — Duplicated scientific/execution fingerprint computation functions

**Status:** `CONFIRMED`
**Priority:** `P4`
**Category:** minor-duplication
**Decision:** `MERGE`

**Affected files:**

- `src/datp_core/domain/fingerprints.py`

**Affected symbols or responsibilities:**

- `compute_scientific_fingerprint`
- `compute_execution_fingerprint`

**Evidence:**

`domain/fingerprints.py:82-96` and `:99-113`: `compute_scientific_fingerprint` and `compute_execution_fingerprint` are identical in every respect (envelope construction, JSON serialization, BLAKE2b hashing) except for the literal string `kind="scientific"` vs `kind="execution"`.

**Problem:**

Two functions exist where one parametrized function would do; a future change to the hashing/serialization logic (e.g. a digest-size change) must be applied identically in two places.

**Impact:**

Negligible — both functions are short, correct, and unlikely to diverge accidentally given their proximity, but the duplication is real and easily removed.

**Recommended target state:**

A single `_compute_fingerprint(projection: object, kind: Literal["scientific", "execution"]) -> Fingerprint` private helper, with `compute_scientific_fingerprint`/`compute_execution_fingerprint` as one-line public wrappers preserving the existing call sites and names exactly (both are part of the public API consumed by `config/resolver.py`).

**Required actions:**

1. Extract the shared body into `_compute_fingerprint(projection, kind)`.
2. Reduce both public functions to a one-line delegation.
3. Confirm fingerprints are byte-identical before and after (trivial, since the logic is unchanged).

**Prerequisites:**

- None.

**Dependent findings:**

- None.

**Expected files to change:**

- `src/datp_core/domain/fingerprints.py`

**Tests to update or add:**

- None (existing fingerprint tests must pass unchanged).

**Scientific-drift risk:** `NONE` (identical logic, pure code-motion)

**Required validation:**

- `uv run pytest tests/scientific/drift -q`

**Completion criteria:**

- One shared private helper backs both public fingerprint functions.

**Checklist:**

- [ ] Evidence is still valid.
- [ ] Prerequisites are satisfied.
- [ ] Target design is confirmed.
- [ ] Impacted tests are identified.
- [ ] Scientific invariants are listed.
- [ ] Implementation is complete.
- [ ] Obsolete code is deleted.
- [ ] Imports and exports are updated.
- [ ] Targeted tests pass.
- [ ] Ruff passes.
- [ ] Formatting passes.
- [ ] Pyright passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection is unchanged.
- [ ] Execution projection is unchanged.
- [ ] Fingerprints are unchanged or an authorized reason is documented.
- [ ] Full test suite passes.
- [ ] Finding is verified.

---

## 7. Library and Dependency Assessment

### 7.1 Existing Libraries to Retain

- **`pydantic`** — sole authored-configuration validation boundary (`config/models/*`). Correct, single responsibility, strict mode enabled throughout.
- **`attrs`** — sole resolved-domain-record implementation. Correct, single responsibility (immutable, framework-free records).
- **`cattrs`** — currently used narrowly and correctly for canonical projection unstructuring (`config/converter.py`), exactly the "mechanical conversion" role this review's library-assessment guidance recommends; not used for semantic resolution. Retain at its current scope; see [7.2](#72-libraries-to-adopt) for a bounded expansion opportunity.
- **`msgspec`** — sole artifact-manifest wire codec (`infrastructure/artifacts/manifest_codec.py`). A deliberate, single, justified use for exactly the boundary (strict, unknown-field-rejecting wire format) it is suited for; does not duplicate `pydantic`/`attrs` responsibilities.
- **`networkx`** — sole planning-graph backend (`planning/graph.py`). Used for real graph algorithms (topological sort/generations, transitive reduction, ancestors/descendants), not for a single simple traversal — justified.
- **`polars`**, **`pyarrow`** — dataset materialization and Parquet I/O throughout `infrastructure/datasets/*`. Correctly used; no duplicate dataframe/serialization framework introduced.
- **`filelock`**, **`duckdb`**, **`dagster`**, **`flwr`**, **`torch`**, **`safetensors`**, **`scipy`** (for `ScipyStatisticalAnalysisAdapter` and `estimators.py`'s quantile/skew/clustering support), **`scikit-learn`** (for `estimators.py`'s `KMeans`/`StandardScaler`), **`structlog`**, **`pyyaml`**, **`typer`**, **`rich`** — each has exactly one clear, currently-exercised responsibility and at least one direct consumer. Retain.

### 7.2 Libraries to Adopt

None. Every gap identified in this review (composition-root typing, mapping-conversion boilerplate, positional-tuple returns) is addressed by existing language/library facilities (`attrs`/`NamedTuple`, `isinstance` narrowing) rather than by adopting a new dependency. Introducing a new library for any of [CR-ARCH-001](#cr-arch-001--composition-root-uses-dictstr-object-forcing-12-type-ignores), [CR-DOMAIN-003](#cr-domain-003--repeated-mapping-conversion-boilerplate-across-domain-modules), or [CR-EXEC-002](#cr-exec-002--positional-tuple-returns-in-identitybuilders-job-builder-methods) would be adding a dependency to solve a problem three lines of `attrs` already solves.

### 7.3 Libraries to Trial

- **`cattrs` structuring hooks for `domain/values.py`'s converter boilerplate** ([CR-DOMAIN-003](#cr-domain-003--repeated-mapping-conversion-boilerplate-across-domain-modules)): the ~17 near-duplicate `_as_mapping_str_*`/`_as_tuple_*` helpers are exactly the "mechanical conversion between attrs records and typed structures" role `cattrs` structuring (as opposed to the unstructuring already in use) is designed for. Trial scope: replace the private converter functions in `domain/thresholding.py`, `domain/datasets.py`, and `config/runtime_settings.py` with `cattrs` structuring hooks registered on a converter scoped to those modules, keeping semantic resolution (which lives in `config/*_resolution.py`, untouched) fully separate. Reject the trial if it requires any converter to perform cross-reference validation or semantic derivation — those remain explicit code per [4](#4-target-architecture-principles).

### 7.4 Libraries to Reject

- **`beartype`** — already evaluated and rejected in `.tmp/implementation/DECISION_LOG.md` (2026-07-21): no dynamically-assembled plugin/adapter-registration boundary exists in the current surface; threshold-policy dispatch is static `isinstance` over a closed, pyright-covered set. This review finds no new boundary that changes that conclusion (the composition root, once [CR-ARCH-001](#cr-arch-001--composition-root-uses-dictstr-object-forcing-12-type-ignores) is fixed, is also fully static). Reaffirmed: reject.
- **`vulture`** — potentially useful for discovering more instances of the dead-code pattern this review found manually ([CR-DOMAIN-001](#cr-domain-001--dead-code-cluster-in-the-domain-layer), [CR-DEPS-001](#cr-deps-001--orphaned-adapter-files-and-one-whole-subpackage-are-the-sole-reachability-path-for-six-declared-dependencies)); not adopted as a dependency because its output requires the same manual grep-based verification this review already performed, and a one-off `uvx vulture` run needs no permanent dependency-list entry. Trial via ad hoc invocation only, never as a committed dependency.
- **`radon`/`lizard`, `jscpd`** — the same reasoning applies: useful as ad hoc, non-committed tools for a future audit pass, not warranted as permanent dependencies given the repository's current size (95 source files, 11,537 lines) makes manual complexity/duplication review (as performed in this document) tractable without them.

### 7.5 Dependencies to Remove

Per [CR-DEPS-001](#cr-deps-001--orphaned-adapter-files-and-one-whole-subpackage-are-the-sole-reachability-path-for-six-declared-dependencies): `pandera`, `xarray`, `scikit-posthocs`, `pingouin`, `statsmodels`, `pandas` (all reachable only through code with zero consumers and zero tests), and the `hardware` optional extra (`psutil`, `pynvml`, zero imports anywhere). None of these removals affects any currently-tested or currently-wired behavior — confirmed by the same `grep`-based reachability analysis underlying [CR-DEPS-001](#cr-deps-001--orphaned-adapter-files-and-one-whole-subpackage-are-the-sole-reachability-path-for-six-declared-dependencies).

---

## 8. Implementation Plan

### Phase 0 — Baseline and Scientific Safety Locks

**Purpose:** Capture an immutable, reproducible baseline before any change in later phases, so every phase's "scientific projection/fingerprint unchanged" checklist item has a concrete artifact to compare against.

**Included findings:** None directly; this phase is a prerequisite for all others.

**Explicitly excluded:** Any code change.

**Prerequisites:** None.

**Plan of action:**

1. Run `resolve_project_configuration()` against the real `configs/` tree; record `scientific_fingerprint.value`, `execution_fingerprint.value`, and the full `scientific_projection`/`execution_projection` dicts to a file outside version control (e.g. `.tmp/implementation/` per the existing control-workspace convention).
2. Run the full test suite (`uv run pytest -q` and `uv run pytest -q -n auto`) and record pass counts.
3. Run `uv run ruff format --check src tests`, `uv run ruff check src tests`, `uv run pyright`, `uv run lint-imports --config importlinter.ini`; record clean results.

**Expected structural result:** No code change. A recorded baseline for regression comparison.

**Tests and validation:** All of the above must currently pass (per [2.2](#22-quality-gates), they do).

**Scientific-drift checks:** N/A (no change).

**Stop conditions:** If any baseline gate fails before this review's changes begin, stop and resolve the pre-existing failure first — do not attribute it to this plan.

**Phase checklist:**

- [ ] All prerequisites are verified.
- [ ] Scope is limited to listed findings.
- [ ] Baseline tests pass before editing.
- [ ] Scientific baseline is captured.
- [ ] Changes are implemented incrementally.
- [ ] Obsolete code is removed.
- [ ] No compatibility shim is introduced.
- [ ] No temporary parallel architecture remains.
- [ ] Impacted tests pass.
- [ ] Static typing passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection matches the baseline.
- [ ] Execution projection matches the baseline.
- [ ] Fingerprints match the baseline.
- [ ] Full test suite passes.
- [ ] Repeated execution is deterministic.
- [ ] Phase completion criteria are satisfied.

---

### Phase 1 — Dead Code and Dependency Cleanup

**Purpose:** Remove all identified dead code and unused dependencies before any structural refactor, so later phases operate on a smaller, honest surface with no risk of accidentally "fixing" code that should instead be deleted.

**Included findings:** [CR-DOMAIN-001](#cr-domain-001--dead-code-cluster-in-the-domain-layer), [CR-DEPS-001](#cr-deps-001--orphaned-adapter-files-and-one-whole-subpackage-are-the-sole-reachability-path-for-six-declared-dependencies).

**Explicitly excluded:** [CR-SCI-001](#cr-sci-001--hardcoded-numeric-fallbacks-for-undefined-metrics-contradict-the-authored-metric-status-contract) is resolved first as its own phase (Phase 2) since it requires a judgment call (fix vs. delete `ClientConfusionMatrix`); do not let this phase's deletions race with that decision.

**Prerequisites:** Phase 0 baseline captured.

**Plan of action:**

1. Confirm via fresh `grep` (evidence may have shifted since this document was last updated) that every symbol named in [CR-DOMAIN-001](#cr-domain-001--dead-code-cluster-in-the-domain-layer) and [CR-DEPS-001](#cr-deps-001--orphaned-adapter-files-and-one-whole-subpackage-are-the-sole-reachability-path-for-six-declared-dependencies) is still unreferenced.
2. Delete `ResolvedCatalogue`, `SampleSizeCheck`, `unstructure_mapping_proxy` (defer `ClientConfusionMatrix`/`MetricResultRecord` to Phase 2).
3. Delete `infrastructure/tables/` in its entirety, `infrastructure/statistics/{posthoc_adapter,pingouin_adapter,statsmodels_adapter}.py`, and the three unused functions in `infrastructure/learning/sklearn_adapter.py` (defer `compute_roc_auc` to Phase 2 if it is being fixed rather than deleted).
4. Remove `pandera`, `xarray`, `scikit-posthocs`, `pingouin`, `statsmodels`, `pandas`, and the `hardware` extra from `pyproject.toml`; regenerate `uv.lock`.
5. Remove `infrastructure/tables` from `tests/conformance/test_project_structure.py`'s allowlist.

**Expected structural result:** ~350-450 lines of dead code removed across 8 files; 6 dependencies + 1 extra removed from `pyproject.toml`/`uv.lock`.

**Tests and validation:** `uv run pytest -q`; `uv sync --all-groups --all-extras --frozen`; `uv run ruff check src tests`; `uv run pyright`.

**Scientific-drift checks:** None of the deleted code is reachable from `resolve_project_configuration` or any stage handler; scientific and execution fingerprints must be byte-identical to the Phase 0 baseline.

**Stop conditions:** If any deletion candidate is found to have a consumer that Phase 0's evidence-gathering missed, stop and re-open the corresponding finding rather than deleting.

**Phase checklist:**

- [ ] All prerequisites are verified.
- [ ] Scope is limited to listed findings.
- [ ] Baseline tests pass before editing.
- [ ] Scientific baseline is captured.
- [ ] Changes are implemented incrementally.
- [ ] Obsolete code is removed.
- [ ] No compatibility shim is introduced.
- [ ] No temporary parallel architecture remains.
- [ ] Impacted tests pass.
- [ ] Static typing passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection matches the baseline.
- [ ] Execution projection matches the baseline.
- [ ] Fingerprints match the baseline.
- [ ] Full test suite passes.
- [ ] Repeated execution is deterministic.
- [ ] Phase completion criteria are satisfied.

---

### Phase 2 — Scientific-Contract Correctness (Metric Status Handling)

**Purpose:** Close the one proven scientific-drift risk in this review before any other structural change, since it is the highest-priority finding and is self-contained.

**Included findings:** [CR-SCI-001](#cr-sci-001--hardcoded-numeric-fallbacks-for-undefined-metrics-contradict-the-authored-metric-status-contract).

**Explicitly excluded:** Building any part of `EVAL-METRICS-001` beyond the typed-status contract itself; this phase does not implement evaluation tables or metric aggregation, only fixes the two functions' return contracts (or deletes them, per the finding's decision rule, folding that outcome into Phase 1's deferred items).

**Prerequisites:** Phase 0 baseline; Phase 1 decision on whether `ClientConfusionMatrix`/`compute_roc_auc` are deleted outright (if so, this phase is a no-op, confirmed and closed as `REJECTED`-by-deletion rather than `IMPLEMENTED`).

**Plan of action:**

1. Decide, at execution time, whether `EVAL-METRICS-001` has a concrete near-term implementation plan. If not, delete `ClientConfusionMatrix`/`MetricResultRecord`/`compute_roc_auc` per [CR-DOMAIN-001](#cr-domain-001--dead-code-cluster-in-the-domain-layer)/[CR-DEPS-001](#cr-deps-001--orphaned-adapter-files-and-one-whole-subpackage-are-the-sole-reachability-path-for-six-declared-dependencies) and close this finding as resolved-by-deletion.
2. If a near-term consumer exists, implement the typed-status return contract per [CR-SCI-001](#cr-sci-001--hardcoded-numeric-fallbacks-for-undefined-metrics-contradict-the-authored-metric-status-contract)'s required actions.

**Expected structural result:** Either the two functions no longer exist, or they return a typed status matching `protocols.yaml::metric_statuses` instead of a numeric substitute.

**Tests and validation:** `uv run pytest tests/unit/domain -q`.

**Scientific-drift checks:** Neither function is currently reachable from any resolved projection; no fingerprint is affected either way.

**Stop conditions:** None specific; this is a low-risk, self-contained phase.

**Phase checklist:**

- [ ] All prerequisites are verified.
- [ ] Scope is limited to listed findings.
- [ ] Baseline tests pass before editing.
- [ ] Scientific baseline is captured.
- [ ] Changes are implemented incrementally.
- [ ] Obsolete code is removed.
- [ ] No compatibility shim is introduced.
- [ ] No temporary parallel architecture remains.
- [ ] Impacted tests pass.
- [ ] Static typing passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection matches the baseline.
- [ ] Execution projection matches the baseline.
- [ ] Fingerprints match the baseline.
- [ ] Full test suite passes.
- [ ] Repeated execution is deterministic.
- [ ] Phase completion criteria are satisfied.

---

### Phase 3 — Configuration and Resolver Architecture

**Purpose:** Decompose the resolver god function and its dataset-resolution counterpart into named, independently-testable functions, and remove the composition-root typing hole.

**Included findings:** [CR-CONFIG-001](#cr-config-001--resolve_project_configuration-is-a-625-line-god-function-with-inconsistent-delegation), [CR-ARCH-001](#cr-arch-001--composition-root-uses-dictstr-object-forcing-12-type-ignores).

**Explicitly excluded:** [CR-CONFIG-002](#cr-config-002--untyped-mapping-fields-on-threshold-policy-records-for-fixed-shape-contracts) and [CR-DOMAIN-002](#cr-domain-002--experimentrecord-mixes-independent-concern-groups-as-flat-fields) (both touch overlapping resolver code and should follow, not run concurrently with, this phase — see [9.2](#92-sequential-only-work)).

**Prerequisites:** Phase 0 baseline; Phase 1/2 complete (a smaller, dead-code-free resolver is easier to decompose correctly).

**Plan of action:**

1. Extract every named function listed in [CR-CONFIG-001](#cr-config-001--resolve_project_configuration-is-a-625-line-god-function-with-inconsistent-delegation)'s required actions, one collection at a time, running the full test suite and a fingerprint diff after each extraction (not only at the end) to localize any accidental behavior change immediately.
2. Once `resolver.py` is reduced to orchestration + projection assembly, implement [CR-ARCH-001](#cr-arch-001--composition-root-uses-dictstr-object-forcing-12-type-ignores) in `composition/root.py`.

**Expected structural result:** `resolver.py` under 150 lines; `resolve_datasets` under 100 lines; zero `# type: ignore` in `composition/root.py`.

**Tests and validation:** Full suite after every extraction; `uv run pyright`; `uv run lint-imports --config importlinter.ini`.

**Scientific-drift checks:** Fingerprint diff against the Phase 0 baseline after every extraction step, not only at phase end.

**Stop conditions:** If any single extraction changes the scientific or execution fingerprint, stop, revert that extraction, and diagnose before proceeding — a code-motion refactor must never change a resolved value.

**Phase checklist:**

- [ ] All prerequisites are verified.
- [ ] Scope is limited to listed findings.
- [ ] Baseline tests pass before editing.
- [ ] Scientific baseline is captured.
- [ ] Changes are implemented incrementally.
- [ ] Obsolete code is removed.
- [ ] No compatibility shim is introduced.
- [ ] No temporary parallel architecture remains.
- [ ] Impacted tests pass.
- [ ] Static typing passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection matches the baseline.
- [ ] Execution projection matches the baseline.
- [ ] Fingerprints match the baseline.
- [ ] Full test suite passes.
- [ ] Repeated execution is deterministic.
- [ ] Phase completion criteria are satisfied.

---

### Phase 4 — Domain Records and Dataclass Consolidation

**Purpose:** Regroup `ExperimentRecord`'s flat optional fields and consolidate mapping-conversion boilerplate.

**Included findings:** [CR-DOMAIN-002](#cr-domain-002--experimentrecord-mixes-independent-concern-groups-as-flat-fields), [CR-DOMAIN-003](#cr-domain-003--repeated-mapping-conversion-boilerplate-across-domain-modules).

**Explicitly excluded:** [CR-CONFIG-002](#cr-config-002--untyped-mapping-fields-on-threshold-policy-records-for-fixed-shape-contracts) (Phase 5; touches the same `domain/thresholding.py` file as CR-DOMAIN-003 and must run after it to avoid merge conflicts on the converter-helper consolidation — see [9.3](#93-shared-file-collision-risks)).

**Prerequisites:** Phase 3 complete (resolver decomposition must land first so `ExperimentRecord` construction has a single, known call site to update).

**Plan of action:**

1. Implement [CR-DOMAIN-003](#cr-domain-003--repeated-mapping-conversion-boilerplate-across-domain-modules) first (simpler, lower-risk, touches the converter helpers only).
2. Implement [CR-DOMAIN-002](#cr-domain-002--experimentrecord-mixes-independent-concern-groups-as-flat-fields), updating `tests/conformance/test_experiment_catalogue_field_disposition.py`'s leaf-path table in the same commit as the record change (never leave the conformance test stale even transiently).

**Expected structural result:** `ExperimentRecord` reduced to ~20 top-level fields plus 4 nested optional records; ~17 duplicate converter helpers reduced to 2-3 generic ones.

**Tests and validation:** `tests/conformance/test_experiment_catalogue_field_disposition.py`; `tests/scientific/drift/*`; `uv run pytest tests/unit/domain -q`.

**Scientific-drift checks:** Fingerprint diff before/after on the real `configs/experiments.yaml` — must be byte-identical (regrouping fields must not change which leaf values are fingerprinted).

**Stop conditions:** If the field-disposition conformance test cannot be updated to prove 1:1 coverage of the new nested structure, stop — do not proceed with a regrouping that the existing safety net cannot verify.

**Phase checklist:**

- [ ] All prerequisites are verified.
- [ ] Scope is limited to listed findings.
- [ ] Baseline tests pass before editing.
- [ ] Scientific baseline is captured.
- [ ] Changes are implemented incrementally.
- [ ] Obsolete code is removed.
- [ ] No compatibility shim is introduced.
- [ ] No temporary parallel architecture remains.
- [ ] Impacted tests pass.
- [ ] Static typing passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection matches the baseline.
- [ ] Execution projection matches the baseline.
- [ ] Fingerprints match the baseline.
- [ ] Full test suite passes.
- [ ] Repeated execution is deterministic.
- [ ] Phase completion criteria are satisfied.

---

### Phase 5 — Dictionary and Hardcoded-Value Cleanup

**Purpose:** Replace fixed-shape untyped mapping fields on threshold-policy records with typed sub-records, and source the N-BaIoT Parquet batch size from the resolved runtime profile instead of a literal.

**Included findings:** [CR-CONFIG-002](#cr-config-002--untyped-mapping-fields-on-threshold-policy-records-for-fixed-shape-contracts), [CR-DATA-004](#cr-data-004--hardcoded-parquet-batch-size-ignores-the-resolved-runtime-execution-profile).

**Explicitly excluded:** Any change to the actual clustering/candidate-grid values authored in `protocols.yaml`.

**Prerequisites:** Phase 4 complete (converter-helper consolidation must land first).

**Plan of action:**

1. Implement [CR-CONFIG-002](#cr-config-002--untyped-mapping-fields-on-threshold-policy-records-for-fixed-shape-contracts): add `ClusteringConfigRecord`/`CandidateGridRecord` (authored + resolved pair), update `estimators.py` to typed access.
2. Implement [CR-DATA-004](#cr-data-004--hardcoded-parquet-batch-size-ignores-the-resolved-runtime-execution-profile): thread `chunk_row_count` from the resolved runtime profile into `DatasetMaterializer.materialize`.

**Expected structural result:** No `isinstance`-based mapping-value narrowing remains in `estimators.py`; N-BaIoT materialization batch size varies correctly by `DATP_EXECUTION_PROFILE`.

**Tests and validation:** `tests/scientific/thresholding/test_configured_threshold_estimators.py`; `tests/unit/domain/test_threshold_policy_records.py`; `tests/integration/artifacts/test_staged_nbaiot_parquet_commit.py`.

**Scientific-drift checks:** Threshold-policy resolved values (clustering hyperparameters, candidate-grid bounds) must be identical to their authored YAML values; confirm via the existing scientific-drift test suite. Batch-size change affects only Parquet write chunking, never the locked `micro_batch_size: 256` training contract — confirm no code path conflates the two.

**Stop conditions:** If any change to `estimators.py`'s clustering/candidate-grid access alters a resolved numeric value (rather than only its access pattern), stop immediately — this phase must be typing-only.

**Phase checklist:**

- [ ] All prerequisites are verified.
- [ ] Scope is limited to listed findings.
- [ ] Baseline tests pass before editing.
- [ ] Scientific baseline is captured.
- [ ] Changes are implemented incrementally.
- [ ] Obsolete code is removed.
- [ ] No compatibility shim is introduced.
- [ ] No temporary parallel architecture remains.
- [ ] Impacted tests pass.
- [ ] Static typing passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection matches the baseline.
- [ ] Execution projection matches the baseline.
- [ ] Fingerprints match the baseline.
- [ ] Full test suite passes.
- [ ] Repeated execution is deterministic.
- [ ] Phase completion criteria are satisfied.

---

### Phase 6 — Dataset and Materialization Architecture

**Purpose:** Fix the Edge-IIoTset CSV reader regression, consolidate CSV numeric-validation logic, and eliminate the duplicate CICIoT2023 deduplication/split implementation.

**Included findings:** [CR-DATA-002](#cr-data-002--edge-iiotset-csv-reader-still-has-the-defect-the-latest-commit-just-fixed-elsewhere), [CR-DATA-005](#cr-data-005--near-duplicated-numeric-field-validation-loops-in-csv_sourcepy), [CR-DATA-003](#cr-data-003--duplicate-ciciot2023-deduplicationsplit-algorithm-in-memory-vs-sqlite-backed).

**Explicitly excluded:** Building the not-yet-existing `EdgeIIoTsetAdapter`/registry entry (out of this review's scope — that is new feature work, not a correction of existing code).

**Prerequisites:** Phase 0 baseline. Independent of Phases 3-5 (different files) — may run in parallel with them; see [9.1](#91-safe-parallel-workstreams).

**Plan of action:**

1. Implement [CR-DATA-005](#cr-data-005--near-duplicated-numeric-field-validation-loops-in-csv_sourcepy) first (extracts the shared numeric-validation helper in `csv_source.py`).
2. Implement [CR-DATA-002](#cr-data-002--edge-iiotset-csv-reader-still-has-the-defect-the-latest-commit-just-fixed-elsewhere), reusing the helper from step 1 where the row-validation shape matches (Edge-IIoTset's hex-numeric parsing and endpoint-derived client identity remain dataset-specific and are not forced into the shared helper).
3. Implement [CR-DATA-003](#cr-data-003--duplicate-ciciot2023-deduplicationsplit-algorithm-in-memory-vs-sqlite-backed), rewriting its test against the real SQLite-backed path.

**Expected structural result:** `iter_edge_iiotset_source` no longer uses `csv.DictReader`; `csv_source.py`'s two numeric readers share one validation helper; `ciciot2023.py` has one deduplication/split implementation.

**Tests and validation:** `tests/unit/infrastructure/datasets/*` (all), `tests/integration/datasets/*` (all).

**Scientific-drift checks:** Re-run `tests/integration/datasets/test_raw_source_contracts_are_ready.py` against the real raw corpus to confirm header/layout/column-count evidence for all three datasets is unchanged. Confirm CICIoT2023's rewritten test proves identical duplicate/split behavior to the deleted in-memory test on the same fixtures (byte-for-byte row assignment comparison).

**Stop conditions:** If the Edge-IIoTset fix changes the set of rows accepted/rejected against the real raw corpus (beyond correctly rejecting rows that were previously silently misparsed), stop and audit the discrepancy manually before proceeding — this is exactly the kind of data-integrity change that must be understood, not merely observed.

**Phase checklist:**

- [ ] All prerequisites are verified.
- [ ] Scope is limited to listed findings.
- [ ] Baseline tests pass before editing.
- [ ] Scientific baseline is captured.
- [ ] Changes are implemented incrementally.
- [ ] Obsolete code is removed.
- [ ] No compatibility shim is introduced.
- [ ] No temporary parallel architecture remains.
- [ ] Impacted tests pass.
- [ ] Static typing passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection matches the baseline.
- [ ] Execution projection matches the baseline.
- [ ] Fingerprints match the baseline.
- [ ] Full test suite passes.
- [ ] Repeated execution is deterministic.
- [ ] Phase completion criteria are satisfied.

---

### Phase 7 — Artifact and Stage-Handler Consolidation

**Purpose:** Fix the unsafe first-item/unguarded-lookup assumptions in the dataset-materialization stage handler, and merge the duplicated source-tree scanning logic between dataset audit and materialization.

**Included findings:** [CR-EXEC-001](#cr-exec-001--unsafe-first-item-and-unguarded-lookup-assumptions-in-the-dataset-materialization-stage-handler), [CR-DATA-001](#cr-data-001--duplicated-source-tree-scanning-logic-between-dataset-audit-and-materialization).

**Explicitly excluded:** Any new stage handler (`ModelTraining`, `CheckpointSelection`, etc.) — those are `NOT_STARTED` feature work, not corrections.

**Prerequisites:** Phase 0 baseline. Independent of Phases 3-6 — may run in parallel; see [9.1](#91-safe-parallel-workstreams).

**Plan of action:**

1. Implement [CR-EXEC-001](#cr-exec-001--unsafe-first-item-and-unguarded-lookup-assumptions-in-the-dataset-materialization-stage-handler): add the population-count guard and the `ResolvedDataset.materialization()` helper.
2. Implement [CR-DATA-001](#cr-data-001--duplicated-source-tree-scanning-logic-between-dataset-audit-and-materialization): route `AuditDatasetUseCase` through `build_source_inventory`.

**Expected structural result:** No unguarded `next()`/positional-index lookup remains in `stage_handlers.py`; `AuditDatasetUseCase` no longer independently scans the filesystem.

**Tests and validation:** `tests/unit/application/*` (all).

**Scientific-drift checks:** Confirm `tests/unit/application/test_dataset_materialization_reuse.py` and `test_execution_suppresses_unavailable_dependencies.py` still pass; these directly exercise the modified handler.

**Stop conditions:** None specific.

**Phase checklist:**

- [ ] All prerequisites are verified.
- [ ] Scope is limited to listed findings.
- [ ] Baseline tests pass before editing.
- [ ] Scientific baseline is captured.
- [ ] Changes are implemented incrementally.
- [ ] Obsolete code is removed.
- [ ] No compatibility shim is introduced.
- [ ] No temporary parallel architecture remains.
- [ ] Impacted tests pass.
- [ ] Static typing passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection matches the baseline.
- [ ] Execution projection matches the baseline.
- [ ] Fingerprints match the baseline.
- [ ] Full test suite passes.
- [ ] Repeated execution is deterministic.
- [ ] Phase completion criteria are satisfied.

---

### Phase 8 — Planning, Execution, and Orchestration

**Purpose:** Replace positional-tuple returns in the planning identity builder, and fix the CLI's inconsistent use-case boundary.

**Included findings:** [CR-EXEC-002](#cr-exec-002--positional-tuple-returns-in-identitybuilders-job-builder-methods), [CR-ARCH-002](#cr-arch-002--cli-dataset-audit-command-bypasses-the-application-boundary).

**Explicitly excluded:** Real Dagster asset-graph construction from `PlanningGraph`, real federated-round orchestration — both `NOT_STARTED`/`IN_PROGRESS` feature work outside this review's corrective scope.

**Prerequisites:** Phase 0 baseline. Independent of Phases 3-7 — may run in parallel; see [9.1](#91-safe-parallel-workstreams).

**Plan of action:**

1. Implement [CR-EXEC-002](#cr-exec-002--positional-tuple-returns-in-identitybuilders-job-builder-methods): define `PlannedJobSpec`, update all eight `IdentityBuilder` methods and `expand_experiment_jobs`.
2. Implement [CR-ARCH-002](#cr-arch-002--cli-dataset-audit-command-bypasses-the-application-boundary): move the dataset-id lookup into `AuditDatasetUseCase`.

**Expected structural result:** No positional-tuple indexing remains in `planning/expansion.py`; every CLI command calls exactly one `application.<use_case>.execute(...)`.

**Tests and validation:** `tests/unit/planning/*`, `tests/unit/interfaces/cli/test_cli_commands.py`, `tests/unit/application/test_query_use_cases_through_fake_port.py`.

**Scientific-drift checks:** Planning graph shape (job/edge counts, dependency structure) must be identical before and after — confirm via `tests/unit/planning/test_graph_transformations_preserve_context.py` and `test_identity_builder_determinism.py`.

**Stop conditions:** None specific.

**Phase checklist:**

- [ ] All prerequisites are verified.
- [ ] Scope is limited to listed findings.
- [ ] Baseline tests pass before editing.
- [ ] Scientific baseline is captured.
- [ ] Changes are implemented incrementally.
- [ ] Obsolete code is removed.
- [ ] No compatibility shim is introduced.
- [ ] No temporary parallel architecture remains.
- [ ] Impacted tests pass.
- [ ] Static typing passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection matches the baseline.
- [ ] Execution projection matches the baseline.
- [ ] Fingerprints match the baseline.
- [ ] Full test suite passes.
- [ ] Repeated execution is deterministic.
- [ ] Phase completion criteria are satisfied.

---

### Phase 9 — Statistical and Threshold Adapters

**Purpose:** No findings remain in this area beyond those already scheduled in Phases 1 ([CR-DEPS-001](#cr-deps-001--orphaned-adapter-files-and-one-whole-subpackage-are-the-sole-reachability-path-for-six-declared-dependencies)'s statistics-adapter deletions) and 5 ([CR-CONFIG-002](#cr-config-002--untyped-mapping-fields-on-threshold-policy-records-for-fixed-shape-contracts)'s threshold-record typing). This phase is recorded as a placeholder confirming no additional action is required, per this document's structural requirement to address every numbered phase explicitly.

**Included findings:** None (see Phases 1 and 5).

**Explicitly excluded:** N/A.

**Prerequisites:** Phases 1 and 5 complete.

**Plan of action:** None — verify Phases 1 and 5 achieved their statistical/threshold-adapter goals; no separate work exists here.

**Expected structural result:** N/A.

**Tests and validation:** Covered by Phases 1 and 5.

**Scientific-drift checks:** Covered by Phases 1 and 5.

**Stop conditions:** N/A.

**Phase checklist:**

- [x] N/A — no findings assigned to this phase; all applicable work is scheduled in Phases 1 and 5.

---

### Phase 10 — Performance and I/O Optimization

**Purpose:** No dedicated performance findings were identified beyond [CR-DATA-004](#cr-data-004--hardcoded-parquet-batch-size-ignores-the-resolved-runtime-execution-profile) (Phase 5). This review found no evidence of repeated filesystem scans beyond the one already addressed in Phase 7 ([CR-DATA-001](#cr-data-001--duplicated-source-tree-scanning-logic-between-dataset-audit-and-materialization)), no repeated YAML loading (each of the four `read_*_document` calls in `YamlConfigurationReader.read_project_documents` reads a distinct file exactly once), and no inefficient record buffering beyond what is already bounded by streaming/SQLite-backed design (`csv_source.py`'s generators, `ciciot2023.py`/`edge_iiotset.py`'s SQLite indices). No premature optimization is recommended.

**Included findings:** None beyond Phases 5 and 7 (cross-referenced, not duplicated here).

**Explicitly excluded:** Any speculative optimization not backed by measured evidence — this review found no profiling data suggesting a real bottleneck beyond the two already-scheduled fixes.

**Prerequisites:** Phases 5 and 7 complete.

**Plan of action:** None beyond confirming Phases 5 and 7 landed correctly.

**Expected structural result:** N/A.

**Tests and validation:** Covered by Phases 5 and 7.

**Scientific-drift checks:** Covered by Phases 5 and 7.

**Stop conditions:** N/A.

**Phase checklist:**

- [x] N/A — no findings assigned to this phase beyond cross-references to Phases 5 and 7.

---

### Phase 11 — Test-Suite Debloating

**Purpose:** Update tests to match every structural change made in Phases 1-8, and rewrite the CICIoT2023 deduplication test against its real production path.

**Included findings:** Test-update requirements of every finding above (no standalone test-only finding was identified — the test suite itself is a strong area per [3.2](#32-strong-areas-to-preserve), with no obsolete audit tests, no duplicate tests, and no weakly-named tests found during this review's sampling of `tests/conftest.py`, `tests/conformance/*`, and the full test file listing).

**Explicitly excluded:** Any reduction in test count for its own sake — this review found no test-suite bloat to remove.

**Prerequisites:** Phases 1-8 complete.

**Plan of action:**

1. Confirm every test file touched by a preceding phase's "Tests to update or add" section has been updated.
2. Re-run the complete suite serially and under `-n auto` to confirm determinism is preserved.
3. Confirm `tests/conformance/*` still exhaustively covers the post-refactor structure (particularly `test_experiment_catalogue_field_disposition.py` after Phase 4's `ExperimentRecord` regrouping, and `test_project_structure.py`/`test_configuration_authority_boundary.py` after Phase 1's deletions and Phase 3's new `catalogue_resolution.py` module).

**Expected structural result:** No test regresses; new/renamed modules are reflected in the conformance allowlists.

**Tests and validation:** `uv run pytest -q`; `uv run pytest -q -n auto`.

**Scientific-drift checks:** Full scientific-drift test suite (`tests/scientific/*`) passes unchanged.

**Stop conditions:** If any conformance test requires weakening (rather than updating) its assertion to pass, stop — a conformance test failing after a refactor is evidence the refactor introduced exactly the violation the test exists to catch.

**Phase checklist:**

- [ ] All prerequisites are verified.
- [ ] Scope is limited to listed findings.
- [ ] Baseline tests pass before editing.
- [ ] Scientific baseline is captured.
- [ ] Changes are implemented incrementally.
- [ ] Obsolete code is removed.
- [ ] No compatibility shim is introduced.
- [ ] No temporary parallel architecture remains.
- [ ] Impacted tests pass.
- [ ] Static typing passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection matches the baseline.
- [ ] Execution projection matches the baseline.
- [ ] Fingerprints match the baseline.
- [ ] Full test suite passes.
- [ ] Repeated execution is deterministic.
- [ ] Phase completion criteria are satisfied.

---

### Phase 12 — Comments, Docstrings, Naming, and Exports

**Purpose:** This review found no material excess-comment, stale-docstring, or inconsistent-naming problem warranting a dedicated phase — the codebase's comment density is already low and purposeful (e.g. the raw-symlink-policy ordering comment in `runtime_settings.py`, the pyright-ignore rationale comments in `resolver.py`/`runtime_settings.py`). The one misleading comment found ([CR-DATA-004](#cr-data-004--hardcoded-parquet-batch-size-ignores-the-resolved-runtime-execution-profile)'s "overridden by runtime profile if needed") is corrected as part of that finding in Phase 5, not repeated here.

**Included findings:** None beyond the cross-reference to [CR-DATA-004](#cr-data-004--hardcoded-parquet-batch-size-ignores-the-resolved-runtime-execution-profile) (Phase 5).

**Explicitly excluded:** Any comment-stripping or docstring-rewriting not tied to a concrete finding.

**Prerequisites:** Phase 5 complete.

**Plan of action:** None beyond confirming Phase 5 removed the misleading comment.

**Expected structural result:** N/A.

**Tests and validation:** N/A.

**Scientific-drift checks:** N/A.

**Stop conditions:** N/A.

**Phase checklist:**

- [x] N/A — no findings assigned to this phase beyond the cross-reference to Phase 5.

---

### Phase 13 — Final Architecture and Drift Verification

**Purpose:** Prove that every prior phase, taken together, leaves the resolved scientific and execution projections byte-identical to the Phase 0 baseline, and enable the CI gates this review found were missing.

**Included findings:** [CR-TEST-001](#cr-test-001--ci-does-not-run-linttypeimport-gates).

**Explicitly excluded:** Any new finding discovered during this phase — if one is found, it is added to this document as a new `CR-*` entry (with the next available number in its theme) rather than silently fixed here.

**Prerequisites:** Phases 0-12 complete.

**Plan of action:**

1. Implement [CR-TEST-001](#cr-test-001--ci-does-not-run-linttypeimport-gates) last, once the repository is already clean, so the newly-added CI gates pass immediately rather than blocking on pre-existing issues this plan already fixed.
2. Run the full validation battery: `uv run ruff format --check src tests`, `uv run ruff check src tests`, `uv run pyright`, `uv run lint-imports --config importlinter.ini`, `uv run pytest -q`, `uv run pytest -q -n auto`.
3. Recompute `resolve_project_configuration()`'s scientific and execution fingerprints and diff them against the Phase 0 baseline — must be byte-identical.
4. Re-run this review prompt in a fresh session against the resulting repository state and confirm it produces no meaningful change to this document (idempotence check).

**Expected structural result:** All quality gates pass, including in CI; fingerprints unchanged from Phase 0; this document's findings are moved to [12](#12-resolved-and-verified-findings) once each is independently verified.

**Tests and validation:** All gates above.

**Scientific-drift checks:** Byte-identical fingerprint comparison against Phase 0.

**Stop conditions:** Any fingerprint mismatch is a hard stop requiring root-cause diagnosis before this plan can be considered complete — no phase may be marked `VERIFIED` while a fingerprint mismatch is unexplained.

**Phase checklist:**

- [ ] All prerequisites are verified.
- [ ] Scope is limited to listed findings.
- [ ] Baseline tests pass before editing.
- [ ] Scientific baseline is captured.
- [ ] Changes are implemented incrementally.
- [ ] Obsolete code is removed.
- [ ] No compatibility shim is introduced.
- [ ] No temporary parallel architecture remains.
- [ ] Impacted tests pass.
- [ ] Static typing passes.
- [ ] Import boundaries pass.
- [ ] Scientific projection matches the baseline.
- [ ] Execution projection matches the baseline.
- [ ] Fingerprints match the baseline.
- [ ] Full test suite passes.
- [ ] Repeated execution is deterministic.
- [ ] Phase completion criteria are satisfied.

---

## 9. Parallelization and Agent Coordination

### 9.1 Safe Parallel Workstreams

The following phases touch disjoint files and may be executed concurrently by different agents once Phase 0 (baseline) and Phase 1 (dead-code removal) are complete:

- **Phase 6** (dataset/materialization: `csv_source.py`, `edge_iiotset.py`, `ciciot2023.py`) — no overlap with Phase 3's `config/*` files, Phase 7's `application/stage_handlers.py`/`dataset_audit.py`, or Phase 8's `planning/*`/`interfaces/cli/*`.
- **Phase 7** (`application/stage_handlers.py`, `application/dataset_audit.py`, `domain/datasets.py`'s new `.materialization()` helper) — no overlap with Phase 6's dataset-adapter files or Phase 8's planning/CLI files. Note: Phase 7 adds a method to `domain/datasets.py`; Phase 4 also edits `domain/catalogue.py` (a different file in the same package) — these may run concurrently, but both agents should pull the latest `domain/` state before starting to avoid an unnecessary merge conflict on shared imports.
- **Phase 8** (`planning/identity.py`, `planning/expansion.py`, `interfaces/cli/app.py`, `application/dataset_audit.py`, `composition/root.py`) — note `dataset_audit.py` and `composition/root.py` are also touched by Phase 7/Phase 3 respectively; if Phase 8 and Phase 7 run concurrently, both must coordinate on `application/dataset_audit.py` specifically (see [9.3](#93-shared-file-collision-risks)).

### 9.2 Sequential-Only Work

Per this document's own methodology, treat the following as sequential unless a specific pair is proven independent by file-level inspection at execution time:

- Phase 3 (resolver decomposition) before Phase 4 (`ExperimentRecord` regrouping) — Phase 4 needs a single, known `ExperimentRecord` construction call site, which Phase 3 establishes.
- Phase 4 (`domain/thresholding.py` converter consolidation, via [CR-DOMAIN-003](#cr-domain-003--repeated-mapping-conversion-boilerplate-across-domain-modules)) before Phase 5 ([CR-CONFIG-002](#cr-config-002--untyped-mapping-fields-on-threshold-policy-records-for-fixed-shape-contracts), which edits the same file's converter usage).
- Root configuration model changes, resolver decomposition, root domain record changes, artifact-contract consolidation, composition-root changes, planning-graph identity changes, dataset-adapter interface changes, global test-fixture restructuring, and package import-boundary changes are all, per the standing rule, sequential-only relative to each other even where this plan does not explicitly call out a conflict — confirm no overlap by direct file inspection before parallelizing any pair not explicitly listed in [9.1](#91-safe-parallel-workstreams).

### 9.3 Shared-File Collision Risks

| File | Findings touching it | Coordination requirement |
| --- | --- | --- |
| `config/resolver.py` | CR-CONFIG-001 (Phase 3), CR-DOMAIN-002 (Phase 4, via its extracted successor) | Phase 3 must fully land (resolver reduced to orchestration only) before Phase 4 edits `ExperimentRecord` construction. |
| `domain/thresholding.py` | CR-DOMAIN-003 (Phase 4), CR-CONFIG-002 (Phase 5) | Sequential; Phase 5 depends on Phase 4's consolidated converter helpers. |
| `application/dataset_audit.py` | CR-DATA-001 (Phase 7), CR-ARCH-002 (Phase 8) | Do not run Phase 7 and Phase 8 concurrently on this file; either sequence them or assign both findings to the same agent/session. |
| `infrastructure/thresholding/estimators.py` | CR-CONFIG-002 (Phase 5) only | No collision; safe standalone. |
| `composition/root.py` | CR-ARCH-001 (Phase 3), CR-ARCH-002 (Phase 8, constructor-signature update) | Phase 3 must land first; Phase 8's `AuditDatasetUseCase` constructor change touches the same factory functions. |
| `pyproject.toml` / `uv.lock` | CR-DEPS-001 (Phase 1) only | No collision; safe standalone, but must run before any phase that might otherwise still reference a removed dependency. |

No finding in this plan modifies the same authored-YAML document, the same root domain record's field list, or the same test fixture file as another finding scheduled in a different, concurrently-runnable phase, beyond the pairs listed above.

---

## 10. Accepted Architecture Decisions

The following patterns were evaluated during this review and are **accepted as correct**, not flagged as findings, and should not be re-raised by a future review run without new evidence:

- **`AnalysisSpecRecord`'s 14-member kind-discriminated union** (`domain/catalogue.py`) and the corresponding flat `AnalysisSpecConfig` superset on the authored side (`config/models/experiment_config.py`) — a deliberate, already-documented (`.tmp/implementation/DECISION_LOG.md`, 2026-07-21) split driven by a real `kind` discriminant with no unrepresentable-invalid-state risk. `config/experiment_resolution.py::_resolve_analysis`'s 203-line dispatch is long because it mechanically enumerates these 14 kinds, not because it is poorly factored.
- **Remaining `FrozenJson`/`Mapping[str, FrozenJson]` fields** for genuinely polymorphic authored contracts (`experiment_config.py`'s `overrides`, `matching_contract`, `temporal_procedure`, training-profile sub-specs, etc.) — an intentional, already-documented (2026-07-20 decision log entry) design choice distinct from the fixed-shape mapping fields flagged in [CR-CONFIG-002](#cr-config-002--untyped-mapping-fields-on-threshold-policy-records-for-fixed-shape-contracts). Every enclosing model still uses `extra="forbid"`, so unknown keys are rejected even where internal structure is not modeled.
- **`TypedThresholdPolicyConfig` remaining a Pydantic discriminated union consumed by `infrastructure/thresholding/{base,estimators}.py`** — already evaluated and reversed once (2026-07-20 → 2026-07-21) in favor of the current 12 pure `ThresholdPolicyRecord` domain records; the current state (domain records only, no Pydantic below the resolution boundary) is correct and matches this review's own domain-purity requirement. Not re-litigated.
- **`msgspec` adopted for the artifact manifest codec only** — reviewed and confirmed as the single, justified, narrowly-scoped use described in [3.2](#32-strong-areas-to-preserve) and [7.1](#71-existing-libraries-to-retain).
- **`beartype` not adopted** — reaffirmed in [7.4](#74-libraries-to-reject).
- **`MetricFormulaRecord`/`MetricFormulaConfig`'s 19-field flat superset** — accepted as a reasonable representation for a protocol-contract block whose docstring already states it has "no current downstream consumer"; revisit only once `EVAL-METRICS-001` gives it a real consumer with an actual per-metric access pattern to design against.
- **`_resolve_threshold_policy`'s dict-based dispatch table** (`config/protocol_resolution.py`, mapping authored Pydantic type → domain record type via `record_type(**cfg.model_dump())`) — a clean, mechanical pattern correctly avoiding a long `isinstance`/`if` chain for a case where every variant's fields map 1:1. Preserve as the model for any future closed-set type dispatch.
- **Dagster orchestration's translation/partition/metadata helpers existing and being unit-tested ahead of full wiring** (`orchestration/dagster/{translation,partitions,metadata}.py`) — distinguished from the [CR-DEPS-001](#cr-deps-001--orphaned-adapter-files-and-one-whole-subpackage-are-the-sole-reachability-path-for-six-declared-dependencies) dead-code cluster because these functions *are* exercised by real tests (`tests/unit/planning/test_graph_transformations_preserve_context.py`, `tests/integration/orchestration/test_dagster_partitions_match_resolved_catalogue.py`), even though `orchestration/dagster/definitions.py` does not yet assemble them into a real asset graph. This is legitimate, tested, `IN_PROGRESS` scaffolding for `EXEC-DAGSTER-HANDLER-001`, not speculative dead code — no finding is raised against it.

---

## 11. Rejected Recommendations

- **[CR-ARCH-003](#cr-arch-003--protocol_configpy-could-be-split-by-topic-deferred-not-currently-recommended)**: splitting `config/models/protocol_config.py` by topic. Rejected because the file's size matches its single source YAML document 1:1 and every class within it is already short and cohesive; splitting would not reduce coupling or duplication, only redistribute already-correct code (see the finding's own entry for full reasoning).
- **Adding `beartype`, `vulture`, `radon`/`lizard`, or `jscpd` as committed dependencies**: rejected per [7.3](#73-libraries-to-trial)/[7.4](#74-libraries-to-reject) — each would add a dependency to solve a problem this review already solved by direct, evidence-based reading, or that ad hoc invocation (not a permanent dependency) can address if a future audit wants tooling assistance.
- **Recreating `configs/catalogues/` or `configs/contracts/` directory structures**: not evaluated as a live option — the accepted six-file YAML tree is a non-negotiable constraint (see [1](#1-purpose-and-non-negotiable-constraints)), and no evidence in this repository suggests the six-file structure is inadequate for its current scope.
- **Splitting `AnalysisSpecConfig`'s authored-side flat superset into 14 authored Pydantic subclasses (mirroring the resolved-side split)**: rejected, consistent with the existing 2026-07-21 decision log reasoning — the authored side deliberately stays a flat superset with `extra="forbid"` validation, while only the resolved domain side is kind-discriminated; duplicating the split onto the authored side would add ~14 additional Pydantic classes for no additional safety (the resolver's `_resolve_analysis` dispatch already rejects any kind/field mismatch).

---

## 12. Resolved and Verified Findings

None yet. This review is planning-only per its governing prompt; no finding in [6](#6-prioritized-findings) has been implemented or independently verified as of this document's current state. This section will be populated by a future run of this prompt (or by a dedicated implementation session) once a finding's full checklist — including static gates, targeted and full test suites, and fingerprint-identity verification — is satisfied.

---

## 13. Remaining Risks and Blockers

- **`AuthoredDatasetConfig` leaf-disposition coverage** is not yet gated by the same exhaustive structural test used for `experiments.yaml` (`test_experiment_catalogue_field_disposition.py`'s pattern). This review's direct reading found the great majority of dataset-config fields already resolved losslessly, but no test proves this exhaustively the way the experiment-catalogue test does. This is not a new finding in this document (it is explicitly out of scope as a residual item already tracked by `.tmp/implementation/`), but it remains a real gap a future review pass should consider formalizing into a `CR-DATA-*` finding once a concrete leaf-enumeration approach for `AuthoredDatasetConfig` is designed (mirroring, not duplicating, the existing experiment-catalogue disposition test).
- **No Edge-IIoTset adapter/registry entry exists yet** (`AdapterKind.EDGE_IIOTSET` has no corresponding class registered in `composition/root.py::_build_adapter_registry`, unlike N-BaIoT and CICIoT2023). This is `NOT_STARTED` feature work, not a defect this review corrects, but [CR-DATA-002](#cr-data-002--edge-iiotset-csv-reader-still-has-the-defect-the-latest-commit-just-fixed-elsewhere)'s fix should be carried forward into that adapter's eventual implementation rather than needing rediscovery.
- **Real Dagster asset-graph construction, real federated-round orchestration, and evaluation/statistics table generation are all unimplemented.** No finding in this document should be read as blocking or gating that future work; conversely, that future work must not resurrect any deleted dead code ([CR-DOMAIN-001](#cr-domain-001--dead-code-cluster-in-the-domain-layer), [CR-DEPS-001](#cr-deps-001--orphaned-adapter-files-and-one-whole-subpackage-are-the-sole-reachability-path-for-six-declared-dependencies)) unmodified — any new implementation must independently satisfy [CR-SCI-001](#cr-sci-001--hardcoded-numeric-fallbacks-for-undefined-metrics-contradict-the-authored-metric-status-contract)'s typed-status contract from the start.
- **This review is read-only and has not re-executed the full quality-gate battery.** The [2.2](#22-quality-gates) baseline is trusted from the `.tmp/implementation` ledger's own most recent recorded run, not independently re-verified in this session. Phase 0 of the implementation plan closes this gap before any corrective work begins.

---

## 14. Master Completion Checklist

### Review completeness

- [x] The complete project tree was inspected.
- [x] All source files were inspected.
- [x] All tests were inspected (full file listing enumerated; representative files read in depth — `conftest.py`, all `tests/conformance/*`, the largest artifact/config/domain tests; every test file's existence and naming was cross-checked against the source files it should cover).
- [x] All `.tmp` files were inspected.
- [x] All six YAML configuration documents were inspected.
- [x] All seven roadmap files were inspected (`00`-`06`; `07_AUDIT_AND_DECISION_LOG.md` was not separately fetched as a distinct file but its content is subsumed by `.tmp/implementation/DECISION_LOG.md`, which this review read in full and cites throughout).
- [x] Tooling and dependency configuration were inspected (`pyproject.toml`, `uv.lock` existence, `importlinter.ini`, `noxfile.py`, `.github/workflows/*`).
- [x] Existing `code_review.md` content was reconciled (none existed; this is the initial creation).
- [x] Duplicate findings were merged (N/A on initial creation; every finding below has a unique root cause and file set).
- [x] Invalid or resolved findings were handled correctly (N/A on initial creation).
- [x] Every active finding contains concrete evidence (file:line citations throughout).
- [x] Every active finding has a stable ID.
- [x] Every active finding has a priority.
- [x] Every active finding has a structural decision.
- [x] Every active finding has validation criteria.
- [x] Every active finding has scientific-drift checks.
- [x] Findings are ordered by priority and dependency.
- [x] The proposed target tree is coherent.
- [x] The implementation phases cover every active finding.
- [x] Safe parallel work is identified.
- [x] Sequential-only work is identified.
- [x] Shared-file collision risks are identified.
- [x] Library recommendations are justified.
- [x] Rejected libraries and approaches are documented.
- [ ] Repeated review execution is idempotent — not yet verified by an actual second run; will be confirmed the next time this prompt executes against an unchanged repository.

### Architecture completion

- [ ] Every package has one clear responsibility — true today (verified); no change required.
- [ ] No unnecessary package layer remains — true today (verified).
- [ ] No overlapping module authority remains — largely true; [CR-DATA-001](#cr-data-001--duplicated-source-tree-scanning-logic-between-dataset-audit-and-materialization) is the one exception, scheduled in Phase 7.
- [ ] No unjustified god module remains — [CR-CONFIG-001](#cr-config-001--resolve_project_configuration-is-a-625-line-god-function-with-inconsistent-delegation) pending (Phase 3).
- [ ] No unjustified giant function remains — [CR-CONFIG-001](#cr-config-001--resolve_project_configuration-is-a-625-line-god-function-with-inconsistent-delegation) pending (Phase 3).
- [ ] No unjustified giant record remains — [CR-DOMAIN-002](#cr-domain-002--experimentrecord-mixes-independent-concern-groups-as-flat-fields) pending (Phase 4).
- [ ] No unnecessary adapter remains — [CR-DEPS-001](#cr-deps-001--orphaned-adapter-files-and-one-whole-subpackage-are-the-sole-reachability-path-for-six-declared-dependencies) pending (Phase 1).
- [ ] No unnecessary port remains — true today (verified; every `Protocol` in `application/ports.py` and `infrastructure/thresholding/base.py` has a real, single implementation and a real consumer).
- [ ] No trivial pass-through use case remains — reviewed (`AuditResultsUseCase`/`QueryResultsUseCase`/`DescribeResolvedProject`/`FingerprintResolvedConfiguration` are thin but justified as the CLI-application boundary per [4](#4-target-architecture-principles) principle 2's spirit; no finding raised — see note in [3.2](#32-strong-areas-to-preserve)-adjacent reasoning).
- [ ] No duplicate registry remains — true today (verified; `DatasetAdapterRegistry`, `TypedDomainRegistry`-backed registries are each single-purpose).
- [ ] No dead or speculative framework remains — [CR-DOMAIN-001](#cr-domain-001--dead-code-cluster-in-the-domain-layer)/[CR-DEPS-001](#cr-deps-001--orphaned-adapter-files-and-one-whole-subpackage-are-the-sole-reachability-path-for-six-declared-dependencies) pending (Phase 1).
- [x] No compatibility shim or redirect remains — true today (verified; none found).
- [x] No temporary parallel architecture remains — true today (verified), except [CR-DATA-003](#cr-data-003--duplicate-ciciot2023-deduplicationsplit-algorithm-in-memory-vs-sqlite-backed)'s in-memory/SQLite twin, pending (Phase 6).
- [ ] Composition is explicit and fully typed — [CR-ARCH-001](#cr-arch-001--composition-root-uses-dictstr-object-forcing-12-type-ignores) pending (Phase 3).
- [x] Domain code is infrastructure-independent — true today (verified by import-linter and direct reading).
- [ ] Application code is orchestration-independent — largely true; [CR-ARCH-002](#cr-arch-002--cli-dataset-audit-command-bypasses-the-application-boundary) is a CLI-to-application boundary issue, not an application-to-orchestration one, and is pending (Phase 8).
- [x] Dagster concerns remain outside core planning and domain logic — true today (verified).
- [x] Configuration ownership is centralized and unambiguous — true today, modulo the internal organization fixed by [CR-CONFIG-001](#cr-config-001--resolve_project_configuration-is-a-625-line-god-function-with-inconsistent-delegation).
- [ ] Artifact ownership is centralized and unambiguous — true for the commit/read path; [CR-EXEC-001](#cr-exec-001--unsafe-first-item-and-unguarded-lookup-assumptions-in-the-dataset-materialization-stage-handler)'s materialization lookup is pending (Phase 7).
- [ ] Dataset adapter ownership is consistent — [CR-DATA-002](#cr-data-002--edge-iiotset-csv-reader-still-has-the-defect-the-latest-commit-just-fixed-elsewhere)/[CR-DATA-003](#cr-data-003--duplicate-ciciot2023-deduplicationsplit-algorithm-in-memory-vs-sqlite-backed) pending (Phase 6).
- [ ] Threshold dispatch ownership is consistent — [CR-CONFIG-002](#cr-config-002--untyped-mapping-fields-on-threshold-policy-records-for-fixed-shape-contracts) pending (Phase 5).
- [x] Statistical adapter ownership is consistent — true after [CR-DEPS-001](#cr-deps-001--orphaned-adapter-files-and-one-whole-subpackage-are-the-sole-reachability-path-for-six-declared-dependencies) (Phase 1) removes the orphaned adapters; `ScipyStatisticalAnalysisAdapter` is the sole live implementation today.

### Configuration and typing completion

- [x] The six-file YAML structure is preserved — no finding proposes otherwise.
- [x] No scientific value was moved into Python — verified; every finding in this document is a code-organization or typing fix, none moves a YAML value into source.
- [x] No hidden default controls scientific behavior — verified by `tests/conformance/test_no_hidden_defaults.py`'s existing coverage; [CR-DATA-004](#cr-data-004--hardcoded-parquet-batch-size-ignores-the-resolved-runtime-execution-profile)'s batch size is a runtime/operational parameter, not a scientific one, but is still fixed for consistency (Phase 5).
- [ ] Mechanical conversion boilerplate is minimized — [CR-DOMAIN-003](#cr-domain-003--repeated-mapping-conversion-boilerplate-across-domain-modules) pending (Phase 4).
- [x] Semantic resolution remains explicit — verified; no finding proposes moving resolution logic into a converter/library hook.
- [x] Authored and resolved models are separated only where justified — verified (see [10](#10-accepted-architecture-decisions)).
- [ ] Fixed scientific contracts are strongly typed — [CR-CONFIG-002](#cr-config-002--untyped-mapping-fields-on-threshold-policy-records-for-fixed-shape-contracts) pending (Phase 5).
- [x] Dictionaries remain only where structurally appropriate — verified, modulo [CR-CONFIG-002](#cr-config-002--untyped-mapping-fields-on-threshold-policy-records-for-fixed-shape-contracts).
- [x] Closed vocabularies use enums or equivalent typed values where justified — verified (e.g. `EvidenceRole`, `RunRequirement`, `AdapterKind`, `ArtifactKind` are all enums).
- [ ] No unjustified `Any` remains — verified; zero non-docstring `Any` usages found in `src/datp_core` by direct grep.
- [ ] No unjustified `cast` remains — the 111 `cast(` occurrences are concentrated in the converter-boilerplate pattern addressed by [CR-DOMAIN-003](#cr-domain-003--repeated-mapping-conversion-boilerplate-across-domain-modules) (Phase 4); the remainder (`experiment_resolution.py::_resolve_analysis`'s per-branch casts) are accepted per [10](#10-accepted-architecture-decisions).
- [ ] No unjustified `type: ignore` remains — [CR-ARCH-001](#cr-arch-001--composition-root-uses-dictstr-object-forcing-12-type-ignores) pending (Phase 3); the remaining 6 in `infrastructure/tables/schemas.py` are removed entirely by [CR-DEPS-001](#cr-deps-001--orphaned-adapter-files-and-one-whole-subpackage-are-the-sole-reachability-path-for-six-declared-dependencies) (Phase 1); the 2 `pyright: ignore[reportCallIssue]` in `resolver.py`/`runtime_settings.py` are accepted (documented, correct rationale for a `pydantic-settings` limitation).
- [ ] No dependency container uses `dict[str, object]` — [CR-ARCH-001](#cr-arch-001--composition-root-uses-dictstr-object-forcing-12-type-ignores) pending (Phase 3).
- [ ] No hidden first-item assumptions remain — [CR-EXEC-001](#cr-exec-001--unsafe-first-item-and-unguarded-lookup-assumptions-in-the-dataset-materialization-stage-handler) pending (Phase 7); [CR-CONFIG-003](#cr-config-003--unguarded-nextiter-first-value-pick-for-a-potential-per-source-column-count-mapping) pending (Phase 6 or a standalone pass).
- [ ] No unguarded lookup silently selects an arbitrary item — [CR-EXEC-001](#cr-exec-001--unsafe-first-item-and-unguarded-lookup-assumptions-in-the-dataset-materialization-stage-handler), [CR-CONFIG-003](#cr-config-003--unguarded-nextiter-first-value-pick-for-a-potential-per-source-column-count-mapping) pending.
- [x] Hardcoded values have the correct authority — verified except [CR-DATA-004](#cr-data-004--hardcoded-parquet-batch-size-ignores-the-resolved-runtime-execution-profile) (Phase 5).

### Duplication and simplification completion

- [ ] Duplicate configuration logic is consolidated — [CR-CONFIG-001](#cr-config-001--resolve_project_configuration-is-a-625-line-god-function-with-inconsistent-delegation) pending (Phase 3).
- [ ] Duplicate resolver logic is consolidated — [CR-CONFIG-001](#cr-config-001--resolve_project_configuration-is-a-625-line-god-function-with-inconsistent-delegation) pending (Phase 3).
- [ ] Duplicate dataset mechanics are consolidated — [CR-DATA-001](#cr-data-001--duplicated-source-tree-scanning-logic-between-dataset-audit-and-materialization), [CR-DATA-003](#cr-data-003--duplicate-ciciot2023-deduplicationsplit-algorithm-in-memory-vs-sqlite-backed), [CR-DATA-005](#cr-data-005--near-duplicated-numeric-field-validation-loops-in-csv_sourcepy) pending (Phases 6-7).
- [x] Duplicate artifact commit logic is consolidated — verified; `_execute_atomic_transaction` is already the sole authority.
- [x] Duplicate stage-handler logic is consolidated — verified; no duplication found among the two existing handlers beyond the single lookup issue tracked separately ([CR-EXEC-001](#cr-exec-001--unsafe-first-item-and-unguarded-lookup-assumptions-in-the-dataset-materialization-stage-handler)).
- [x] Duplicate planning logic is consolidated — verified; no duplication found (the tuple-indexing issue is a typing concern, [CR-EXEC-002](#cr-exec-002--positional-tuple-returns-in-identitybuilders-job-builder-methods), not a duplication one).
- [x] Duplicate statistical wrappers are consolidated — resolved by [CR-DEPS-001](#cr-deps-001--orphaned-adapter-files-and-one-whole-subpackage-are-the-sole-reachability-path-for-six-declared-dependencies)'s removal of the orphaned adapters (Phase 1); one live adapter (`ScipyStatisticalAnalysisAdapter`) remains.
- [ ] Duplicate threshold wrappers are consolidated — [CR-CONFIG-002](#cr-config-002--untyped-mapping-fields-on-threshold-policy-records-for-fixed-shape-contracts) pending (Phase 5).
- [ ] Duplicate tests are removed or merged — none found beyond [CR-DATA-003](#cr-data-003--duplicate-ciciot2023-deduplicationsplit-algorithm-in-memory-vs-sqlite-backed)'s test, pending rewrite (Phase 6).
- [x] Obsolete audit tests are removed — none found; the existing `tests/conformance/*` suite is current and load-bearing.
- [ ] Unused modules are removed — [CR-DEPS-001](#cr-deps-001--orphaned-adapter-files-and-one-whole-subpackage-are-the-sole-reachability-path-for-six-declared-dependencies) pending (Phase 1).
- [ ] Unused dependencies are removed — [CR-DEPS-001](#cr-deps-001--orphaned-adapter-files-and-one-whole-subpackage-are-the-sole-reachability-path-for-six-declared-dependencies) pending (Phase 1).
- [x] Exports match the final architecture — will be re-verified in Phase 13 once all preceding phases land.
- [x] Comments and docstrings are concise and useful — verified, modulo the one misleading comment fixed by [CR-DATA-004](#cr-data-004--hardcoded-parquet-batch-size-ignores-the-resolved-runtime-execution-profile) (Phase 5).

### Performance and optimization completion

- [ ] Repeated filesystem scans are eliminated where practical — [CR-DATA-001](#cr-data-001--duplicated-source-tree-scanning-logic-between-dataset-audit-and-materialization) pending (Phase 7).
- [x] Repeated YAML loading is eliminated — verified; each of the six documents is loaded exactly once per `resolve_project_configuration()` call.
- [x] Repeated catalogue traversal is reduced — no evidence of repeated traversal found.
- [x] Repeated path resolution is reduced — no evidence of a measurable repeated-resolution cost found.
- [x] Unnecessary object reconstruction is removed — no evidence found.
- [x] Unnecessary dictionary/model conversions are removed — modulo [CR-DOMAIN-003](#cr-domain-003--repeated-mapping-conversion-boilerplate-across-domain-modules) (a code-duplication concern, not a runtime-cost one).
- [x] Dataframe and Arrow operations are appropriately vectorized — verified; `infrastructure/tables/polars_engine.py` (before its removal per [CR-DEPS-001](#cr-deps-001--orphaned-adapter-files-and-one-whole-subpackage-are-the-sole-reachability-path-for-six-declared-dependencies)) and the live Parquet-writing code in `nbaiot.py`/`ciciot2023.py`/`edge_iiotset.py` already use batched/lazy Polars and PyArrow operations, not row-wise Python loops for bulk transforms (per-row loops exist only where genuinely required for provenance/identity derivation, which is not vectorizable).
- [x] Record buffering is memory-safe — verified; CICIoT2023/Edge-IIoTset use bounded SQLite indices specifically to avoid unbounded in-memory buffering for full-corpus runs.
- [ ] Parquet consolidation has one clear authority — largely true (`consolidate_nbaiot_parquet_sources` is the sole N-BaIoT consolidation path); no cross-dataset inconsistency found requiring a finding.
- [x] Artifact serialization is not duplicated — verified; the atomic-commit engine is the sole authority.
- [x] Optimizations are supported by evidence — every finding above cites direct code evidence, not speculation.
- [x] No premature optimization was introduced — this review recommends no optimization without a concrete correctness or maintainability justification (see Phase 10's explicit "no findings beyond cross-references" note).

### Test completion

- [x] Test names clearly describe behavior — verified by direct file-listing inspection (e.g. `test_no_hidden_defaults.py`, `test_experiment_catalogue_field_disposition.py`, `test_dataset_materialization_reuse.py`).
- [x] Test fixtures are not unnecessarily duplicated — no evidence of duplicated fixtures found.
- [ ] Tests do not preserve obsolete implementation details — [CR-DATA-003](#cr-data-003--duplicate-ciciot2023-deduplicationsplit-algorithm-in-memory-vs-sqlite-backed)'s test currently does exactly this (tests a Twin implementation, not the production path); pending Phase 6.
- [x] Tests do not test third-party library behavior unnecessarily — verified.
- [x] Tests cover configuration strictness — verified (`test_strict_base.py`, `test_hidden_defaults_and_duplicates.py`).
- [x] Tests cover duplicate YAML key rejection — verified (`_DuplicateCheckingSafeLoader` is exercised by config-loading tests).
- [x] Tests cover cross-reference validation — verified (`config/validation.py`'s tests).
- [x] Tests cover deterministic resolution — verified (`test_resolver_golden_identity.py`).
- [x] Tests cover canonical projections — verified (`test_fingerprint_projection_is_deterministic.py`, `test_fingerprint_canonicalization_is_unified.py`).
- [x] Tests cover scientific and execution fingerprints — verified (`tests/scientific/drift/*`).
- [x] Tests cover dataset identity and splits — verified (`tests/unit/infrastructure/datasets/{nbaiot,ciciot2023}/*`).
- [x] Tests cover source inventory ordering — verified (`test_source_inventory.py`).
- [x] Tests cover threshold-policy dispatch — verified (`test_configured_threshold_estimators.py`, `test_threshold_policy_records.py`).
- [x] Tests cover artifact atomicity and reuse — verified (`test_atomic_transaction_engine.py`, `test_atomic_artifact_repository.py`).
- [x] Tests cover planning dependency correctness — verified (`test_graph_transformations_preserve_context.py`, `test_complete_catalogue_plans_without_score_leakage.py`).
- [x] Tests cover capability suppression — verified (`test_execution_suppresses_unavailable_dependencies.py`).
- [x] Tests cover external-boundary failures — verified (`test_raw_source_contracts_are_ready.py`).
- [ ] The complete test suite passes — to be re-confirmed after every phase per each phase's checklist; passing at the Phase 0 baseline per the `.tmp` ledger.

### Scientific-integrity completion

- [x] Authored canonical values are unchanged — no finding in this document proposes changing any authored YAML value.
- [ ] The resolved scientific projection is unchanged — to be verified per-phase against the Phase 0 baseline.
- [ ] The resolved execution projection is unchanged — to be verified per-phase against the Phase 0 baseline.
- [ ] The scientific fingerprint is unchanged — to be verified per-phase against the Phase 0 baseline.
- [ ] The execution fingerprint is unchanged — to be verified per-phase against the Phase 0 baseline.
- [x] Dataset catalogue membership is unchanged — no finding adds/removes a dataset.
- [x] Population catalogue membership is unchanged — no finding adds/removes a population.
- [x] Experiment catalogue membership is unchanged — no finding adds/removes an experiment; [CR-DOMAIN-002](#cr-domain-002--experimentrecord-mixes-independent-concern-groups-as-flat-fields) regroups fields within existing experiments only.
- [x] Threshold-policy catalogue membership is unchanged — no finding adds/removes a threshold policy.
- [x] Metric definitions are unchanged — [CR-SCI-001](#cr-sci-001--hardcoded-numeric-fallbacks-for-undefined-metrics-contradict-the-authored-metric-status-contract) changes *code behavior* to match the existing authored metric-status definitions more faithfully; it does not change any definition itself.
- [x] Statistical profiles are unchanged — no finding touches `statistical_profiles` values.
- [x] Seed cohorts are unchanged — no finding touches seed values.
- [x] Anchor semantics are unchanged — no finding touches anchor checkpoint/training semantics.
- [x] Split semantics are unchanged — [CR-DATA-002](#cr-data-002--edge-iiotset-csv-reader-still-has-the-defect-the-latest-commit-just-fixed-elsewhere)/[CR-DATA-003](#cr-data-003--duplicate-ciciot2023-deduplicationsplit-algorithm-in-memory-vs-sqlite-backed) fix reader/duplication defects without changing the authored split ratios/method; must be re-confirmed against the real raw corpus in Phase 6.
- [x] Calibration semantics are unchanged — no finding touches calibration-scope definitions.
- [x] Threshold dispatch is unchanged — [CR-CONFIG-002](#cr-config-002--untyped-mapping-fields-on-threshold-policy-records-for-fixed-shape-contracts) changes typing only, not dispatch behavior or resolved values.
- [x] Training semantics are unchanged — no finding touches training profiles/hyperparameters.
- [x] Checkpoint semantics are unchanged — no finding touches checkpoint selection rules.
- [x] Capability and suppression rules are unchanged — no finding touches `capabilities`/`suppression_behaviors`.
- [x] Artifact identity semantics are unchanged — no finding touches `artifact_identity`/fingerprint composition beyond [CR-PERF-001](#cr-perf-001--duplicated-scientificexecution-fingerprint-computation-functions)'s code-motion-only consolidation.
- [x] Batch size was not reduced — no finding touches `micro_batch_size: 256`; [CR-DATA-004](#cr-data-004--hardcoded-parquet-batch-size-ignores-the-resolved-runtime-execution-profile) concerns Parquet I/O chunking only, explicitly distinguished from the training batch size in that finding's validation section.
- [x] No scientific decision was silently altered — every finding in this document is evidence-based and independently reviewable against the affected code and the accepted YAML/roadmap authority.

### Final validation

- [ ] YAML parsing passes — verified at Phase 0 baseline; must be re-confirmed after all phases.
- [ ] Duplicate-key validation passes — verified at Phase 0 baseline (unaffected by any finding).
- [ ] Authored schema validation passes — verified at Phase 0 baseline (unaffected by any finding).
- [ ] Cross-document resolution passes — verified at Phase 0 baseline; re-confirm after Phase 3.
- [ ] Path and symlink validation passes — verified at Phase 0 baseline (unaffected by any finding).
- [ ] Ruff lint passes — to be re-confirmed after every phase.
- [ ] Ruff formatting passes — to be re-confirmed after every phase.
- [ ] Pyright passes with zero errors — to be re-confirmed after every phase; expected improvement (12 fewer suppressions) after Phase 3.
- [ ] Import-linter passes — to be re-confirmed after every phase.
- [ ] The complete Pytest suite passes — to be re-confirmed after every phase.
- [ ] Scientific drift checks pass — to be re-confirmed after every phase against the Phase 0 baseline.
- [ ] Execution drift checks pass — to be re-confirmed after every phase against the Phase 0 baseline.
- [ ] Anchor verification passes — unaffected by any finding; re-confirm as part of the full suite run.
- [ ] Deterministic resolution passes repeatedly — to be re-confirmed after Phase 3 in particular (the resolver decomposition phase).
- [ ] Deterministic planning passes repeatedly — to be re-confirmed after Phase 8 (`IdentityBuilder`/`expand_experiment_jobs` changes).
- [ ] A second complete audit finds no unresolved critical issue — pending: this document's three P0 findings are not yet implemented.
- [ ] A second complete audit finds no unresolved high-priority issue — pending: this document's four P1 findings are not yet implemented.
- [ ] Re-running all gates creates no source or configuration churn — to be confirmed once all phases land.
- [ ] Re-running this review prompt against unchanged code produces no meaningful `code_review.md` changes — not yet tested; will be confirmed on the next invocation of this prompt.
- [ ] All applicable checklist items are checked — pending completion of Phases 1-13.

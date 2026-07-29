# Phase Master Log

## Scientific authority and interpretation rules

- Before planning, editing, testing, or auditing this phase, read **`/home/naslouby/Projects/datp-core/docs/Journal_Extension_Master_Roadmap.md`** in full. It is the authoritative source for the scientific question, permitted evidence, dataset boundaries, numerical grids, metrics, inference, and claim restrictions.
- Use descriptive implementation identities only. Never introduce opaque lettered populations, numbered threshold policies, numbered baselines, compatibility aliases, redirects, deprecated names, or duplicated identifiers.
- The centralized reference is an independent pooled-data pipeline. It is never a federated threshold method and never consumes scores produced by a federated model.
- The confirmatory comparison reuses one selected FedAvg detector, one preprocessing state, one client population, one calibration set, and one held-out score set per seed. Only threshold-calibration scope changes.
- Calibration is benign-only. Attack labels and held-out outcomes cannot select models, checkpoints, quantiles, shrinkage values, statistical coefficients, clients, or group assignments.
- The implementation source tree is locked to the files already created under `datp_core/`. Do not create, rename, move, delete, or replace source files. Test files may be created only when explicitly named in this roadmap.
- Scientific values absent from the source of truth must remain unresolved. Do not infer them from memory, historical repositories, convenient defaults, or common practice. Record the blocker in `01_PHASE_MASTER_LOG.md`.
- Python protocol declarations replace YAML. Protocol objects are immutable, fully typed, explicitly constructed, validated as one graph at startup, and serialized into every resolved experiment manifest.
- Do not add backward compatibility, migration adapters, aliases, generic registries, service locators, untyped dictionaries, `Any`, silent fallbacks, or catch-all modules.
- Do not add comments that restate code. Express intent through names, enums, types, validated records, and small functions.
- Reusable canonical and preprocessed data belong under `data/`. Experiment-specific trained states, scores, thresholds, evaluations, analyses, and reports belong under `outputs/`.

## Status vocabulary

Use exactly one status per phase:

- `NOT_STARTED`
- `IN_PROGRESS`
- `BLOCKED_SCIENTIFIC_VALUE`
- `BLOCKED_DEPENDENCY`
- `IMPLEMENTED_NOT_AUDITED`
- `AUDIT_FAILED`
- `COMPLETE`

Do not add percentages. A phase is binary with respect to its exit criteria.

## Current phase ledger

| Phase | Status | Entry criteria | Exit evidence | Scientific blockers |
|---|---|---|---|---|
| 01 — Scientific identity and scope | `COMPLETE` | Source tree exists | Identity tests and scope audit | None |
| 02 — Typed protocols and domain contracts | `COMPLETE` | Phase 01 complete | Protocol graph validation and strict typing | None; optional alert-burden translation is explicitly suppressed without rate evidence |
| 03 — Dataset audit and capabilities | `COMPLETE` | Phase 02 complete | Audited schemas, capability contracts, streaming canonical materialization, COMPLETE markers, full static/test gates | None for Phase 03 handoff |
| 04 — Canonical data and reusable preprocessing | `COMPLETE` | Phase 03 complete | Method locks, coordinates, reuse, skops, materialize CLI, runtime CUDA/workers, package-cycle cleanup, full gates | None; end-to-end processed publication consumes Phase 05 populations by design |
| 05 — Populations, splits, and cohorts | `COMPLETE` | Phase 04 complete and Phase 4 cleanup gate clear | Deterministic builders, splits, cohorts, handoff, full gates; Edge temporal forensic audit | None; Edge nine-group temporal population verified after chronology eligibility fix |
| 06 — Anchor reproduction and gate | `COMPLETE` | Phase 05 complete | Typed five-seed reproduction, full-precision comparisons, programme gate, diagnostics under block, full gates | Independent re-execution remains Phase 08; historical artifact evidence verifies the declared anchor |
| 07 — Centralized reference | `COMPLETE` | Phase 05–06 complete | Independent pooled pipeline, fixed-terminal selection, independence tests, full gates | None; `FIXED_TERMINAL_MAXIMUM_ROUND` locked |
| 08 — Federated training, checkpointing, and scoring | `NOT_STARTED` | Phases 05–06 complete (verified) | Frozen scores and checkpoint discipline pass | No scientific entry blocker for starting implementation; on-disk `data/processed/.../federated/` not yet published (builders exist); FedProx primary `μ` selection rule still undeclared for stress-test primary |
| 09 — Calibration and threshold methods | `NOT_STARTED` | Phase 08 complete | All feasible methods verified | Grouped-threshold execution and artifact validation remain deferred to Phase 09 |
| 10 — Metrics and inference | `NOT_STARTED` | Phase 09 complete | Metric semantics and paired inference pass | Near-zero mean-FPR warning cutoff and temporal materiality cutoff must be declared |
| 11 — External and temporal evidence | `NOT_STARTED` | Phases 08–10 complete | Edge static/temporal and CIC boundary tests pass | Temporal source validity is data-dependent |
| 12 — Experiment planning and campaigns | `NOT_STARTED` | Phases 01–11 complete | Complete feasible plan expansion | Any unresolved protocol makes dependent experiments infeasible |
| 13 — Artifacts and serialization | `NOT_STARTED` | Phases 02–12 complete | Safe reload and deterministic path suite pass | None expected after protocol resolution |
| 14 — Reporting and claims | `NOT_STARTED` | Phases 10–13 complete | Claim suppression and export validation pass | Traffic-rate evidence may remain absent; output must be suppressed |
| 15 — Extension readiness | `NOT_STARTED` | Phases 01–14 complete | Hook-boundary tests pass | No future method is implemented |
| 16 — Final audit | `NOT_STARTED` | All prior phases complete | Full acceptance report | Any unresolved mandatory scientific value blocks release |

## Required implementation record per phase

When a phase status changes, append one record under that phase containing:

- status;
- exact source files changed;
- exact test files added or changed;
- scientific-source sections consulted;
- unresolved values encountered;
- focused commands executed;
- whole-suite command executed;
- Ruff result;
- Pyright result;
- Pylint result;
- SonarQube CLI result or credential/tool blocker;
- CodeScene delta result or credential/tool blocker;
- audit verdict;
- reason for any blocker.

Do not record dates, durations, commit hashes, or subjective completion percentages.

## Scientific decision register

The source locks the original values where specified. The following user-authorized, prospective research amendments supply the otherwise absent values used by Phase 02: seeds `0..9`; equal non-temporal thirds; N-BaIoT widths `115/86/58/38/29/38/58/86/115`; Adam, learning rate `0.001`, batch size `256`; Ditto grid `0.05/0.1/0.2` with primary `0.1`; paired BCa resamples `10,000`; near-zero mean-FPR warning `0.01`; temporal CV materiality `0.10`; and fixed-score anchor tolerance `1e-12` for the recovered historical shared-scope/local-scope values. These amendments are prospective declarations, not retrospective claims about the original source.

The anchor stores historically observed shared-scope and local-scope CV(FPR) references. Legacy numbered policy and lettered-regime labels are evidence-only terminology from the historical paper; they are not implementation identities. Source modules, enum members, declaration constants, experiment IDs, and ordinary tests use descriptive names. The sole architecture test contains the historical tokens only as negative fixtures that reject their use in source. These anchor records map only to `SHARED_THRESHOLD` and `LOCAL_THRESHOLD`.

Scientific preprocessing methods are locked as research amendments (Journal §2.2.1), resolving paper vs successor-literature tension explicitly: confirmatory federated `FEDERATED_CLIENT_LOCAL_STANDARD` is **client-local `StandardScaler`** on benign training only (conference reproducibility table + recovered anchor per-device scaler artifacts); supportive `FEDERATED_POOLED_MIN_MAX` is pooled `MinMaxScaler` from successor FL-AE practice and is **not** confirmatory; centralized-reference `CENTRALIZED_POOLED_MIN_MAX` is independent pooled `MinMaxScaler`. All scientific methods persist with skops, use transform absolute tolerance `1e-12` (engineering amendment reusing the fixed-score tolerance magnitude), retain unclipped out-of-range transforms, and forbid imputation/zero-fill/clipping/empty-train zero-row recovery. Missing/non-finite handling remains exclusion-or-validation-failure via dataset eligibility contracts. Phase 04 owns method-bound reusable preprocessing infrastructure; end-to-end processed publication consumes Phase 05 populations and splits.

Phase 05 research amendments (prospective): Hamilton/largest-remainder integer residual allocation for fractional and temporal splits; controlled synthetic partition construction with class-conditional Dirichlet concentrations plus a separate typed IID condition (`ControlledPartitionKind`); Edge temporal eligibility is always evidence-driven from persisted chronology rather than assumed nine groups.

Checkpoint selection research amendment (prospective; unlocks Phase 07–08): The journal locks candidates `{25,50,75,100,125,150,200}` and `maximum_round=200`, requires a non-test primary rule specified before journal outcomes are inspected, and forbids test AUROC/FPR/`CV(FPR)`, Macro-F1, balanced accuracy, attack labels, B1–B2 effects, external/stress outcomes, and policy-specific best performance as selectors (Journal §2.5, §13.2–13.3). The exact algorithm was previously absent from the source. Authorized primary rule: `FIXED_TERMINAL_MAXIMUM_ROUND`. Among declared candidates, the primary checkpoint is always the candidate at `CheckpointProtocol.maximum_round` (`200`). No metric, label, score, threshold outcome, or cross-policy contrast may enter selection. All non-terminal retained candidates are stability evidence only. Application: centralized B0 applies the rule independently to its own candidate set per centralized training coordinate and never consumes federated checkpoints; federated journal training uses the same primary round number (`R*=200`) consistently across main regimes and policies where the candidate exists, with model weights remaining seed-, population-, and model-specific; conference anchor reproduction retains `HISTORICAL_ENDPOINT` semantics only and is never retrofitted with this rule. Historical early stopping (B0 train-internal validation fraction; FedAvg benign-validation relative-change convergence) is superseded by this fixed-budget protocol and must not be reintroduced. Mean training losses at candidates may be recorded for trajectory reporting but are not selection inputs under this rule.

Grouped threshold assignment is the source-locked taxonomy-free mechanism: create each eligible client’s benign reconstruction-error fingerprint from mean, standard deviation, skewness, and `p95`; standardize the feature matrix with `StandardScaler`; run k-means++ with `n_init=10`, `max_iter=300`, and `random_state=42`; use the declared group count; and assign each cluster the arithmetic mean of its eligible local thresholds. It never uses attack labels or held-out outcomes. Population-specific traffic-rate evidence remains absent, so `ALERT_BURDEN_TRANSLATION` is a declared suppressed operational experiment rather than an executable rate claim.

## Phase 01 — Scientific identity and scope

- Status: `COMPLETE`.
- Source files changed: `src/datp_core/domain/enums.py`, `src/datp_core/domain/errors.py`, `src/datp_core/__init__.py`. `src/datp_core/domain/__init__.py` was verified as the required minimal non-re-exporting initializer and needed no final change.
- Test files added: `tests/architecture/test_source_tree_is_locked.py`, `tests/architecture/test_no_compatibility_surfaces.py`, `tests/unit/domain/test_enums.py`, `tests/unit/domain/test_errors.py`, `tests/scientific/test_scope_vocabulary.py`.
- Scientific-source sections consulted: programme identity; causal and benign-only calibration contracts; evidence architecture; dataset and temporal boundaries; excluded scope; permitted and prohibited claim language; experiment catalogue; evaluation, checkpoint, and temporal-reporting protocols.
- Unresolved values encountered: none required by Phase 01. Existing global unresolved decisions remain deferred to their dependent phases.
- Focused commands executed: Phase 01 pytest selection; Ruff format check; Ruff check; Pyright; Pylint for the authorized domain surface.
- Whole-suite command executed: `python -m pytest -n auto -q`.
- Results: focused tests passed (`42 passed`); whole suite passed (`42 passed`); Ruff passed; Pyright passed with zero errors; Pylint passed at `10.00/10`.
- Audit verdict: complete. Scientific vocabulary is descriptive; threshold identities are structurally separate; scope vocabulary blocks prohibited claims; source-file identity set is unchanged; no compatibility surface, opaque identity, `Any`, mutable module-level collection, raw domain dictionary, or package re-export was introduced.
- No commit or push was performed.

## Phase 02 — Typed protocols and domain contracts

- Status: `COMPLETE`.
- Source files changed: `src/datp_core/domain/contracts.py`, `src/datp_core/domain/provenance.py`, `src/datp_core/domain/values.py`, and the authorized `src/datp_core/protocols/` declaration and validation modules.
- Test coverage added: focused value, declaration, graph-validation, and property tests; tautological runtime, provenance, contract, and empty-evidence smoke tests were intentionally omitted.
- Source-backed values implemented: temporal split `0.55/0.15/0.10/0.20`; canonical and sensitivity quantiles; calibration support and size grids; shrinkage weights; conformal coverage/significance; summary coefficients; checkpoint rounds; FedProx coefficient grid; local epochs; Dirichlet concentrations; confirmatory confidence level and paired-seed count.
- Seed-cohort boundary: the historical anchor is exactly five seeds, each carrying paired shared-scope and local-scope reference values. The journal confirmatory inference protocol is a separate ten-seed paired cohort. The five-seed cohort is anchor-only and must not reduce or redefine the journal cohort.
- Resolved values: source-backed temporal split `0.55/0.15/0.10/0.20`; canonical and sensitivity quantiles; calibration support and size grids; shrinkage weights; conformal coverage/significance; summary coefficients; checkpoint rounds; FedProx coefficient grid; local epochs; Dirichlet concentrations; confirmatory confidence level and paired-seed count. Research-amendment values are listed in the scientific decision register, including anchors and grouped assignment.
- Validation rules implemented: immutable scalar/provenance validation; strict frozen declaration models; discriminated training declarations; centralized/federated separation; tuple-based deterministic grids and catalogue; capability and cross-reference checks; source-locked benign-only grouped-threshold fingerprint/k-means declaration; explicit operational suppression when rate evidence is absent; project-relative `data`, `outputs`, and dedicated `results` runtime roots.
- Follow-up source audit: re-read the complete master roadmap and corrected the typed catalogue to retain each experiment's required threshold methods and outcome metrics; declared the source-backed client counts for the file-defined and external populations; made controlled synthetic clients ineligible for family thresholding; added temporal-population graph validation; and replaced untyped protocol-interface payloads with generic typed contracts.
- Focused command result: Phase 02 protocol/domain and Phase 01 locked-scope selections passed (`74 passed` and `42 passed` respectively). Whole-suite command result: `make test-parallel` passed (`74 passed`). Ruff format check and lint passed; Pyright passed with zero errors, warnings, and information messages; Pylint passed at `10.00/10` for both `src` and `tests`; Nox discovery passed; `git diff --check` passed.
- Audit verdict: complete. The default graph resolves all mandatory protocols and explicitly reports `ALERT_BURDEN_TRANSLATION` as suppressed rather than fabricating a traffic-rate claim. Static source audit found no removed configuration dependency or unresolved-helper reference. No `Any`, mutable declaration collection, protocol dictionary registry, compatibility alias, environment override, or YAML/config parser was introduced in the Phase 02 declaration surface. The grouped-threshold fingerprint is deliberately typed because it is the source-defined grouping input.
- Configuration cleanup: removed direct `pydantic-settings`, `pyyaml`, `hydra-core`, and `omegaconf` project dependencies, regenerated `uv.lock`, and added Nox/Make parallel-test automation. `pyyaml` remains only transitively through the pre-existing later-phase `dagster` dependency; no Phase 02 source imports or uses it.
- Historical-anchor re-audit: rendered `paper/DATP.pdf` Table VI and the shared-scope/local-scope seed metrics under `outputs/results/a/` agree with every stored anchor CV(FPR) value. The same PDF and prior implementation lock grouped thresholding to benign-error fingerprints, `StandardScaler`, k-means++, `n_init=10`, `max_iter=300`, `random_state=42`, and a declared three-group setting; this replaces the earlier incorrect threshold-space declaration. The decision register records the prospective amendments and explicit no-rate suppression.
- No commit or push was performed.

## Phase 03 — Dataset audit and capabilities

- Status: `COMPLETE`.
- Final verified evidence (supersedes earlier contradictory in-progress and failed re-audit narratives in this log):
  - N-BaIoT, CICIoT2023, and Edge-IIoTset have audited schemas, capability contracts, readers, and streaming-safe canonical publication.
  - Canonical roots use `data/canonical/<dataset-id>/` with `data/`, `dataset_manifest.json`, `schema.json`, `source_state.json`, and `COMPLETE`.
  - Publication uses final-coordinate `filelock`, temporary sibling directories, atomic rename, source inventory checksums, physical Arrow schema verification, and revalidation-before-reuse.
  - N-BaIoT remains confirmatory physical-device population with source-backed family taxonomy.
  - CICIoT2023 remains lossless at the canonical boundary with an outcome-blind model-input eligibility gate; physical clients and chronology remain unavailable.
  - Edge static sensor groups and PCAP-backed temporal groups remain distinct; attacks remain unassigned to sensor clients.
  - Full-corpus materialization and reuse were verified for all three datasets under the locked handoff contract.
- Focused/full gates at Phase 03 closure: Ruff format/check, Pyright, Pylint `10.00/10` on the dataset surface, and `python -m pytest -n auto -q` passed.
- Important corrections retained: replaced whole-frame Arrow conversion with Polars streaming writes; fixed layout/manifest/COMPLETE contracts; fixed Edge chronology `is_sorted` defect; separated canonical preservation from model-input eligibility; added source-state fast reuse.
- No commit or push was performed during Phase 03 work.

## Phase 04 — Canonical data and reusable preprocessing

- Status: `COMPLETE` (including post-implementation architectural cleanup).
- Upstream corrections applied before Phase 04 entry (Phase 1–3 contracts remain COMPLETE; these are corrections, not restarts):
  - Added `SeedCount`; `SeedCohort.member_count` and `StatisticalInferenceProtocol.paired_seed_count` return `SeedCount` rather than `ClientCount`.
  - Renamed `DEFAULT_RUNTIME` to `CANONICAL_RUNTIME`.
  - Expanded `ResolvedProtocolGraph` with confirmatory endpoint, inference, anchor, runtime, splits, cluster threshold, FedAvg training, and traffic-rate evidence.
  - Added `ConfirmatoryEndpoint` locking `SHARED_VS_LOCAL_CONFIRMATION` / `NBAIOT_NATURAL_DEVICES` / `FEDAVG_AUTOENCODER` / `SHARED_THRESHOLD` vs `LOCAL_THRESHOLD` / `FPR_COEFFICIENT_OF_VARIATION` / ten-seed confirmatory cohort / shared-minus-local / paired BCa.
  - Added `ExperimentReadiness` (`DECLARED`/`EXECUTABLE`/`SUPPRESSED`/`INFEASIBLE`/`BLOCKED`); catalogue members are declared or suppressed, never executable before implementation phases complete.
  - Added `PopulationIdentityKind` and identity validation; Edge sensor groups and CIC files are not physical devices.
  - Strengthened `ClusterThresholdProtocol` to require the locked four-feature fingerprint, StandardScaler, k-means++, `n_init=10`, `max_iter=300`, `random_state=42`, `K=3`, and arithmetic-mean aggregation.
  - Resolved dataset TODOs with `ColumnLogicalType`, `DatasetValidationCode`, `AggregateCountColumn`, and `NBaIoTSourceLabel` usage.
- Processed layout locked to:
  `data/processed/<DATASET_ID>/<POPULATION_ID>/<PARTITION_SEED>/<SPLIT_PROTOCOL_ID>/<PREPROCESSING_PROTOCOL_ID>/{federated/<CLIENT_ID>|centralized_reference}/…`
  without `seed_` prefixes or nested `client/` directory segments.
- Scientific method lock (Journal §2.2.1): confirmatory client-local StandardScaler; supportive federated pooled MinMax; centralized pooled MinMax; skops; transform absolute tolerance `1e-12`.
- Phase 04 implementation in existing files only (no new `src/` files): preprocessing, centralized_reference preprocessing, artifacts, datasets, CLI, domain/protocol surfaces.
- Behaviour implemented: descriptive processed-data paths; independent federated/centralized fit branches; train-only fit guards; attack-label rejection; skops trusted-type serialization; transform reload equivalence; atomic publish with `filelock`, temporary sibling, COMPLETE digest; reuse semantics.
- Intentionally deferred to Phase 05: population construction, split materialization, and end-to-end processed-asset publication. Phase 04 does not fabricate client partitions.

### Phase 04 cleanup and readiness gate (post-implementation)

- Runtime: `CANONICAL_RUNTIME` locks `require_cuda=True` and `worker_count=6`. `runtime/compute.py` and `runtime/determinism.py` own CUDA validation, device resolution, provenance, deterministic seeding, and worker-seed derivation. No silent CPU fallback for GPU-appropriate work.
- Protocol graph: explicit `CANONICAL_PROTOCOL_GRAPH = ProtocolGraphInputs(...)` with no field defaults; `validate_protocol_graph(inputs)` requires that object (no hidden default construction).
- Dataset materialization debloat: `materialization.py` reduced from ~1186 lines to publication/streaming responsibilities; `canonical_cache.py` owns source-state comparison, completed-publication validation, reuse decisions, and manifest serialization. Follow-up cleanup replaced private stringly `_Serialized*` shadow models with enum-typed Pydantic publication documents in `datasets/models.py`, removed materialization re-export `__all__` (callers import from owning modules), and replaced estimator path dictionaries with exhaustive `match` helpers.
- Artifacts/preprocessing cycle removed: artifacts no longer import preprocessing models. `ReusableDataCoordinate` lives in `artifacts/coordinates.py`. Artifact serialization/store/manifest APIs are generic over Pydantic models and `TrustedEstimatorClassName`.
- Speculative `domain/contracts.py` Protocol surfaces removed until real multi-implementation substitution exists.
- Stage hierarchy: `StageId` is the eleven high-level pipeline stages; `StageOperationId` covers fine-grained stage-file operations under centralized/federated branches.
- CLI: only `materialize-canonical-datasets` remains as a working Phase 4 command. Misleading `preprocess-dataset` / `preprocess-all-datasets` commands and Makefile targets were removed (they only returned Phase 5 blocked status).
- Configuration: typed Python protocol modules remain the sole scientific configuration source; no YAML/TOML/Hydra scientific configuration layer.
- Tests: unit/integration/architecture/scientific plus CUDA smoke tests in `tests/unit/runtime/`; full suite `152 passed`.
- Static gates: Ruff format/check pass; Pyright 0 errors; Pylint ~9.94/10 (pre-existing duplicate-code similarity notices only).
- SonarQube CLI: `totalIssues=0`; Vortex agentic analysis returned organization-side 403 for changed files (service limitation, not authentication failure).
- CodeScene delta: materialization Code Health improved `8.03 -> 9.68`; JSON new-issue report empty after argument-bundling cleanup.
- Phase 5 was not started. Populations package remains empty/unimplemented.
- No branch, commit, or push was performed.

## Phase 05 — Populations, splits, and evaluation cohorts

- Status: `COMPLETE`.
- Source files changed (Phase 05 authorized surface):
  - `src/datp_core/populations/models.py`
  - `src/datp_core/populations/capabilities.py`
  - `src/datp_core/populations/nbaiot_natural_devices.py`
  - `src/datp_core/populations/ciciot_file_clients.py`
  - `src/datp_core/populations/nbaiot_dirichlet_clients.py`
  - `src/datp_core/populations/edge_sensor_groups.py`
  - `src/datp_core/populations/edge_temporal_groups.py`
  - `src/datp_core/populations/splits.py`
  - `src/datp_core/populations/integrity.py`
  - `src/datp_core/populations/catalogue.py`
  - `src/datp_core/evaluation/cohorts.py`
- Upstream blocking corrections (Phase 1–4 defects, smallest fix):
  - `src/datp_core/domain/enums.py`: added `ControlledPartitionKind` (`DIRICHLET`, `IID`) so IID is not a fake infinite concentration.
  - `src/datp_core/datasets/edge_iiotset/capabilities.py`: `valid_populations` now includes `EDGE_TEMPORAL_GROUPS` as well as `EDGE_SENSOR_GROUPS`.
- Test files added: all Phase 05 unit/property/integration files listed in `06_PHASE_05_POPULATIONS_SPLITS_AND_EVALUATION_COHORTS.md`, plus `tests/conftest.py` miniature fixtures (module rename `test_population_models.py` avoids basename clash with protocol tests).
- Scientific-source sections consulted: Regime A/C/D/D-temporal populations; equal-thirds and temporal split ratios; minimum benign calibration support 100; benign-only train/calibration; cohort rules; fixed-detector handoff boundary.
- Research amendments documented in Phase 05 roadmap before implementation: Hamilton residual allocation; class-conditional Dirichlet/IID synthetic construction; evidence-driven Edge temporal feasibility.
- Real-data verification (read-only construction, no training):
  - N-BaIoT natural: 9/9 clients, 7,062,606 rows, attack-in-train/cal = 0, unique rows conserved.
  - CICIoT file clients: 63/63 clients, 45,018,243 eligible model-input rows.
  - N-BaIoT Dirichlet IID: 20 clients, full row conservation.
  - Edge static: 10/10 including Modbus, attack rows = 0.
  - Edge temporal: expected 9, observed eligible 0, feasibility `infeasible` (persisted chronology).
- Focused/full gates: Phase 05 selection and full suite `222 passed` with `.venv/bin/python -m pytest -n 6 -q`; Ruff format/check pass; Pyright 0 errors; Pylint ~9.86/10 (pre-existing similarity notices only).
- No Phase 06 behavior implemented. No new `src/` files. No commit or push.

### Edge temporal forensic audit and Phase 05 closure cleanup

- Independent raw CSV/PCAP audit proved complete alignment for all nine non-Modbus groups (matched == CSV rows; display offset exactly 3_600_000_000 µs = 1 h). Source-order micro-inversions exist in the raw PCAP streams; after stable sort by capture timestamp, inversion count is zero.
- Root cause of prior zero temporal eligibility: `temporal_eligible = (out_of_order_rows == 0)` was stricter than Journal Regime D-temporal (“stably sorted by genuine capture time”). Fix: complete verified alignment grants eligibility; `is_monotonic` remains diagnostic. Edge canonical rebuilt with nine temporal assets; Modbus remains excluded.
- Phase 05 cleanup: removed scientific default split-protocol arguments; removed split re-exports; typed `SplitAssignment.partition_role` as `PartitionRole`; typed catalogue diagnostics union; removed dead fingerprint/helper; removed silent temporal→static asset fallback; removed private `_sums_to_unit_fraction` import; removed residual Edge candidate-count special case; required explicit `dirichlet_condition` on construction requests.
- Real-data smoke (all five populations): N-BaIoT 9/9, 7_062_606 rows, attack train/cal = 0; CIC 63/63, 45_018_243 eligible rows; Dirichlet IID 20 clients, conserved; Edge static 10/10 incl. Modbus; Edge temporal 9/9, 11_050_411 rows, split 6_077_725 / 1_657_561 / 1_105_042 / 2_210_083, no future leakage; Edge materialize second run `reused`.
- Gates: full suite `222 passed`; Ruff pass; Pyright 0 errors; Pylint ~9.91/10; architecture pass. No Phase 06. No commit or push. Temporary audit artifacts removed.

## Phase 06 — Anchor reproduction and programme gate

- Status: `COMPLETE`.
- Implementation vocabulary: source identifiers use historical / confirmatory / dependent terms only; code does not use `journal` or `conference` tokens. Gate field is `dependent_readiness`. Float comparisons use `FIXED_SCORE_ABSOLUTE_TOLERANCE` / explicit absolute tolerances via `isclose`, never bare `==`. Historical metrics documents use `Seed`, `MetricValue`, `ClientCount`, and enum tokens; artifact filenames use `AnchorArtifactFileName`.
- Source files changed (Phase 06 authorized surface only):
  - `src/datp_core/anchor/models.py`
  - `src/datp_core/anchor/comparison.py`
  - `src/datp_core/anchor/reproduction.py`
  - `src/datp_core/anchor/gate.py`
  - `src/datp_core/orchestration/stages/verify_anchor.py`
  - `protocols/anchor.py` unchanged; existing fixed-score absolute tolerance `1e-12` and five-seed CV(FPR) references remain source of truth.
- Test files added:
  - `tests/unit/anchor/test_anchor_models.py` (basename `test_models.py` renamed to avoid pytest import clash with `tests/unit/protocols/test_models.py`)
  - `tests/unit/anchor/test_comparison.py`
  - `tests/unit/anchor/test_reproduction.py`
  - `tests/unit/anchor/test_gate.py`
  - `tests/unit/anchor/helpers.py`
  - `tests/unit/orchestration/stages/test_verify_anchor.py`
  - `tests/integration/anchor/test_anchor_reproduction_pipeline.py`
  - `tests/scientific/test_anchor_blocks_dependent_claims.py`
  - `tests/scientific/test_anchor_preserves_historical_checkpoint_semantics.py`
- Scientific-source sections consulted: Journal confirmatory five-seed reproduction gate; fixed-score absolute tolerance research amendment; historical endpoint/checkpoint isolation; shared-versus-local CV(FPR) references; seed-cohort boundary versus ten-seed confirmatory cohort.
- Evidence inspected and accepted:
  - Protocol references: seeds `0..4`, shared CV(FPR) and local CV(FPR) full-precision values with absolute tolerance `1e-12`.
  - Historical metrics artifacts under sibling project `datp/outputs/results/a/{b1,b2}/seed_{0..4}/metrics.json`: every `cv_fpr` equals the stored protocol reference at full precision; shared and local scopes per seed share identical `model_checkpoint_identity` and `score_artifact_identity` (fixed detector); `threshold_scope` tokens `eligible_client_arithmetic_mean` / `per_client_percentile` map only to `SHARED_THRESHOLD` / `LOCAL_THRESHOLD`; dataset `nbaiot`, regime physical-device anchor, nine eligible clients.
  - Historical artifacts rejected when schema-incomplete, seed-mismatched, wrong scope token, wrong population counts, non-historical checkpoint status, or ten-seed cohort supplied.
- Tolerance rules used: metric-specific `AbsoluteToleranceRule` with declared `FIXED_SCORE_ABSOLUTE_TOLERANCE=1e-12` for all mandatory CV(FPR) anchor references; exact, relative, interval-overlap, exact-count, and source-defined strategies implemented and tested; global floating-point tolerance explicitly rejected; relative comparison against zero is unavailable.
- Gate decision on verified historical observations: `PASS` (zero discrepancies). Without observations or independent re-execution: `BLOCKED` with typed Phase 08 dependency blocker; diagnostics preserved. Dependent readiness becomes `DECLARED` only on pass paths and `BLOCKED` on failures; never `EXECUTABLE`.
- Focused commands: Phase 06 unit/integration/scientific selections.
- Whole-suite command: `.venv/bin/python -m pytest -n 6 -q` → `278 passed`.
- Ruff format/check on Phase 06 surface: pass. Pyright on changed sources: 0 errors. Pylint on `src/datp_core/anchor` and `verify_anchor.py`: `10.00/10`. Architecture tests pass. No `Any`, no raw domain dictionaries in the Phase 06 surface.
- SonarQube CLI: `totalIssues=0`; Vortex agentic analysis returned organization-side 403 for changed files (service limitation, not authentication failure).
- CodeScene delta: residual complexity/argument findings on validation-heavy helpers after cleanup; no unresolved actionable defect requiring further science change. Scores improved after extraction of document validation and comparison outcome records.
- Unresolved values: none for Phase 06 gate machinery. Independent training/checkpoint/score re-execution remains Phase 08 by design; Phase 06 loads typed historical observations or records the dependency blocker.
- No Phase 07 or Phase 08 implementation. No new `src/` files. No commit or push.

## Phase 07 — Independent centralized reference pipeline

- Status: `COMPLETE`.
- Entry-criteria findings:
  - Phase 05 `COMPLETE`; Phase 06 `COMPLETE`.
  - Centralized training hyperparameter declarations resolve from `CANONICAL_PROTOCOL_GRAPH` / training protocols: Adam, learning rate `0.001`, weight decay `0.0`, batch size `256`, N-BaIoT widths `(115, 86, 58, 38, 29, 38, 58, 86, 115)`, checkpoint candidates `25..200`, selection rule `FIXED_TERMINAL_MAXIMUM_ROUND`, centralized model `CENTRALIZED_AUTOENCODER`, quantile `CANONICAL_QUANTILE=0.95` via `CENTRALIZED_POOLED_QUANTILE_PROTOCOL`.
  - CUDA required by `CANONICAL_RUNTIME`; no silent CPU fallback.
  - No Phase 08 federated training/scoring/threshold surface was implemented beyond documenting the shared selection rule for Phase 08 to consume.
  - Locked source tree preserved: only existing authorized files were modified; no new `src/` files.
- Source files changed (Phase 07 authorized surface only):
  - `src/datp_core/centralized_reference/preprocessing.py` (existing Phase 04 pooled path retained)
  - `src/datp_core/centralized_reference/training.py`
  - `src/datp_core/centralized_reference/checkpointing.py`
  - `src/datp_core/centralized_reference/scoring.py`
  - `src/datp_core/centralized_reference/thresholding.py`
  - `src/datp_core/centralized_reference/evaluation.py`
  - `src/datp_core/orchestration/stages/preprocess_centralized_reference.py`
  - `src/datp_core/orchestration/stages/train_centralized_reference.py`
  - `src/datp_core/orchestration/stages/select_centralized_reference_checkpoint.py`
  - `src/datp_core/orchestration/stages/score_centralized_reference.py`
  - `src/datp_core/orchestration/stages/construct_centralized_reference_threshold.py`
  - `src/datp_core/orchestration/stages/evaluate_centralized_reference.py`
- Test files added:
  - `tests/unit/centralized_reference/helpers.py`
  - `tests/unit/centralized_reference/test_training.py`
  - `tests/unit/centralized_reference/test_checkpointing.py`
  - `tests/unit/centralized_reference/test_scoring.py`
  - `tests/unit/centralized_reference/test_thresholding.py`
  - `tests/unit/centralized_reference/test_evaluation.py`
  - `tests/unit/orchestration/stages/test_centralized_reference_stages.py`
  - `tests/integration/centralized_reference/test_centralized_reference_pipeline.py`
  - `tests/scientific/test_centralized_reference_is_independent.py`
  - `tests/scientific/test_centralized_reference_never_enters_federated_dispatch.py`
- Scientific-source sections consulted: Journal §2.2.1 centralized pooled MinMax; B0 centralized reference identity; checkpoint candidates and non-test selection requirement; decision rule `score > threshold`; pooled benign quantile; benign-only train/calibration; confirmatory ladder separation; fixed-detector and independence boundaries; Phase 04–08 roadmap boundary documents.
- Protocol values used: `CENTRALIZED_TRAINING_PROTOCOL`, `NBAIOT_AUTOENCODER`, `OPTIMIZER=ADAM`, `LEARNING_RATE=0.001`, `WEIGHT_DECAY=0.0`, `BATCH_SIZE=256`, `CHECKPOINT_PROTOCOL` candidates, `CHECKPOINT_SELECTION_RULE=FIXED_TERMINAL_MAXIMUM_ROUND`, `CANONICAL_QUANTILE=0.95`, `CENTRALIZED_POOLED_MIN_MAX`, `CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE`, `CANONICAL_RUNTIME.require_cuda=True`.
- Unresolved values:
  - Quantile interpolation is operationalized as NumPy linear (`numpy.quantile(..., method="linear")`) and recorded as `QuantileInterpolationSemantics.NUMPY_QUANTILE_LINEAR`; the journal locks the level; this operationalization is the declared engineering completion of that level.
- Implementation completed:
  - Independent pooled MinMax preprocessing path with federated-state rejection.
  - Deterministic CUDA centralized autoencoder training with SafeTensors persistence and declared batch size and Adam weight decay.
  - Declared checkpoint candidate retention and SafeTensors reload.
  - `FIXED_TERMINAL_MAXIMUM_ROUND` selection; held-out metrics and attack labels rejected; non-terminal candidates marked `STABILITY_EVIDENCE`.
  - Deterministic pooled calibration/evaluation scoring with polarity check and reload equality.
  - Pooled benign quantile threshold from protocol quantile (not hardcoded `0.95` in execution).
  - Pooled evaluation with confusion counts, unavailable/undefined metric statuses, supportive evidence role only.
  - Stage orchestration chain with atomic publish/reuse and federated-artifact rejection guards.
- Centralized/federated independence evidence:
  - Structural rejection of federated preprocessing, checkpoints, scores, local-quantile means, and federated dispatch insertion.
  - Scientific AST tests forbid centralized imports of `thresholding`, `learning.federated`, and `scoring`.
  - Evaluation cannot enter confirmatory B1–B2 ladder or claim confirmatory role.
- Real-data smoke (controlled N-BaIoT natural-device pooled branch):
  - Full split conservation: 7_062_606 assignment rows; train 185_314 / calibration 185_309 / evaluation 6_691_983; disjoint partitions.
  - Smoke subsample: train 2048 benign, calibration 1024 benign, evaluation 1024; independent MinMax skops reload at tolerance `1e-12`.
  - CUDA device used (`NVIDIA GeForce RTX 5060 Ti`); batch size 256; widths match 115-feature AE; candidates retained for controlled short protocol rounds `(2, 4)`.
  - Selection under `FIXED_TERMINAL_MAXIMUM_ROUND` chooses the maximum declared candidate.
  - Scoring/threshold/evaluation on the selected terminal candidate: calibration 1024, evaluation 1024, quantile 0.95, threshold computed, confirmatory ladder membership false; no federated artifacts read or written.
- Focused Phase 07 selections pass after selection unlock; whole-suite command re-run for completion.
- Ruff format/check on Phase 07 surface: pass.
- Pyright on Phase 07 sources: 0 errors.
- Audit verdict: complete. Independent centralized pipeline verified; non-test checkpoint rule locked as `FIXED_TERMINAL_MAXIMUM_ROUND`; Phase 08 remains clear to start on Phases 05–06 entry criteria with the shared selection rule already declared.
- No Phase 08 federated trainer implementation. No new `src/` files. No commit or push.


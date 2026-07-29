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
| 04 — Canonical data and reusable preprocessing | `COMPLETE` | Phase 03 complete | Method locks, coordinates, reuse, skops, CLI, focused/full gates | None; end-to-end processed publication consumes Phase 05 populations by design |
| 05 — Populations, splits, and cohorts | `NOT_STARTED` | Phase 04 complete | Deterministic split/cohort manifests | Non-temporal split ratios are research-amendment equal thirds; remaining work is builders and leak-free cohorts |
| 06 — Anchor reproduction and gate | `NOT_STARTED` | Phase 05 complete | Explicit equivalence/discrepancy decision | Metric-specific tolerances absent from source truth remain blocking |
| 07 — Centralized reference | `NOT_STARTED` | Phase 05 complete | Independent pooled execution and tests | Centralized training values absent from source truth remain blocking |
| 08 — Federated training, checkpointing, and scoring | `NOT_STARTED` | Phases 05–06 complete | Frozen scores and checkpoint discipline pass | Exact architecture/optimizer/batch values must be sourced |
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

- Status: `COMPLETE`.
- Upstream corrections applied before Phase 04 entry (Phase 1–3 contracts remain COMPLETE; these are corrections, not restarts):
  - Added `SeedCount`; `SeedCohort.member_count` and `StatisticalInferenceProtocol.paired_seed_count` return `SeedCount` rather than `ClientCount`.
  - Renamed `DEFAULT_RUNTIME` to `CANONICAL_RUNTIME`.
  - Expanded `ResolvedProtocolGraph` with confirmatory endpoint, inference, anchor, runtime, splits, cluster threshold, FedAvg training, and traffic-rate evidence; `validate_protocol_graph()` constructs the one canonical graph.
  - Added `ConfirmatoryEndpoint` locking `SHARED_VS_LOCAL_CONFIRMATION` / `NBAIOT_NATURAL_DEVICES` / `FEDAVG_AUTOENCODER` / `SHARED_THRESHOLD` vs `LOCAL_THRESHOLD` / `FPR_COEFFICIENT_OF_VARIATION` / ten-seed journal cohort / shared-minus-local / paired BCa.
  - Added `ExperimentReadiness` (`DECLARED`/`EXECUTABLE`/`SUPPRESSED`/`INFEASIBLE`/`BLOCKED`); catalogue members are declared or suppressed, never executable before implementation phases complete.
  - Added `PopulationIdentityKind` and identity validation; Edge sensor groups and CIC files are not physical devices.
  - Strengthened `ClusterThresholdProtocol` to require the locked four-feature fingerprint, StandardScaler, k-means++, `n_init=10`, `max_iter=300`, `random_state=42`, `K=3`, and arithmetic-mean aggregation.
  - Resolved dataset TODOs with `ColumnLogicalType`, `DatasetValidationCode`, `AggregateCountColumn`, and `NBaIoTSourceLabel` usage.
- Processed layout locked to:
  `data/processed/<DATASET_ID>/<POPULATION_ID>/<PARTITION_SEED>/<SPLIT_PROTOCOL_ID>/<PREPROCESSING_PROTOCOL_ID>/{federated/<CLIENT_ID>|centralized_reference}/…`
  without `seed_` prefixes or nested `client/` directory segments.
- CLI/Make: `datp-core preprocess-dataset`, `datp-core preprocess-all-datasets`, `--overwrite` (rebuild only; no path override); `make preprocess-dataset DATASET=… OVERWRITE=0|1`, `make preprocess-all-datasets`.
- Enums reused/extended for path/partition/protocol identities: `PartitionRole`, `SplitProtocolId`, `PreprocessingProtocolId`, `ReusableDataCoordinateKind`, `TrustedEstimator*`, `PreprocessExecutionStatus`.
- Fixed Edge attack-source glob to `*{_attack.csv}` (previous exact-suffix glob discovered zero attack CSVs).
- Scientific method lock (Journal §2.2.1): confirmatory `SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD` = client-local StandardScaler (paper+anchor); supportive `SCIENTIFIC_FEDERATED_POOLED_MIN_MAX_METHOD` = pooled MinMax (FL-AE literature); centralized pooled MinMax; via existing enums + `build_preprocessing_protocol`; transform tolerance reuses `FIXED_SCORE_ABSOLUTE_TOLERANCE.value`.
- Phase 04 implementation in existing files only (no new `src/` files):
  - `preprocessing/models.py`, `federated.py`, `validation.py`
  - `centralized_reference/preprocessing.py`
  - `artifacts/coordinates.py`, `layout.py`, `serialization.py`, `manifest.py`, `completion.py`, `reload_validation.py`, `store.py`
  - `cli.py`, `domain/enums.py`, dataset/protocol upstream corrections
- Behaviour implemented: descriptive processed-data paths; independent federated/centralized fit branches; train-only fit guards; attack-label rejection; skops trusted-type serialization; transform reload equivalence; atomic publish with `filelock`, temporary sibling, COMPLETE digest; reuse and partial-rebuild semantics.
- Intentionally deferred to Phase 05 (not a Phase 04 scientific hole): population construction, split materialization, and therefore end-to-end processed-asset publication. CLI correctly exits `blocked_population_construction` until Phase 05 supplies partitions.
- Tests: unit preprocessing/artifacts/centralized_reference; integration reuse, reload, cache invalidation, atomic publication; protocol/domain updates.
- Final gates for Phase 04 closure recorded under validation commands in the closing audit of this task.
- Phase 5+ scientific algorithms were not implemented.
- No branch, commit, or push was performed.


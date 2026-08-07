# Domain & Types Audit — DATP-Core

Scope: `src/datp_core/domain/*`, `src/datp_core/protocols/*`, plus CLI/workflow/dispatch call sites.
Format: `file:line — finding — severity — journal relevance`.

---

## 1. Enum members never used in production `src/` (CLI, workflows, dispatch)

- `src/datp_core/domain/enums.py:36` — `ProgrammeStatus`: 7/12 members unused in src: `PREPARATION_READY`, `RUNNING`, `INCOMPLETE`, `INVALID`, `EXECUTION_COMPLETE`, `REPORT_READY`, `REPORT_GENERATED` — medium — dead status vocabulary; `campaign.py` only emits NOT_STARTED/DATASET_READY/BLOCKED_*/ANALYSIS_COMPLETE; `INVALID`/`INCOMPLETE` only appear as raw strings in `pipeline/execution/models.py:94`, `pipeline/publication/models.py:30-36`, `datasets/contracts.py:63`.
- `src/datp_core/domain/enums.py:196` — `StageOperationId`: 14/18 members unused in src: `ANALYZE`, `CALIBRATE`, `CONSTRUCT_CENTRALIZED_REFERENCE_THRESHOLD`, `CONSTRUCT_FEDERATED_THRESHOLDS`, `EVALUATE_CENTRALIZED_REFERENCE`, `MATERIALIZE`, `PREPROCESS_CENTRALIZED_REFERENCE`, `PREPROCESS_FEDERATED`, `SCORE_CENTRALIZED_REFERENCE`, `SCORE_FEDERATED`, `SELECT_CENTRALIZED_REFERENCE_CHECKPOINT`, `SELECT_FEDERATED_CHECKPOINT`, `TRAIN_CENTRALIZED_REFERENCE`, `TRAIN_FEDERATED` — medium — parallel `PipelineStage` enum (finding 2.2) replaced it; only SPLIT/CONSTRUCT_POPULATION/EVALUATE_FEDERATED/VERIFY_ANCHOR used.
- `src/datp_core/domain/enums.py:225` — `SerializationFormat.PYDANTIC_JSON` — low — used only in tests (`tests/unit/scoring/test_score_models.py:73`); production serializes parquet/safetensors/skops.
- `src/datp_core/domain/enums.py:232` — `CommunicationEstimationMethod.MEASURED_NETWORK_TRAFFIC` — low — tests only; roadmap §excluded scope forbids deployment measurement; enum member is out-of-scope vocabulary that should be removed.
- `src/datp_core/domain/enums.py:296` — `PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION` — medium — test-only identity; absent from `preprocessing/service.py:43-50` dispatch; pollutes the closed protocol vocabulary.
- `src/datp_core/domain/enums.py:305` — `ContractSubject` unused members: `CANDIDATES`, `CONFIRMATORY_LADDER`, `LOCAL_QUANTILE_MEAN`, `QUANTILE`, `THRESHOLD_IDENTITY` — low — dead error-subject vocabulary (5/36).
- `src/datp_core/protocols/experiments.py:252,285,301,317,333,341,349,357,405,421` — 10 declared `ExperimentId` members with zero production reference outside the declaration file: `SHARED_CONSTRUCTION_SENSITIVITY`, `PER_CLIENT_SCORE_GEOMETRY`, `THRESHOLD_MOVEMENT_TRADEOFF`, `FIXED_SHRINKAGE_CURVE`, `LOCAL_CONFORMAL_COVERAGE`, `FEDERATED_BENIGN_STATISTICS_COMPARISON`, `FEDERATED_QUANTILE_ESTIMATION`, `FIXED_COEFFICIENT_STATISTICS_SENSITIVITY`, `ALERT_BURDEN_TRANSLATION`, `OPTIONAL_EQUITY_INDICES` — high — declared-but-orphaned; no workflow/analysis/report path.
- `src/datp_core/protocols/experiments.py:325` — `ExperimentId.SIZE_AWARE_SHRINKAGE` only referenced at declaration (name collides with `FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE`) — high — experiment has no workflow and its sole method is a permanent blocker (finding 6.2).

## 2. Duplicate enums / overlapping vocabulary

- `src/datp_core/evaluation/models.py:48` — `MetricStatus` duplicates 5/6 values of `AvailabilityStatus` (`available/unavailable/undefined/suppressed/infeasible`) plus `blocked` — high — CLAUDE.md §8.1 forbids duplicating vocabulary across enums; `AvailabilityStatus` (enums.py:183) and `MetricStatus` must be one enum.
- `src/datp_core/pipeline/execution/models.py:14` — `PipelineStage` overlaps `StageOperationId` (`construct_population`, `verify_anchor` share values); two parallel stage enums; the domain one is 78% dead (finding 1.2) — high — stage vocabulary should collapse to one enum.
- `src/datp_core/calibration/models.py:19` — `EligibilityStatus.CANDIDATE = "candidate"` equals `CheckpointStatus.CANDIDATE` — low — value collision across domains.
- `src/datp_core/reporting/validation.py:14,22` — `ClaimStatus`/`ClaimKind` reuse `blocked`, `suppressed`, `confirmatory`, `supportive` values from `ExperimentReadiness`/`AvailabilityStatus`/`EvidenceRole` — medium — separate claim vocabulary but value-overlapping.
- `src/datp_core/anchor/models.py:493` — `HistoricalDatasetToken.NBAIOT = "nbaiot"` duplicates `DatasetId.NBAIOT` — low — historical legacy token duplicates dataset identity.
- `src/datp_core/anchor/models.py:339` — `AnchorGateStatus.BLOCKED = "blocked"` equals `ExperimentReadiness.BLOCKED` — low.
- `src/datp_core/analysis/scientific_decision.py:13` — `ScientificDecision.SUPPORTED/DIRECTIONAL_INCONCLUSIVE/BLOCKED` overlap `EvidenceDecision` (reporting/validation.py:32) — low — two decision vocabularies.
- `src/datp_core/datasets/contracts.py:60` — `AggregateCountColumn.INVALID = "invalid"` equals `ProgrammeStatus.INVALID` — low.
- `src/datp_core/datasets/contracts.py:66` — `CanonicalProvenanceColumn.STABLE_ROW_ID` equals `ScoreFrameColumn.STABLE_ROW_ID` (enums.py:351) — low.
- `src/datp_core/datasets/capabilities.py:10` — `CapabilityStatus.UNAVAILABLE` equals `AvailabilityStatus.UNAVAILABLE` — low.

## 3. Raw string usage where enum should be used

- `src/datp_core/evaluation/models.py:48-54` — raw status strings baked into a duplicate enum (finding 2.1) — high — should reference a single `AvailabilityStatus`-style enum.
- `src/datp_core/reporting/export.py:229` — `"undefined"` equals `AvailabilityStatus.UNDEFINED` — low — display fallback; prefer enum `.value` for provenance.
- `src/datp_core/reporting/export.py:371,386-388,593,704-767` — repeated `"unavailable"` equals `TrafficRateEvidenceType.UNAVAILABLE`/`AvailabilityStatus.UNAVAILABLE` — low — display strings in markdown; value-overlap with closed vocabulary.
- `src/datp_core/pipeline/execution/layout.py:12-29` — `ExecutionArtifactDirectory`/`ExecutionRootDirectory`/`EvaluationRunAssetDirectory` reuse `split`, `training`, `scores`, `federated`, `threshold`, `evaluation` values from `ContractSubject`/`ProcessedDataBranch`/`PartitionRole` — low — filesystem fragments, distinct domain, but value collisions across enums.
- All other `src` string hits matching enum values (`"cuda"`, `"label"`, `"autoencoder"`, `"metrics"`, `"candidates"`, dict keys in `anchor/gate.py`, `personalization.py`, `provenance.py`) are legitimate library args, JSON/checksum keys, or path segments — no change.

## 4. `Any` types / untyped dicts at domain boundaries

- No `Any` type or `dict[str, Any]` anywhere in `src/` (only a code comment in `pipeline/planning.py:160`). No `Mapping[str, object]` domain contracts. Clean.
- `src/datp_core/domain/provenance.py:19-27,60` — `CanonicalValue` recursive alias and `canonical_mapping -> dict[str, CanonicalValue]` — low — allowed JSON-serialization boundary per CLAUDE.md §9.2; verify all callers immediately convert back to typed models (callers: `datasets/contracts.py:12`, serialization paths) — currently confined to serialization layer.

## 5. Missing enum members for journal-required concepts

- No `RegimeId` enum — roadmap §12.6 locks `Regime A / B-a / B-b / C / D / D-temporal` as identifiers — medium — code maps regimes only implicitly via `DatasetId`/`PopulationId`; locked regime vocabulary absent.
- No `ThresholdPolicyId` (B0–B4, B-FedStatsBenign) enum — roadmap locks B0–B4 policy identifiers (§4-5, §12) — medium — policy identity is expressed only through `FederatedThresholdMethod`/`CentralizedThresholdMethod`; the locked B-labels are not represented (only `HistoricalThresholdScopeToken` at `anchor/models.py:480` maps legacy tokens to methods).
- `MetricId` (enums.py:149) has no member for JS divergence or cluster stability — low — these are mechanism result types (`analysis/mechanisms/*`), not operating-point metrics; acceptable.
- Temporal drift quantities `drift_excess` / `recovered_amount` / `recovery_ratio` have no dedicated value object or metric id — low — stored as bare `MetricValue` fields (`analysis/preparation.py:141-143`).

## 6. Protocol implementations never selected/used; dead protocol code

- `src/datp_core/protocols/calibration.py:102,216` — `ConformalProtocol` class and `CONFORMAL_PROTOCOL` constant unused in src (tests only) — medium — dispatch calls `construct_local_conformal_threshold(eligible, quantile)` and derives coverage from `Quantile` (`dispatch.py:151-152`); declared protocol object is dead.
- `src/datp_core/protocols/calibration.py:97,212` — `SizeAwareShrinkageProtocol` class and `SIZE_AWARE_SHRINKAGE_PROTOCOL` constant unused anywhere — medium — dispatch calls `construct_size_aware_shrinkage(coordinate)` (`dispatch.py:149-150`).
- `src/datp_core/thresholding/methods/shrinkage.py:146-154` — `construct_size_aware_shrinkage` always returns `ThresholdUnavailableResult` (`SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED`) — high — the SIZE_AWARE_SHRINKAGE threshold method is a permanent blocker stub; any experiment declaring it (ExperimentId.SIZE_AWARE_SHRINKAGE) can never succeed.
- `src/datp_core/protocols/calibration.py:192,196,200,204` — `SHARED_THRESHOLD_PROTOCOL`, `LOCAL_THRESHOLD_PROTOCOL`, `POOLED_SHARED_QUANTILE_PROTOCOL`, `SAMPLE_WEIGHTED_SHARED_THRESHOLD_PROTOCOL` unused in src — medium — `thresholding/dispatch.py:121-141` rebuilds equivalent `QuantileProtocol(...)` inline; declared constants are dead duplicates of the dispatch constructions.
- `src/datp_core/protocols/training.py:151` — `fixed_terminal_checkpoint_status` — high — never called in src or tests (dead); selection logic is reimplemented inline in `checkpoints.py:106-113` and `selection.py`.
- `src/datp_core/protocols/checkpoints.py:91` — `validate_checkpoint_inventory_files` and its `CheckpointIntegrityContract` (line 38) — medium — never called anywhere; integrity validation only reaches `validate_persisted_checkpoint_file` (`src` refs 11).
- `src/datp_core/protocols/calibration.py:180-186` — `CALIBRATION_SIZES`, `CALIBRATION_SUBSAMPLE_REPLICATE_COUNT`, `FIXED_SHRINKAGE_WEIGHTS`, `CONFORMAL_COVERAGE`, `SUMMARY_COEFFICIENTS` — low — no src usage outside the calibration module (tests only or none); `FIXED_SHRINKAGE_WEIGHTS` only feeds the dead-adjacent `FIXED_SHRINKAGE_PROTOCOL`.
- `src/datp_core/protocols/seeds.py:31` — `BOUNDED_EVIDENCE_PAIRED_SEED_COUNT` — low — unused outside `seeds.py` (mirrors `CONFIRMATORY_PAIRED_SEED_COUNT`); dead duplicate constant.

## 7. Minor

- `src/datp_core/domain/errors.py:16` — `DatpCoreError.subject: Enum | None` — low — accepts any Enum, so the closed `ContractSubject` vocabulary is not enforced at the error boundary; callers legitimately pass `ExperimentId`/`PopulationId`/`FederatedThresholdMethod`/`TemporalState` as subjects. Intentional but worth documenting.
- `src/datp_core/domain/__init__.py`, `src/datp_core/protocols/__init__.py` — empty — low — no re-export contract; all consumers import directly from modules (consistent).

---

## Summary counts

- 1 high enum-usage gap (10 orphaned experiments) + 1 high stub method (SIZE_AWARE_SHRINKAGE) + 1 high dead function (`fixed_terminal_checkpoint_status`).
- 2 high duplicate-enum pairs (`MetricStatus`/`AvailabilityStatus`; `PipelineStage`/`StageOperationId`).
- 14 unused `StageOperationId` members, 7 unused `ProgrammeStatus` members, 5 unused `ContractSubject` members.
- 2 missing journal-locked enum concepts (`RegimeId`, `ThresholdPolicyId` B0–B4).
- 4 unused-in-src protocol instances + 2 unused protocol classes + 1 unused constant pair.
- No `Any` / `dict[str, Any]` leaks found.

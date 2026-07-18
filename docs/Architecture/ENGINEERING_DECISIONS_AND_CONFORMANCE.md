# ENGINEERING_DECISIONS_AND_CONFORMANCE

## Purpose

Record active decisions, blockers, errors, tests, extension rules, and final
conformance.

## Authoritative for

Non-scientific architecture decisions and verification gates.

## Not authoritative for

Scientific scope, configuration examples, or execution implementation.

## 1. Status vocabulary

| Status | Meaning |
|---|---|
| `LOCKED` | Required by the roadmap and this architecture |
| `DESIGNED_NOT_IMPLEMENTED` | Contract defined; implementation status unknown |
| `BLOCKED` | Cannot be finalized without named evidence or authority |
| `DEFERRED` | Intentionally postponed |
| `OUT_OF_SCOPE` | Must not be implemented in current scope |
| `REJECTED` | Considered and explicitly declined |
| `SUPPRESSED` | Scientifically defined but intentionally not executed or reported quantitatively under a stated condition |

Nothing in this package is asserted `implemented`, `tested`, `passing`, or
`complete`; every design commitment carries one of the seven statuses above.

## Roadmap ownership map

| Roadmap requirement | Single architectural owner |
|---|---|
| Dataset and client construction | `DataDefinition` and `SCIENTIFIC_FOUNDATION.md §5`. |
| Splits and preprocessing | `DataDefinition`; dataset schemas and mapping. |
| Model and training profile | `ModelDefinition`; model schemas and mapping. |
| Checkpoint production and selection | `PIPELINE_EXECUTION_AND_ARTIFACTS.md §7`; separate primary-round and artifact selection values. |
| Calibration and score generation | Typed split/score artifacts and registered scoring stages. |
| Threshold construction | `EvaluationDefinition` and the closed threshold union. |
| Evaluations and metrics | `EVALUATION_REPORTING_AND_PROVENANCE.md`. |
| Statistical analyses | `AnalysisDefinition` and `StatisticalProcedure` variants. |
| Experiments and sweeps | Experiment schemas and `ConfigurationResolutionResult`. |
| External feasibility | `DatasetAuditDefinition`, source inspection, and feasibility audit stages. |
| Stress tests | Stress-test scientific definitions, outside the core ladder. |
| Temporal evaluation | Chronological data/split definitions and `TEMPORAL_SCORE`. |
| Reporting and provenance | Result freeze, reporting definitions, and artifact lineage. |
| Rejected, suppressed, and future work | `CatalogueDisposition`; never an executable run definition. |

The roadmap is complete enough to define the architecture. When an authority
or source inspection must supply a value before execution, it is reported as
a typed boundary blocker by configuration validation; it is never preserved
as a value in a resolved definition.

## 2. Canonical rule register

Every rule is defined exactly once here; other files reference the
identifier rather than repeat the text.

### `SCI-*` — scientific invariants

`SCI-01`–`SCI-13` are defined in `SCIENTIFIC_FOUNDATION.md §3`. Additional:

| ID | Rule |
|---|---|
| `SCI-14` | Only `CONFIRMATORY` may carry `TIER_1`; no other evidence role may. |
| `SCI-15` | `SharedThreshold` and `FamilyThreshold` use unweighted arithmetic means of eligible local quantiles. |
| `SCI-16` | `ClusterThreshold` requires canonical `K = 3` for any claim rendered as canonical; other K is exploratory only, and its per-quantile assignment is the unweighted mean of member local quantiles, never a q-mutated fingerprint. |
| `SCI-17` | `FederatedSummaryStatisticThreshold` always uses the full pooled variance including the between-client mean-shift term and a larger-k tie rule; neither is a configurable boolean. |
| `SCI-18` | Fixed-k `FederatedSummaryStatisticThreshold` sensitivity can never become the primary comparator result. |
| `SCI-19` | The model architecture carries no batch normalization. |

### `ANCHOR-*` — anchor reproduction and equivalence

| ID | Rule |
|---|---|
| `ANCHOR-01` | The anchor is a `ScientificExperimentDefinition` with `evidence_role = ANCHOR`; no separate technical system exists. |
| `ANCHOR-02` | `AnchorEquivalenceGate` is a decision service, not a pipeline fork; only applicable stages are planned. |
| `ANCHOR-03` | A less-favorable ten-seed confirmatory result is never suppressed in favor of a more-favorable five-seed anchor result. |
| `ANCHOR-04` | The centralized reference (B0) reuses `StageIdentity`/`ArtifactKey`; it never gains a parallel identity hierarchy. |
| `ANCHOR-05` | Artifact namespace is derived from `evidence_role`, never supplied as an independently settable field. |
| `ANCHOR-06` | An anchor artifact is reusable only when its scientific identity is compatible with the current anchor definition; provenance from the original reference project never substitutes for this check. |

### `NAME-*` — semantic naming

| ID | Rule |
|---|---|
| `NAME-01` | No letter-based identifier (dataset setting, threshold code, experiment ID) drives control flow anywhere in `domain` or `application`; a letter-based label may exist only as a derived, non-authoritative value (`Regime`, `SCIENTIFIC_FOUNDATION.md §5`) or metadata field (`roadmap_reference`), never as a constructor input, discriminator, or branch condition. |
| `NAME-02` | DATP-Core is never called the journal system, and the anchor is never called legacy, old, or reference DATP. |
| `NAME-03` | Publication threshold codes (`B0`–`B4`, `B-FedStatsBenign`, `B-LaridiFaithful`) exist only as `roadmap_reference` metadata. |
| `NAME-04` | Roadmap experiment identifiers (`E-C1`, `E-S1`, …) exist only as `roadmap_reference` metadata on a semantically slugged `ExperimentIdentity`. |
| `NAME-05` | A model-personalization comparator is named for the algorithm it implements; never labeled "Ditto" unless genuine Ditto is present. |
| `NAME-06` | No module is named `utils`, `common`, `base`, `manager`, `helpers`, `misc`, `shared`, `requests`, or `results`; no class is named `Manager`, `Handler`, `Processor`, `Context`, `Payload`, `Data`, `Item`, or `Entity`. |

### `ARCH-*` — dependency and ownership

| ID | Rule |
|---|---|
| `ARCH-01` | `ScientificExperimentDefinition` owns metadata, data, model, evaluations, analyses, seed cohort, prerequisites, and operations; `DatasetAuditDefinition` owns only audit fields. |
| `ARCH-02` | Statistics are owned by `AnalysisDefinition`, never duplicated per `EvaluationDefinition` or across evaluations of the same comparison. |
| `ARCH-03` | No backward-compatibility shim, alias layer, or migration facade toward the prior architecture or the original reference project exists. |
| `ARCH-04` | No root `experiments/` package exists; experiment identity lives in `domain/experiments.py`, YAML in `configs/experiments/`, mapping in `config/mapping/`, expansion in `application/planning/`. |
| `ARCH-05` | Framework-free analysis/reporting specifications live in `application/reporting`; no separate analysis layer exists. |
| `ARCH-06` | `cli` never constructs an adapter, binds a port, or resolves a path; it only invokes `composition`. |

### `TYPE-*` — typing and dataclasses

| ID | Rule |
|---|---|
| `TYPE-01` | Cross-stage or cross-role identity confusion is prevented by `StageIdentity`, `ArtifactKey`, and `ArtifactRef`, never by a structural alias. |
| `TYPE-02` | No bare `Result`, `Payload`, `Context`, `Manager`, or `Handler` type exists. |
| `TYPE-03` | `Any`, `object`, and generic mappings are absent from every `domain` and `application` contract. |
| `TYPE-04` | Every multi-variant type carries an explicit discriminator tag, exhaustively matched with `typing.assert_never`. |
| `TYPE-05` | Every float-wrapping value object rejects `NaN` and infinity at construction. |
| `TYPE-06` | A dataclass is introduced only under the admission test in `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §5`; a three-argument function does not justify one. |

### `CFG-*` — configuration

| ID | Rule |
|---|---|
| `CFG-01` | Every identity-bearing field is present in YAML or reached through a deterministic typed reference; none has a Python or Pydantic default. |
| `CFG-02` | A discriminated configuration variant rejects a field it does not own. |
| `CFG-03` | Removing a required identity-bearing field from YAML is a validation failure, never a fallback. |
| `CFG-04` | No YAML merge key, YAML anchor, or deep inheritance exists. |
| `CFG-05` | `None` represents a meaningful domain state, never an omitted required value. |
| `CFG-06` | A resolved configuration snapshot is fingerprinted and persisted before planning. |
| `CFG-07` | An unsupported configuration schema version fails clearly; no automatic migration exists. |
| `CFG-08` | Experiment authorization is enforced by construction validators on closed unions and cross-field validators, never by a duplicate "authorized profile" object. |
| `CFG-09` | The CLI accepts no scientific override flag; a scientific change requires an edited, reviewed configuration document. |
| `CFG-10` | An incomplete boundary document reports a typed blocker; resolve, plan, and run reject it and no frozen domain value carries a sentinel. |
| `CFG-11` | Experiment and dataset-audit CLIs expose the same seven lifecycle verbs and no scientific-affecting override. |
| `CFG-12` | A zero-input Make target selects exactly one CLI action and one registered experiment configuration, contains no user-supplied parameter, and fails if its referenced configuration does not exist; a generic parameterized target (`make run EXPERIMENT=...`) is never defined. |
| `CFG-13` | Every source column of every dataset is a typed `SourceFieldDescriptor` with a named `SourceFieldRole`; `model_feature_order` never includes a column carrying identity, label, timestamp, provenance, or a documented leakage/high-cardinality risk, and an excluded column always carries a cited reason (`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §11`). |

### `PIPE-*` — stages and planning

| ID | Rule |
|---|---|
| `PIPE-01` | Adding a stage requires only its implementation, an optional configuration variant, and one registry line. |
| `PIPE-02` | Reuse is decided by comparing typed stage identities, never by filename or modification time. |
| `PIPE-03` | The planner deduplicates every compatible stage across confirmatory, supportive, mechanism, variant, and comparator evaluations sharing a seed. |
| `PIPE-04` | `RUNNING → REUSED` does not exist; reuse is always decided before computation. |
| `PIPE-05` | A collision between distinct resolved-run snapshots is a typed planning error. |

### `EXEC-*` — runtime and lifecycle

| ID | Rule |
|---|---|
| `EXEC-01` | A CUDA-required stage that cannot obtain CUDA raises a typed error; there is no silent CPU fallback. |
| `EXEC-02` | No runtime component reduces, adapts, or substitutes a resolved batch-execution profile once a stage begins, in any execution mode. |
| `EXEC-03` | A `CudaOutOfMemoryError` is terminal for its execution attempt; it is never a classified transient failure and never auto-recovers. |
| `EXEC-04` | Any stage touching CUDA uses a per-stage spawn context; the global `set_start_method` is never used. |
| `EXEC-05` | At most one concurrent GPU training job and, by default, one concurrent GPU scoring job run. |

### `ART-*` — artifacts and reuse

| ID | Rule |
|---|---|
| `ART-01` | An `ArtifactKey` is derived deterministically from artifact type, typed scope, and stage identity; an `ArtifactRef` exists only after verified persistence and adds the content hash. |
| `ART-02` | The same logical artifact identifier appearing with a different content hash is a typed integrity error, never resolved by minting a new identifier. |
| `ART-03` | A multi-file bundle is reader-visible only after every declared member is verified and a final commit marker is written. |
| `ART-04` | Recovery state and a scientific checkpoint occupy distinct kinds, roots, and namespaces; recovery state can never be selected as scientific evidence. |
| `ART-05` | A concrete path never enters a domain identity, scientific specification, stage fingerprint, artifact key, or scientific manifest. |
| `ART-06` | A centralized (B0) artifact and a federated-averaging artifact are never fused under one identity. |
| `ART-07` | An `ESTIMATED` resource-cost value is never rendered as measured, and an advisory execution-cost estimate never enters scientific identity or reuse. |

### `EVAL-*` — evaluation

`EVAL-01`–`EVAL-06` are defined in `EVALUATION_REPORTING_AND_PROVENANCE.md
§§1–6`. `EVAL-07` (`§7`): a communication/storage cost value is either a
disclosed `MEASURED`/`ESTIMATED` derivation from the resolved configuration
or omitted; it is never fabricated from an approximate model when a real
derivation is available.

### `STAT-*` — statistics

`STAT-01`–`STAT-02` are defined in `EVALUATION_REPORTING_AND_PROVENANCE.md
§8`. Additional: `STAT-06` (`§5`) — expected statistical degeneracy is
persisted as a typed unavailable result, never raised as an exception or
retried.

### `REPORT-*` — reporting

`REPORT-01`–`REPORT-04` are defined in `EVALUATION_REPORTING_AND_PROVENANCE.md
§§9–12`.

### `PROV-*` — provenance

`PROV-01`–`PROV-02` are defined in `EVALUATION_REPORTING_AND_PROVENANCE.md
§10`.

### `TEST-*` — testing

Defined in `§8` below.

## 3. Accepted decisions

- The anchor is represented as `evidence_role = ANCHOR` on an ordinary
  `ScientificExperimentDefinition` (`ANCHOR-01`, `LOCKED`).
- No `Regime` type controls behavior; a dataset evaluation setting is
  composed. `Regime` itself is restored as a derived, publication-only
  label (`NAME-01`, `LOCKED`; `SCIENTIFIC_FOUNDATION.md §5`).
- `RunRequirement`, `FeasibilityStatus`, and `ParticipationStrategy` are
  restored as explicit enums, each kept distinct from a field it might
  otherwise be collapsed into (`evidence_role`, a transient gate result,
  and a hardcoded literal, respectively) — see
  `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §§2, 3.2, 14`.
- Per-stage identity dataclasses collapse to `StageIdentity` and
  `ArtifactKey` (`TYPE-01`, `LOCKED`).
- `ExperimentSpec`/`ExperimentProfileSpec`/`ScientificProtocolSpec`/`ClaimSpec`
  collapse to `ScientificExperimentDefinition` with eight owned branches (`ARCH-01`,
  `LOCKED`).
- There is no domain-level `ExperimentTemplate`; a sweep dimension exists
  only as a boundary-schema construct in `config`, expanded directly into
  `tuple[ScientificExperimentCell, ...]` by `config/compose.py`
  (`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §4`, `LOCKED`).
- `OperationsDefinition` has two owned sub-fields, `execution` and
  `reporting`; artifact namespace is a pure derivation
  (`derive_artifact_namespace`) from `evidence_role`, never a third stored
  sub-field (`ANCHOR-05`, `LOCKED`).
- Bootstrap resample count (`10000` for every BCa procedure) and every
  numeric resource-budget ceiling are supplied by validated configuration
  rather than boundary-blocked; they enter a resolved run as authored values
  (`CFG-01`; §7).

## 4. Old-concept disposition table

| Prior concept | Disposition | Notes |
|---|---|---|
| `ExperimentSpec` | Merged | Into `ScientificExperimentDefinition` |
| `ExperimentProfileSpec` | Split | Into a boundary-only sweep schema in `config` (never a `domain` type) and the resolved `ScientificExperimentDefinition`; `config/compose.py` expands the former directly into `tuple[ScientificExperimentCell, ...]` |
| `ScientificProtocolSpec` | Removed | Fields redistributed directly to `data`/`model`/`evaluations`/`analyses` |
| `ClaimSpec` | Removed | `evidence_role`/`tier` moved to `ExperimentIdentity`; fallback wording moved to `EVALUATION_REPORTING_AND_PROVENANCE.md §§8.2, 12` |
| `RegimeDataSpec` | Renamed | `DataDefinition` |
| `DetectorBranchSpec` | Renamed | `ModelDefinition`; the stored `DetectorBranchRole` field is removed and replaced by the pure `classify_training_profile` function |
| `EvaluationArmSpec` | Split | `EvaluationDefinition` (threshold, suite, metrics) owned directly by `ScientificExperimentDefinition`, plus `AnalysisDefinition` (comparison, statistics) as its own sibling branch — removing both the prior arm/branch cross-reference check and the prior per-evaluation statistics duplication (`ARCH-02`) |
| `ExecutionPolicy` / `ArtifactPolicy` / `ReportingPolicy` | Merged | Into `OperationsDefinition` with two named sub-fields (`execution`, `report`); `ArtifactPolicy`'s sole live field, namespace, is a pure derivation from `evidence_role` (`derive_artifact_namespace`) rather than a third stored sub-field |
| `ProtocolTrack` (`DATP_ANCHOR` / `COMPLETE`) | Removed | Replaced by `EvidenceRole.ANCHOR`; namespace is derived, not an independent scientific type |
| ~20 per-stage identity dataclasses | Merged | Into `StageIdentity` and `ArtifactKey` |
| Per-role score artifact IDs (calibration/test/temporal) | Merged | Into `ArtifactRef` discriminated by `SplitRole` |
| Six parallel centralized (B0) identity classes | Removed | `CentralizedPooledTraining` reuses `StageIdentity`/`ArtifactKey` (`ANCHOR-04`) |
| `CoreThresholdPolicy` (parallel to `ThresholdConstructionKind`) | Removed | One discriminated `ThresholdConstruction` union is sufficient |
| `RobustClusterMedianThresholdSpec` | Merged | Into `ClusterThreshold.aggregation` |
| `Regime` enum | Kept, redefined | Restored as a derived, publication-only label computed from `DataDefinition` (`SCIENTIFIC_FOUNDATION.md §5`); never a constructor input or discriminator |
| `RegimeCompatibilitySpec` | Removed | Composition of `DataDefinition` plus ordinary cross-field validation (`SCIENTIFIC_FOUNDATION.md §8`) replaces its closed compatibility mapping |
| `ExperimentRole` | Kept, renamed, narrowed | `EvidenceRole`, eight executable members (`ANCHOR` added; the non-executable `FUTURE_WORK`/`FORBIDDEN` dropped — future work is `CatalogueDisposition.FUTURE_WORK`, forbidden is a Tier-9 manuscript rule, `SCIENTIFIC_FOUNDATION.md §4`) |
| `RunRequirement` | Kept, narrowed | `MANDATORY`, `OPTIONAL`, `SUPPRESSED`; rejected and future catalogue entries use `CatalogueDisposition` rather than executable run status |
| `FeasibilityStatus` | Kept unchanged | field of the persisted `FEASIBILITY_RESULT` artifact, distinct from the transient `FeasibilityGateDecision` result union |
| `ParticipationStrategy` | Kept unchanged | retained as a real, single-member-today enum because the roadmap names `PARTIAL` as future work |
| `CheckpointSelectionStrategy` | Removed | single-member enum with no documented future variant; replaced by the locked value `CheckpointSelectionPolicy` |
| `ManifestType` | Merged | into `ArtifactType`; each of its thirteen members already names a specific `ArtifactType` member (`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §14.4`) |
| `ThresholdComparatorRole` | Removed | B0 never enters the shared `ThresholdConstruction` union; "outside the ladder" is expressed by the owning experiment's `evidence_role = STRESS_TEST` |
| `ThresholdVariant` | Removed | redundant with the `ThresholdConstruction` union's own members |
| Six scope-specific key classes | Merged | Into one `ArtifactKey` with a discriminated `ArtifactScopeKey`; `ArtifactRef` adds only verified content identity |
| `DraftPlannedStage`/`FinalPlannedStage` | Retained | Same shape; still carry no reuse decision pre-preflight and a classified reuse decision post-preflight respectively |
| `ResourceBudget`, `ParallelismSpec`, `SeedPlan`, `HardwareInventory` | Retained | Execution-only types, unchanged in role |
| Letter-based labels (`B1`–`B5`, `A`/`B-a`/`C`/`D`) | Retained as metadata | `roadmap_reference` field only, never a discriminator |
| `TestProfileExecutor`/`TestProfileSpec` | Retained, confined | Test infrastructure only; never imported by production `src/datp_core` (`TEST-01`) |

## 5. Rejected alternatives

- **A separate anchor pipeline, runner, or compatibility facade** —
  rejected; the anchor uses the same generic stage machinery and only its
  applicable registered contracts.
- **Letter-based identifiers as control flow** — rejected everywhere; a
  roadmap code survives only as metadata.
- **A universal `Result`, `Payload`, `Context`, or `Manager` type** —
  rejected; every operation returns a precisely named result.
- **A generic `ArtifactRepository` god-interface** — rejected; persistence
  is narrowed into `ArtifactStore`, `CheckpointStore`, `ManifestStore`,
  `ArtifactLockProvider`.
- **A recursive dictionary diff or `dict[str, Any]` in a domain/application
  contract** — rejected; every structured value is a named frozen dataclass
  or a typed collection.
- **Inferring a configuration variant from an optional field** — rejected;
  every variant carries an explicit discriminator.
- **A single whole-experiment fingerprint as the reuse key** — rejected;
  reuse is stage-scoped.
- **Hashing a JSON serialization of a specification** — rejected; a
  fingerprint hashes a canonical typed, quantized tuple.
- **A `Result[T, E]` monad at stage boundaries** — rejected; typed
  exceptions are used, with discriminated result values only for pure
  fallible functions (statistics, gate decisions).
- **A global `multiprocessing.set_start_method`** — rejected; a per-stage
  spawn context is used for any CUDA-touching stage.
- **Approximate quantile estimators as a silent substitute** — rejected;
  every `QuantileEstimatorType` member is exact; an approximate estimator
  would be a separately named, equivalence-tested, non-confirmatory method.
- **Simple pooled variance or a caller-controlled tie rule for the
  federated summary-statistic comparator** — rejected; full pooled variance
  and the larger-k tie rule are structural, not configurable.
- **A root `experiments/` package** — rejected; it would duplicate
  `domain/experiments.py`, `configs/experiments/`, and `application/planning/`.
- **`ArtifactPathResolver` as an application-facing port** — rejected; path
  resolution is confined to `infrastructure/persistence`.
- **A domain-level `ExperimentTemplate`** — rejected; a sweep exists only
  as a boundary-schema construct in `config`, expanded directly into
  `ScientificExperimentCell` values by the composer.
- **A stored `ArtifactDefinition.namespace` field** — rejected; namespace
  is a pure derivation from `evidence_role` (`derive_artifact_namespace`),
  removing the caller-supplied-inconsistency failure mode a stored,
  independently settable field would reintroduce.
- **A per-evaluation procedure field** — rejected; statistics
  are owned once per comparison, by `AnalysisDefinition`, never repeated
  under each compared threshold's `EvaluationDefinition`.
- **A parameterized CLI scientific override or Make-target argument** —
  rejected; every scientific change requires an edited, reviewed
  configuration document (`CFG-09`, `CFG-11`, `CFG-12`).

## 6. Complete error taxonomy

Every error inherits `DatpCoreError`. Each family carries typed context,
never a bare string; infrastructure and framework exceptions are translated
at the adapter boundary and never cross into `application` or `domain`.

| Error | Disposition |
|---|---|
| `ConfigurationError` | `RUN_BLOCKING` |
| `DomainValidationError` | `RUN_BLOCKING`; includes a non-finite value in any fingerprinted field |
| `DatasetError` / `PartitionError` / `SplitError` | `STAGE_BLOCKING` |
| `PreprocessingError` | `STAGE_BLOCKING` |
| `CudaUnavailableError` | `RUN_BLOCKING`; no CPU fallback |
| `CudaOutOfMemoryError` | `STAGE_BLOCKING`; terminal for the execution attempt; no automatic recovery or retry |
| `RamPreflightError` / `DiskSpaceError` / `ResourceBudgetExceededError` | `RUN_BLOCKING` before execution |
| `UnsafeParallelismError` | `RUN_BLOCKING` at plan time |
| `InvalidCpuFallbackError` | `RUN_BLOCKING` |
| `TrainingError` | `STAGE_BLOCKING`; convergence is diagnostic metadata, never an exception |
| `FullParticipationViolationError` / `RoundAbortedError` | round aborted; no aggregation, advance, or checkpoint |
| `CheckpointError` / `CheckpointSelectionError` | `STAGE_BLOCKING` / `RUN_BLOCKING` |
| `RecoveryStateMismatchError` / `ResumeIncompatibilityError` | `STAGE_BLOCKING`; refuse resume |
| `ScoringError` / `ThresholdError` / `EvaluationError` | `STAGE_BLOCKING` |
| `StatisticsError` | `STAGE_BLOCKING`; reserved for genuinely unexpected failure, never for expected degeneracy |
| `ArtifactError` / `PartialArtifactError` / `IncompleteArtifactBundleError` | `STAGE_BLOCKING`; recompute; never mark complete |
| `ArtifactLockConflict` | `RETRYABLE_TRANSIENT`, bounded |
| `PathResolutionError` | `RUN_BLOCKING`; escape or invalid path |
| `ProvenanceError` | `STAGE_BLOCKING`; refuse untraced output |
| `StageFingerprintMismatchError` | `STAGE_BLOCKING`; block reuse |
| `ReuseIncompatibilityError` | classify `RECOMPUTE` |
| `ReuseBlockedError` | `STAGE_BLOCKING` |
| `DeterminismViolationError` | `RUN_BLOCKING` |
| `FeasibilityRejection` | `RUN_BLOCKING` |
| `AmbiguousPlanError` / `CyclicPlanError` | `RUN_BLOCKING`; refuse plan |
| `AnchorReproductionFailure` | blocks journal-expansion track only |
| `EnvironmentIncompatibilityError` | `RUN_BLOCKING` |
| `ReportingError` | `STAGE_BLOCKING` |

## 7. Genuine blockers

Each is carried into `ScientificReadinessResult`; a `SCIENTIFIC` or
`PRINT_GRADE` plan cannot schedule an affected stage until the named
authority closes it, and smoke behavior against it is explicitly
non-citable.

| Decision | Authority needed | Blocked stages | Status |
|---|---|---|---|
| External-device (Edge-IIoTset) partition granularity (device vs. group) | first-principles feasibility audit | every `external_device_validation` stage | `BLOCKED` |
| External-device post-encoding `model_feature_order` width | source inspection (data-dependent one-hot expansion) | materialization onward for `external_device_validation` | `BLOCKED`; the 63-column raw schema and its 15-drop/7-encode column lists are verified (`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §11.3`) — only the final encoded width is open |
| CICIoT2023 feature count (conference value d = 39) | `processed_feature_verification` audit's own run | any quantitative `file_pseudo_client_applicability_boundary` claim | `BLOCKED` pending the audit's own execution; manually corroborated at exactly 39 against the mounted corpus (`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §11.2`) |
| Genuine Edge-IIoTset timestamp semantics | source inspection | `chronological_recalibration_evaluation` | `BLOCKED`; `frame.time` is confirmed well-formed in the raw per-sensor captures but malformed in sampled rows of the combined "Selected" files — the malformed-value distribution across the full corpus is unresolved (`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §11.3`) |
| N-BaIoT row-1 cold-start handling policy | scientific authority | any `natural_device_evaluation`/`controlled_heterogeneity_evaluation` materialization | `BLOCKED`; the artifact itself is verified (every raw file's first row carries a raw epoch timestamp in its `HH_jit_*_mean` columns instead of a jitter statistic) — only the drop-vs-flag policy is open (`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §11.1`) |
| N-BaIoT / CICIoT2023 duplicate-row handling policy | scientific authority | materialization for `natural_device_evaluation`, `file_pseudo_client_evaluation` | `BLOCKED`; a low, nonzero duplicate rate is confirmed on sampled files (`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §§11.1–11.2`); the full-corpus rate for either dataset is unmeasured |
| CICIoT2023 `Rate = inf` / empty `Std`,`Variance` degenerate-window handling policy | scientific authority | materialization for `file_pseudo_client_evaluation` and any experiment referencing `ciciot2023` | `BLOCKED`; confirmed recurring on real rows (single-packet flow windows), never a transcription error (`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §11.2`) |
| Edge-IIoTset `Temperature_and_Humidity` subnet-consistency anomaly | source inspection | `edge_iiotset_client_granularity_feasibility` | `BLOCKED`; the other nine `Normal traffic/` sensor folders each occupy one consistent `/24` subnet, this one does not in the sampled rows (`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §11.3`) |
| Canonical clustering `n_init`/`max_iter` constants | pre-registration | canonical `ClusterThreshold` in `SCIENTIFIC`/`PRINT_GRADE` runs | `BLOCKED` |
| "Material movement toward zero" numeric tolerance for anchor equivalence | scientific/statistical authority | journal-expansion planning | `BLOCKED`; the approximately-20%-wider-than-reference rule is already locked (`SCIENTIFIC_FOUNDATION.md §2`) |

Already resolved and therefore **not** blockers: the bootstrap resample
count `10000` for every BCa procedure; the base `experiment_seed = 0` for
every experiment and its deterministic derivation rule
(`training_seed[i] = experiment_seed + i`,
`analysis_seed[i] = experiment_seed + 300 + i`, for `i ∈ [0, paired_seed_count)` —
anchor `paired_seed_count = 5` giving seeds 0–4 / 300–304, DATP-Core
`paired_seed_count = 10` giving seeds 0–9 / 300–309); the RAM/VRAM ceilings
and worker count sized from an inspected host (execution-budget provenance
note below); the genuine-Ditto model-personalization comparator
(`personalization: ditto`, `personalization_proximal_weight: 1.0`); the
matched-exceedance k-grid step `0.05`; the anchor reference
interval `[0.647, 0.769]`; the ten-paired-seed confirmatory cohort size; the
named `checkpoint_profiles` (`datp_core` = `{25,50,75,100,125,150,200}`,
`anchor_terminal` = `{150}`), each experiment referencing one via
`checkpoint_profile` — the anchor a single terminal checkpoint at round 150
(`rounds_max = 150`) and DATP-Core the seven checkpoints through round 200
(`rounds_max = 200`), two distinct schedules that never share a `rounds_max`
or a terminal state — and their selection rule; B4
canonical `K = 3`; the `n_min = 100` eligibility rule and Regime-D-equivalent
90% coverage gate; the canonical chronological 70/30 boundary; the full
`FederatedSummaryStatisticThreshold` variance and tie rule; the FedProx
µ-grid `{0.001, 0.01, 0.1}` bound per experiment through
`training.parameters.mu: { from_sweep: federated_proximal_mu }` so the
reusable `federated_proximal` profile carries no literal µ; the encoder architecture, optimizer, batch
size, precision, and determinism level (`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md
§12`); the N-BaIoT 115-column feature schema and its exact
aggregation/window/statistic generation rule; the CICIoT2023 39-column raw
feature schema and its 63-vs-309-file structure; the Edge-IIoTset
63-column raw source schema and its 15-drop/7-encode preprocessing recipe
(`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §§11.1–11.3` — feature-*schema
identity* is closed by direct inspection for all three datasets even where
a downstream numeric *value* remains blocked).

**Execution-budget provenance.** The `execution.yaml` resource budgets were
sized from an inspected host: 1× NVIDIA GeForce RTX 5060 Ti with 16,311 MiB
(15.93 GiB) total VRAM (~1.6 GiB held by the desktop session), `MemTotal`
11.68 GiB RAM, 6 logical CPUs (AMD Ryzen 5 7600), and 581 GiB free disk. The
`scientific` and `print_grade` profiles set `max_ram_gib = 10`,
`max_vram_gib = 12`, and `worker_count = 4` (4 of 6 CPUs);
`process_start_method = spawn` is the locked rule for every CUDA-touching
stage (`EXEC-04`), and `fork` is permitted only for the `cpu_only` profiles
(`dataset_audit`). Data-loading mechanics are execution-owned: each profile
carries a `data_loading` block (`chunk_row_count`, `streaming`) — 50000 for
`scientific`/`print_grade`/`dataset_audit`, 10000 for `development`, 1000 for
`smoke`/`test_smoke` — and datasets no longer carry a `chunk_profile`. These
budgets must be re-verified against the real training host before any
`SCIENTIFIC` or `PRINT_GRADE` run.

## 8. Test architecture

| Level | Directory | Purpose |
|---|---|---|
| `UNIT` | `tests/unit/{domain,application,config,analysis}/` | domain invariants (benign-only calibration, delta orientation, AUROC-control, canonical-K derivation, eligibility, non-finite rejection); concrete-service behavior with typed test doubles; schema-to-domain mapping; framework-free specification construction |
| `PROPERTY` | `tests/property/` | value-object ranges and finiteness; `cv_fpr`, pooled variance including the between term, `fpr_target = 1 − q` under the canonical `Decimal`; Cliff's delta antisymmetry and bounds |
| `CONTRACT` | `tests/contract/` | every infrastructure adapter exercised against its port's shared contract suite |
| `INTEGRATION` | `tests/integration/{data,detection,persistence,reporting,cuda}/` | chunked-versus-reference equivalence; checkpoint selection and reuse across the ladder and B0; atomic commit and bundle rejection; result-freeze/provenance closure; CUDA refusal/no-fallback/spawn-context and sequential-versus-parallel equivalence |
| `ARCHITECTURE` | `tests/architecture/` | `test_dependency_rules.py`, `test_framework_confinement.py`, `test_no_forbidden_module_names.py`, `test_no_module_side_effects.py`, `test_no_cycles.py` |
| `SYSTEM_SYNTHETIC` | `tests/system/synthetic/` | a reduced synthetic end-to-end run of the full stage sequence |
| `SCIENTIFIC_SMOKE` | `tests/system/scientific_smoke/` | the confirmatory BCa rule and its failure behavior on a small real-data subsample |
| `GOLDEN` | `tests/golden/` | fixed cluster-assignment and adjusted-Rand snapshots; manifest/provenance snapshot regression |

No test writes to a scientific output root; every test resolves storage
beneath an isolated sandbox. `TestProfileSpec` (suite, data scale,
isolation, device requirement, parallelism, external-dependency policy,
resource budget, artifact policy, logging) is test infrastructure only and
is never imported by production `src/datp_core` (`TEST-01`).

### 8.1 Scientific metamorphic tests

- Changing only a threshold policy does not change compatible score artifact keys.
- Changing only a report format does not invalidate a scientific artifact.
- The core ladder's threshold constructions consume identical compatible
  calibration and test score sets.
- Attack samples never enter threshold calibration.
- A confusion count reconciles exactly with the recorded population size.
- AUROC is invariant under a threshold-only change.
- A paired comparison uses the same seed cohort and the same eligible-client
  set for both compared policies.
- A missing required YAML field fails rather than defaulting.
- An incompatible artifact is recomputed or blocked, never reused.
- A source column absent from the authored `DatasetFieldSchema`, or an
  authored `model_feature_order` entry absent from the actual source
  header, fails `SOURCE_INSPECTION` rather than silently reshuffling or
  padding the feature vector.
- The anchor uses the same generic planner, executor, persistence, and registry machinery; only its applicable stage contracts are planned.
- Adding a pipeline stage requires no change to the core executor.
- An `ExperimentCellIdentity` collision between two distinct resolved cells
  raises a typed planning error rather than overwriting silently.
- Expected statistical degeneracy is a persisted typed result, never a
  raised exception.

## 9. Extension proofs

1. **New dataset** — a `Dataset` member; a source-inspection/partitioner
   adapter that derives the dataset's own `DatasetFieldSchema` from its
   actual source columns (`CFG-13`); one new `configs/datasets/<name>.yaml`
   document (audits, setups, split, preprocessing, and eligibility all in
   that one file); one composition binding; contract, memory-equivalence,
   and schema-drift-detection tests. No evaluation, reporting, or metric
   edit.
2. **New client construction** — a new `ClientConstruction` variant, its
   implementation, its validation, one composition binding. No letter-based
   label, no copied experiment.
3. **New threshold policy** — the correct `ThresholdConstruction` variant, a
   discriminated configuration arm with exactly its own fields, an
   infrastructure implementation, one registry line. Scores are reused
   automatically because the threshold change preserves compatible score artifact keys.
4. **New metric** — a `MetricId` member in its correct family, a
   `MetricSpec`, a typed per-family calculator, reporting metadata. No
   renderer edited per metric, no raw dictionary.
5. **New pipeline stage** — worked in full in
   `PIPELINE_EXECUTION_AND_ARTIFACTS.md §4.1`; the core executor,
   persistence engine, and lifecycle logic are unchanged.
6. **New experiment** — one new entry appended to the `configs/experiments/`
   family document matching its scientific role, referencing existing
   dataset/setup, model/training-profile, and execution-profile identities,
   with its report inlined; no random code, no new planner or executor
   branch, no new family document required.
7. **New report** — a new `ReportDefinition` consuming a frozen result and
   its provenance; it never recomputes a scientific value.

### 9.1 Consolidated forbidden-shape rules

These hold across every `domain` and `application` contract and are each
enforced by a named test (`§8`). They restate, in one place, the shape
constraints scattered across the type rules so an implementer never has to
reassemble them.

| # | Forbidden | Instead | Enforced by |
|---|---|---|---|
| F-01 | `dict`, `dict[str, Any]`, `Mapping[str, Any]`, `list[dict[str, Any]]` in a public contract | a frozen dataclass, a `tuple`, or a snapshotted frozen mapping | `tests/architecture/test_framework_confinement.py`, `TYPE-03` |
| F-02 | `Any`, `object`, `Sequence[object]`, `tuple[object, ...]` | a named type or a discriminated union | `TYPE-03` |
| F-03 | a mutable `list`/`dict`/`set`, NumPy array, tensor, DataFrame, or estimator as a public field | an immutable `tuple` / frozen snapshot; framework carriers stay in `infrastructure` | `test_framework_confinement.py`, `§8` |
| F-04 | variant inference from an optional field's presence | an explicit discriminator, exhaustively matched | `TYPE-04` |
| F-05 | a Python/dataclass/Pydantic default, `dict.get` fallback, env fallback, or CLI override on an identity-bearing field | an explicit YAML value or a typed reference; otherwise a boundary blocker | `unit/config` missing-field tests, `CFG-01`, `CFG-03` |
| F-06 | a raw `float` in a fingerprint | a canonical `Decimal` value object rejecting `NaN`/infinity | `tests/property/`, `TYPE-05` |
| F-07 | the same field owned by two aggregates | one authoritative owner; downstream holds an `ArtifactRef`/`StageIdentity` | `§3.5` of `DOMAIN`, `ARCH-01/02` |
| F-08 | a framework object crossing into `domain`/`application` | a framework-neutral `ArtifactRef`/descriptor | `test_framework_confinement.py`, `§8` of `DOMAIN` |
| F-09 | zero/`NaN`/infinity/empty/missing-key for an unavailable scientific value | a typed unavailable outcome (`UndefinedCvResult`, `DegenerateBootstrapIntervalResult`) | `unit/domain` degeneracy tests, `EVAL-04`, `STAT-06` |
| F-10 | a generic `Result`/`Payload`/`Context`/`Manager`/`Handler`/`Kind` type | a precisely named result and a union discriminator | `test_no_forbidden_module_names.py`, `TYPE-02`, `NAME-06` |

### 9.2 Extension seams for future research (localized-change proofs)

The present scope is strict (`SCI-09`); no future-research type is implemented
now. Each direction below, when authorized, is a localized addition along an
existing seam — never a repository-wide redesign. Each row names the seam and
the files touched; none requires an optional field on every existing
dataclass, an edit to every experiment, a new planner/executor branch, a
replacement identity system, or a compatibility shim.

| Future direction | Seam | Localized additions | Never touched |
|---|---|---|---|
| **New run family** (e.g. a genuinely non-experiment, non-audit run) | `RunDefinition` union | a new `RunDefinition` variant; its stages' `is_applicable`; a registry binding | `ScientificExperimentDefinition`, `DatasetAuditDefinition`, existing stages |
| **Dynamic / temporally adaptive thresholds** (Dynamic DATP) | `ThresholdConstruction` union + `ArtifactScopeKey` | a threshold variant carrying its state reference; a temporal/state `ArtifactScopeKey` variant; a stage implementation | `ArtifactKey`/`ArtifactRef`, the reuse algorithm, score generation |
| **Multi-time-coordinate evaluation** (streaming windows) | `SplitDefinition` + `ArtifactScopeKey` | a temporal `SplitDefinition` member; a windowed scope variant; a scoring/eval stage | existing single-window evaluations |
| **Stateful policy** (a policy carrying immutable state across runs) | artifact model | an immutable state/policy `ArtifactType` + scope variant; a stage that reads/writes it | the stateless-artifact reuse path |
| **Transformation / intervention workflow** (a run that mutates state) | provenance model | an explicit transformation/intervention `ProvenanceRecord` field set; a stage; a scope variant | existing clean-run provenance |
| **New model family** (different architecture or training lifecycle) | `TrainingProfile` union, `configs/models/` | a new `configs/models/<name>.yaml` document; a `TrainingProfile` variant if the lifecycle genuinely differs; a training/scoring adapter; `classify_training_profile` gains one arm | the checkpoint identity model, existing model documents |
| **New dataset / client construction** | `Dataset` registry + `ClientConstruction` union | a registry entry / a construction variant + adapter; one binding | central enums, thresholds, metrics, reports |

Each seam is already load-bearing in the current design (the `RunDefinition`
union has two members today; `ArtifactScopeKey` is already a discriminated
family; `ProvenanceRecord` already carries typed upstream references), so the
future addition extends a mechanism that exists rather than introducing a new
one. No vague `Plugin`/`Extension`/`Strategy`/`Hook` abstraction is added
ahead of a concrete use (`§5` rejected alternatives).

## 10. Source-coverage ledger

| Source concept | Destination | Disposition |
|---|---|---|
| Roadmap §§1–3 (identity, invariants, confirmatory claim) | `SCIENTIFIC_FOUNDATION.md §§1–3` | retained, renamed to semantic form |
| Roadmap §4 (nomenclature) | `SCIENTIFIC_FOUNDATION.md §6` | retained, letter codes demoted to metadata |
| Roadmap §§5–6 (claim hierarchy, RQs) | `SCIENTIFIC_FOUNDATION.md §4` | retained |
| Roadmap §7 (regime table) | `SCIENTIFIC_FOUNDATION.md §5` | retained; `Regime` no longer controls behavior but is kept as a derived citation label over composed `DataDefinition` values |
| Roadmap §8 (module integration) | `SCIENTIFIC_FOUNDATION.md §7.2–7.3` | retained |
| Roadmap §9 (experiment matrix, all 28 catalogue items plus B0/boundary/rejections) | `SCIENTIFIC_FOUNDATION.md §7` in full | retained, semantically renamed |
| Roadmap §10 (statistics) | `EVALUATION_REPORTING_AND_PROVENANCE.md §8` | retained |
| Roadmap §11 (temporal outcomes) | `EVALUATION_REPORTING_AND_PROVENANCE.md §6.5` | retained |
| Roadmap §12 (fallback wording) | `EVALUATION_REPORTING_AND_PROVENANCE.md §§8.2, 12` | retained as claim-outcome mechanism, not reproduced verbatim per outcome |
| Roadmap §13 (reviewer register) | distributed across `SCIENTIFIC_FOUNDATION.md` and this file | answered structurally; every listed objection maps to a named experiment or locked rule already covered, not reproduced as a 28-row table |
| Roadmap §§14, 20 (checklists, go/no-go) | §9 conformance checklist below | retained |
| Roadmap §16 (scope boundaries) | `SCIENTIFIC_FOUNDATION.md §§3, 7.6` | retained as `SCI-09` and the rejected-experiment table |
| Roadmap §17 (implementation planning) | `DOMAIN_AND_APPLICATION_ARCHITECTURE.md`, `CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md` in full | retained |
| Prior architecture §§1–2 (purpose, principles) | `SCIENTIFIC_FOUNDATION.md §3`, this file §2 | retained, restated as rule IDs |
| Prior architecture §3 (dependency model) | `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §1` | retained, six-to-seven-layer shape preserved |
| Prior architecture §§6–7 (enums, value objects) | `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §§3, 6.2, 14` | every enum given an explicit disposition in the complete catalogue (§14); no silent omission |
| Prior architecture §8 (aggregate specifications) | `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §§2–3` | merged into the four-branch `ScientificExperimentDefinition` |
| Prior architecture §9 (spec/request/result catalogue) | `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §6` | consolidated into the complete public contract catalogue |
| Prior architecture §§12–14 (ports, lineage, planning) | `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §7`, `PIPELINE_EXECUTION_AND_ARTIFACTS.md §§1–7` | retained |
| Prior architecture §15 (path/storage) | `PIPELINE_EXECUTION_AND_ARTIFACTS.md §8` | retained, six scope-specific key classes merged into one discriminated `ArtifactScopeKey` |
| Prior architecture §16 (CUDA/batching) | `PIPELINE_EXECUTION_AND_ARTIFACTS.md §§10–10.1` | retained |
| Prior architecture §17 (checkpoints/recovery) | `PIPELINE_EXECUTION_AND_ARTIFACTS.md §9`, `SCIENTIFIC_FOUNDATION.md §2` | retained |
| Prior architecture §18 (lifecycle) | `PIPELINE_EXECUTION_AND_ARTIFACTS.md §11` | retained |
| Prior architecture §19 (logging) | `PIPELINE_EXECUTION_AND_ARTIFACTS.md §12` | retained |
| Prior architecture §20 (errors/retry) | this file §§6, `PIPELINE_EXECUTION_AND_ARTIFACTS.md §13` | retained in full |
| Prior architecture §21 (test architecture) | this file §8 | retained |
| Prior architecture §22 (reporting/provenance) | `EVALUATION_REPORTING_AND_PROVENANCE.md §§9–11` | retained |
| Prior architecture §23 (rejected alternatives) | this file §5 | retained, condensed to the decisions still relevant after consolidation |
| Prior architecture §25 (extension playbooks) | this file §9 | retained |
| Prior architecture §§26–27 (deferred/blockers) | `SCIENTIFIC_FOUNDATION.md §7.6`, this file §7 | retained in full, no invented resolution |
| Prior architecture §28 (class responsibilities) | `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §7` | consolidated into the use-case/port tables |
| Prior architecture §29 (invariants, 81 invalid states) | this file §2 rule register | condensed into rule IDs; every invalid state maps to at least one `SCI-*`, `ARCH-*`, `TYPE-*`, `ART-*`, `PIPE-*`, or `EXEC-*` rule above |

No source section was omitted without an explicit destination or an
explicit removal reason recorded in §4 or §5 above.

## 11. Final conformance checklist

- ☐ No letter-based identifier controls behavior anywhere in `domain` or
  `application`.
- ☐ The anchor has no separate pipeline, port, or artifact type.
- ☐ Every multi-variant type carries an explicit, exhaustively matched tag.
- ☐ No identity-bearing field has a Python, dataclass, or Pydantic default;
  incomplete boundary input is reported as a blocker and never mapped into a
  resolved value.
- ☐ `Any`, `object`, and generic mappings are absent from `domain` and
  `application` contracts.
- ☐ No two aggregates own the same field.
- ☐ Evaluation never trusts a supplied confusion count.
- ☐ Reporting never recomputes a scientific value.
- ☐ Every roadmap experiment (§7 of `SCIENTIFIC_FOUNDATION.md`) has a
  semantic slug and, where named, a `roadmap_reference`.
- ☐ Every genuine blocker in §7 above is recorded, none silently resolved.
- ☐ Exactly eight Markdown files exist in this package (`README.md` plus the
  seven content documents, including `PROJECT_STRUCTURE_AND_MODULE_CATALOGUE.md`),
  none exceeding its approximate word target without cause.
- ☐ Configuration resolution is a pre-pipeline composition operation, never
  a stage; plans contain only applicable registered stages and have no fixed
  stage-count invariant.
- ☐ No domain-level `ExperimentTemplate` exists; every sweep is a boundary
  schema construct expanded by `config/compose.py` into `ScientificExperimentCell`
  values before planning.
- ☐ No `EvaluationDefinition` carries a procedure field;
  every statistical procedure is owned by an `AnalysisDefinition`.
- ☐ `configs/models/` is the only model-configuration directory name used
  anywhere in this package; no `configs/detectors/`, `configs/protocols/`,
  `configs/dataset_audits/`, `configs/data_sources/`, `configs/runtime/`, or
  `configs/reporting/` reference remains — the four-directory tree
  (`datasets/`, `models/`, `experiments/`, `execution.yaml`) is identical,
  file for file, in `CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §1` and
  `PROJECT_STRUCTURE_AND_MODULE_CATALOGUE.md §3`.
- ☐ The CLI exposes exactly the seven `datp-core experiment <action>`
  verbs and accepts no scientific override flag.
- ☐ Every regularly executed root experiment in
  `CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §22.1` has a discoverable
  zero-input Make target for each of its meaningful actions; no
  parameterized Make target exists.
- ☐ No standalone experiment root exists for an item this package
  classifies as an attached analysis (`SCIENTIFIC_FOUNDATION.md §7.4`); the
  cluster and federated-summary families are each a single merged
  experiment entry within its family document.
- ☐ Every `schema_version` example in this package is the integer `1`.
- ☐ Every root experiment, dataset audit check, dataset setup, model
  training profile, and execution profile has a concrete configuration
  document (`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §§9–16`); each
  unresolved value is a marked boundary blocker, never a default.
- ☐ Every public value object, identifier, union member, request, result,
  planning/execution/artifact/provenance type has a concrete frozen
  declaration (`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §16`); every closed
  enum has an explicit member list (`§17`).
- ☐ Every `PipelineStage` has a per-stage contract (identity projection,
  reuse trigger, failure, retry, test) and every root experiment and dataset
  audit has a workflow row (`PIPELINE_EXECUTION_AND_ARTIFACTS.md §§16–17`).
- ☐ The forbidden-shape rules (`§9.1`) and the future-research extension
  seams (`§9.2`) are enumerated with the seam and files each touches; no
  future-research type is implemented now.
- ☐ No implementation agent must invent a major type, configuration family,
  workflow, artifact, ownership rule, or module boundary: each is defined
  concretely with fields, producers, consumers, and persistence status.

# ENGINEERING_DECISIONS_AND_CONFORMANCE

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
| `SCI-19` | The detector architecture carries no batch normalization. |

### `ANCHOR-*` — anchor reproduction and equivalence

| ID | Rule |
|---|---|
| `ANCHOR-01` | The anchor is an `ExperimentDefinition` with `evidence_role = ANCHOR`; no separate technical system exists. |
| `ANCHOR-02` | `AnchorEquivalenceGate` is a decision service, not a pipeline fork; it runs the same eighteen stages as every experiment. |
| `ANCHOR-03` | A less-favorable ten-seed confirmatory result is never suppressed in favor of a more-favorable five-seed anchor result. |
| `ANCHOR-04` | The centralized reference (B0) reuses `StageIdentity`/`ScoreIdentity`; it never gains a parallel identity hierarchy. |
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
| `ARCH-01` | `ExperimentDefinition` has exactly four owned branches: `data`, `detector`, `evaluations`, `operations`. |
| `ARCH-02` | Statistics are owned by `EvaluationDefinition`, never duplicated at the experiment level. |
| `ARCH-03` | No backward-compatibility shim, alias layer, or migration facade toward the prior architecture or the original reference project exists. |
| `ARCH-04` | No root `experiments/` package exists; experiment identity lives in `domain/experiments.py`, YAML in `configs/experiments/`, mapping in `config/mapping/`, expansion in `application/planning/`. |
| `ARCH-05` | `analysis` imports only `domain`, or narrowly a stable framework-free application reporting contract; never a persistence adapter. |
| `ARCH-06` | `cli` never constructs an adapter, binds a port, or resolves a path; it only invokes `composition`. |

### `TYPE-*` — typing and dataclasses

| ID | Rule |
|---|---|
| `TYPE-01` | Cross-stage or cross-role identity confusion is prevented by a tagged value (`StageIdentity`/`ScoreIdentity`), never by a structural alias. |
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
| `CFG-10` | A value neither source document specifies is marked `unresolved` and blocks `SCIENTIFIC`/`PRINT_GRADE` scheduling; it is never given a plausible invented value. |

### `PIPE-*` — stages and planning

| ID | Rule |
|---|---|
| `PIPE-01` | Adding a stage requires only its implementation, an optional configuration variant, and one registry line. |
| `PIPE-02` | Reuse is decided by comparing typed stage identities, never by filename or modification time. |
| `PIPE-03` | The planner deduplicates every compatible stage across confirmatory, supportive, mechanism, variant, and comparator evaluations sharing a seed. |
| `PIPE-04` | `RUNNING → REUSED` does not exist; reuse is always decided before computation. |
| `PIPE-05` | A `CellIdentity` collision between two distinct resolved cells is a typed planning error. |

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
| `ART-01` | An `ArtifactRef` is derived deterministically from artifact type, scope key, and stage identity; never randomly generated for a scientific artifact. |
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
  `ExperimentDefinition` (`ANCHOR-01`, `LOCKED`).
- No `Regime` type controls behavior; a dataset evaluation setting is
  composed. `Regime` itself is restored as a derived, publication-only
  label (`NAME-01`, `LOCKED`; `SCIENTIFIC_FOUNDATION.md §5`).
- `ExecutionStatus`, `FeasibilityStatus`, and `ParticipationStrategy` are
  restored as explicit enums, each kept distinct from a field it might
  otherwise be collapsed into (`evidence_role`, a transient gate result,
  and a hardcoded literal, respectively) — see
  `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §§2, 3.2, 14`.
- Per-stage identity dataclasses collapse to `StageIdentity` and
  `ScoreIdentity` (`TYPE-01`, `LOCKED`).
- `ExperimentSpec`/`ExperimentProfileSpec`/`ScientificProtocolSpec`/`ClaimSpec`
  collapse to `ExperimentDefinition` with four owned branches (`ARCH-01`,
  `LOCKED`).
- Bootstrap resample count and every numeric resource-budget ceiling are
  explicitly marked `unresolved` rather than defaulted (`CFG-10`,
  `BLOCKED`; §7).

## 4. Old-concept disposition table

| Prior concept | Disposition | Notes |
|---|---|---|
| `ExperimentSpec` | Merged | Into `ExperimentDefinition` |
| `ExperimentProfileSpec` | Split | Into `ExperimentTemplate` (sweep-capable) and the resolved `ExperimentDefinition` |
| `ScientificProtocolSpec` | Removed | Fields redistributed directly to `data`/`detector`/`evaluations` |
| `ClaimSpec` | Removed | `evidence_role`/`tier` moved to `ExperimentIdentity`; fallback wording moved to `EVALUATION_REPORTING_AND_PROVENANCE.md §§8.2, 12` |
| `RegimeDataSpec` | Renamed | `DataDefinition` |
| `DetectorBranchSpec` | Renamed | `DetectorDefinition`; the stored `DetectorBranchRole` field is removed and replaced by the pure `classify_detector` function |
| `EvaluationArmSpec` | Renamed | `EvaluationDefinition`; owned directly by `ExperimentDefinition`, removing the prior arm/branch cross-reference check |
| `ExecutionPolicy` / `ArtifactPolicy` / `ReportingPolicy` | Merged | Into `OperationsDefinition` with three named sub-fields |
| `ProtocolTrack` (`DATP_ANCHOR` / `COMPLETE`) | Removed | Replaced by `EvidenceRole.ANCHOR`; namespace is derived, not an independent scientific type |
| ~20 per-stage identity dataclasses | Merged | Into `StageIdentity` and `ScoreIdentity` |
| Per-role score artifact IDs (calibration/test/temporal) | Merged | Into `ArtifactRef` discriminated by `SplitRole` |
| Six parallel centralized (B0) identity classes | Removed | `CentralizedPooledTraining` reuses `StageIdentity`/`ScoreIdentity` (`ANCHOR-04`) |
| `CoreThresholdPolicy` (parallel to `ThresholdConstructionKind`) | Removed | One discriminated `ThresholdConstruction` union is sufficient |
| `RobustClusterMedianThresholdSpec` | Merged | Into `ClusterThreshold.aggregation` |
| `Regime` enum | Kept, redefined | Restored as a derived, publication-only label computed from `DataDefinition` (`SCIENTIFIC_FOUNDATION.md §5`); never a constructor input or discriminator |
| `RegimeCompatibilitySpec` | Removed | Composition of `DataDefinition` plus ordinary cross-field validation (`SCIENTIFIC_FOUNDATION.md §8`) replaces its closed compatibility mapping |
| `ExperimentRole` | Kept, renamed | `EvidenceRole`, ten members (`ANCHOR` added) |
| `ExecutionStatus` | Kept unchanged | `MANDATORY`, `OPTIONAL`, `SUPPRESSED`, `REJECTED`, `FUTURE`; a field of `ExperimentIdentity` distinct from `evidence_role` |
| `FeasibilityStatus` | Kept unchanged | field of the persisted `FEASIBILITY_RESULT` artifact, distinct from the transient `FeasibilityGateDecision` result union |
| `ParticipationStrategy` | Kept unchanged | retained as a real, single-member-today enum because the roadmap names `PARTIAL` as future work |
| `CheckpointSelectionStrategy` | Removed | single-member enum with no documented future variant; replaced by the locked value `CheckpointSelectionPolicy` |
| `ManifestType` | Merged | into `ArtifactType`; each of its thirteen members already names a specific `ArtifactType` member (`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §14.4`) |
| `ThresholdComparatorRole` | Removed | B0 never enters the shared `ThresholdConstruction` union; "outside the ladder" is expressed by the owning experiment's `evidence_role = STRESS_TEST` |
| `ThresholdVariant` | Removed | redundant with the `ThresholdConstruction` union's own members |
| Six scope-specific `ArtifactKey` variant classes | Merged | Into one `ArtifactRef` with a discriminated `ArtifactScopeKey` |
| `DraftPlannedStage`/`FinalPlannedStage` | Retained | Same shape; still carry no reuse decision pre-preflight and a classified reuse decision post-preflight respectively |
| `ResourceBudget`, `ParallelismSpec`, `SeedPlan`, `HardwareInventory` | Retained | Execution-only types, unchanged in role |
| Letter-based labels (`B1`–`B5`, `A`/`B-a`/`C`/`D`) | Retained as metadata | `roadmap_reference` field only, never a discriminator |
| `TestProfileExecutor`/`TestProfileSpec` | Retained, confined | Test infrastructure only; never imported by production `src/datp_core` (`TEST-01`) |

## 5. Rejected alternatives

- **A separate anchor pipeline, runner, or compatibility facade** —
  rejected; the anchor uses the same eighteen stages as every experiment.
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
| Bootstrap resample count | statistical authority | every bootstrap analysis | `BLOCKED` |
| Numeric RAM/VRAM/disk ceilings, worker count | operational authority | preflight for every `SCIENTIFIC`/`PRINT_GRADE` run | `BLOCKED` |
| Base `experiment_seed` integer for deterministic seed derivation | statistical/operational authority | every seed-dependent stage | `BLOCKED` |
| Personalization comparator choice and hyperparameters | documented pre-training decision | `model_personalization_absorption_test` | `BLOCKED` |
| External-device (Edge-IIoTset) partition granularity (device vs. group) | first-principles feasibility audit | every `external_device_validation` stage | `BLOCKED` |
| External-device feature schema / input dimension | source inspection | materialization onward for `external_device_validation` | `BLOCKED` |
| CICIoT2023 feature count (conference value d = 39) | inspected actual artifact | any quantitative `file_pseudo_client_applicability_boundary` claim | `BLOCKED` |
| Genuine Edge-IIoTset timestamp semantics | source inspection | `chronological_recalibration_evaluation` | `BLOCKED` |
| Matched-exceedance k-grid step for `FederatedSummaryStatisticThreshold` | authoritative protocol record | `federated_summary_threshold_comparison`, `fixed_parameter_comparator_sensitivity` | `BLOCKED` |
| Canonical clustering `n_init`/`max_iter` constants | pre-registration | canonical `ClusterThreshold` in `SCIENTIFIC`/`PRINT_GRADE` runs | `BLOCKED` |
| "Material movement toward zero" numeric tolerance for anchor equivalence | scientific/statistical authority | journal-expansion planning | `BLOCKED`; the approximately-20%-wider-than-reference rule is already locked (`SCIENTIFIC_FOUNDATION.md §2`) |

Already resolved and therefore **not** blockers: the anchor reference
interval `[0.647, 0.769]`; the ten-paired-seed confirmatory cohort size; the
`{25,50,75,100,125,150,200}` checkpoint schedule and its selection rule; B4
canonical `K = 3`; the `n_min = 100` eligibility rule and Regime-D-equivalent
90% coverage gate; the canonical chronological 70/30 boundary; the full
`FederatedSummaryStatisticThreshold` variance and tie rule; the FedProx
µ-grid `{0.001, 0.01, 0.1}`; the encoder architecture, optimizer, batch
size, precision, and determinism level (`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md
§12`).

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

- Changing only a threshold policy does not change a `ScoreIdentity`.
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
- The anchor executes through the same stage sequence as every experiment.
- Adding a pipeline stage requires no change to the core executor.
- A `CellIdentity` collision between two distinct resolved cells raises a
  typed planning error rather than overwriting silently.
- Expected statistical degeneracy is a persisted typed result, never a
  raised exception.

## 9. Extension proofs

1. **New dataset** — a `Dataset` member; a source-inspection/partitioner
   adapter; a `datasets/` YAML document; one composition binding; contract
   and memory-equivalence tests. No evaluation, reporting, or metric edit.
2. **New client construction** — a new `ClientConstruction` variant, its
   implementation, its validation, one composition binding. No letter-based
   label, no copied experiment.
3. **New threshold policy** — the correct `ThresholdConstruction` variant, a
   discriminated configuration arm with exactly its own fields, an
   infrastructure implementation, one registry line. Scores are reused
   automatically because the threshold change preserves `ScoreIdentity`.
4. **New metric** — a `MetricId` member in its correct family, a
   `MetricSpec`, a typed per-family calculator, reporting metadata. No
   renderer edited per metric, no raw dictionary.
5. **New pipeline stage** — worked in full in
   `PIPELINE_EXECUTION_AND_ARTIFACTS.md §4.1`; the core executor,
   persistence engine, and lifecycle logic are unchanged.
6. **New experiment** — a new `configs/experiments/` document referencing
   existing dataset/protocol/runtime/reporting entries; no random code, no
   new planner or executor branch.
7. **New report** — a new `ReportDefinition` consuming a frozen result and
   its provenance; it never recomputes a scientific value.

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
| Prior architecture §8 (aggregate specifications) | `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §§2–3` | merged into the four-branch `ExperimentDefinition` |
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
  every unresolved value is marked, not invented.
- ☐ `Any`, `object`, and generic mappings are absent from `domain` and
  `application` contracts.
- ☐ No two aggregates own the same field.
- ☐ Evaluation never trusts a supplied confusion count.
- ☐ Reporting never recomputes a scientific value.
- ☐ Every roadmap experiment (§7 of `SCIENTIFIC_FOUNDATION.md`) has a
  semantic slug and, where named, a `roadmap_reference`.
- ☐ Every genuine blocker in §7 above is recorded, none silently resolved.
- ☐ Exactly seven Markdown files exist in this package, none exceeding its
  approximate word target without cause.

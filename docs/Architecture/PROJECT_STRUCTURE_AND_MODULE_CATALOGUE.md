# PROJECT_STRUCTURE_AND_MODULE_CATALOGUE

## Purpose

Define the complete intended repository organization: the `src/datp_core`
layer-and-module tree, the `configs/` catalogue, the `tests/` tree, the
output and storage roots, file/module naming conventions, and the localized
placement rules for a new stage, dataset adapter, threshold implementation,
metric, report, or experiment.

## Authoritative for

The physical and conceptual repository layout, module responsibilities and
boundaries, and where each new artifact of work is placed.

## Not authoritative for

Scientific meaning (`SCIENTIFIC_FOUNDATION.md`), type contracts
(`DOMAIN_AND_APPLICATION_ARCHITECTURE.md`), configuration semantics
(`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md`), stage mechanics
(`PIPELINE_EXECUTION_AND_ARTIFACTS.md`), or rendering
(`EVALUATION_REPORTING_AND_PROVENANCE.md`). Where this document names a type,
stage, or rule, the owning document above is authoritative for its meaning;
this document is authoritative only for where it lives.

This is a design. No path, module, class, or test named here is asserted to
exist, to be implemented, or to be passing; each design commitment carries a
status from `ENGINEERING_DECISIONS_AND_CONFORMANCE.md §1`. A path that is
physically present in the repository ahead of this specification is
scaffolding at `DESIGNED_NOT_IMPLEMENTED`, not a conformance claim.

## 1. Repository root

```text
datp-core/
├── src/datp_core/       # the importable package (§2)
├── configs/             # authored boundary documents (§3)
├── tests/               # every test level (§4)
├── docs/                # this architecture package and the roadmap
├── outputs/             # runtime-resolved artifact and report roots (§5)
├── models/              # runtime-resolved external model/dataset inputs (§5)
├── ai/                  # AI operating system (governance); not imported by src
├── pyproject.toml       # package, dependency, and tool configuration
├── uv.lock              # pinned dependency lock (DEPENDENCY_LOCK_STATE source)
├── importlinter.ini     # enforces the §2.1 layer-direction contract
├── noxfile.py           # quality-gate task entry points
└── Makefile             # zero-input CLI aliases (CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §22)
```

`src/`, `configs/`, `tests/`, and `docs/` are version-controlled source.
`outputs/` and `models/` are runtime-resolved roots (§5): their concrete
paths never enter a domain identity, a scientific specification, a stage
fingerprint, an `ArtifactKey`, or a scientific manifest (`ART-05`). The
runtime-resolved `models/` root (external model/dataset input copies) is a
distinct concept from the version-controlled `configs/models/` directory
(`§3`); the former never contains YAML and the latter never contains a
dataset or checkpoint file.

## 2. `src/datp_core` layer tree

Six import layers, one allowed direction, exactly as
`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §1` defines. Every module below
belongs to exactly one layer and imports only what that layer permits.

```text
src/datp_core/
├── domain/               # pure types, invariants, value objects; no framework, no I/O
│   ├── experiments.py     # RunDefinition, ScientificExperimentDefinition, ScientificExperimentCell,
│   │                       #   ExperimentIdentity, ExperimentCellIdentity, DatasetAuditDefinition,
│   │                       #   OperationsDefinition, SeedCohortDefinition, ExperimentPrerequisite,
│   │                       #   EvidenceRole, RunRequirement, ClaimTier, CatalogueDisposition,
│   │                       #   PublicationRegimeLabel + derive_publication_regime,
│   │                       #   derive_artifact_namespace
│   ├── data.py             # DataDefinition, ClientConstruction union, SplitDefinition union,
│   │                       #   PreprocessingDefinition, CalibrationSubsetDefinition/Result,
│   │                       #   Dataset, SplitRole, DatasetVersion,
│   │                       #   SourceFieldType, SourceFieldRole, SourceFieldDescriptor,
│   │                       #   DatasetFieldSchema (field-level schema identity, DOMAIN §3.1),
│   │                       #   SourceInspectionDefinition, FeasibilityDefinition (dataset-owned audits),
│   │                       #   EligibilityDefinition's single owner value (minimum_calibration_sample_count)
│   ├── model.py             # ModelDefinition, AutoencoderArchitecture, ReconstructionObjective,
│   │                       #   TrainingProfile union, OptimizerDefinition, SchedulerDefinition,
│   │                       #   CheckpointProductionDefinition/Schedule, CheckpointSelectionPolicy,
│   │                       #   ParticipationStrategy, ModelPersonalizationStrategy,
│   │                       #   Training/ScoringBatchDefinition, classify_training_profile,
│   │                       #   effective_batch_size, rounds_max, PrimaryCheckpointRoundSelection,
│   │                       #   CheckpointArtifactSelection
│   ├── thresholding.py       # ThresholdConstruction union (8 members), CentralizedPooledThreshold,
│   │                       #   ThresholdConstructionResult, threshold value objects
│   ├── evaluation.py          # EvaluationDefinition, EvaluationSuiteDefinition union, EligibilityDefinition,
│   │                       #   AnalysisDefinition union (8 members), AnalysisMetadata,
│   │                       #   StatisticalProcedure union, metric ids/roles/direction,
│   │                       #   every evaluation/statistical result type (§6.5 of DOMAIN),
│   │                       #   TrafficRateEvidence, ClaimOutcome, absorption/temporal bands
│   ├── artifacts.py            # StageIdentity, ArtifactKey, ArtifactRef, ArtifactType, ArtifactScopeKey,
│   │                       #   ProvenanceRecord, ResolvedConfigurationSnapshot, ReuseDecision union,
│   │                       #   ResultFreezeManifest, PreSpecificationRecord, SuppressionRecord,
│   │                       #   FeasibilityRecord/FeasibilityStatus, manifests, ReuseImpact
│   ├── operations.py           # execution/runtime/planning value types that are pure domain:
│   │                       #   ExecutionMode, DevicePolicy, ResourceBudget, DeviceSpec, ParallelismSpec,
│   │                       #   SeedPlan/SeedDerivationRule, ResolvedRuntimePlan, ResolvedBatchExecutionProfile,
│   │                       #   RunStatus/lifecycle states, FailureDisposition, ScientificReadinessResult
│   ├── reporting.py             # ReportDefinition, ReportArtifactSpec, SemanticColumn, TableDefinition,
│   │                       #   FigureDefinition, RowProjectionRule (derived), DeterministicOrdering,
│   │                       #   MissingValuePolicy, TableType/FigureType, ReportArtifactType,
│   │                       #   SerializationFormat, RenderingStatus, TableProvenance/FigureProvenance
│   ├── mathematics.py            # canonical Decimal quantization, blake3 fingerprint tuple helpers,
│   │                       #   pure numeric routines (cv, pooled variance, Cliff's delta) with no framework
│   ├── identifiers.py             # ExperimentSlug, EvaluationLabel, AnalysisLabel, DatasetAuditSlug,
│   │                       #   ClientId, DeviceFamilyId, ClusterId, Seed, RoundNumber, RelativeArtifactPath,
│   │                       #   ContentHash, StageFingerprint, ConfigurationFingerprint, registries (§2.4)
│   └── errors.py                   # DatpCoreError and every typed error family (ENGINEERING §6)
├── application/           # use cases and ports over domain; no framework, no config, no cli
│   ├── ports/              # Protocol definitions only, one module per boundary family (§2.2)
│   │   ├── data.py          #   DatasetSourceInspector, ClientPartitioner, SplitDefinitionBuilder,
│   │   │                    #     PreprocessorFitter, ProcessedSplitMaterializer
│   │   ├── training.py       #   ModelTrainingBackend, ScoreGenerator, ThresholdConstructor
│   │   ├── statistics.py      #   StatisticalProcedureBackend
│   │   ├── persistence.py     #   ArtifactStore, CheckpointStore, ManifestStore, ArtifactLockProvider
│   │   ├── runtime.py          #   HardwareInspector, EventSink
│   │   └── reporting.py         #   ReportRenderer
│   ├── configuration/      # ResolveConfigurationRequest handling contract consumed from config output;
│   │                       #   persists RESOLVED_CONFIGURATION snapshots through ArtifactStore
│   ├── planning/           # ExperimentPlanner, ArtifactReuseGate, AnchorEquivalenceGate,
│   │                       #   StageRunnerRegistry consumption, DAG construction, deduplication
│   ├── stages/            # one module per PipelineStage member (PIPELINE §2); each owns only its computation
│   ├── runtime/            # ExecutionPreflight, PlanExecutor, run/stage lifecycle
│   ├── evaluation/         # evaluate_client_operating_points and confusion/fleet derivation use cases
│   ├── statistics/         # estimate_paired_threshold_effect, anchor-equivalence use case
│   └── reporting/          # freeze (RESULT_FREEZE), table/figure/wording projection, provenance tracing
├── config/               # boundary parsing, mapping, sweep expansion; imports domain only
│   ├── schemas/           # Pydantic boundary models, one per configs/ file family (§3.2)
│   ├── mapping/           # boundary-model → frozen domain mapping, one per schema family
│   └── compose.py         # load → validate → resolve refs → expand family/sweeps → build domain → validate
├── infrastructure/       # framework adapters implementing application ports; imports application, domain
│   ├── data/              # dataset source inspection, partitioning, splitting, preprocessing, materialization
│   ├── training/          # model training and reconstruction-scoring backends (Torch/Flower confined here)
│   ├── thresholding/      # ThresholdConstructor implementations per variant
│   ├── statistics/        # StatisticalProcedureBackend adapter (bootstrap/Wilcoxon/Spearman/regression)
│   ├── persistence/       # ArtifactStore/CheckpointStore/ManifestStore/ArtifactLockProvider,
│   │                       #   ArtifactPathResolver, BoundStorageRoot, atomic-commit engine (§5)
│   ├── runtime/           # HardwareInspector, process/GPU orchestration, spawn contexts
│   ├── reporting/         # ReportRenderer (Markdown/LaTeX/figure) adapters
│   └── telemetry/         # EventSink console/JSONL renderers
├── composition/          # the only layer that constructs adapters and binds ports
│   ├── root.py            # composition root: wires use cases, ports, adapters
│   └── registries.py       # explicit StageRunnerRegistry and port bindings (no import-time side effects)
└── cli/                  # thin entry points; imports composition and boundary result/error types only
    ├── main.py            # datp-core entry point
    └── commands/          # experiment and dataset-audit verb handlers (§3.6)
```

The indentation comments above name the primary public types each module
owns; the authoritative type contract for each remains its owning
architecture document. A module is a directory (package) rather than a single
file only when its type family is large enough that one file would exceed the
maximum-responsibility guideline (§6); the choice never changes the module's
layer, allowed imports, or public surface. `domain/model.py` and
`application/ports/training.py`/`infrastructure/training/` are the renamed
homes of what a prior draft of this package called `detection.py` and
`detectors/`/`detection/`: the roadmap's own vocabulary is "model" and
"training profile," never "detector" (`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md
§2`).

### 2.1 Layer import matrix

Enforced mechanically by `importlinter.ini`; a violation fails the
architecture test suite (`tests/architecture/test_dependency_rules.py`).

| Layer | May import | Must not import |
|---|---|---|
| `domain` | standard library, other `domain` modules | Pydantic, PyYAML, NumPy, pandas, PyArrow, Torch, Flower, scikit-learn, Matplotlib, filesystem, CLI frameworks |
| `application` | `domain` | `config`, `infrastructure`, `cli`, any scientific/serialization framework |
| `config` | `domain`, Pydantic/PyYAML (boundary only) | `application`, `infrastructure`, `cli`, scientific computation |
| `infrastructure` | `application`, `domain`, its own frameworks | `config`, `cli` |
| `composition` | `domain`, `application`, `config`, `infrastructure` | direct framework use (delegates to `infrastructure`) |
| `cli` | `composition`, shared boundary result/error types | `infrastructure`, `config`, direct adapter construction |

There is **no** top-level `analysis/` layer. Framework-free table, figure,
and wording *specifications* live in `domain/reporting.py` (types) and
`application/reporting/` (projection use cases); *rendering* adapters live in
`infrastructure/reporting/` (`ARCH-05`). Any physically present top-level
`src/datp_core/analysis/` package is superseded scaffolding to be folded into
these homes; this document is authoritative over the earlier conceptual tree
snippet in `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §9`.

### 2.2 Ports placement

`application/ports/` contains only `Protocol` definitions, grouped by
boundary family (data, training, statistics, persistence, runtime,
reporting). A port exists only for a genuine framework or hardware boundary
or a genuinely interchangeable backend
(`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §7.2`); a deterministic domain
calculation (Cliff's delta, `cv_fpr`, threshold arithmetic) is a
`domain`/`application` function and never gains a port. No `ArtifactRepository`
god-interface exists; persistence is four non-overlapping ports.

### 2.3 Stage modules

`application/stages/` holds exactly one module per `PipelineStage` member
(`PIPELINE_EXECUTION_AND_ARTIFACTS.md §2`). Each module implements the
`ExperimentStage` protocol (`is_applicable`, `build_identity`, `execute`)
over already-catalogued domain types and delegates all framework work to an
injected port. A stage module never constructs an adapter, resolves a path,
declares its own parallel identity/manifest family, or branches on another
stage's `PipelineStage` name.

### 2.4 Open identifiers versus enums

`domain/identifiers.py` owns the open, validated identifier types plus their
registries for vocabularies expected to grow — `Dataset` IDs, experiment
slugs, dataset-audit check names, model names, training-profile names,
execution-profile names. Adding one such value is a registry entry, never a
central-enum edit (`ENGINEERING §9` extension proofs 1 and 6). Genuinely
closed, stable vocabularies remain `enum`/`StrEnum` members in their owning
module (`SplitRole`, `ExecutionMode`, `ArtifactType`, `EvidenceRole`, …);
`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §14` is the authoritative enum
disposition catalogue.

## 3. `configs/` catalogue

Four boundary owners — one per real dataset, one for the model family, one
per experiment family, and one for every execution profile
(`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §§1–2`). Every authored document
carries `schema_version` and contains no YAML anchor, merge key, implicit
inheritance, or hidden default.

```text
configs/
├── datasets/
│   ├── nbaiot.yaml           # PhysicalDeviceClients + DirichletPartitionedClients setups; source audits
│   ├── ciciot2023.yaml       # DatasetFilePseudoClients setup (boundary role only); feature-count audit
│   └── edge_iiotset.yaml     # ExternalDeviceOrGroupClients (device/group) + chronological setups; audits
│
├── models/
│   └── autoencoder.yaml      # architecture, objective, optimizer, checkpointing; every named training profile
│
├── experiments/
│   ├── anchor.yaml                    # anchor_reproduction
│   ├── threshold_scope.yaml           # confirmatory_threshold_scope_effect + its two Tier-2 rule-outs
│   ├── heterogeneity.yaml             # controlled_heterogeneity_response
│   ├── calibration_mechanisms.yaml    # cluster_mechanism, calibration_window_size_stability,
│   │                                  #   local_global_threshold_shrinkage, conformal_local_threshold_coverage
│   ├── external_validation.yaml       # external_device_dataset_validation, chronological_recalibration_evaluation
│   ├── training_stress_tests.yaml     # fedprox_aggregation_stress_test, model_personalization_absorption_test
│   └── references_and_boundaries.yaml # centralized_pooled_reference, federated_summary_comparator,
│                                       #   file_pseudo_client_applicability_boundary
│
└── execution.yaml            # every named execution profile (scientific, print_grade, development,
                               #   smoke, dataset_audit, test_smoke) in one file
```

No `dataset_audits/`, `data_sources/`, `detectors/`, `protocols/`,
`runtime/`, or `reporting/` directory exists anywhere in this tree
(`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §1.1` records exactly where each
prior responsibility moved). This tree is identical, file for file, to the
one in `CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §1`; a discrepancy between
the two is a documentation defect, not an authorized second layout.

### 3.1 `configs/datasets/`

One document per real dataset — never per client-construction setup, and
never a separate audit root. Each document owns its own `audits` list
(source inspection and feasibility checks, `CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md
§2.1`), a `setups` map of every authorized client-construction variant for
that dataset, its split definition, its preprocessing, and its one
`eligibility.minimum_calibration_sample_count` value. `ciciot2023.yaml` is
explicitly boundary-role only (`SCIENTIFIC_FOUNDATION.md §5`); its single
`file_pseudo_clients` setup never generalizes beyond
`file_pseudo_client_applicability_boundary`. `edge_iiotset.yaml`'s
`external_device`/`external_group` setups are authored only after the
`client_granularity_feasibility` check closes, and its `chronological` setup
only after `timestamp_semantics_verification` closes
(`SCIENTIFIC_FOUNDATION.md §5.1`). Worked examples:
`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §11`.

### 3.2 `configs/models/`

One document, `autoencoder.yaml` — the only model family this design
authorizes. It owns architecture, reconstruction objective, optimizer,
checkpoint schedule, precision, determinism, and training-batch definition
exactly once, plus a `training_profiles` map naming every authorized
variant: `federated_averaging` (core ladder), `federated_averaging_personalized`
(the one authorized personalization comparator, `SCI-07`),
`federated_proximal` (the FedProx µ-grid stress test, matched to
`federated_averaging` in every non-strategy field), and `centralized_pooled`
(B0, its own identity chain, never fused with a federated artifact,
`ANCHOR-04`). Adding a genuinely new model family — a different
architecture, not a new training profile of the autoencoder — is a new
`configs/models/<name>.yaml` document; it is never required merely to add a
training profile of the existing family. Worked example:
`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §12`.

### 3.3 `configs/experiments/`

Seven family documents, each an `experiments` list of independently
resolvable entries; the complete family-to-slug mapping and each entry's
identity-bearing fields are given in
`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §§9–10, 16`. No standalone
experiment root exists for an item this package classifies as an attached
analysis (`SCIENTIFIC_FOUNDATION.md §7.4`); the cluster mechanism and
federated-summary-comparator families are each a single merged experiment
entry within their family document, not several sibling entries. A slug
matching a rejected or out-of-scope entry
(`SCIENTIFIC_FOUNDATION.md §7.6`) is refused at resolution and appears in no
family document.

### 3.4 `configs/execution.yaml`

One file, a `profiles` map keyed by profile name. Every mode requires a
complete explicit profile; `development` and `smoke` use explicit reduced
values and are non-citable by mode, never an automatic reduction of
`scientific` (`EXEC-02`). Worked example:
`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §13`.

Ownership boundaries are fixed by
`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §2`: a dataset document owns
dataset identity/construction/split/preprocessing/eligibility and never
execution limits, model settings, thresholds, metrics, or report formats;
`models/autoencoder.yaml` owns model definition only (eligibility is
dataset-owned, never re-authored here); `execution.yaml` owns execution
only; an experiment entry's inline `report` owns presentation only and
never a scientific value. A reduced smoke profile is a named entry in
`execution.yaml`, never a runtime backoff (`EXEC-02`).
`models/autoencoder.yaml`'s `federated_averaging_personalized` training
profile remains a genuine blocker until the comparator and its
hyperparameters are documented (`ENGINEERING §7`).

## 4. `tests/` tree

The level structure is fixed by `ENGINEERING_DECISIONS_AND_CONFORMANCE.md
§8`; this is its physical layout. No test writes to a scientific output root;
every test resolves storage beneath an isolated sandbox
(`ArtifactNamespace.TEST_SANDBOX`).

```text
tests/
├── unit/
│   ├── domain/           # invariants: benign-only calibration, delta orientation, AUROC-control,
│   │                      #   canonical-K derivation, eligibility, non-finite rejection
│   ├── application/       # use-case behavior with typed test doubles
│   ├── config/           # schema→domain mapping; missing/extra-field failure; no-hidden-default;
│   │                      #   experiment-family expansion (one document → many independent entries);
│   │                      #   DatasetFieldSchema drift detection (renamed/reordered/added source column)
│   └── reporting/        # framework-free specification construction (was analysis/)
├── property/             # value-object ranges/finiteness; cv_fpr; pooled variance; fpr_target = 1 − q;
│                          #   Cliff's-delta antisymmetry and bounds
├── contract/             # every infrastructure adapter against its port's shared contract suite
├── integration/
│   ├── data/              # chunked-vs-reference equivalence
│   ├── training/         # checkpoint selection and reuse across the ladder and B0
│   ├── persistence/      # atomic commit, bundle rejection, result-freeze/provenance closure
│   ├── reporting/        # trace-refusal and rendering
│   └── cuda/             # CUDA refusal/no-fallback/spawn-context; sequential-vs-parallel equivalence
├── architecture/         # test_dependency_rules.py, test_framework_confinement.py,
│                          #   test_no_forbidden_module_names.py, test_no_module_side_effects.py,
│                          #   test_no_cycles.py
├── system/
│   ├── synthetic/        # reduced synthetic end-to-end run of the full stage sequence
│   └── scientific_smoke/  # confirmatory BCa rule and failure behavior on a small real subsample
└── golden/               # cluster-assignment/adjusted-Rand snapshots; manifest/provenance regression
```

The metamorphic and extension tests enumerated in `ENGINEERING §§8.1, 9`
(threshold-only change preserves score keys, report-only change preserves
scientific artifacts, a new stage requires no executor change, a new dataset
requires no threshold/metric change, a new experiment requires no planner
branch, no forbidden module name, no framework object in a domain/application
contract, no import cycle) live under `unit/`, `architecture/`, and
`integration/` at the level matching what each asserts.

## 5. Output and storage roots

`outputs/` and `models/` are runtime-resolved. A concrete path is produced
only inside `infrastructure/persistence` by `ArtifactPathResolver`, from a
typed `ArtifactKey`/`ArtifactScopeKey` and a `BoundStorageRoot`; it never
enters a domain identity, scientific specification, stage fingerprint,
artifact key, or scientific manifest (`ART-05`,
`PIPELINE_EXECUTION_AND_ARTIFACTS.md §8`).

| Root concept | `StorageRootKind` / `ArtifactNamespace` | Holds | Enters scientific identity |
|---|---|---|---|
| Scientific artifact store | derived from `evidence_role` (anchor vs complete-study namespace, `ANCHOR-05`) | content-addressed, Git-object-sharded artifacts (manifests, checkpoints, score sets, thresholds, metrics, statistics, freezes) | never (path); the `content_hash` does |
| Reports | report-level scope | rendered tables, figures, wording | never |
| Resolved configuration | run-level scope | `RESOLVED_CONFIGURATION` snapshots | the fingerprint does; the path never |
| Recovery state | `RECOVERY` | resume-only checkpoints; distinct kind/root/namespace from scientific checkpoints (`ART-04`) | never; can never be scientific evidence |
| Cache / staging | `CACHE` / `STAGING` | same-filesystem staging for atomic replace | never |
| Test sandbox | `TEST_SANDBOX` | all test output | never |
| Models / external inputs | `models/` | immutable external dataset copies and any external model input; referenced as `RAW_DATASET_REF` | the reference/hash does; the path never |

An atomic single-file artifact is staged, flushed, hash-verified, replaced
at its final path, then manifested; a multi-file bundle is reader-visible
only after every member is verified and a commit marker is written
(`ART-03`). Identical content deduplicates by construction.

## 6. Naming and responsibility conventions

- **No generic-name modules.** No module named `utils`, `common`, `base`,
  `manager`, `helpers`, `misc`, `shared`, `requests`, or `results`; no class
  named `Manager`, `Handler`, `Processor`, `Context`, `Payload`, `Data`,
  `Item`, or `Entity` (`NAME-06`). `tests/architecture/test_no_forbidden_module_names.py`
  enforces this over `src/datp_core`.
- **No letter/roadmap-code identifiers.** No `B1`–`B4`, `A`/`B-a`/`C`/`D`, or
  roadmap experiment code (`E-C1`, …) is a module name, class name, filename,
  configuration key, discriminator, method name, or control-flow value; each
  survives only as a `roadmap_reference` metadata field (`NAME-01`, `NAME-03`,
  `NAME-04`).
- **Semantic module names.** A module is named for the concept it owns
  (`thresholding.py`, checkpoint-bearing `model.py`), readable without
  opening another file. "Detector" is never used as a module, type, or
  configuration-directory name; the roadmap's own vocabulary — "model" and
  "training profile" — is used throughout.
- **Maximum responsibility.** A module owns one coherent type family or one
  boundary. When a family grows past roughly a few hundred lines or begins
  serving two distinct questions, it splits along the concept boundary (a
  package with sibling modules), never into a `utils` bucket. A dataclass is
  admitted only under `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §5`.
- **No import-time side effects.** Module import is pure (`test_no_module_side_effects.py`);
  registries are assembled explicitly at the composition root — no decorator
  self-registration, reflection, package scanning, or global mutable locator
  (`PIPE-01`, `PIPELINE_EXECUTION_AND_ARTIFACTS.md §4`).
- **Framework confinement.** NumPy, pandas, PyArrow, Torch (`nn.Module`,
  tensors, state dicts), Flower, scikit-learn, and Matplotlib appear only in
  `infrastructure`; they never cross into a `domain` or `application` contract
  (`test_framework_confinement.py`, `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §8`).

## 7. Placement rules for new work

Each rule is the physical counterpart of an extension proof in
`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §9`; none requires an optional
field on every existing dataclass, an edit to every experiment, a new planner
or executor branch, a replacement identity system, or a compatibility shim.

| New thing | Files touched | Never touched |
|---|---|---|
| **Dataset** | `Dataset`/registry entry in `domain/identifiers.py`; a new `configs/datasets/<name>.yaml` document (audits, setups, split, preprocessing, eligibility, and its `SOURCE_INSPECTION`-derived `DatasetFieldSchema` all traced to this one file); a source-inspector/partitioner adapter in `infrastructure/data/`; one binding in `composition/registries.py`; contract + memory-equivalence + schema-drift-detection tests | any threshold, metric, evaluation, reporting module, `models/autoencoder.yaml`, or any `configs/experiments/` family |
| **Client construction (dataset setup)** | a `ClientConstruction` variant in `domain/data.py`; its schema arm in `config/schemas/data.py` + mapping; its `infrastructure/data/` implementation; one binding; one new `setups` entry on the owning dataset document | any experiment file, any letter-based label |
| **Threshold policy** | a `ThresholdConstruction` variant in `domain/thresholding.py`; a discriminated schema arm carrying only its own fields; an `infrastructure/thresholding/` implementation; one registry line | score-generation code (scores are reused via preserved keys) |
| **Training profile of the existing model family** | one new entry in `models/autoencoder.yaml`'s `training_profiles` map; a `TrainingProfile` variant in `domain/model.py` if it introduces a genuinely new `kind` | a new `configs/models/` document, any dataset, threshold, or experiment file |
| **New model family** | a new `configs/models/<name>.yaml` document; its architecture/objective/optimizer schema arms if genuinely distinct | any existing experiment referencing `autoencoder` |
| **Metric** | a `MetricId` member in its family + `MetricSpec` + typed calculator in `domain/evaluation.py`; reporting metadata | any renderer per-metric; any threshold artifact |
| **Pipeline stage** | a module in `application/stages/`; an optional config variant; one line in `StageRunnerRegistry` | the executor, planner branching, persistence, recovery, logging, or any existing stage (`PIPE-01`) |
| **Experiment** | one new entry appended to the `configs/experiments/` family document matching its scientific role, referencing existing dataset/setup and model/training-profile identities; a Make-target family | any code; any new planner or executor branch; any other family document |
| **Report** | one `ReportDefinition` (`domain/reporting.py` type) inlined on the producing experiment entry, consuming a frozen result | any recomputation of a scientific value; any `configs/reporting/` document (none exists) |
| **Run family** (future) | a new `RunDefinition` variant + its planner applicability; new stage `is_applicable` returns | any weakening of `ScientificExperimentDefinition` or `DatasetAuditDefinition` |

A future research direction the roadmap names but excludes today (dynamic
thresholding, streaming drift, poisoning, Byzantine-robust conformal,
fleet-scale validation) reuses these same seams — a typed variant, a stage
contract, a scope variant, a registry binding — and requires no
repository-wide redesign (`SCIENTIFIC_FOUNDATION.md §7.6`,
`ENGINEERING §9`). It is added only when authorized, never scaffolded ahead
of use.

## 8. Conceptual versus runtime-resolved paths

- **Conceptual, version-controlled, identity-neutral:** every path under
  `src/`, `configs/`, `tests/`, `docs/`. These are authored and reviewed;
  a scientific change is an edited `configs/` document producing a new
  resolved snapshot (`CFG-09`).
- **Runtime-resolved, never in identity:** every path under `outputs/` and
  `models/`. These are produced by `ArtifactPathResolver` from a key and a
  bound root and are confined to `infrastructure/persistence`; the domain and
  application never construct one, and a resolution escaping its bound root is
  a typed `PathResolutionError` (`ART-05`, `ENGINEERING §6`).

No path of either kind ever appears in a stage fingerprint, an `ArtifactKey`,
or a scientific manifest; lineage is carried by `content_hash` and typed
identity alone.

## 9. Per-module responsibility matrix

For every module: its single responsibility, layer, the concrete types it
owns (declared in `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §16`), whether it
may contain framework-specific code, its covering tests, and its extension
point. Allowed/forbidden imports follow the layer of the module exactly
(`§2.1`); only non-obvious boundaries are annotated.

| Module | Layer | Responsibility | Owns (representative) | Framework code | Tests | Extension point |
|---|---|---|---|---|---|---|
| `domain/experiments.py` | domain | run/experiment identity and aggregate roots | `RunDefinition`, `ScientificExperimentDefinition`, `ScientificExperimentCell`, `DatasetAuditDefinition`, `EvidenceRole`, `RunRequirement`, `CatalogueDisposition`, `derive_publication_regime`, `derive_artifact_namespace` | no | `unit/domain` | a new `RunDefinition` variant |
| `domain/data.py` | domain | dataset/client/split/preprocessing/audit/field-schema definitions | `DataDefinition`, `ClientConstruction`, `SplitDefinition`, `PreprocessingDefinition`, `Dataset`, `SplitRole`, `SourceInspectionDefinition`, `FeasibilityDefinition`, `DatasetFieldSchema`, `SourceFieldDescriptor` | no | `unit/domain`, benign-only test, schema-drift-detection test | a `ClientConstruction`/`SplitDefinition` variant; a new dataset-owned audit check; a new `SourceFieldRole` |
| `domain/model.py` | domain | model/training-profile/checkpoint definitions | `ModelDefinition`, `TrainingProfile`, `CheckpointSelectionPolicy`, `classify_training_profile` | no | `unit/domain` | a `TrainingProfile` variant |
| `domain/thresholding.py` | domain | threshold constructions | `ThresholdConstruction` (8), `CentralizedPooledThreshold` | no | `property`, threshold-only-change test | a `ThresholdConstruction` variant |
| `domain/evaluation.py` | domain | evaluation/analysis/metric/result types | `EvaluationDefinition`, `AnalysisDefinition`, `StatisticalProcedure`, every result type, `MetricId`/role/direction | no | `unit/domain`, `property` | a `MetricId`/family, an `AnalysisDefinition` variant |
| `domain/artifacts.py` | domain | identity, scope, provenance, records | `StageIdentity`, `ArtifactKey`, `ArtifactRef`, `ArtifactScopeKey`, `ArtifactType`, `ProvenanceRecord`, `ResultFreezeManifest`, `FeasibilityRecord` | no | `unit/domain`, `integration/persistence` | an `ArtifactScopeKey`/`ArtifactType` variant |
| `domain/operations.py` | domain | execution/planning/readiness value types | `ExecutionMode`, `ResourceBudget`, `ResolvedRuntimePlan`, `ScientificReadinessResult`, `RunStatus`, `FailureDisposition` | no | `unit/domain` | an `ExecutionMode`/lifecycle state |
| `domain/reporting.py` | domain | framework-free report specifications | `ReportDefinition`, `SemanticColumn`, `TableDefinition`, `FigureDefinition`, `TableType`, `FigureType` | no | `unit/reporting` | a `ReportDefinition`, `TableType`/`FigureType` |
| `domain/mathematics.py` | domain | canonical numerics; pure routines | `CanonicalDecimal`, fingerprint-tuple helpers, cv/pooled-variance/Cliff's-delta functions | no | `property` | a new pure statistic |
| `domain/identifiers.py` | domain | validated identifiers + registries | `ExperimentSlug`, `EvaluationLabel`, `ClientId`, `Seed`, `RoundNumber`, `ContentHash`, open registries | no | `unit/domain` | a registry entry (dataset/experiment/profile name) |
| `domain/errors.py` | domain | typed error taxonomy | `DatpCoreError` and every family (`ENGINEERING §6`) | no | `unit/domain` | a new error family |
| `application/ports/*` | application | port protocols | the seventeen ports (`DOMAIN §7.2`) | no | `contract/` | a new port for a genuine boundary |
| `application/configuration/` | application | resolved-config persistence use case | `resolve_configuration` result handling | no | `unit/application` | — |
| `application/planning/` | application | DAG planning, reuse gate, anchor gate | `ExperimentPlanner`, `ArtifactReuseGate`, `AnchorEquivalenceGate`, `StageRunnerRegistry` consumption | no | `unit/application`, `system/synthetic` | — (registry is composition-owned) |
| `application/stages/*` | application | one stage's computation | `ExperimentStage` implementations | no (delegates to ports) | `unit/application`, `integration/*` | a new stage module + registry line |
| `application/runtime/` | application | preflight, execution, lifecycle | `ExecutionPreflight`, `PlanExecutor`, lifecycle records | no | `integration/cuda`, `system/synthetic` | — |
| `application/evaluation/` | application | operating-point derivation | `evaluate_client_operating_points`, `ConfusionMatrixEvaluator` | no | `unit/application`, `property` | — |
| `application/statistics/` | application | analysis/anchor use cases | `estimate_paired_threshold_effect`, `verify_anchor_equivalence` | no | `unit/application`, `scientific_smoke` | — |
| `application/reporting/` | application | freeze, projection, tracing | `RESULT_FREEZE`, table/figure/wording projection, `TableFigureTracer` | no | `integration/reporting` | a projection for a new `ReportDefinition` |
| `config/schemas/*` | config | Pydantic boundary models | one schema per `configs/` file family (`data.py`, `model.py`, `experiment.py`, `execution.py`) | Pydantic/PyYAML (boundary only) | `unit/config` | a schema arm for a new variant |
| `config/mapping/*` | config | boundary→domain mapping | one mapper per schema family | no scientific compute | `unit/config` | a mapping for a new variant |
| `config/compose.py` | config | load→validate→resolve→expand family/sweeps→build | `ConfigurationResolutionResult` construction | Pydantic/PyYAML | `unit/config` | — (persists nothing) |
| `infrastructure/data/*` | infrastructure | dataset adapters | source inspector, partitioner, splitter, preprocessor, materializer | pandas/PyArrow | `contract/`, `integration/data` | an adapter for a new dataset |
| `infrastructure/training/*` | infrastructure | training/scoring backends | model training, score generation | Torch/Flower | `contract/`, `integration/training`, `integration/cuda` | an adapter for a new `TrainingProfile` |
| `infrastructure/thresholding/*` | infrastructure | threshold implementations | one per `ThresholdConstruction` variant | NumPy | `contract/`, `property` | an implementation for a new threshold |
| `infrastructure/statistics/*` | infrastructure | statistical backend | bootstrap/Wilcoxon/Spearman/regression adapter | SciPy | `contract/`, `property` | — (Cliff's delta is a vetted pure fn, not here) |
| `infrastructure/persistence/*` | infrastructure | stores, path resolver, atomic commit | `ArtifactStore`, `CheckpointStore`, `ManifestStore`, `ArtifactLockProvider`, `ArtifactPathResolver`, `BoundStorageRoot` | filesystem | `contract/`, `integration/persistence` | — (path resolution confined here, `ART-05`) |
| `infrastructure/runtime/*` | infrastructure | hardware, process/GPU orchestration | `HardwareInspector`, spawn contexts, GPU assignment | CUDA/multiprocessing | `integration/cuda` | — |
| `infrastructure/reporting/*` | infrastructure | renderers | `ReportRenderer` (Markdown/LaTeX/figure) | Matplotlib | `integration/reporting` | a renderer for a new `SerializationFormat` |
| `infrastructure/telemetry/*` | infrastructure | event rendering | `EventSink` console/JSONL | logging | `unit/application` (via double) | a new `LogEventKind` renderer |
| `composition/root.py` | composition | wire use cases + adapters | the composition root | constructs adapters only here | `system/synthetic` | — |
| `composition/registries.py` | composition | explicit registry assembly | `StageRunnerRegistry`, port bindings | no import-time side effects | `architecture/`, `system/synthetic` | one binding per new stage/adapter |
| `cli/main.py`, `cli/commands/*` | cli | verb entry points | `experiment`/`dataset-audit` verb handlers | no | `system/synthetic` | a new verb only if the lifecycle grows |

The two non-obvious boundaries: (1) statistical *specifications* and pure
statistics (Cliff's delta, `cv_fpr`) live in `domain`, while only the
interchangeable numeric backend (bootstrap resampling, SciPy calls) is an
`infrastructure` adapter behind `StatisticalProcedureBackend` — the split
keeps vetted pure math testable without a port and confines the framework
call; (2) report *specifications* live in `domain/reporting.py` and their
*projection* in `application/reporting/`, while only *rendering* is
`infrastructure/reporting/` — so a format change never reaches a scientific
type (`ARCH-05`).

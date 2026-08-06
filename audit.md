# DATP-Core Deep Architecture Audit — `origin/main`

**Repository:** `naslouby-salahe/datp-core`  
**Audited branch:** `main` (`origin/main`)  
**Audited commit:** `3a3c8f5bbe112e113f7349a527a3fbef13371d03`  
**Audit date:** 2026-08-06  
**Scope:** static source audit of every top-level package under `src/datp_core`, with focused inspection of the largest and highest-coupling modules.

## 1. Audit status and limitations

This report is based on the exact current GitHub `main` snapshot, not a local branch and not an older pull request.

The latest commit reports:

- 723 passing tests;
- one environment-dependent worker-count test failure;
- 13 passing import-linter contracts;
- seven remaining Pyright errors.

Those test and type-check results are commit-reported results. I did not independently execute the suite because this audit used the GitHub repository connector and no local checkout was available.

The repository has already undergone a substantial decomposition. The previous broad `protocols/models.py`, root `domain/values.py`, and many package-owned entries from `domain/enums.py` have been removed or redistributed. This audit therefore focuses on the architectural debt that remains after that migration.

## 2. Executive verdict

The repository is significantly cleaner than its previous architecture, but it is not yet at the target state described by its own architectural rules.

The primary remaining problem is no longer one giant monolithic package. It is **duplicated scientific and lifecycle logic spread across otherwise well-named packages**:

1. Bespoke workflows bypass the generic campaign engine.
2. Centralized evaluation duplicates the canonical evaluation package.
3. Artifact publication has duplicate result types and raw dictionary serialization.
4. Scientific coordinates and artifact identity are fragmented.
5. Value objects still intentionally accept primitives.
6. Dataset and preprocessing boundaries still contain raw strings, dictionaries, booleans, defaults, and positional construction.
7. Several large `models.py` files remain collection hubs instead of ownership-based contracts.
8. A current Ditto path appears internally inconsistent and should fail before training.

### Overall package health

| Package | Assessment | Priority |
|---|---|---:|
| `pipeline` | Largest remaining architectural and duplication risk | P0/P1 |
| `learning` | Strong concepts, but duplicated model legality and oversized contracts | P0/P1 |
| `evaluation` | Good canonical implementation; not consistently reused | P1 |
| `datasets` | Scientifically careful, but oversized cache/contracts and weak typed deserialization | P1 |
| `preprocessing` | Improved decomposition, but duplicated protocols and orchestration | P1 |
| `domain` | Strong nominal model set, but primitive compatibility weakens it | P1 |
| `protocols` | Correct home for locked values; experiment catalogue still primitive-heavy | P1/P2 |
| `anchor` | Strong validation, but `models.py` remains a broad hub | P2 |
| `thresholding` | Good method decomposition; shared primitives still leak | P2 |
| `calibration` | Cohesive, with raw client maps and forwarding wrappers | P2 |
| `analysis` | Generally cohesive; a few duplicated policy constants and publication concerns | P2 |
| `runtime` | Small, but hardcoded/import-time environment behavior is problematic | P1 |
| `cli` | Mostly legitimate composition; one cross-layer entry point | P2 |
| `reporting` | Small and cohesive; only minor boundary cleanup | P3 |

---

# 3. Highest-priority findings

## P0-1 — Ditto global coordinate construction contradicts its validator

### Files

- `src/datp_core/learning/federated/models.py`
- `src/datp_core/pipeline/workflows/personalization.py`

### Finding

`FederatedTrainingCoordinate` requires both `DITTO_GLOBAL_AUTOENCODER` and `DITTO_PERSONALIZED_AUTOENCODER` coordinates to carry a `DittoRegularization`.

The personalization workflow constructs:

```python
global_coordinate = FederatedTrainingCoordinate(
    ...
    model=TrainingModelId.DITTO_GLOBAL_AUTOENCODER,
    model_coefficient=None,
)
```

This contradicts `_require_model_coefficient`, which accepts only a `DittoRegularization` for either Ditto model identity.

### Impact

The personalized stress-test path should fail during coordinate construction before training starts. This is not merely architectural debt; it is a direct execution defect.

### Action

Use the same `DittoRegularization` for both peer coordinates and centralize creation through one factory:

```text
DittoTrainingCoordinates.create(
    population,
    training_seed,
    split_protocol,
    preprocessing_identity,
    regularization,
)
```

That factory should construct and validate the global/personalized pair together. Remove direct independent construction from workflows.

---

## P0-2 — Centralized metric logic duplicates the canonical evaluation implementation

### Files

- `src/datp_core/pipeline/decision/centralized.py`
- `src/datp_core/evaluation/client_metrics.py`
- `src/datp_core/evaluation/confusion.py`
- `src/datp_core/evaluation/population_metrics.py`
- `src/datp_core/evaluation/models.py`

### Finding

`pipeline/decision/centralized.py` is approximately 32 KB and owns all of the following:

- pooled threshold construction;
- threshold persistence and reload;
- confusion counts;
- FPR;
- TPR;
- balanced accuracy;
- binary macro-F1;
- AUROC;
- evaluation document conversion;
- evaluation publication.

The `evaluation` package already owns canonical confusion and metric semantics for federated evaluation. The centralized branch reimplements the same mathematical behavior with its own constants and record/document types.

### Impact

This is a high scientific-drift risk. A metric fix or undefined-metric policy change can be applied to federated evaluation without being applied to centralized evaluation, or vice versa.

### Action

Refactor centralized evaluation to use the same canonical components:

1. Convert pooled scores and the pooled threshold into the standard evaluation inputs.
2. Reuse `calculate_confusion_counts`.
3. Reuse `calculate_client_metrics` or introduce a neutral `calculate_binary_metrics`.
4. Reuse the existing `MetricAvailability` semantics.
5. Keep only centralized threshold construction and centralized evidence-role restrictions in the centralized decision module.

Delete the duplicate centralized metric formula implementation after parity tests prove identical behavior.

---

## P1-1 — Parallel orchestration paths remain

### Files

- `src/datp_core/pipeline/execution/engine.py`
- `src/datp_core/pipeline/workflows/confirmatory.py`
- `src/datp_core/pipeline/workflows/external.py`
- `src/datp_core/pipeline/workflows/personalization.py`
- `src/datp_core/pipeline/workflows/temporal.py`

### Finding

The confirmatory workflow uses the campaign engine, while personalization and temporal workflows manually execute preparation, preprocessing, training, checkpointing, scoring, threshold construction, evaluation, and analysis.

The bespoke workflows also hardcode:

- population identities;
- dataset identities;
- split protocols;
- preprocessing protocols;
- output roots;
- subdirectory names;
- `overwrite=False`;
- threshold method loops;
- score and analysis layouts.

### Impact

There are multiple effective orchestration systems. Fixes to the generic stage runner do not automatically apply to personalization and temporal execution. The bespoke paths are already showing divergent construction behavior, including the Ditto coordinate defect.

### Action

Create one execution route per experiment family through the campaign engine:

```text
ExperimentDeclaration
    -> resolved ExperimentCoordinate
    -> CampaignEntry
    -> PipelineStageRunner
```

Personalization and temporal behavior should be specialized by typed stage inputs and stage strategy selection, not by reimplementing the entire pipeline.

No workflow should call low-level training, scoring, thresholding, or evaluation functions directly when a pipeline stage service already exists.

---

## P1-2 — Artifact publication violates the repository's strongest boundary rules

### File

- `src/datp_core/pipeline/publication/service.py`

### Findings

1. Broad `except Exception` is used for cleanup.
2. `CompletionRecord` is manually converted to and from raw dictionaries.
3. `json.loads` payloads are indexed directly.
4. `build_completion_record` accepts `Checksum | str`.
5. `PublicationOutcome` and `ArtifactPublicationResult` contain the same fields.
6. `RelatedPublicationOutcome` and `RelatedArtifactPublicationResult` contain the same fields.
7. Completion marker names have defaults even when the artifact contract should be explicit.
8. The functional codec classes are pass-through wrappers around four callables.

### Impact

This layer is reused everywhere, so every weakness propagates to training, scoring, decisions, and evidence publication.

### Actions

- Make `CompletionRecord` a strict serialized model and use canonical model serialization.
- Accept only `Checksum`; remove string coercion.
- Merge duplicate publication result classes.
- Replace broad exception cleanup with a scoped transaction/context manager.
- Make the completion artifact identity explicit in each publication contract.
- Retain one typed codec abstraction, but remove duplicate protocol/result layers that add no behavior.
- Add publication contract tests for partial replace, interrupted writes, rebase, and malformed completion documents.

---

## P1-3 — Planning, feasibility, and coordinate identity remain fragmented

### Files

- `src/datp_core/pipeline/planning.py`
- `src/datp_core/pipeline/feasibility.py`
- `src/datp_core/pipeline/coordinates.py`
- `src/datp_core/pipeline/execution/layout.py`
- `src/datp_core/pipeline/publication/layout.py`

### Findings

`planning.py` owns:

- coordinate models;
- coordinate stable keys;
- execution route selection;
- plan expansion;
- plan digest generation;
- readiness-to-disposition conversion;
- external feasibility;
- temporal feasibility;
- attack-sensitive metric policy;
- training coefficient expansion;
- temporal-state expansion.

Meanwhile, `pipeline/feasibility.py` owns preflight and extension feasibility under the same broad term.

The declared `PipelineCoordinate` protocol is described as complete, but it omits identity fields required by persisted paths, including preprocessing identity and model coefficient.

`execution/layout.py` imports `CoordinateIdentitySegment` from `planning.py`, meaning filesystem identity depends on a planner implementation detail.

### Primitive and flag leakage

External/temporal feasibility requests contain multiple raw booleans, such as:

- grouped assignment available;
- required artifacts available;
- attack assignment claimed available;
- routed through confirmatory command.

### Actions

Split ownership without creating excessive files:

- `pipeline/planning.py`: plan expansion and digest only.
- `pipeline/feasibility.py`: all feasibility requests and decisions.
- `pipeline/coordinates.py`: complete coordinate model, identity segments, stable key, and exhaustive route.
- `pipeline/layout.py`: path codecs operating only on complete coordinates.

Replace boolean-heavy feasibility requests with typed capability/evidence objects.

The stable-key and plan-digest encoding should use canonical typed serialization instead of manually delimited strings.

---

## P1-4 — Value objects still permit primitive interoperability

### Files

- `src/datp_core/domain/values/base.py`
- `src/datp_core/domain/values/counts.py`
- `src/datp_core/domain/values/ratios.py`

### Finding

The value-object base intentionally supports:

- comparing a value object with raw `int` or `float`;
- adding raw integers to typed counts;
- comparison families that allow different classes to compare by their raw numeric values.

This makes `RowCount(10) == 10` and similar expressions possible.

### Impact

The repository has many nominal types, but their boundary is porous. A caller can silently mix scientific concepts and primitives, weakening the purpose of the type system.

Comparison families also allow semantically different values to compare because they share a family string.

### Action

Adopt strict nominal behavior:

- equality and ordering only against the same concrete type;
- explicit conversion methods for intentionally comparable concepts;
- no arithmetic with raw primitives;
- typed arithmetic result rules;
- no generic string-based `comparison_family`.

Examples:

```text
RowCount.plus(RowCount) -> RowCount
CalibrationSize.fits_within(RowCount) -> bool
ThresholdValue.difference(ThresholdValue) -> ThresholdDelta
```

Do not merge the semantic classes in `counts.py` or `ratios.py`. Their nominal distinction is valuable. Refactor the shared base instead.

Also make the Pydantic schema helpers public, typed, and owned by a boundary module rather than imported through underscored functions.

---

## P1-5 — Import-time runtime configuration is hardcoded and environment-dependent

### Files

- `src/datp_core/runtime/configuration.py`
- `src/datp_core/runtime/compute.py`

### Findings

`CANONICAL_RUNTIME` is constructed at import time with:

- `Path("data")`;
- `Path("outputs")`;
- `Path("results")`;
- CUDA device index `0`;
- `WorkerCount(cpu_count() or 1)`.

The current commit itself reports a worker-count test failure caused by environment dependence.

### Impact

The supposedly canonical runtime configuration changes according to the machine that imports the module. That is not deterministic protocol state.

### Action

Separate:

1. **Scientific runtime requirements** — CUDA required, deterministic mode, batching policy.
2. **Detected host resources** — CPU count, CUDA devices, names, versions.
3. **Execution configuration** — selected roots, worker count, CUDA index.

Build an explicit `RuntimeConfiguration` at the application composition root. Persist it in run provenance. Avoid import-time host detection.

Paths should be passed as a typed repository layout, not imported as global `DATA_ROOT` and `OUTPUTS_ROOT` throughout workflows.

---

## P1-6 — Duplicated scientific decision constants

### Files

- `src/datp_core/protocols/training.py`
- `src/datp_core/analysis/mechanisms/absorption.py`

### Finding

The same retention boundaries are declared twice:

- partial retention: `0.25`;
- full retention: `0.75`.

They use different names in protocol and analysis modules.

### Impact

A future edit can change the protocol without changing the analysis verdict logic.

### Action

Define one typed `ModelAbsorptionDecisionProtocol` in the protocols package and inject it into `decide_model_absorption`.

Analysis must never define scientific cutoffs.

---

# 4. Package-by-package audit

## 4.1 `analysis`

### What is good

- Statistical procedures are separated into inference and mechanism modules.
- Evidence roles and blocked/unavailable outcomes are explicit.
- The package generally avoids mixing analysis with model training or dataset preparation.

### Issues

1. `analysis/documents.py` combines:
   - analysis requests;
   - serialized result documents;
   - asset filenames;
   - publication result wrappers.
2. `AnalysisPublication[DocumentT]` is a generic wrapper around asset name, document, and digest, while publication lifecycle behavior lives elsewhere.
3. Model-absorption cutoffs are duplicated from protocol declarations.
4. Some result fields remain raw primitives, especially differences and correlation intermediates in individual modules.
5. The package's `documents.py` name obscures whether a class is an analysis result or a publication boundary model.

### Actions

- Keep pure analysis results in analysis modules.
- Move asset naming and persistence requests to `pipeline/decision/evidence.py` or an analysis publication adapter.
- Inject every scientific cutoff through a protocol object.
- Use explicit delta/effect value types where values have different semantics from ordinary metrics.
- Avoid adding another large analysis model hub; move each document model beside the analysis that creates it.

### Priority

P2.

---

## 4.2 `anchor`

### What is good

- Historical artifacts are treated as an explicit external boundary.
- Comparison strategies and discrepancy reasons are typed.
- The package records blocked and unavailable states instead of silently accepting missing evidence.

### Issues

1. `anchor/models.py` remains a 21 KB model hub containing:
   - historical boundary documents;
   - artifact file names;
   - tolerance strategies;
   - scientific coordinates;
   - references;
   - observations;
   - comparisons;
   - discrepancies;
   - dependency blockers;
   - reproduction and gate results.
2. It imports private `_str_enum_schema` from `domain.values.base`.
3. Several serialized fields are raw:
   - `generated_at_utc: str`;
   - `signed_difference: float | None`;
   - `relative_difference: float | None`.
4. `AnchorDiscrepancy` overlaps significantly with `AnchorMetricComparison`; it is mostly a publication projection.
5. Historical filename and directory-prefix enums are implementation details, not shared anchor-domain identities.

### Class ownership plan

Move existing classes into their owning modules instead of creating many new files:

- `reproduction.py`: historical boundary documents and artifact discovery.
- `comparison.py`: tolerance rules, metric reference/observation/comparison.
- `gate.py`: discrepancy, dependency blocker, gate decision/result.
- retain a small `models.py` only for truly shared anchor coordinates.

### Actions

- Replace private schema import with a public typed boundary helper.
- Introduce typed timestamp and metric-delta values.
- Serialize comparison/gate result models directly rather than constructing parallel publication projections.
- Make dataclasses keyword-only where multiple same-shaped enum/value fields exist.

### Priority

P2.

---

## 4.3 `calibration`

### What is good

- Calibration is benign-only and score/evaluation overlap checks are explicit.
- Eligibility, support, sampling, and service responsibilities are separated.
- Nested deterministic subsampling is validated.

### Issues

1. `calibration/service.py` uses raw dictionaries for:
   - evaluation row IDs by client;
   - references by client.
2. Client keys switch between `client_id: str` and `ClientIdentity`.
3. `_evaluation_stable_row_ids` returns `frozenset[str]`, losing `StableRowId`.
4. Request and result dataclasses are not keyword-only.
5. `EligibilityDecision` adds forwarding properties for `client`, `coordinate`, and support count without adding new behavior.
6. `_raise_first_violation` represents validation requirements as nested primitive tuples.

### Actions

- Use `ClientCollection[ClientIdentity, ...]` consistently.
- Preserve `StableRowId` through overlap checks.
- Make public requests/results keyword-only.
- Remove forwarding properties or replace the nested `support` field with the fields actually required by callers.
- Replace nested `(bool, message)` validation tuples with direct invariant functions or a typed violation object.

### Priority

P2.

---

## 4.4 `cli`

### What is good

- `cli/app.py` and `cli/execution.py` are valid composition roots.
- Small Typer command modules are not compatibility shims.
- CLI code is generally free of scientific computation.

### Issues

1. `cli/plan.py` calls both `pipeline.planning.expand_experiment_plan` and `pipeline.execution.engine.build_campaign`, crossing planning and execution internals.
2. Command adapters depend on global runtime roots through downstream services.
3. Some command modules are one-command files; this is acceptable only when they represent stable command families.

### Actions

- Introduce one application-facing planning service returning the plan and campaign summary.
- Keep root and family Typer composition modules.
- Do not merge all commands into one large file.
- Do not expose low-level stage services directly to CLI modules.

### Priority

P2.

---

## 4.5 `datasets`

### What is good

- Dataset-specific adapters are separated.
- Canonical schemas, inventories, exclusions, chronology evidence, and model-input eligibility are explicit.
- Materialization reuse checks bind source state and canonical artifacts.

### Issues

#### `canonical_cache.py`

This file is approximately 22 KB and combines:

- canonical path rules;
- schema serialization;
- manifest serialization;
- completion checks;
- source-state capture;
- reuse probing;
- deserialization;
- reconstruction of domain objects;
- validation report reconstruction;
- chronology reconstruction;
- file locking.

Several reconstruction helpers accept untyped parameters such as `report`, `inventory`, and `document`.

#### `contracts.py`

This file remains a broad 19 KB contract hub. It includes raw primitives and default-heavy chronology state:

- column names as `str`;
- source identity as `str | None`;
- booleans for monotonicity, temporal eligibility, and alignment;
- raw microsecond offsets as `int | None`;
- default `RowCount(0)` values;
- several positional dataclasses.

`ChronologyValidation` represents multiple mutually dependent facts as optional fields and booleans, allowing many invalid intermediate states.

#### `registry.py`

- Five `_construct_*_binding` functions are thin pass-through adapters.
- `DatasetPublication = MaterializedDataset[StrEnum, StrEnum]` erases dataset-specific role and reason types.
- `_DATASET_BINDINGS` is a raw dictionary registry.
- `_POPULATION_BINDINGS` is built with positional dataclass construction.
- `resolve_population` linearly scans a tuple even though the key is unique.

### Actions

Split `canonical_cache.py` into three existing-responsibility modules, not many tiny files:

1. reuse probe and source-state validation;
2. typed manifest codec;
3. domain reconstruction.

Refactor `ChronologyValidation` into a discriminated state:

```text
ChronologyUnavailable
ChronologyObserved
ChronologyAligned
```

Use typed column-name and source-identity values.

Make each dataset population constructor accept `PopulationConstructionRequest` directly, then bind it without thin `_construct_*_binding` adapters.

Preserve generic parameters in dataset bindings instead of erasing them to `StrEnum`.

Use keyword-only binding construction and one exhaustive keyed registry abstraction.

### Priority

P1.

---

## 4.6 `domain`

### What is good

- Cross-cutting identities are centralized.
- Counts, ratios, identifiers, paths, and checksums are now separated.
- `ClientCollection` and `ClientOwned` are useful replacements for raw client dictionaries.

### Issues

1. Primitive equality, ordering, and arithmetic are supported by the value-object base.
2. `comparison_family` is a string-based cross-type compatibility mechanism.
3. Pydantic schema hooks use untyped parameters and private helpers.
4. `domain/enums.py` still contains implementation-owned identities:
   - `RawDatasetDirectory`;
   - `PreprocessExecutionStatus`;
   - `TrainingHistoryColumn`;
   - `ScoreFrameColumn`;
   - `QuantileInterpolationSemantics`;
   - some artifact/serialization execution statuses.
5. `_NonEmptyString` validates only non-empty, not whitespace-only.
6. Several value subclasses are empty nominal classes. That is acceptable and should not be treated as boilerplate merely because their body is small.

### Actions

- Make the value-object system strictly nominal.
- Move package-owned enums to their implementation owners when import direction permits.
- When moving an enum would cause a cycle, define a domain concept rather than an implementation filename/column token.
- Expose typed public Pydantic adapters.
- Strengthen string values with trim/path/token-specific validation.
- Expand `ClientCollection` usage across calibration, workflows, preprocessing, and threshold assignments.

### Priority

P1.

---

## 4.7 `evaluation`

### What is good

- Undefined and unavailable metrics are not converted to zero.
- Per-client and population metrics are separated.
- Cohort construction and fixed-score evidence have dedicated subpackages.
- Metric calculation is generally explicit and scientifically readable.

### Issues

1. The canonical implementation is bypassed by centralized evaluation.
2. Raw arithmetic constants remain embedded in formulas.
3. `Sequence[ScoreValue]` and `Sequence[PopulationOutcomeLabel]` allow mutable and heterogeneous boundary inputs.
4. Some generic metric/status/document types overlap with centralized-specific equivalents.
5. Communication, conformal, threshold-estimation, and threshold-evidence modules each own related evidence records; ensure they use one availability/result vocabulary.

### Actions

- Make evaluation the only metric computation package for every branch.
- Introduce a neutral binary evaluation input/result contract used by centralized and federated execution.
- Delete centralized metric record/document classes after migration.
- Keep mathematical constants local when they are formula invariants, but name shared rank/F1 constants once if multiple modules need them.
- Prefer immutable typed sequences at stage boundaries.

### Priority

P1 because of duplicated centralized logic; otherwise P2.

---

## 4.8 `learning`

### What is good

- Autoencoder, centralized, and federated learning are separated.
- FedAvg, FedProx, and Ditto protocols are explicit.
- Checkpoint, provenance, communication, and training results are strongly validated.
- GPU requirements are explicit.

### Issues

1. The Ditto global coordinate inconsistency is a direct defect.
2. Model/coefficient legality is repeated in:
   - protocol resolution;
   - `FederatedTrainingCoordinate.__post_init__`;
   - global training validation.
3. `learning/federated/models.py` is approximately 27 KB and owns:
   - coordinates;
   - client training inputs;
   - updates;
   - communication;
   - round history;
   - snapshots;
   - checkpoint candidates;
   - checkpoint decisions;
   - training results;
   - outcomes.
4. A `learning/federated/checkpoints/` package already exists, but candidate/decision contracts remain in the parent model hub.
5. `global_training.py` is largely validation plus delegation.
6. `validate_federated_training_inputs(..., autoencoder.widths[0])` leaks architecture representation and raw positional meaning.
7. `AutoencoderProtocol.widths` is `tuple[int, ...]`, even though widths are core scientific architecture values.

### Class move and merge plan

- Move checkpoint candidate, decision, and snapshot contracts to `learning/federated/checkpoints/contracts.py`.
- Keep coordinate, client input, update, round result, and training result in a smaller training contract module.
- Replace repeated model/coefficient validation with `ResolvedFederatedTrainingProtocol`.
- Create one `DittoTrainingCoordinates` pair object.
- Introduce typed `LayerWidth`/`AutoencoderArchitecture`, including validated symmetric structure if that is scientifically required.

### Priority

P0/P1.

---

## 4.9 `pipeline`

### What is good

- The package now has recognizable subdomains: execution, preparation, training, scoring, decision, publication, and workflows.
- Import-linter contracts constrain many invalid dependency directions.
- Generic artifact publication and campaign execution abstractions exist.

### Issues

This is still the primary architectural hotspot.

#### Planning and feasibility

- `planning.py` mixes too many responsibilities.
- Feasibility names and responsibilities are split across two modules.
- attack-sensitive metrics are hardcoded in planning.
- training-model coefficient categories are hardcoded in planning.
- temporal split mapping is hardcoded in planning.
- plan digests are manually delimited.
- several decision dataclasses are positional.
- feasibility requests are boolean-heavy.

#### Execution and workflows

- generic campaign execution coexists with bespoke full workflows.
- workflows reconstruct coordinates by expanding plans repeatedly.
- temporal code selects the first completed method as fixed-score reference, making behavior partly dependent on method ordering.
- output roots and subdirectories are imported/hardcoded.
- overwrite behavior is hardcoded.
- `TemporalStateExecution` wraps only one `result` field and adds no behavior.
- personalization manually repeats cohort, scoring, thresholding, and metric work.

#### Scoring

- federated scoring has both:
  - a manual reusable/delete/generate lifecycle;
  - the generic `publish_artifact` lifecycle.
- centralized and federated score persistence share concepts but use partially different implementations.
- identity hashing uses its own manual length-prefix codec.

#### Decision

- centralized decision is a 32 KB threshold/evaluation/publication hub.
- federated decision and centralized decision do not share the same metric pipeline.
- result and document projections duplicate state.

#### Publication

- duplicate outcomes;
- raw dict JSON;
- broad catches;
- defaulted completion markers;
- pass-through codec layers.

#### Preparation

`preparation/populations.py` is approximately 24 KB. Population construction belongs in datasets; the pipeline module should resolve a declaration, call the dataset service, and publish the result. It should not accumulate dataset-specific split and artifact behavior.

### Actions

1. Enforce one campaign/stage execution path.
2. Consolidate complete coordinate identity.
3. Split planning from feasibility.
4. Make publication the only artifact lifecycle.
5. Delete the manual federated scoring lifecycle.
6. Reuse evaluation for centralized metrics.
7. Reduce workflows to experiment selection plus campaign invocation.
8. Move population-specific implementation to datasets.
9. Eliminate positional construction for scientific requests.
10. Eliminate hardcoded roots, overwrite flags, and path fragments from workflows.

### Priority

P0/P1.

---

## 4.10 `preprocessing`

### What is good

- The previous service hub has been decomposed.
- Client partitions, CICIoT specialization, persisted artifacts, validation, and fitted state are separated.
- Train-only fit and serialization constraints are strongly validated.

### Issues

1. `ScientificPreprocessingMethod` and `PreprocessingProtocol` duplicate almost the same fields.
2. `CentralizedFittedPreprocessingState` and `FederatedFittedPreprocessingState` differ only by client ownership.
3. `preprocess_federated` and `preprocess_published_federated` duplicate:
   - dataset resolution;
   - canonical completion check;
   - schema resolution;
   - feature-name resolution;
   - protocol construction;
   - context construction;
   - partitioning;
   - estimator fitting;
   - publication;
   - result construction.
4. `capture_timestamp_column` is `str | None`.
5. `PublishedFederatedPreprocessingRequest.capture_timestamp_column` defaults to `None`.
6. `_capture_timestamp_column_for` silently supplies the Edge timestamp column when omitted.
7. CICIoT client-local behavior is selected through an explicit dataset conditional in the generic service.
8. Preprocessing result models contain both absolute paths and protocol identity but no single immutable publication coordinate.

### Actions

- Merge method and protocol into one complete immutable declaration containing feature schema.
- Represent preprocessing ownership as a discriminated union:
  - pooled owner;
  - client owner.
- Extract a shared prepared-population context used by both source paths.
- Move dataset-specific preprocessing specialization into the dataset binding.
- Use a typed `CaptureTimestampColumn` and require it through the temporal protocol.
- Remove hidden timestamp fallback.
- Pass a complete preprocessing publication coordinate to path builders and persistence.

### Priority

P1.

---

## 4.11 `protocols`

### What is good

- This is the correct package for locked scientific values.
- Constants such as quantiles, cluster count, seeds, calibration sizes, rounds, and model grids are not inherently magic numbers when declared here with scientific names.
- Protocol objects use strong Pydantic validation.
- The recent removal of `protocols/models.py` was correct.

### Issues

1. `experiments.py` defines the catalogue as `_EXPERIMENT_COORDINATES`, a large tuple of primitive tuples, then converts it to typed declarations.
2. Repeated threshold-method tuple composition obscures the authoritative method sets.
3. Execution identity declarations duplicate parts of experiment declarations.
4. Readiness is derived through special-case logic rather than declared directly.
5. `AutoencoderProtocol.widths` is raw `tuple[int, ...]`.
6. Checkpoint candidate rounds and model coefficient grids are generated from primitive tuples.
7. Model-absorption cutoffs are duplicated in analysis.
8. `ClusterThresholdProtocol` compares `.value` rather than typed value objects in several checks.
9. Some protocol properties manufacture other value types through arithmetic on raw values, such as conformal significance.

### Actions

- Instantiate `ExperimentDeclaration` directly in the catalogue.
- Add explicit named protocol objects for reusable threshold method sets.
- Make execution identity a property or derived projection of an experiment declaration.
- Declare readiness explicitly.
- Type architecture widths and grids through sequence value objects.
- Keep locked scientific values in code; do not externalize them into YAML or environment defaults.
- Inject decision protocols into analysis rather than duplicating constants.

### Priority

P1/P2.

---

## 4.12 `reporting`

### What is good

- The package is small.
- It renders already-decided claims and does not perform statistical analysis.
- Atomic writing is delegated to runtime filesystem utilities.
- Tables and figures are separate.

### Issues

1. `export_markdown` constructs the whole document through mutable raw string lists.
2. Blocked claims are detected by checking `wording == ""`, which treats an empty string as a status signal.
3. Report layout and section titles are hardcoded in the exporter.
4. Analysis asset publication and reporting publication use separate document concepts.

### Actions

- Give `ClaimDecision` an explicit publication status rather than empty wording.
- Use a typed report section model before rendering.
- Keep formatting constants here; they are presentation choices, not scientific configuration.
- Do not move analysis calculations into reporting.

### Priority

P3.

---

## 4.13 `runtime`

### What is good

- Compute, determinism, filesystem, logging, workspace, and configuration are separated.
- CUDA unavailability fails explicitly.
- CUDA provenance is captured.

### Issues

1. Global runtime configuration is constructed at import.
2. Worker count changes with the host.
3. CUDA device index is hardcoded to zero.
4. repository roots are hardcoded.
5. `CudaProvenance` represents availability with a boolean plus nullable fields, allowing complex state combinations.
6. `resolve_cuda_device` calls availability/index resolution more than once.
7. global root constants are imported deeply by workflow modules.

### Actions

- Build runtime configuration once at the CLI/application root.
- Persist detected resources separately from selected configuration.
- Use a discriminated CUDA state:
  - unavailable;
  - available and selected.
- Resolve the CUDA device once and pass a typed compute context.
- Eliminate global path imports from scientific workflows.

### Priority

P1.

---

## 4.14 `thresholding`

### What is good

- Each threshold method has an owning module.
- Dispatch is exhaustive and uses `assert_never`.
- Population capability checks are explicit.
- Centralized threshold methods are rejected at the federated boundary.
- Group/family unavailability is represented explicitly.

### Issues

1. `ThresholdConstructionRequest.family_by_client` is a nested tuple of pairs instead of a typed assignment collection.
2. Shared validation uses:
   - `tuple[float, ...]` normalized weights;
   - raw `int` expected counts;
   - nested primitive expected pairs.
3. `mean_local_threshold` returns `float` rather than `ThresholdValue`.
4. Request dataclasses are positional.
5. Protocol creation is repeated in dispatch for several basic methods.
6. Group threshold validation infers whether a message concerns family or cluster by searching text in `match_message`.
7. Method results and publication projections should be checked for parallel structures.

### Actions

- Introduce `FamilyAssignment` and typed grouped assignment collections.
- Use `Ratio`/`NormalizedWeight` and typed counts.
- Return `ThresholdValue` or a specific aggregate threshold type.
- Make construction requests keyword-only.
- Resolve each method to a complete protocol before dispatch.
- Replace message-text branching with a typed group kind.
- Keep method modules separate; do not merge all threshold logic into dispatch.

### Priority

P2.

---

# 5. Thin wrappers, shims, aliases, and redirects

## Explicit compatibility shims

No active backward-compatibility shim, deprecated redirect module, or legacy import alias was found in the current `main` source tree. The latest commit also removed stale refactor migration machinery.

## Thin wrappers that should remain

These are meaningful composition boundaries:

- `cli/app.py`;
- `cli/execution.py`;
- pipeline training adapters that bind a request to the publication lifecycle;
- dataset materialization lifecycle;
- exhaustive threshold dispatch.

Removing them would push orchestration into callers or create duplicated lifecycle code.

## Thin wrappers or forwarding layers to remove or redesign

1. `TemporalStateExecution` — one field, no behavior.
2. Dataset `_construct_*_binding` pass-through functions.
3. `EligibilityDecision` forwarding properties.
4. Duplicate publication outcome/result classes.
5. Parallel result/document conversion classes where the result can be serialized directly.
6. Repeated protocol-binding validation in `global_training.py`.
7. Manual federated score materialization beside generic artifact publication.
8. Repeated coordinate reconstruction through `expand_experiment_plan`.

## Wrapper rule for the refactor

A wrapper should survive only when it owns at least one of:

- a stable public boundary;
- lifecycle management;
- validation not guaranteed by construction;
- adaptation between genuinely different representations;
- transactionality;
- polymorphic dispatch.

One-call forwarding alone is not enough.

---

# 6. Primitive leakage inventory

## Highest-impact primitive leaks

| Area | Current primitive | Replacement |
|---|---|---|
| value-object base | `int`/`float` comparison and arithmetic | strict nominal operations |
| calibration service | raw dictionaries and `frozenset[str]` | `ClientCollection`, `StableRowId` |
| threshold assignments | `tuple[float]`, raw `int`, pair tuples | `NormalizedWeight`, typed counts, assignment models |
| protocol architecture | `tuple[int, ...]` widths | `AutoencoderArchitecture` |
| preprocessing | timestamp column `str | None` | typed column identity |
| datasets | raw column/source strings | column/source value objects |
| chronology | booleans and optional raw offset | discriminated chronology states |
| publication | raw JSON dictionaries | strict serialized models |
| anchor | raw differences and timestamp string | delta and timestamp values |
| planning feasibility | multiple booleans | typed evidence/capability states |
| workflows | raw `float(value)` score construction | `ScoreValue` sequence |
| completion | `Checksum | str` | `Checksum` only |

## Important distinction

Not every numeric literal is a magic number:

- `0.5` in a mathematical midpoint formula;
- `2.0` in F1;
- one-based rank offsets;
- zero/one used in probability algebra.

Those are formula invariants and can remain local when named or obvious.

The problematic numbers are values that define scientific policy, artifact identity, execution behavior, or resource selection outside their protocol owner.

---

# 7. Hardcoded and magic-value audit

## Correctly located locked scientific values

The following are appropriately declared in `protocols`:

- canonical quantile;
- quantile grid;
- minimum calibration support;
- calibration sizes;
- shrinkage grid;
- conformal coverage;
- cluster fingerprint;
- cluster count;
- k-means initialization count;
- k-means maximum iterations;
- cluster random state;
- round candidates;
- maximum round;
- learning rate;
- batch size;
- model coefficient grids.

They should remain Python protocol declarations.

## Values requiring relocation or consolidation

1. Model absorption cutoffs duplicated in analysis.
2. runtime paths and CUDA index.
3. worker count detected at import.
4. `overwrite=False` in workflows.
5. path fragments such as `"canonical"`, `"scores"`, `"bounded_evidence"`.
6. completion marker defaults.
7. identity digest size and length-prefix size outside a shared codec.
8. attack-sensitive metric sets in planning rather than metric capability declarations.
9. temporal split mapping in planning rather than temporal protocol.
10. preprocessing method selected globally during plan expansion rather than resolved from the experiment/training declaration.

---

# 8. Recommended class merges and moves

| Current classes/modules | Recommended target |
|---|---|
| `PublicationOutcome` + `ArtifactPublicationResult` | one `PublicationResult[T]` |
| `RelatedPublicationOutcome` + `RelatedArtifactPublicationResult` | one `RelatedPublicationResult[T]` |
| `ScientificPreprocessingMethod` + `PreprocessingProtocol` | one complete `PreprocessingProtocol` |
| centralized metric record/document types | canonical evaluation metric result |
| `PooledThresholdResult` + `PooledThresholdDocument` | one serializable pooled threshold result |
| `CentralizedEvaluationResult` + `CentralizedEvaluationDocument` | one serializable evaluation result |
| `TemporalStateExecution` | remove; return `TemporalStateResult` |
| anchor tolerance/comparison models | move into `anchor/comparison.py` |
| anchor gate/discrepancy models | move into `anchor/gate.py` |
| historical anchor boundary models | move into `anchor/reproduction.py` |
| federated checkpoint models in `learning/federated/models.py` | `learning/federated/checkpoints/contracts.py` |
| coordinate sentinels/stable-key logic in planning | `pipeline/coordinates.py` |
| external/temporal feasibility models in planning | `pipeline/feasibility.py` |
| dataset-specific registry wrappers | direct request-based constructors |
| raw client maps | `ClientCollection` |
| Ditto peer coordinates | `DittoTrainingCoordinates` |

Classes that should **not** be merged:

- distinct count and ratio value objects;
- centralized and federated training protocols;
- individual threshold-method implementations;
- analysis mechanisms with different scientific meaning;
- CLI command-family composition modules.

---

# 9. Ordered implementation plan

## Step 1 — Fix current correctness risks

1. Fix the Ditto global coordinate coefficient.
2. Add a focused test constructing and running the Ditto coordinate pair.
3. Add a test proving both coordinates carry the same regularization.
4. Remove positional construction for `ThresholdConstructionRequest`.
5. Make high-risk scientific dataclasses keyword-only.

## Step 2 — Establish one orchestration path

1. Route personalization through the campaign engine.
2. Route temporal execution through the campaign engine.
3. Remove duplicated stage loops from workflows.
4. Resolve output layout and overwrite policy from execution configuration.
5. Make workflows select declarations and invoke application services only.

## Step 3 — Unify evaluation

1. Extract neutral binary metric calculation from evaluation.
2. Migrate centralized evaluation.
3. Prove metric parity with golden tests.
4. Delete centralized formula duplication and parallel metric documents.

## Step 4 — Repair publication infrastructure

1. Merge duplicate publication result types.
2. Replace raw completion dictionaries with a strict model.
3. Remove `Checksum | str`.
4. Remove broad catches through a transaction context manager.
5. Make completion artifact identities explicit.
6. Remove manual federated score lifecycle.

## Step 5 — Consolidate coordinate identity

1. Define the complete scientific/artifact coordinate.
2. Move stable key and path identity out of planning.
3. Use one canonical coordinate serializer for digests.
4. Make execution/publication layouts depend only on the complete coordinate.
5. Remove repeated plan expansion used only to recover coordinates.

## Step 6 — Tighten primitive boundaries

1. Make domain numeric objects strictly nominal.
2. Replace raw client dictionaries with `ClientCollection`.
3. Add assignment and normalized-weight types.
4. Type column identities and chronology offsets.
5. Type autoencoder widths.
6. Type threshold and metric deltas.

## Step 7 — Simplify protocols and preprocessing

1. Instantiate experiment declarations directly.
2. derive execution identity from declarations.
3. merge preprocessing method/protocol duplication.
4. centralize common preprocessing flow.
5. move dataset-specific preprocessing routing into dataset bindings.
6. remove timestamp fallback.

## Step 8 — Decompose remaining model hubs by ownership

1. move checkpoint contracts out of federated `models.py`;
2. move anchor models into comparison/gate/reproduction owners;
3. split dataset contracts only along stable ingestion/schema/chronology boundaries;
4. keep files substantial enough to avoid recreating tiny wrapper sprawl.

## Step 9 — Clean lower-priority wrappers and statuses

1. remove `TemporalStateExecution`;
2. remove dataset pass-through binding functions;
3. remove forwarding properties;
4. replace empty-string claim status;
5. move implementation-owned enums from domain where safe.

## Step 10 — Validate the final architecture

Run and fix:

- compile;
- Ruff check;
- Ruff format check;
- Pyright;
- import-linter;
- full pytest suite;
- scientific invariant tests;
- artifact interruption/reuse tests;
- centralized/federated metric parity tests;
- Ditto execution smoke test;
- temporal fixed-detector identity test.

---

# 10. Final conclusion

The current `main` branch has removed the most obvious historical hubs, and there is no strong evidence of active compatibility shims or redirect modules. The remaining debt is more consequential: duplicated execution paths, duplicated metric semantics, porous primitive boundaries, and fragmented scientific identity.

The highest-value refactor is not another broad file-tree reshuffle. It is to make four things authoritative and singular:

1. one complete experiment/artifact coordinate;
2. one pipeline execution lifecycle;
3. one artifact publication lifecycle;
4. one metric implementation.

Once those are singular, most of the remaining wrappers, duplicate document/result classes, hardcoded workflow choices, and defensive validations become unnecessary and can be removed safely.

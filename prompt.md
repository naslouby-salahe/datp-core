You are working in:

`/home/naslouby/Projects/datp-core`

The new `src/datp_core/learning/` implementation has already been manually extracted into the repository. Treat this new implementation as the forward architectural source of truth.

Your goal is to adapt the entire repository to the new learning package, remove the superseded implementation, update all configurations, resolvers, planners, composition roots, stage jobs, artifact contracts, tests, and dependent packages, and continue working until every acceptance criterion in this prompt is satisfied.

Do not redesign the new package around the old repository. Adapt the repository to the new package.

Do not commit or push.

# 1. Execution model

Maintain at least six parallel subagents whenever unresolved work remains and there are independent workstreams available.

Use parallel subagents for distinct areas such as:

1. Configuration models, YAML, and resolution.
2. Pipeline planning, contexts, jobs, and artifact contracts.
3. Learning-package integration and dependency cleanup.
4. Training and checkpoint tests.
5. Scoring and artifact tests.
6. Scientific invariants and reproducibility audits.
7. Static analysis and typing.
8. Repository-wide stale-reference and architecture audits.

Do not let parallel agents independently make conflicting changes to the same files. Assign explicit ownership boundaries.

The main agent must coordinate, inspect, integrate, test, and audit all changes. Do not merely delegate and report subagent summaries.

Use this continuous idempotent loop:

1. Read the source-of-truth documentation.
2. Inventory the current repository.
3. Build a dependency and migration plan.
4. Assign parallel workstreams.
5. Implement one coherent forward migration.
6. Run impacted validation.
7. Audit architecture and scientific semantics.
8. Replan from remaining failures.
9. Continue until every checklist item passes.
10. Run two final independent audit passes.

Do not stop after partial compilation or a small passing test subset.

# 2. Read before editing

Read all relevant repository instructions and scientific roadmaps before changing code, including:

`/home/naslouby/Projects/datp-core/CLAUDE.md`

`/home/naslouby/Projects/datp-core/docs/DATP-Core Simplification.md`

The complete `roadmap/` directory, especially:

`roadmap/00_ROADMAP_INDEX.md`

`roadmap/01_SCIENTIFIC_IDENTITY_AND_SCOPE.md`

`roadmap/02_CLAIMS_AND_DECISION_RULES.md`

`roadmap/03_EXPERIMENT_CATALOGUE.md`

`roadmap/04_EVALUATION_AND_REPORTING_PROTOCOL.md`

`roadmap/05_IMPLEMENTATION_ROADMAP.md`

`roadmap/06_REVIEWER_RISKS_AND_READINESS.md`

`roadmap/07_AUDIT_AND_DECISION_LOG.md`

`roadmap/SCIENTIFIC_SOURCE_OF_TRUTH.md`, when present.

Resolve apparent conflicts in favor of the locked scientific source of truth and the new forward architecture. Do not revive deprecated implementation details to satisfy an old test.

# 3. New authoritative learning tree

The required final package tree is:

```text
src/datp_core/learning/
├── __init__.py
├── contracts/
│   ├── enums.py
│   ├── model.py
│   ├── training.py
│   └── checkpoints.py
├── model/
│   ├── autoencoder.py
│   └── runtime.py
├── training/
│   ├── local.py
│   ├── engine.py
│   └── handler.py
├── checkpoints/
│   ├── codec.py
│   └── selection.py
└── scoring/
    ├── data.py
    ├── service.py
    └── handler.py
```

Do not add generic files such as:

`utils.py`

`helpers.py`

`common.py`

`types.py`

`models.py`

`compat.py`

`legacy.py`

`aliases.py`

Do not split the package further unless a demonstrated architectural defect makes it strictly necessary. Prefer deleting and merging boilerplate.

# 4. Delete the superseded files

Delete these obsolete files after all callers have been migrated:

```text
src/datp_core/learning/contracts/architecture.py
src/datp_core/learning/contracts/optimization.py
src/datp_core/learning/contracts/seeds.py

src/datp_core/learning/model/determinism.py
src/datp_core/learning/model/device.py

src/datp_core/learning/training/aggregation.py
src/datp_core/learning/training/federated.py
src/datp_core/learning/training/models.py
src/datp_core/learning/training/personalization.py

src/datp_core/learning/scoring/checkpoints.py
src/datp_core/learning/scoring/compute.py
src/datp_core/learning/scoring/models.py
```

Do not replace them with forwarding modules.

Do not leave import redirects, deprecated aliases, re-exports, wrappers, or compatibility functions.

The old modules must become invalid import paths.

# 5. Forward-only migration rule

The new learning package is authoritative.

Adapt every external caller to its contracts.

Do not modify the new package merely because an old caller, fixture, YAML field, test, or helper expects the previous API.

A change to the new package is allowed only when all of the following are true:

1. A concrete correctness, typing, scientific, or runtime defect is demonstrated.
2. The defect is reproduced with a focused test.
3. The fix preserves the new architecture.
4. The fix does not introduce compatibility behavior.
5. All callers are still migrated forward.
6. The reason is recorded in the working audit log.

Never revert to:

1. Optional algorithm-specific fields in one universal training model.
2. Free-form strings for closed domains.
3. Raw dictionaries as domain contracts.
4. Handler-owned numerical logic.
5. Feature inference by excluding metadata columns.
6. Temporary Parquet files.
7. Raw JSON dictionaries.
8. Independent duplicated FedAvg, FedProx, and Ditto loops.
9. Direct Safetensors mappings outside `checkpoints/codec.py`.
10. Silent CPU fallback.
11. Hidden population or output selection.
12. Hardcoded optimizer, loss, device, precision, batching, or initialization behavior.

# 6. Repository-wide migration scope

Find and adapt every reference to the former learning package.

Search the full repository, including source, tests, configuration, scripts, documentation, import contracts, dependency rules, and orchestration composition.

At minimum, update the following areas.

## 6.1 Configuration contracts and YAML resolution

Update configuration parsing and resolution to construct the new models:

1. `DenseAutoencoderProfile`
2. `AdamOptimizerProfile`
3. `BatchingProfile`
4. Discriminated `TrainingProfile`
5. `CheckpointProfile`
6. `LearningDataSchema`
7. `TorchRuntimeProfile`
8. `SeedDerivationProfile`

Every Pydantic model must use:

```python
ConfigDict(frozen=True, extra="forbid")
```

unless a stronger existing repository base model already guarantees the same behavior.

Do not add field defaults to make old YAML pass.

Update YAML explicitly.

Every scientific or runtime value must be:

1. Explicitly configured, or
2. Strictly derived from configured values and validated input artifacts.

Do not invent values.

Do not preserve duplicate descriptive fields that do not control runtime behavior.

Remove stale fields such as:

1. `bottleneck_dim` when derived from hidden dimensions.
2. Free-form implementation descriptions.
3. Duplicate checkpoint selection fields.
4. `effective_batch_size` as stored configuration.
5. `PersonalizationStrategy.NONE`.
6. Algorithm-irrelevant nullable fields.
7. Boolean flags that restate validation rules.
8. Prose-valued enums.
9. Fields declared but never executed.

Add the learning-data schema association required by the new handlers.

Each resolved materialization must explicitly reference a `learning_schema_id`.

Each learning schema must explicitly declare:

1. Ordered model feature columns.
2. Standard or temporal split profile.
3. Exact training split.
4. Exact calibration split.
5. Exact test split.
6. Future recalibration split for temporal profiles.

Do not infer feature columns from all non-metadata columns.

Do not infer split semantics from filenames or output names outside the typed binding.

## 6.2 Registries and composition

Update every registry type and composition root.

The model architecture, optimizer, batching, learning-data schema, training-profile, and checkpoint-profile registries must contain the new contract types.

Update handler construction to inject:

1. `FederatedTrainingEngine`
2. `ReconstructionScoringService`
3. `TorchRuntimeProfile`
4. `SeedDerivationProfile`
5. `LearningDataSchema` registry

Do not instantiate services repeatedly inside handlers.

Do not use service locators or global mutable registries.

Keep Dagster as the canonical orchestrator.

Do not replace Dagster with Hydra or another orchestration framework.

## 6.3 Pipeline contexts and planning

Make planning resolve all required values before execution.

A model-training or score-generation handler must never select:

1. The first population.
2. The first output.
3. A fallback checkpoint evidence input.
4. A default split.
5. A default training seed.
6. A default sweep parameter.
7. A feature schema by convention.

Update `TrainingContext` or replace it with correctly discriminated stage contexts when necessary.

The final context must explicitly carry:

1. Experiment identifier.
2. Population identifier.
3. Training seed.
4. Exactly one algorithm-specific resolved parameter when required.
5. No irrelevant sweep parameter.

Invalid examples that must fail during planning or contract validation:

1. FedAvg with a FedProx coefficient.
2. FedAvg with a Ditto weight.
3. FedProx without a coefficient.
4. FedProx with a Ditto weight.
5. Ditto without a personalization weight.
6. Ditto with a FedProx coefficient.
7. Training without an explicit population.
8. Training without an explicit seed.

Prefer discriminated contexts or typed parameter records over nullable-field combinations.

## 6.4 Artifact contracts

Update artifact kinds, stage inputs, outputs, manifests, and provenance.

Required model-training outputs:

For centralized, FedAvg, and FedProx:

```text
checkpoint
selection_evidence
```

For Ditto:

```text
checkpoint
personalized_checkpoint
selection_evidence
```

The output set must match the resolved algorithm exactly.

Update checkpoint evidence consumers to parse:

`CheckpointSelectionEvidence.model_validate_json(...)`

Do not use `json.loads`.

Do not access nested untyped dictionaries.

Selection evidence must preserve:

1. Selected round.
2. Captured rounds.
3. Complete round metrics.
4. Algorithm identity.
5. Resolved FedProx or Ditto coefficient where applicable.
6. Model initialization seed.
7. Dataloader shuffle seeds.
8. Worker seeds.
9. Global versus personalized loader branch.

Update artifact schemas and manifests so these values remain traceable.

Safetensors tensor mappings must exist only in:

`src/datp_core/learning/checkpoints/codec.py`

Do not access `state_dict()` mappings, Safetensors mappings, or raw checkpoint key construction elsewhere.

## 6.5 Checkpoint planning and authorization

Update checkpoint selection planning and evidence lookup.

The implemented selection kinds are:

1. First qualifying convergence.
2. Lowest calibration loss.
3. Fixed round.
4. Authorized FedAvg selection lookup.

Enforce:

1. All capture rounds are explicit.
2. Capture rounds are sorted and unique.
3. Capture rounds fall within the total round budget.
4. Every possible selected round is captured.
5. A fixed round must be captured.
6. Convergence selection must capture the final round.
7. Authorized lookup must read exact FedAvg evidence.
8. Test scores and test labels never participate.
9. Threshold metrics never participate.
10. Poisoned outcomes never participate.
11. A stress-test training profile may not independently tune against the core ladder’s threshold results.

Do not restore free-form checkpoint formulas.

If the existing historical anchor convergence semantics differ from the new implementation, verify the authoritative roadmap and conference protocol. Add an oracle test before changing the selection implementation. Preserve scientific behavior, not obsolete class shapes.

## 6.6 Training and scoring consumers

Update all callers to use:

1. In-memory Parquet bytes.
2. Explicit feature columns.
3. Explicit split membership.
4. Typed global or personalized scoring requests.
5. Typed checkpoint evidence.
6. Typed runtime initialization.
7. CUDA-required execution.
8. Batch-based validation and scoring.

Remove all temporary materialization files.

Do not reduce configured batch size.

Do not silently switch to CPU.

Do not load an entire client dataset onto the GPU for validation or scoring.

Do not reconstruct personalized models through dictionaries.

# 7. Coding rules

Apply these rules throughout all modified code, not only inside `learning`.

## 7.1 Closed domains

Use `StrEnum` for every closed domain.

Do not use free-form strings for:

1. Algorithms.
2. Model kinds.
3. Activation functions.
4. Output activations.
5. Normalization.
6. Loss objectives.
7. Loss reductions.
8. Precision.
9. Initialization.
10. Optimizers.
11. Schedulers.
12. Gradient clipping.
13. Batch policies.
14. Participation.
15. Checkpoint selection.
16. Checkpoint authorization.
17. Artifact kinds.
18. Score kinds.
19. Score orientation.
20. Loader branches.
21. Split-profile kinds.

Do not create enums for open-ended feature names, artifact paths, or client identifiers.

## 7.2 Domain data

No raw dictionaries in domain logic.

The only permitted tensor dictionary boundary is the framework-required implementation inside:

`src/datp_core/learning/checkpoints/codec.py`

Do not allow dictionaries in:

1. Public signatures.
2. Configuration models.
3. Runtime results.
4. Stage contexts.
5. Artifact schemas.
6. Test fixtures representing domain records.
7. Service requests.
8. Handler data flow.

Use:

1. Frozen Pydantic models for parsed configuration and artifacts.
2. Frozen slotted dataclasses for runtime PyTorch objects.
3. Tuples for immutable ordered collections.
4. Discriminated unions for mutually exclusive variants.
5. Existing identifier value objects where available.

Do not use `Any`.

Do not use `object` as a substitute for tensor typing.

Do not use production `assert`.

Do not introduce `type: ignore` merely to silence a design problem.

## 7.3 Defaults and hardcoding

Do not add convenience defaults.

Values such as the following must come from configuration or strict derivation:

1. Batch size.
2. Accumulation steps.
3. Local epochs.
4. Round count.
5. Optimizer parameters.
6. Precision.
7. CUDA device index.
8. Initialization.
9. Scheduler.
10. Gradient clipping.
11. Worker count.
12. Pin-memory behavior.
13. Checkpoint rounds.
14. Selection policy.
15. Seed namespaces.
16. Digest length.
17. Feature columns.
18. Split membership.

A literal is acceptable only when it is:

1. Serialization syntax.
2. A schema version.
3. A mathematical identity.
4. A closed enum value.
5. A locked protocol invariant already represented by a named contract.

Do not hide scientific choices in factories.

## 7.4 Clean code

Do not add explanatory AI-generated comments.

Keep only useful module, class, and public-contract docstrings.

Delete stale comments and descriptions that no longer match execution.

Do not create mass-edit scripts.

Perform intentional file-level edits.

Do not create repository debris, temporary reports, backup files, or duplicate copies.

Use the configured `.tmp` workspace for temporary audit data when needed, and remove it after completion.

# 8. Scientific non-negotiables

Preserve the DATP scientific identity.

## 8.1 Core causal ladder

For the core B1–B4 threshold-policy ladder:

1. FedAvg remains the canonical training algorithm.
2. Local epochs remain `E=1` where locked by the anchor protocol.
3. Participation remains full.
4. Aggregation remains weighted by local benign training sample count.
5. The autoencoder is trained once per seed and frozen.
6. The same selected checkpoint and score artifacts are reused across B1–B4.
7. Threshold-calibration scope is the sole causal-ladder variable.
8. Calibration is benign-only.
9. Attack rows never fit thresholds.
10. AUROC remains a model-quality control, not the thresholding verdict.
11. The primary concern remains per-client FPR disparity.

## 8.2 Stress-test separation

FedProx and Ditto remain external stress tests.

They must not:

1. Replace FedAvg in the core ladder.
2. Share a misleading causal label with B1–B4.
3. Tune checkpoint selection against threshold results.
4. Reuse personalized model states as if they were global FedAvg states.
5. Overwrite anchor artifacts.
6. Change the confirmatory claim.
7. Become defaults for experiments that specify FedAvg.
8. Contaminate conference-faithful reproduction.

True Ditto semantics must be preserved:

1. Global client branches participate in aggregation.
2. Personalized client states persist across rounds.
3. Personalized states are never aggregated.
4. Each personalized state remains bound to its client.
5. Personalized training uses its declared positive proximal weight.
6. Global and personalized dataloader seed namespaces remain distinct.
7. Personalized checkpoint keys cannot collide across clients or rounds.

True FedProx semantics must be preserved:

1. The proximal reference is the round-start global model.
2. The coefficient is strictly positive.
3. A zero coefficient is rejected, not treated as FedAvg.
4. The proximal penalty applies to trainable parameters.
5. Server aggregation remains sample-weighted.
6. FedProx is not represented through optional FedAvg fields.

## 8.3 Data isolation

Verify:

1. Model training uses benign training rows only.
2. Checkpoint selection uses authorized benign calibration rows only.
3. Calibration scoring contains no attack rows.
4. Test rows do not enter training.
5. Test labels do not enter checkpoint selection.
6. Test outcomes do not choose hyperparameters.
7. Temporal historical and future memberships are exact.
8. Row identities remain unique and stable.
9. Feature order is explicit and stable.
10. No score output is joined by row position without identity validation.

# 9. Required test migration

The old tests must adapt to the new architecture.

Do not modify the production code to satisfy tests that assert obsolete APIs.

Delete tests whose only purpose is backward compatibility.

Rewrite tests around behavior, contracts, and scientific invariants.

Use parallel test workstreams, but ensure one owner reviews the complete test architecture.

Required target coverage includes:

```text
tests/unit/learning/contracts/
tests/unit/learning/model/
tests/unit/learning/training/
tests/unit/learning/checkpoints/
tests/unit/learning/scoring/

tests/integration/learning/
tests/scientific/learning/
```

Exact paths may follow established repository conventions, but coverage must include the following.

## 9.1 Contract tests

Test:

1. Dense architecture validation.
2. Empty hidden dimensions rejected.
3. Derived bottleneck dimension.
4. Optimizer beta bounds.
5. Scheduler discrimination.
6. Gradient-clipping discrimination.
7. Worker and persistent-worker invariants.
8. Effective batch size derivation.
9. Standard and temporal split discrimination.
10. Explicit ordered feature schema.
11. FedAvg profile construction.
12. FedProx invalid-state rejection.
13. Ditto invalid-state rejection.
14. Seed-cohort count and uniqueness.
15. Checkpoint round ordering.
16. Fixed-round capture requirement.
17. Convergence final-round capture.
18. Evidence schema strictness.
19. Unknown fields rejected.
20. No algorithm-irrelevant fields accepted.

## 9.2 Autoencoder tests

Test every implemented enum branch:

1. Activation functions.
2. Output activations.
3. Normalization types.
4. Weight initialization.
5. Bias initialization.
6. Precision.
7. Symmetric decoder dimensions.
8. Output dimension equals explicit input dimension.
9. Deterministic initialization for identical seeds.
10. Different initialization seeds produce different states.

## 9.3 Local training tests

Test:

1. Micro-batching.
2. Gradient accumulation.
3. Exact effective batch behavior.
4. Partial accumulation stepping.
5. Partial accumulation gradient rescaling.
6. Dropped partial accumulation.
7. Incomplete batch keep/drop behavior.
8. Configured shuffle policy.
9. Worker seed initialization.
10. Scheduler execution.
11. Gradient clipping execution.
12. No batches produced fails.
13. FedProx requires state and coefficient together.
14. Positive FedProx coefficient.
15. Batched validation.
16. No full-client GPU copy.

## 9.4 Federated engine tests

Test:

1. Deterministic client ordering.
2. Training/calibration client equality.
3. Unique client identifiers.
4. Equal feature dimensions.
5. Finite input requirements.
6. Full participation.
7. Sample-count weighting.
8. Flower aggregation is actually invoked.
9. FedAvg oracle.
10. FedProx oracle.
11. FedProx coefficient-grid enforcement.
12. Ditto weight-grid enforcement.
13. Ditto personalized persistence.
14. Ditto states never aggregate.
15. Global and personalized seeds differ.
16. Captured rounds exactly match configuration.
17. BatchNorm aggregation rejection.
18. Centralized path behavior.
19. Global checkpoint state finiteness.
20. Repeated-run determinism.

## 9.5 Checkpoint tests

Test:

1. State capture.
2. Strict model-state loading.
3. State-to-Flower-array order.
4. Flower-array-to-state restoration.
5. Global checkpoint round-trip.
6. Personalized checkpoint round-trip.
7. Missing round rejection.
8. Missing client rejection.
9. Duplicate key rejection.
10. Non-finite tensor rejection.
11. Global/personalized key separation.
12. Client identifier escaping.
13. Lowest-loss selection.
14. Tie-break behavior.
15. Fixed-round selection.
16. Convergence selection.
17. No-qualifying-round behavior.
18. Authorized lookup algorithm validation.
19. Selected round must be captured.
20. Test and threshold metrics absent from selection inputs.

## 9.6 Scoring tests

Test:

1. In-memory Parquet reading.
2. Explicit feature-column order.
3. Missing feature rejection.
4. Duplicate row identity rejection.
5. Non-finite feature rejection.
6. Standard calibration split.
7. Temporal historical calibration split.
8. Future recalibration split.
9. Standard test split.
10. Temporal future evaluation split.
11. Attack rows rejected from calibration scoring.
12. Global checkpoint scoring.
13. Personalized client-bound scoring.
14. Missing personalized client rejected.
15. Batched scoring.
16. Score count equality.
17. Finite non-negative score validation.
18. Original row order preserved.
19. Checkpoint provenance columns.
20. Score-orientation enum value.

## 9.7 Handler and planning tests

Test:

1. Explicit population required.
2. Explicit seed required.
3. Exact output set for each algorithm.
4. No `outputs[0]` convention.
5. No first-population fallback.
6. No selection-evidence fallback.
7. Exact learning schema resolution.
8. Exact materialization input.
9. Exact checkpoint input.
10. Ditto personalized artifact requirement.
11. Authorized lookup input requirement.
12. Thin handlers contain no numerical algorithm.
13. Atomic persistence.
14. Failures become correct stage outcomes.
15. Composition injects engine and scoring service.

# 10. Mandatory scientific oracle tests

These tests are acceptance gates, not optional unit tests.

## 10.1 FedAvg oracle

Construct a deterministic synthetic multi-client case.

Verify independently:

1. Every eligible client participates.
2. Every local client starts from the same round-start global state.
3. Aggregation weight equals benign local training row count.
4. Flower aggregation equals the independently calculated weighted mean.
5. The produced global state matches the oracle tensor by tensor.
6. Calibration loss is computed only from benign calibration rows.

## 10.2 FedProx oracle

Verify:

1. Reference state is the round-start global state.
2. Reference tensors match trainable parameter order.
3. The objective equals reconstruction loss plus the declared proximal term.
4. Positive configured coefficient is used exactly.
5. Zero is rejected.
6. FedProx server aggregation matches FedAvg weighting.
7. No threshold outcome influences training.

## 10.3 Ditto isolation oracle

Verify:

1. Global branches aggregate.
2. Personalized branches do not aggregate.
3. Client A personalized state cannot be loaded for client B.
4. Personalized states persist between rounds.
5. Global and personalized branches use separate seed namespaces.
6. Personalized checkpoints are complete for all clients.
7. Global scoring does not accidentally use personalized states.
8. Personalized scoring does not accidentally use the global checkpoint.

## 10.4 Reproducibility oracle

Run the same small execution twice and compare:

1. Model initialization seed.
2. Shuffle seeds.
3. Worker seeds.
4. Round metrics.
5. Selected round.
6. Checkpoint tensor names.
7. Checkpoint tensor values.
8. Personalized state values.
9. Score row order.
10. Score values.
11. Evidence JSON.
12. Safetensors bytes when deterministic serialization ordering guarantees equality.

## 10.5 Anchor scientific equivalence

Reproduce the conference-faithful FedAvg anchor behavior using the resolved anchor configuration.

Compare against the accepted scientific reference using the repository’s declared tolerances.

Do not compare only whether the code runs.

Compare:

1. Training round semantics.
2. Local epochs.
3. Full participation.
4. Weighting.
5. Selected round.
6. Score orientation.
7. Calibration/test split identities.
8. Threshold-input score artifacts.
9. AUROC control behavior.
10. B1–B4 reuse of the same frozen model and scores.

Any difference must be classified as:

1. Intended correction with scientific justification.
2. Numerical tolerance.
3. Regression.

Do not silently update expected scientific fixtures.

# 11. Static and architectural validation

Run impacted checks after each coherent workstream.

Do not run the full repository suite repeatedly during incomplete migration.

Once the package and all dependents are migrated, run the complete repository gates.

Required gates:

```text
ruff format --check
ruff check
pyright
pylint
import-linter
pytest with pytest-xdist
```

Also inspect Pylance diagnostics through the repository’s established workflow.

Run SonarCloud and CodeScene checks when credentials and quotas permit.

If an external service or quota is unavailable:

1. Record the exact unavailable check.
2. Continue all local checks.
3. Retry later in the same work loop.
4. Do not claim the unavailable check passed.
5. Do not weaken acceptance criteria.

Search the repository for prohibited remnants:

```text
datp_core.learning.contracts.architecture
datp_core.learning.contracts.optimization
datp_core.learning.contracts.seeds
datp_core.learning.model.determinism
datp_core.learning.model.device
datp_core.learning.training.aggregation
datp_core.learning.training.federated
datp_core.learning.training.models
datp_core.learning.training.personalization
datp_core.learning.scoring.checkpoints
datp_core.learning.scoring.compute
datp_core.learning.scoring.models
```

All production and test imports of these paths must be removed.

Also audit for:

```text
Any
Mapping[str, object]
assert
TemporaryDirectory
json.loads
json.dumps
population_ids[0]
job.outputs[0]
Field(default
```

Raw tensor dictionaries are permitted only in `learning/checkpoints/codec.py`.

Do not mechanically reject legitimate factory mappings from enums to PyTorch classes. The audit must distinguish an explicit enum-controlled framework factory from a hardcoded scientific decision.

# 12. Multiple independent audits

Run at least the following audits after implementation.

Each audit must inspect code, configuration, tests, and generated artifacts where applicable.

## Audit A — Contract-to-execution traceability

For every learning configuration field, record:

1. Parsing location.
2. Validation location.
3. Runtime consumer.
4. Test proving consumption.
5. Provenance location.

Pass condition:

No declared-but-unused configuration field.

No runtime behavior without a configuration source or documented strict derivation.

## Audit B — Algorithm identity

Independently verify:

1. FedAvg mathematics.
2. FedProx mathematics.
3. Ditto mathematics.
4. Flower aggregation.
5. Client weighting.
6. Participation.
7. Persistent personalized states.
8. Global/personalized isolation.

Pass condition:

Each algorithm is scientifically identifiable and not selected through incidental nullable fields.

## Audit C — Core-ladder scientific isolation

Verify:

1. FedAvg remains core.
2. FedProx and Ditto remain stress tests.
3. One frozen model and score set is reused across B1–B4.
4. Threshold scope is the only ladder variable.
5. Checkpoint selection is independent of thresholds.
6. No stress-test artifact overwrites anchor artifacts.

Pass condition:

No causal-scope contamination.

## Audit D — Data leakage and split integrity

Verify:

1. Benign-only training.
2. Benign-only calibration.
3. No test leakage.
4. No attack calibration rows.
5. Exact temporal split bindings.
6. Exact feature ordering.
7. Stable row identities.
8. No filename-derived split semantics.
9. No implicit population.
10. No cross-client personalized-state substitution.

Pass condition:

Zero unauthorized data path.

## Audit E — Determinism and provenance

Verify:

1. All stochastic operations have a namespace.
2. Shuffle and worker seeds are separate.
3. Global and personalized branches use distinct namespaces.
4. CUDA deterministic settings are active.
5. Seed evidence is persisted.
6. Repeated executions agree.
7. Artifact ordering is deterministic.
8. Client order cannot depend on hashing or filesystem order.

Pass condition:

Repeated equivalent runs are reproducible within the declared numerical contract.

## Audit F — Artifact and codec isolation

Verify:

1. Safetensors mappings only exist in the codec.
2. Checkpoint keys are constructed centrally.
3. Global and personalized keys cannot collide.
4. Selected rounds are captured.
5. Missing states fail.
6. Evidence rejects unknown fields.
7. Atomic writes remain.
8. No raw JSON domain parsing remains.

Pass condition:

One authoritative tensor serialization boundary.

## Audit G — Resource and batching behavior

Verify:

1. Training is batched.
2. Validation is batched.
3. Scoring is batched.
4. Gradient accumulation is real.
5. Partial accumulation is correctly scaled.
6. Configured batch size is unchanged.
7. Entire client datasets are not copied to GPU.
8. Checkpoints are deliberately moved to CPU.
9. Personalized execution does not retain uncontrolled GPU copies.
10. Temporary Parquet files are eliminated.

Pass condition:

No hidden resource fallback and no batching-contract drift.

## Audit H — No backward compatibility

Search source, tests, imports, documentation, and configuration.

Verify:

1. No old module remains.
2. No compatibility wrapper remains.
3. No deprecated alias remains.
4. No re-export remains.
5. No old YAML field remains.
6. No test imports an old path.
7. No comments instruct future users to use the old API.

Pass condition:

The repository has one forward architecture.

After all audits pass, run two additional clean audit passes from fresh repository scans. The second pass must not rely on the first pass’s file list.

# 13. Manual execution checks

After static and automated tests pass:

1. Run a small deterministic synthetic GPU smoke test.
2. Run one representative FedAvg experiment.
3. Run one FedProx stress-test condition.
4. Run one Ditto stress-test condition.
5. Run global checkpoint scoring.
6. Run personalized checkpoint scoring.
7. Run one representative campaign interruption/restart flow if learning artifacts participate in campaign recovery.
8. Verify outputs and provenance manually.
9. Delete all smoke and temporary outputs afterward.

Use the configured batch sizes.

Do not reduce batch sizes to make a smoke run pass.

If CUDA is unavailable, report the blocked GPU checks accurately and continue every non-GPU gate. Do not introduce CPU fallback.

# 14. Required working checklist

Maintain this checklist during execution and do not mark an item complete without evidence.

## Architecture

* [ ] New 15-file learning tree is present.
* [ ] All obsolete files are deleted.
* [ ] No compatibility file exists.
* [ ] No stale import exists.
* [ ] No generic helper module was added.
* [ ] Handlers are thin.
* [ ] One shared training engine owns all round orchestration.
* [ ] Flower performs server aggregation.
* [ ] Safetensors mappings are isolated.

## Contracts

* [ ] Closed domains use enums.
* [ ] Training profiles are discriminated.
* [ ] Checkpoint selection profiles are discriminated.
* [ ] Split profiles are discriminated.
* [ ] Algorithm-specific fields are not nullable fields on unrelated profiles.
* [ ] Unknown config fields fail.
* [ ] No convenience defaults were added.
* [ ] Effective batch size is derived.
* [ ] Ordered feature columns are explicit.
* [ ] Every field has a runtime consumer.

## Configuration

* [ ] All YAML files use the new fields.
* [ ] No old fields remain.
* [ ] Every materialization references a learning schema.
* [ ] Runtime profile is explicit.
* [ ] Seed namespaces are explicit.
* [ ] Worker seed namespace is explicit.
* [ ] Checkpoint rounds are explicit.
* [ ] No invented scientific value was introduced.

## Pipeline

* [ ] Population is resolved before execution.
* [ ] Seed is resolved before execution.
* [ ] Sweep parameters are algorithm-valid.
* [ ] Inputs are exact.
* [ ] Outputs are exact.
* [ ] Selection-evidence authorization is exact.
* [ ] No first-item fallback exists.
* [ ] No split is inferred from a filename.
* [ ] Composition injects engine and service instances.

## Training

* [ ] FedAvg oracle passes.
* [ ] FedProx oracle passes.
* [ ] Ditto isolation oracle passes.
* [ ] Full participation is enforced.
* [ ] Sample weighting is correct.
* [ ] Gradient accumulation is correct.
* [ ] Partial accumulation scaling is correct.
* [ ] Validation is batched.
* [ ] CUDA-required behavior is preserved.
* [ ] Batch size was not reduced.
* [ ] BatchNorm state is not incorrectly aggregated.

## Checkpoints

* [ ] Global round-trip passes.
* [ ] Personalized round-trip passes.
* [ ] Missing round fails.
* [ ] Missing client fails.
* [ ] Selected round is always captured.
* [ ] Lookup evidence is FedAvg-authorized.
* [ ] Test outcomes cannot select checkpoints.
* [ ] Threshold outcomes cannot select checkpoints.
* [ ] Seed evidence is complete.

## Scoring

* [ ] Materialization stays in memory.
* [ ] Explicit features are used.
* [ ] Calibration attack rows fail.
* [ ] Global scoring passes.
* [ ] Personalized scoring passes.
* [ ] Missing client state fails.
* [ ] Row order is preserved.
* [ ] Scores are finite and non-negative.
* [ ] Provenance columns are correct.

## Scientific integrity

* [ ] FedAvg remains the core causal-ladder model.
* [ ] E=1 anchor semantics are preserved.
* [ ] Full participation anchor semantics are preserved.
* [ ] Benign-only training is preserved.
* [ ] Benign-only calibration is preserved.
* [ ] Frozen score reuse across B1–B4 is preserved.
* [ ] FedProx remains a stress test.
* [ ] Ditto remains a stress test.
* [ ] AUROC remains a control metric.
* [ ] Anchor equivalence is verified.

## Quality gates

* [ ] Impacted tests pass.
* [ ] Full tests pass after migration completes.
* [ ] Ruff formatting passes.
* [ ] Ruff checks pass.
* [ ] Pyright passes.
* [ ] Pylint passes.
* [ ] Import-linter passes.
* [ ] Pylance diagnostics are clean.
* [ ] SonarCloud is checked.
* [ ] CodeScene is checked.
* [ ] Two final independent audit passes find no new issue.
* [ ] Temporary files and smoke outputs are deleted.
* [ ] No commit was created.
* [ ] Nothing was pushed.

# 15. Completion standard

Do not declare completion because the new package compiles.

Completion requires all of the following:

1. The entire repository imports the new architecture.
2. Old paths are deleted and unreferenced.
3. Config resolution constructs the new profiles.
4. Pipeline planning produces valid explicit contexts.
5. Artifact contracts use typed checkpoint evidence.
6. All impacted tests are rewritten around forward behavior.
7. Scientific oracle tests pass.
8. Static analysis passes.
9. The full repository suite passes.
10. Manual smoke checks pass where the environment permits.
11. All scientific audits pass.
12. Two final clean audit passes find no remaining issue.
13. No backwards compatibility was introduced.
14. No commit or push was performed.

Continue planning, implementing, testing, auditing, and correcting until this standard is reached.

Do not stop to ask whether to continue.

Do not revert the new package to accommodate old code.

Adapt the rest of DATP-Core to the new package.

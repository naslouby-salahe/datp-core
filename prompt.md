# Goal: Fully Debloat, Refactor, and Integrate `datp_core.thresholding`

Work inside:

```text
/home/naslouby/Projects/datp-core
```

Your goal is to completely refactor and debloat:

```text
src/datp_core/thresholding
```

This is not a local cosmetic cleanup. It is a repository-integrated architectural refactor.

You must inspect, redesign, implement, test, and validate the entire thresholding capability and every repository component that constructs, validates, resolves, schedules, invokes, serializes, consumes, reports, or tests thresholding behavior.

Continue working until the package and every affected consumer are fully migrated, all obsolete code is deleted, all relevant configuration is cleaned, all tests are adapted, all quality gates pass, and a second complete audit finds no unresolved issue.

Do not stop after creating a partially cleaner abstraction. Do not leave migration work for later. Do not claim completion while old and new architectures coexist.

---

# 1. Absolute Rules

## 1.1 No backward compatibility

Backward compatibility is explicitly forbidden.

Do not create or retain:

1. Compatibility modules.
2. Redirect modules.
3. Import-forwarding modules.
4. Re-export shims.
5. Deprecated aliases.
6. Old names mapped to new names.
7. Compatibility constructors.
8. Legacy schema adapters.
9. Dual old/new policy representations.
10. Fallback dispatch to old implementations.
11. Temporary compatibility branches.
12. Barrel modules whose purpose is preserving old imports.
13. Comments saying that legacy support can be removed later.
14. Tests that preserve obsolete imports or behavior only for compatibility.

When a symbol, module, field, configuration key, or API is replaced:

1. Update every real consumer.
2. Update every relevant test.
3. Update configuration and documentation that describe it.
4. Delete the old symbol or file in the same refactor.

The repository must finish with one architecture, one vocabulary, one schema, and one execution path.

## 1.2 No superficial patching

Do not patch symptoms while retaining the flawed design.

Do not:

1. Add more wrapper classes around the existing wrappers.
2. Add another registry beside the current registries.
3. Add helper functions that preserve bad primitive-heavy interfaces.
4. Cast untyped values merely to satisfy the type checker.
5. broaden exception handling to hide contract failures.
6. weaken tests to accept incomplete output.
7. preserve descriptive configuration because removing it touches many files.
8. leave unused configuration fields in place.
9. keep dead enum members “for possible future use.”
10. retain duplicate representations of policy kind, construction mode, ownership, scope, or diagnostics.
11. use temporary `dict[str, object]` payloads between layers.
12. serialize unknown diagnostics using a generic placeholder.

Fix the architecture at its source and adapt every caller properly.

## 1.3 No mass-editing shortcuts

Do not use broad regular-expression replacement, uncontrolled search-and-replace scripts, generated mass-edit scripts, or blind AST rewrites.

Process source files deliberately.

For every edited source file:

1. Read the complete file.
2. Inspect its imports and consumers.
3. inspect its associated tests.
4. identify its responsibilities and contracts.
5. implement the intended architecture.
6. run its impacted tests.
7. inspect the resulting file again.
8. record completion in the temporary progress ledger.
9. only then proceed.

Test files may be analyzed or updated in parallel when their ownership does not overlap.

## 1.4 No low-quality code

Do not introduce:

1. `Any`.
2. untyped `object` payloads.
3. `dict`-based domain transport.
4. raw string discriminators where an enum is appropriate.
5. magic strings.
6. magic scientific numbers.
7. mutable global registries.
8. unnecessary protocols.
9. unnecessary abstract classes.
10. one-method wrapper classes.
11. avoidable `cast(...)`.
12. `type: ignore`.
13. `# noqa` used to conceal design problems.
14. circular imports.
15. runtime imports from higher-level analysis packages.
16. optional fields that permit internally invalid states.
17. duplicated schema definitions.
18. handwritten serialization that Pydantic already handles.
19. comments narrating obvious code.
20. AI-style explanatory comments.
21. commented-out code.
22. dead code.
23. TODO, FIXME, temporary, workaround, legacy, deprecated, or compatibility markers left unresolved in the affected scope.
24. file names such as `utils.py`, `helpers.py`, `common_utils.py`, or other dumping grounds.
25. generic exceptions where a domain exception is required.
26. hidden scientific defaults in Python.
27. implicit fallback behavior not represented by the validated contract.

Prefer small, cohesive modules with explicit ownership.

---

# 2. Required Initial Discovery

Before editing code, perform a complete repository-level impact analysis.

## 2.1 Verify available tools

Check the existence and usability of applicable tools before relying on them:

1. Git.
2. `uv`.
3. Pytest.
4. pytest-xdist.
5. Ruff.
6. Pyright or the repository’s configured strict type checker.
7. Pylint, when configured.
8. import-linter.
9. SonarCloud access.
10. CodeScene access.
11. Graphify or the repository’s graph/dependency inspection tool.
12. repository-specific validation commands.
13. Codex or another independent reviewer, when available.

A missing external service must not block the refactor.

When SonarCloud, CodeScene, Codex, Graphify, or another external tool is unavailable, rate-limited, or out of quota:

1. record the failure in the temporary ledger;
2. continue using local analysis and checks;
3. retry the tool before final completion;
4. never treat an unavailable external tool as a passing result.

## 2.2 Create resumable temporary tracking

Use:

```text
/home/naslouby/Projects/datp-core/.tmp/thresholding-refactor/
```

Create at least:

```text
.tmp/thresholding-refactor/
├── plan.md
├── inventory.md
├── dependency-map.md
├── configuration-ledger.md
├── behavior-baseline.md
├── progress.md
├── test-ledger.md
├── audit-ledger.md
└── unresolved.md
```

These files are temporary execution state, not product documentation.

They must make the task idempotent and resumable after interruption. On restart, inspect them and the current repository state before doing new work.

Delete the entire temporary directory after final completion and after its information has been included in the final report.

Do not commit `.tmp`.

## 2.3 Read scientific and architectural sources of truth

Read all repository documents that define:

1. the fixed-model threshold-calibration identity;
2. the B0/B1/B2/B3/B4 threshold semantics;
3. benign-only calibration;
4. family and cluster behavior;
5. shrinkage;
6. calibration-size fallback;
7. split conformal behavior;
8. federated summary-statistic thresholding;
9. deterministic seed derivation;
10. experiment sweep behavior;
11. artifact schemas;
12. reporting requirements;
13. import-layer rules;
14. configuration conventions.

At minimum inspect the current roadmap files, configuration files, project configuration models, pipeline planning code, artifact schemas, reporting code, and relevant tests.

The roadmap and validated configuration are the scientific source of truth. The current source layout is not a source of truth.

Do not alter scientific meaning merely to simplify code.

## 2.4 Build a complete dependency map

Search the entire repository for every use of:

```text
datp_core.thresholding
ThresholdPolicyKind
ThresholdPolicyRecord
ThresholdConstructionRequest
ThresholdSet
ThresholdRecord
ThresholdOwnerKind
ThresholdOwnership
ThresholdEstimator
ThresholdEstimatorRegistry
ESTIMATOR_KIND_REGISTRY
ConstructThresholdsUseCase
CalibrationSubsamplingStageHandler
ThresholdConstructionStageHandler
BenignCalibrationScores
selected_coefficient
quantile_override
fingerprint_features_override
coverage_alpha
nominal_coverage
target_exceedance
aggregation_formula
global_mean_formula
pooled_variance_formula
rank_formula
interpolation_formula
provenance_separation
exchangeability_limitation
requires_diagnostics
diagnostics
```

Also search semantically for:

1. imports from old thresholding subpackages;
2. policy parsing;
3. policy registration;
4. experiment expansion;
5. sweep resolution;
6. configuration serialization;
7. stage registration;
8. threshold artifact generation;
9. threshold artifact reading;
10. diagnostics loading;
11. reporting fields;
12. tests creating threshold policies directly;
13. tests asserting old paths;
14. YAML keys related to thresholding;
15. docs describing the old module tree or old configuration schema.

Classify each occurrence as:

```text
producer
resolver
planner
consumer
serializer
reporter
test
documentation
obsolete
```

Do not begin structural deletion until this map exists.

## 2.5 Establish a behavioral baseline

Before restructuring, add or improve characterization tests for all currently supported scientific behaviors.

The baseline must cover:

1. shared-mean quantile thresholding;
2. pooled quantile thresholding;
3. sample-weighted shared thresholding;
4. local per-client quantiles;
5. family-mean thresholding;
6. cluster thresholding;
7. cluster-label canonicalization;
8. split-conformal finite-sample ranks;
9. fixed shrinkage;
10. calibration-size-aware shrinkage or fallback;
11. federated fixed-coefficient thresholding;
12. federated matched-exceedance thresholding;
13. federated pooled-moment equivalence;
14. deterministic calibration subsampling;
15. nested calibration samples;
16. threshold artifact schema;
17. diagnostics serialization;
18. stage-handler input and output contracts;
19. deterministic client ordering;
20. invalid configuration rejection;
21. empty calibration failure;
22. insufficient calibration failure;
23. non-finite score rejection.

Record representative expected outputs in:

```text
.tmp/thresholding-refactor/behavior-baseline.md
```

Preserve scientifically correct behavior while fixing confirmed defects. When a behavior changes because the existing implementation is defective, document the defect, expected contract, affected tests, and correction.

---

# 3. Required Target Architecture

The final source tree must be:

```text
src/datp_core/thresholding/
├── __init__.py
├── enums.py
├── policies.py
├── models.py
├── calibration.py
├── engine.py
├── estimators/
│   ├── __init__.py
│   ├── quantile.py
│   ├── grouped.py
│   └── federated.py
├── serialization.py
└── stages.py
```

The final test tree should be:

```text
tests/unit/thresholding/
├── test_policies.py
├── test_calibration.py
├── test_quantile_estimators.py
├── test_grouped_estimators.py
├── test_federated_estimators.py
├── test_engine.py
├── test_serialization.py
└── test_stages.py
```

Use the repository’s actual test root if it differs, but preserve this logical organization.

Do not retain the old directory hierarchy as redirect packages.

After migration, delete obsolete directories such as:

```text
src/datp_core/thresholding/calibration/
src/datp_core/thresholding/execution/
src/datp_core/thresholding/policies/
```

Delete old estimation modules that are absorbed by the target modules.

The final package must not contain both the old and target architecture.

---

# 4. Required Module Responsibilities

## 4.1 `__init__.py`

Keep this file empty or expose only a deliberately tiny, stable domain-facing API required by current repository consumers.

It must not:

1. re-export old paths;
2. preserve compatibility imports;
3. import every implementation symbol;
4. become a circular-import workaround;
5. act as a general barrel module.

Prefer direct imports from the owning module.

## 4.2 `enums.py`

Place all authoritative closed thresholding domains here.

At minimum evaluate and consolidate:

```text
ThresholdPolicyKind
ThresholdScope
QuantileMethod
ThresholdAggregation
FingerprintFeature
FingerprintStandardization
ClusterAggregation
TieBreakRule
CalibrationSelectionStrategy
CalibrationNestingPolicy
SeedDerivationMethod
```

Use enums only for genuine closed domains.

Do not retain overlapping enums describing the same concept.

Replace ownership variants such as estimator-specific owner values with one scope enum:

```text
SHARED
CLIENT
FAMILY
CLUSTER
```

The estimator identity is already represented by the policy identifier and policy kind. Do not duplicate it in ownership.

Delete enum members that have no implementation.

Every retained enum member must be:

1. parsed;
2. validated;
3. executed;
4. serialized when applicable;
5. directly tested.

## 4.3 `policies.py`

Use Pydantic v2 for validated configuration models.

Create one shared frozen base model and one authoritative discriminated union using:

```python
kind: ThresholdPolicyKind
```

Use:

1. `ConfigDict(frozen=True, extra="forbid")`;
2. `Field(discriminator="kind")`;
3. `TypeAdapter`;
4. constrained numeric types;
5. `Annotated`;
6. `PositiveInt`;
7. direct enum types;
8. `model_validator` for cross-field invariants.

Collapse the policy-model explosion into a compact hierarchy:

```text
QuantilePolicy
ClusterPolicy
ConformalPolicy
ShrinkagePolicy
FederatedPolicy
```

Do not create one class per tiny construction variation when a discriminator and validated fields provide a clearer contract.

Do not allow impossible combinations through optional fields.

A policy model must contain only values that affect validation or execution.

Delete:

1. duplicated `policy`, `construction`, and `mode` discriminators;
2. `ClassVar kind` duplication;
3. textual formulas;
4. explanatory prose fields;
5. textual empty-state behavior;
6. textual provenance declarations;
7. textual exchangeability limitations;
8. unused diagnostics declarations;
9. configuration fields that merely describe the implementation;
10. values that are completely derivable from one authoritative parameter;
11. runtime-only overrides;
12. arbitrary mappings;
13. `BeforeValidator(dict)`;
14. `arbitrary_types_allowed=True`;
15. manual `from_config()` conversion helpers;
16. unsafe casts.

The resulting configuration schema must be strict and minimal.

## 4.4 `models.py`

Use frozen, slotted dataclasses for in-memory commands and results when serialization is not their primary role.

Use Pydantic models for serialized diagnostics and artifact-bound records when that materially reduces serialization code.

Define explicit domain types for:

1. benign calibration batches;
2. calibration sample requests;
3. calibration sample results;
4. resolved threshold-construction commands;
5. family assignments;
6. threshold assignments;
7. threshold records;
8. threshold sets;
9. typed diagnostics;
10. package exceptions.

`ThresholdSet.diagnostics` must be:

```text
ThresholdDiagnostics | None
```

It must never be `object`, `Any`, or an arbitrary mapping.

Create a discriminated diagnostics union containing only the diagnostics actually produced, for example:

```text
ClusterDiagnostics
ConformalDiagnostics
ShrinkageDiagnostics
CalibrationFallbackDiagnostics
FederatedFixedDiagnostics
MatchedExceedanceDiagnostics
CalibrationSamplingDiagnostics
```

Do not keep a diagnostics type that no execution path produces.

Remove generic builder signatures containing many optional mappings. Do not retain a builder equivalent to:

```text
thresholds
lambdas
cluster_labels
conformal_ranks
conformal_attainability
diagnostics
```

Construct complete typed threshold assignments directly.

Use one validated non-negative finite threshold scalar type. Do not use a union such as:

```text
NonNegativeFloat | float
```

Introduce a package exception hierarchy, including suitable equivalents of:

```text
ThresholdingError
InvalidThresholdPolicyError
EmptyCalibrationError
InsufficientCalibrationError
NonFiniteCalibrationError
UnsupportedThresholdPolicyError
ThresholdConfigurationError
ThresholdArtifactError
```

Use the existing project-wide base exception if one exists and is architecturally appropriate.

## 4.5 `calibration.py`

Merge deterministic calibration subsampling into one cohesive module.

Introduce a frozen typed request containing:

1. requested sample count;
2. training seed;
3. selection seed;
4. replicate;
5. typed seed namespace;
6. digest size;
7. selection strategy;
8. nesting policy.

Replace strings such as:

```text
never_thresholds_only_recomputed
derived_seed_algorithm_with_namespace_calibration_subsample
```

with validated enum-backed configuration where the choice is genuinely configurable.

When only one behavior is supported, remove the configuration field and make it part of the executable contract.

Required behavior:

1. validate finite score data;
2. validate required score columns using the canonical artifact schema;
3. preserve deterministic client ordering;
4. preserve deterministic source ordering;
5. derive seeds through the canonical project seeding primitive;
6. preserve nested-by-size behavior;
7. return a typed sampling result and diagnostics;
8. never silently drop a client;
9. raise `InsufficientCalibrationError` when a requested sample cannot be produced for every required client;
10. reject invalid replicate, count, namespace, or digest values before sampling;
11. avoid local duplication of artifact-column names.

Property-test nesting and determinism.

## 4.6 `engine.py`

Replace all estimator wrapper classes, estimator protocols, and duplicate registries with one `ThresholdEngine`.

The engine must:

1. accept a fully resolved, immutable threshold policy;
2. accept a typed construction command;
3. validate request-policy compatibility;
4. validate calibration once;
5. calculate shared intermediate values only when needed;
6. dispatch by `ThresholdPolicyKind`;
7. delegate scientific calculation to the appropriate estimator module;
8. return one typed `ThresholdSet`;
9. never mutate policy models;
10. never perform configuration sweep expansion;
11. never copy policies with runtime updates;
12. never read raw unvalidated configuration mappings.

Use one explicit exhaustive `match` over `ThresholdPolicyKind`.

Do not create another registry.

Delete:

```text
ThresholdEstimator
ThresholdEstimatorRegistry
ESTIMATOR_KIND_REGISTRY
_POLICY_TYPE_TO_KIND
per-policy one-method estimator classes
runtime estimator registration calls
```

The match must fail explicitly for an unsupported enum value. Static typing and tests must establish exhaustiveness.

## 4.7 `estimators/quantile.py`

Consolidate:

1. quantile validation;
2. shared mean;
3. pooled quantile;
4. weighted shared quantile;
5. local quantile;
6. fixed shrinkage;
7. calibration-size-aware shrinkage;
8. calibration fallback;
9. split conformal.

Remove callable injection such as `quantile_fn` when only one canonical quantile implementation exists.

Do not calculate local quantiles for policies that do not need them.

Do not pass local-threshold dictionaries merely to recover client keys.

Use explicit typed inputs and outputs.

### Conformal contract

Keep the existing fail-fast scientific behavior and make it explicit.

When any required client lacks enough calibration rows to satisfy the configured finite-sample conformal rank:

1. raise `InsufficientCalibrationError`;
2. fail the construction;
3. do not emit a partial artifact;
4. remove `ConformalAttainabilityStatus`;
5. remove unreachable `UNATTAINABLE` records;
6. do not retain dead attainability fields.

Store one authoritative conformal parameter and derive duplicated values such as coverage, alpha, target exceedance, or quantile where mathematically appropriate.

Test the exact finite-sample rank rule and boundary sample sizes.

## 4.8 `estimators/grouped.py`

Consolidate family and cluster estimation.

### Family estimation

Use typed `FamilyAssignments`, not `dict[str, str]`.

Validate:

1. every required client has a family;
2. no unknown client assignment is silently accepted;
3. every family bucket is non-empty;
4. deterministic ordering is preserved.

### Cluster estimation

Replace raw fingerprint strings with:

```text
FingerprintFeature
```

Do not parse estimator formulas from strings such as:

```text
quantile_0_95_linear_interpolated_order_statistic
```

Represent the fingerprint quantile directly as a validated numeric parameter.

The implementation must:

1. validate supported fingerprint features;
2. construct fingerprints deterministically;
3. validate finite feature values;
4. require at least `cluster_count` unique feature rows;
5. apply the configured standardization behavior;
6. remove unused standardization fields or execute them;
7. apply explicit KMeans initialization configuration;
8. remove unnecessary numeric casts;
9. remove Scikit-learn typing suppressions;
10. canonicalize cluster labels deterministically;
11. preserve canonical labels under input-order permutations;
12. produce complete `ClusterDiagnostics`;
13. include memberships and cluster thresholds;
14. report configured fingerprint features;
15. reject degenerate matrices clearly.

Do not keep a configuration option that `StandardScaler()` ignores.

## 4.9 `estimators/federated.py`

Implement federated summary-statistic thresholding according to actual federated semantics.

Do not flatten all client scores into one centralized array for matched exceedance.

Each client summary must provide only the values required by the algorithm, including appropriate combinations of:

1. row count;
2. sum;
3. squared sum;
4. local exceedance counts for the candidate grid.

The server must aggregate these summaries.

The implementation must:

1. establish pooled mean and variance equivalence with a centralized reference;
2. validate zero and near-zero variance;
3. validate the candidate-grid minimum, maximum, and step;
4. construct the candidate grid deterministically;
5. avoid floating-point boundary drift from ad hoc `np.arange`;
6. calculate achieved exceedance from aggregated client counts;
7. implement the configured matching metric;
8. implement the configured tie-break rule;
9. record the complete set of tied candidates;
10. record the selected candidate;
11. produce diagnostics for fixed and matched modes;
12. reject unsupported metrics or tie rules at configuration load;
13. never use one field for both shrinkage weight and federated coefficient.

Replace `selected_coefficient` with distinct strongly typed values owned by their policy:

```text
shrinkage_weight
federated_coefficient
matched_coefficient
```

Do not move these unrelated concepts through one primitive slot.

## 4.10 `serialization.py`

Use canonical artifact schemas.

Do not duplicate threshold-column names, Polars dtypes, or empty-frame schemas when the artifact package already owns them.

Serialize diagnostics losslessly using Pydantic:

```python
diagnostics.model_dump_json()
```

Delete manual diagnostics type-switch code and any fallback equivalent to:

```json
{"note": "diagnostics_present"}
```

Unknown diagnostics must be impossible after union validation. They must not be silently reduced to a placeholder.

Serialization must validate:

1. finite thresholds;
2. unique client records;
3. deterministic row ordering;
4. required metadata;
5. policy identity;
6. threshold scope;
7. diagnostics schema;
8. artifact schema compatibility.

Add round-trip tests.

## 4.11 `stages.py`

Merge calibration-subsampling and threshold-construction stage adapters into one stage adapter module.

Handlers must remain thin.

They may only:

1. validate context type;
2. validate required context values;
3. resolve named input and output paths;
4. read canonical artifacts;
5. create typed commands;
6. invoke calibration or threshold services;
7. serialize results;
8. translate known domain exceptions to stage outcomes.

Do not:

1. use `assert isinstance(...)`;
2. use positional input access such as `job.inputs[0]`;
3. mutate policies;
4. resolve sweeps;
5. parse formula strings;
6. calculate scientific values;
7. inspect an `isinstance` tuple to decide diagnostics requirements;
8. catch arbitrary programming errors as normal stage failures;
9. hide missing outputs.

Diagnostics requirements must be part of the resolved policy contract.

---

# 5. Configuration Cleanup

Configuration cleanup is part of this task, not a later follow-up.

Inspect every file under:

```text
configs/
```

and every Python configuration model, resolver, validator, catalogue model, experiment model, and planning model related to thresholding.

## 5.1 Remove descriptive configuration masquerading as runtime configuration

Delete configuration keys whose only purpose is describing formulas, documentation, provenance, limitations, or implementation behavior.

This applies to both:

1. Python configuration models.
2. YAML configuration files.

Remove keys such as, or equivalent to:

```text
aggregation_formula
global_mean_formula
pooled_variance_formula
rank_formula
interpolation_formula
provenance_separation
exchangeability_limitation
empty_behavior
unavailable_behavior
source_description
scope_description
formula
algorithm_description
implementation_notes
diagnostic_description
```

Do not merely stop reading these keys. Remove them from:

1. YAML.
2. Pydantic models.
3. validators.
4. resolved models.
5. serialization.
6. tests.
7. examples.
8. documentation describing the runtime schema.

Scientific explanations belong in the roadmap or documentation, not the executable configuration contract.

## 5.2 Executable configuration rule

Every retained runtime configuration field must satisfy at least one of these:

1. It selects an implemented behavior.
2. It supplies an actual runtime value.
3. It defines a validated scientific parameter.
4. It controls an experiment sweep that is resolved before execution.
5. It controls serialization or reporting behavior that is truly configurable.

Every retained field must be read and acted upon.

A field that does not affect execution or validation must be deleted.

A field with only one supported value must normally be deleted and represented by the implementation contract instead of configuration.

## 5.3 No hidden defaults

Do not move removed YAML values into hidden Python defaults.

Scientific values must remain explicit in configuration when they are genuinely variable, including appropriate values such as:

1. quantiles;
2. cluster count;
3. fingerprint features;
4. KMeans seed;
5. KMeans initialization runs;
6. maximum iterations;
7. tolerance;
8. shrinkage weights;
9. calibration sample sizes;
10. conformal coverage;
11. candidate-grid bounds;
12. candidate-grid step;
13. fixed federated coefficient;
14. tie-breaking behavior when more than one behavior is implemented.

Implementation-invariant details must be code contracts, not configurable strings.

Do not use YAML anchors or aliases.

Do not duplicate the same scientific value across multiple configuration files without one explicit source of truth.

Do not invent a new large configuration hierarchy solely for this refactor. Preserve the repository’s current normalized configuration organization unless a concrete architectural defect requires a focused change.

## 5.4 Resolve sweeps before threshold execution

Move quantile, fingerprint-feature, coefficient, calibration-size, and similar sweep expansion to the catalogue or planning layer.

The thresholding engine must receive an already resolved policy.

Delete threshold-engine parameters equivalent to:

```text
quantile_override
fingerprint_features_override
selected_coefficient
```

Update experiment planning, context objects, job construction, manifests, fingerprints, and tests accordingly.

Every expanded experiment job must carry its complete resolved policy identity and values.

No `model_copy(update=...)` policy mutation is allowed during stage execution.

## 5.5 Strict configuration validation

Configuration parsing must:

1. reject unknown keys;
2. reject stale keys;
3. reject unsupported enum values;
4. reject incompatible field combinations;
5. reject missing required executable parameters;
6. reject impossible cluster settings;
7. reject invalid conformal settings;
8. reject invalid candidate grids;
9. reject invalid shrinkage settings;
10. reject invalid calibration subset settings;
11. reject non-finite numbers;
12. reject duplicated policy identifiers.

Add negative tests proving that old descriptive fields and removed keys are no longer accepted.

---

# 6. Repository-Wide Consumer Migration

Do not limit changes to `src/datp_core/thresholding`.

Adapt every affected file properly.

Inspect and update, where applicable:

```text
src/datp_core/config/
src/datp_core/catalogue/
src/datp_core/orchestration/
src/datp_core/pipeline/
src/datp_core/artifacts/
src/datp_core/evaluation/
src/datp_core/analysis/
src/datp_core/reporting/
src/datp_core/interfaces/
src/datp_core/composition/
src/datp_core/runtime/
configs/
tests/
README.md
docs/
```

Update all consumers to use the new typed API directly.

Do not leave adapters at the thresholding boundary.

Specific integration work includes:

1. Update project configuration parsing.
2. Update resolved project models.
3. Update policy registries or repositories outside thresholding.
4. Remove duplicate threshold-policy dispatch elsewhere.
5. Update experiment catalogue resolution.
6. Update sweep expansion.
7. Update stage contexts.
8. Update job planning.
9. Update stage registration.
10. Update dependency-injection or composition roots.
11. Update artifact schemas.
12. Update threshold artifact readers.
13. Update evaluation consumers.
14. Update analysis consumers.
15. Update reporting exports.
16. Update manifest and fingerprint construction.
17. Update CLI commands that expose threshold policy values.
18. Update fixtures.
19. Update factories.
20. Update test helpers.
21. Update import-linter contracts if the legitimate architecture changes.
22. Update documentation that describes old imports, old fields, or old trees.
23. Delete all stale imports and dead consumer code.

The dependency direction must remain clean.

Thresholding must not import policy contracts from `analysis`. Move the relevant contract to a neutral lower-level package or into thresholding when thresholding owns it, then adapt consumers.

Do not introduce circular dependencies to avoid moving a type.

---

# 7. Scientific Integrity Requirements

The refactor must preserve DATP’s scientific identity.

Verify throughout:

1. Core B1–B4 comparisons use the same frozen model and score artifacts.
2. Calibration remains benign-only.
3. Threshold scope remains the causal variable in the core ladder.
4. AUROC remains a control, not the thresholding verdict.
5. Local, family, cluster, shared, conformal, shrinkage, and federated policies retain their authored meanings.
6. Client identity is stable.
7. Family assignments are explicit and validated.
8. Cluster canonicalization is deterministic.
9. Calibration subsampling remains deterministic and nested.
10. Federated matched-exceedance uses federated summaries rather than hidden central pooling.
11. Experiment sweep values are resolved before execution.
12. No policy changes based on observed results.
13. No scientific constants become hardcoded accidentally.
14. No test uses attack-labeled rows as benign calibration.
15. No empty or partial threshold artifact is silently accepted.
16. No diagnostics evidence is discarded.
17. No policy identifier is silently mapped to a different construction.
18. No output schema change occurs without updating every reader.

Run at least two explicit scientific-drift audits:

1. after the new engine and policies are integrated;
2. after all consumers and configuration are migrated.

Record each audit in:

```text
.tmp/thresholding-refactor/audit-ledger.md
```

---

# 8. Testing Requirements

## 8.1 Test adaptation rules

Tests are part of the refactor and must also be debloated.

Do not preserve obsolete tests to maintain old architecture.

Delete or rewrite tests that:

1. assert legacy import paths;
2. instantiate deleted wrapper classes;
3. test duplicate registries;
4. test descriptive configuration fields;
5. rely on arbitrary mappings;
6. accept incomplete diagnostics;
7. accept silent client dropping;
8. depend on runtime policy mutation;
9. duplicate implementation details without testing behavior;
10. contain excessive fixtures or boilerplate.

Tests must assert domain behavior and public contracts, not internal scaffolding.

## 8.2 Required test coverage

Add direct tests for:

### Policies and configuration

1. Every `ThresholdPolicyKind`.
2. Discriminated union parsing.
3. Unknown-key rejection.
4. Removed descriptive-key rejection.
5. Invalid field combinations.
6. Strict enum parsing.
7. Frozen policy behavior.
8. resolved sweep policy creation.

### Calibration

1. Deterministic repeated sampling.
2. Nested-by-size samples.
3. Stable client ordering.
4. Stable source ordering.
5. insufficient rows.
6. invalid replicate.
7. invalid digest.
8. missing columns.
9. non-finite score rejection.
10. no silent client loss.

### Quantile estimators

1. Shared mean.
2. Pooled.
3. Weighted.
4. Local.
5. Fixed shrinkage.
6. calibration-size shrinkage.
7. fallback boundaries.
8. conformal finite-sample rank.
9. insufficient conformal calibration.
10. non-finite inputs.
11. empty calibration.

### Grouped estimators

1. Complete family assignments.
2. missing family assignment.
3. family aggregation.
4. fingerprint extraction.
5. selected feature subsets.
6. standardization.
7. insufficient unique fingerprints.
8. cluster-count boundaries.
9. canonical-label determinism.
10. input-order invariance.
11. cluster diagnostics.

### Federated estimators

1. pooled mean equivalence.
2. pooled variance equivalence.
3. fixed coefficient.
4. matched exceedance.
5. candidate-grid determinism.
6. tie detection.
7. tie-breaking.
8. zero variance.
9. invalid grid.
10. aggregated exceedance counts.
11. proof that execution does not require flattening all client scores.
12. complete diagnostics.

### Engine

1. every policy dispatch.
2. unsupported policy failure.
3. request-policy mismatch.
4. no runtime policy mutation.
5. no registry dependency.
6. deterministic output.
7. empty calibration failure.

### Serialization

1. threshold-frame schema.
2. deterministic row order.
3. diagnostic JSON round trip.
4. no diagnostic information loss.
5. duplicate-client rejection.
6. finite threshold validation.

### Stages

1. explicit context validation.
2. named input paths.
3. missing input failure.
4. domain error translation.
5. output writing.
6. diagnostics writing.
7. no positional input assumptions.
8. no scientific logic in handlers.

## 8.3 Property-based tests

Use Hypothesis selectively for high-value invariants:

1. quantile monotonicity;
2. threshold finiteness;
3. threshold non-negativity where required;
4. shrinkage thresholds lying between local and shared values;
5. calibration nesting;
6. deterministic seed derivation;
7. federated moments matching centralized moments;
8. cluster labels remaining canonical under input permutation;
9. serialization round trips;
10. candidate-grid tie handling.

Do not add property-based tests that merely duplicate trivial unit tests.

## 8.4 Test execution cadence

For each processed source file:

1. run its directly impacted tests;
2. run type checking for the touched package or files;
3. run Ruff for the touched files;
4. inspect failures before continuing.

Do not run the entire repository test suite after every small edit.

After the complete thresholding package is migrated:

1. run the complete thresholding test suite;
2. run all directly affected package suites;
3. run import-linter;
4. run strict type checking;
5. run Ruff and formatting checks;
6. run Pylint when configured;
7. run the full repository test suite with appropriate parallelism;
8. run an end-to-end threshold-construction smoke test;
9. run one calibration-subsampling-to-threshold-artifact smoke flow;
10. delete smoke outputs afterward.

Do not lower batch sizes, weaken scientific settings, or alter production behavior merely to make tests pass.

---

# 9. File-by-File Execution Order

Follow this order unless dependency analysis proves that two read-only or test tasks can run safely in parallel.

## Phase 1: Discovery and characterization

1. Complete inventory.
2. Complete dependency map.
3. Complete configuration ledger.
4. Complete baseline tests.
5. Identify scientific invariants.
6. Produce final implementation plan.
7. Review the plan twice before editing architecture.

## Phase 2: Domain vocabulary and policies

1. Implement `enums.py`.
2. Implement strict `policies.py`.
3. Adapt configuration parsing tests.
4. remove obsolete policy models.
5. remove descriptive fields from Python models.
6. remove descriptive fields from YAML.
7. adapt all configuration consumers.
8. verify stale keys are rejected.

## Phase 3: Runtime models and diagnostics

1. Implement `models.py`.
2. introduce typed exceptions.
3. introduce typed diagnostics.
4. replace generic optional mapping builders.
5. adapt artifact and reporting consumers.
6. add serialization-independent model tests.

## Phase 4: Calibration

1. Implement `calibration.py`.
2. adapt calibration stage planning.
3. adapt deterministic seeding access.
4. update calibration tests.
5. delete the old calibration subpackage after all imports are migrated.

## Phase 5: Estimators

Process independently:

1. `estimators/quantile.py`
2. `estimators/grouped.py`
3. `estimators/federated.py`

For each estimator module:

1. migrate the scientific behavior;
2. add direct behavioral tests;
3. compare against the baseline;
4. remove absorbed old modules;
5. verify no duplicate implementation remains.

## Phase 6: Engine

1. Implement `engine.py`.
2. replace both registry mechanisms.
3. delete thin estimator classes.
4. delete the estimator protocol.
5. remove runtime registration.
6. adapt construction consumers.
7. verify one dispatch path remains.

## Phase 7: Serialization and stages

1. Implement `serialization.py`.
2. implement `stages.py`.
3. adapt canonical artifact schemas.
4. adapt stage registration.
5. adapt output readers.
6. adapt diagnostics consumers.
7. delete old execution modules.

## Phase 8: Planning and consumer migration

1. move all policy override resolution to catalogue/planning;
2. replace primitive override fields with resolved policy values;
3. adapt contexts and jobs;
4. adapt manifests and fingerprints;
5. adapt evaluation;
6. adapt analysis;
7. adapt reporting;
8. adapt CLI and composition roots;
9. adapt all tests and fixtures;
10. search the entire repository again for old names.

## Phase 9: Deletion and debloating

Delete:

1. old policy files;
2. old estimator files;
3. old registries;
4. old protocols;
5. old handlers;
6. old frame builders;
7. old conversion helpers;
8. old configuration fields;
9. old YAML keys;
10. old tests;
11. dead imports;
12. empty obsolete directories.

Do not leave forwarding files.

## Phase 10: Full validation

1. run package tests;
2. run consumer tests;
3. run static checks;
4. run import architecture checks;
5. run full repository tests;
6. run smoke flows;
7. inspect SonarCloud;
8. inspect CodeScene;
9. run Graphify/dependency audit;
10. run independent review when available;
11. fix every relevant finding;
12. rerun all gates.

## Phase 11: Final idempotence audit

Run the entire audit again from a clean working state.

Confirm:

1. a second run proposes no further source changes;
2. no old imports exist;
3. no old configuration keys exist;
4. no duplicate policy path exists;
5. no temporary compatibility code exists;
6. generated artifacts are deterministic;
7. tests are stable;
8. formatting is stable;
9. configuration resolution is stable;
10. the package tree matches the target.

---

# 10. Parallel Agent Rules

Use parallel subagents for independent analysis and validation when supported.

Use at least six parallel read-only or non-overlapping agents during the major discovery and audit phases where sufficient independent work exists.

Suitable independent tasks include:

1. source architecture audit;
2. configuration audit;
3. test audit;
4. consumer/import audit;
5. scientific-invariant audit;
6. typing and static-quality audit;
7. artifact/serialization audit;
8. dependency-direction audit.

Write ownership must be explicit.

No two agents may edit the same file concurrently.

A subagent working on one source file may inspect and update only:

1. that source file;
2. its directly affected test file;
3. directly required consumer files assigned to it.

Cross-cutting architectural decisions remain controlled by the main agent.

Review every subagent result before integrating it. Do not accept generated patches blindly.

Use Codex or another independent model as a reviewer when available, but do not block completion when it is unavailable.

---

# 11. Quality Gates

The task is not complete until all applicable gates pass.

## 11.1 Structural gates

1. The target source tree exists.
2. The target test tree exists.
3. Old thresholding directories are deleted.
4. There is one policy discriminator.
5. There is one dispatch path.
6. There is no estimator registry.
7. There is no estimator wrapper hierarchy.
8. There is no runtime policy mutation.
9. There are no redirects, aliases, re-exports, or shims.
10. There are no duplicate old/new APIs.

## 11.2 Configuration gates

1. Descriptive configuration is removed from Python.
2. Descriptive configuration is removed from YAML.
3. Removed keys are rejected.
4. Every remaining field affects validation or execution.
5. Scientific variable values remain explicit.
6. No hidden code defaults replace removed YAML values.
7. No YAML anchors or aliases exist.
8. Sweep values are resolved before threshold execution.
9. Configuration models forbid unknown keys.
10. Configuration parsing is strictly typed.

## 11.3 Code-quality gates

1. No `Any`.
2. No arbitrary `object` diagnostics.
3. No domain `dict` transport.
4. No avoidable casts.
5. No `type: ignore`.
6. No unexplained `noqa`.
7. No dead enum members.
8. No magic strings.
9. No hidden scientific constants.
10. No duplicated schema.
11. No unnecessary wrappers.
12. No unnecessary protocols.
13. No mutable global registries.
14. No AI comments.
15. No unresolved TODO/FIXME.
16. No circular imports.
17. No thresholding dependency on higher-level analysis contracts.

## 11.4 Behavioral gates

1. Every policy has direct tests.
2. Calibration is deterministic.
3. Nested sampling is verified.
4. Cluster labels are deterministic.
5. Federated moments match the centralized mathematical reference.
6. Matched exceedance uses aggregated client summaries.
7. Diagnostics are complete.
8. Diagnostics serialize losslessly.
9. Empty calibration fails explicitly.
10. Insufficient calibration fails explicitly.
11. Non-finite scores fail explicitly.
12. Every output has deterministic ordering.
13. Every consumer reads the new artifact contract.
14. No scientific drift is detected.

## 11.5 Tool gates

Run and pass the repository’s actual equivalents of:

```text
ruff check
ruff format --check
pyright
pylint
import-linter
pytest thresholding tests
pytest impacted package tests
pytest full suite with xdist
```

Review current SonarCloud findings for the touched scope and fix all relevant issues.

Review CodeScene findings for the touched scope and fix relevant complexity, duplication, and hotspot issues.

Do not declare SonarCloud or CodeScene clean without checking their latest available analysis.

External-tool failure must be reported honestly.

---

# 12. Audit Loops

Perform at least five focused audits before completion.

## Audit 1: Architecture

Check:

1. package cohesion;
2. dependency direction;
3. duplicate abstractions;
4. module count;
5. class count;
6. wrapper count;
7. registry count;
8. circular imports;
9. ownership clarity.

Fix all findings.

## Audit 2: Configuration

Check:

1. descriptive runtime fields;
2. unused fields;
3. duplicated values;
4. hidden defaults;
5. raw strings;
6. stale YAML keys;
7. invalid combinations;
8. sweep resolution;
9. strict parsing.

Fix all findings.

## Audit 3: Scientific behavior

Check:

1. formulas;
2. quantiles;
3. calibration semantics;
4. conformal ranks;
5. cluster construction;
6. federated summaries;
7. threshold scopes;
8. deterministic behavior;
9. output provenance.

Fix all findings.

## Audit 4: Typing and clean code

Check:

1. `Any`;
2. `object`;
3. raw dicts;
4. primitive obsession;
5. casts;
6. suppressions;
7. dead code;
8. duplicate code;
9. long functions;
10. excessive optional fields;
11. exception quality;
12. comments.

Fix all findings.

## Audit 5: Tests and integration

Check:

1. missing policy coverage;
2. obsolete tests;
3. weak assertions;
4. over-mocking;
5. duplicated fixtures;
6. consumer breakage;
7. artifact round trips;
8. stage behavior;
9. full suite stability;
10. idempotence.

Fix all findings.

After the five audits, perform one final holistic audit. Repeat the loop when any material issue remains.

---

# 13. Completion Search

Before declaring completion, search the entire repository for:

```text
ThresholdEstimatorRegistry
ESTIMATOR_KIND_REGISTRY
ThresholdEstimator
ThresholdOwnerKind
ThresholdOwnership
ThresholdPolicyRecord
selected_coefficient
quantile_override
fingerprint_features_override
aggregation_formula
global_mean_formula
pooled_variance_formula
rank_formula
interpolation_formula
provenance_separation
exchangeability_limitation
diagnostics: object
dict[str, object]
arbitrary_types_allowed
BeforeValidator(dict)
type: ignore
TODO
FIXME
deprecated
legacy
compat
shim
redirect
re-export
```

For each occurrence:

1. prove it is legitimate under the target architecture; or
2. remove it.

Do not ignore occurrences in tests, configuration, documentation, or scripts.

Also search for old module paths. No old path may remain merely because imports still work through a shim.

---

# 14. Git and Cleanup Rules

Do not use Git history as a substitute for understanding the current code.

Do not revert unrelated user work.

Do not modify unrelated files unless required by the thresholding migration.

Keep the working tree understandable throughout the task.

After all gates pass:

1. remove generated smoke outputs;
2. remove caches introduced by the task where appropriate;
3. delete `.tmp/thresholding-refactor`;
4. verify no temporary files remain;
5. inspect the final diff manually;
6. confirm no unrelated changes were included;
7. create one intentional commit for the completed thresholding refactor;
8. push the completed commit when repository credentials and the intended remote are available;
9. never push a failing or partially migrated state.

Use a clear commit message describing the architectural refactor, not a vague “cleanup” message.

---

# 15. Required Final Report

Provide a factual final report containing:

1. final verdict;
2. final source tree;
3. final test tree;
4. files deleted;
5. files added;
6. major files adapted outside thresholding;
7. old abstractions removed;
8. configuration fields removed;
9. YAML files changed;
10. scientific behavior preserved;
11. confirmed defects fixed;
12. test results with exact command outcomes;
13. static-analysis results;
14. import-linter result;
15. SonarCloud result;
16. CodeScene result;
17. smoke-test result;
18. idempotence result;
19. commit hash;
20. push result;
21. any external tool that was unavailable.

Do not claim:

```text
complete
clean
fully tested
no drift
production ready
go
```

unless the corresponding evidence exists.

When a gate could not be executed, state that explicitly. Do not replace missing evidence with confidence language.

---

# 16. Definition of Done

This task is done only when all of the following are true:

1. `src/datp_core/thresholding` matches the target cohesive architecture.
2. Every real consumer uses the new API directly.
3. Every obsolete thresholding file is deleted.
4. Every old import is removed.
5. No compatibility code exists.
6. No redirect or shim exists.
7. No old/new dual representation exists.
8. Descriptive configuration is gone from Python.
9. Descriptive configuration is gone from YAML.
10. Every remaining configuration field is executable.
11. Every policy is strictly typed.
12. Every policy is directly tested.
13. Diagnostics are typed and lossless.
14. Calibration behavior is explicit and deterministic.
15. Federated calculations preserve federated semantics.
16. Cluster behavior is deterministic and fully diagnosed.
17. Conformal failure behavior is coherent.
18. Empty and insufficient inputs fail explicitly.
19. Tests and fixtures are debloated.
20. Ruff passes.
21. Formatting passes.
22. Strict type checking passes.
23. Pylint passes when configured.
24. import-linter passes.
25. Thresholding tests pass.
26. Impacted package tests pass.
27. Full repository tests pass.
28. Smoke flows pass.
29. SonarCloud findings are addressed or honestly unavailable.
30. CodeScene findings are addressed or honestly unavailable.
31. At least five audits have been completed.
32. A final holistic audit finds no remaining material issue.
33. Re-running the task produces no further changes.
34. Temporary files and outputs are removed.
35. The final commit contains no unrelated changes.

Continue until every achievable condition is satisfied. Do not stop at a partial implementation, a passing narrow test subset, or a superficially cleaner package.

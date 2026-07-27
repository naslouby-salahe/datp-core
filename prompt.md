# Goal: Completely Debloat, Refactor, Validate, and Finalize `datp_core.evaluation`

Work continuously and idempotently until the `src/datp_core/evaluation` package reaches the architecture, correctness, scientific-integrity, typing, testing, and cleanliness goals defined below.

Do not stop after producing an analysis, plan, partial implementation, passing focused tests, or a superficial cleanup. Continue through planning, independent plan audits, replanning, implementation, integration, test adaptation, repository-wide caller migration, repeated audits, and final verification.

The task is complete only after every mandatory checklist is satisfied and two consecutive independent final audit rounds find no unresolved issue.

---

# 1. Repository and Scope

Repository:

```text
/home/naslouby/Projects/datp-core
```

Primary package:

```text
src/datp_core/evaluation
```

The package includes all evaluation definitions, runtime models, operating-point metrics, AUROC computation, cross-client diagnostics, score-distribution projections, threshold trade-offs, calibration-variance analysis, and evaluation-stage execution.

The scope also includes every directly affected:

* caller;
* import;
* configuration model;
* YAML field;
* artifact schema;
* pipeline context;
* stage registration;
* reporting consumer;
* analysis consumer;
* interface;
* fixture;
* unit test;
* integration test;
* architecture rule;
* documentation reference.

Do not restrict the work artificially to files currently under `src/datp_core/evaluation` when a clean migration requires adapting legitimate consumers elsewhere.

Do not perform unrelated repository-wide redesigns. Any external change must be directly required by the evaluation refactor and must be included in the impact map before editing.

Do not commit or push.

---

# 2. Mandatory Sources of Truth

Before planning or editing anything, read all of the following that exist.

## 2.1 Repository governance

Read:

```text
AGENTS.md
CLAUDE.md
ai/README.md
```

Then inspect the applicable files under:

```text
ai/agents/
ai/contracts/
ai/hooks/
ai/skills/
ai/workflows/
```

Select and follow the appropriate implementation, architecture-cleanup, typing, testing, scientific-integrity, no-backward-compatibility, dependency, and cleanup workflows.

Repository governance is mandatory. Do not duplicate or bypass its gates.

## 2.2 Scientific roadmap

Read every active, non-archived roadmap file completely:

```text
roadmap/00_ROADMAP_INDEX.md
roadmap/01_SCIENTIFIC_IDENTITY_AND_SCOPE.md
roadmap/02_CLAIMS_AND_DECISION_RULES.md
roadmap/03_EXPERIMENT_CATALOGUE.md
roadmap/04_EVALUATION_AND_REPORTING_PROTOCOL.md
roadmap/05_IMPLEMENTATION_ROADMAP.md
roadmap/06_REVIEWER_RISKS_AND_READINESS.md
roadmap/07_AUDIT_AND_DECISION_LOG.md
```

Also read:

```text
roadmap/SCIENTIFIC_SOURCE_OF_TRUTH.md
```

only if that file exists and remains active.

Enumerate `roadmap/` before proceeding. If additional active roadmap files exist, read them. Do not use archived, superseded, or historical files as authority when a current source exists.

## 2.3 Configuration

Read and trace the complete loading path for:

```text
configs/datasets/nbaiot.yaml
configs/datasets/ciciot2023.yaml
configs/datasets/edge_iiotset.yaml
configs/experiments.yaml
configs/protocols.yaml
configs/runtime.yaml
```

Do not invent scientific values, defaults, formulas, statuses, thresholds, estimators, `ddof`, interpolation rules, eligibility rules, or fallback behavior.

Scientific and behavioral settings must come from validated configuration when the roadmap treats them as configurable.

## 2.4 Existing implementation and consumers

Read the complete current implementation of:

```text
src/datp_core/evaluation/
```

Then search the full repository for every import, reference, construction, serialization, schema check, field name, string identifier, and output path related to the package.

Use semantic/code graph tooling such as Graphify when available. If an external tool is unavailable or quota-limited:

1. record the failure only under `.tmp/`;
2. continue with repository-native search and static inspection;
3. retry the unavailable tool before final completion;
4. never claim that a tool passed when it did not run.

---

# 3. Non-Negotiable Scientific Boundaries

The refactor must preserve the DATP scientific identity.

The core DATP ladder compares threshold-calibration scope while keeping the trained detector and score artifacts fixed. Do not introduce model retraining, aggregation changes, score transformation, label changes, or experimental redesign into the evaluation package.

Preserve all roadmap-defined semantics, including:

* calibration is benign-only;
* attack data are evaluation-only;
* the production prediction rule is exactly the configured rule, currently expected to be `score > threshold`;
* AUROC is threshold-independent;
* AUROC is a model-quality control and is not the primary thresholding verdict;
* CV(FPR) is the primary operating-point disparity metric where specified;
* per-client metrics are computed before cross-client aggregation;
* ineligible clients are handled according to explicit configured rules;
* missing-class and zero-denominator outcomes are represented explicitly;
* no metric may silently substitute a different metric;
* no test-set-driven threshold fitting or checkpoint selection may be introduced;
* no scientific value may be silently hardcoded;
* no metric formula, quantile estimator, variance definition, or eligibility rule may change without explicit roadmap/config support.

If code and roadmap disagree, treat the roadmap and active validated configuration as authoritative. Document the mismatch in `.tmp`, fix the implementation, update tests, and continue.

Do not reinterpret scientific behavior merely to simplify code.

---

# 4. Absolute Engineering Rules

The following are mandatory:

* No backward compatibility.
* No shims.
* No redirect modules.
* No compatibility wrappers.
* No deprecated aliases.
* No legacy import paths.
* No legacy configuration keys.
* No fallback to old field names.
* No duplicate old and new APIs.
* No re-exporting old symbols from new modules.
* No broad barrel exports.
* No placeholder implementations.
* No dead code.
* No commented-out code.
* No unused configuration fields.
* No unexplained `Any`.
* No untyped dictionaries as domain contracts.
* No stringly typed behavioral vocabulary when an enum or established value object is appropriate.
* No mass-edit scripts.
* No repository-wide regex replacement scripts.
* No generated migration layer.
* No temporary files outside `.tmp/`.
* No audit or planning reports left in production directories.
* No inline comments describing refactor history.
* No AI-style explanatory comments.
* No speculative abstractions.
* No one-class-per-file fragmentation.
* No wrapper classes without meaningful behavior.
* No library addition unless it removes meaningful custom code or boilerplate and fits repository dependency policy.
* No reduction in scientific validation or schema strictness to make tests pass.
* No weakening of typing checks.
* No skipping failures as “preexisting.”
* No declaring warnings, duplication, or quality findings to be false positives without resolving their actual cause.

Update all callers, tests, configuration, documentation, and schemas directly to the canonical design.

---

# 5. Parallel-Agent Operating Model

Use multiple subagents in parallel throughout planning, discovery, auditing, test design, and review.

Maintain at least six active subagents whenever six independent workstreams remain. Do not create fake parallelism and do not assign multiple agents to edit the same production file simultaneously.

The coordinator owns integration and the authoritative checklist.

## 5.1 Required initial read-only agents

Start at least these six independent agents before creating the implementation plan:

### Agent A — Scientific protocol guardian

Inspect the roadmap, configuration, metric definitions, eligibility behavior, AUROC role, CV(FPR), variance semantics, prediction rule, and output contracts.

Deliver:

* locked scientific invariants;
* code-to-roadmap mismatches;
* scientific drift risks;
* fields that must be config-driven;
* tests required to protect each invariant.

### Agent B — Architecture and ownership auditor

Inspect package boundaries, nested packages, barrel exports, redirect behavior, duplicate ownership, unnecessary modules, naming, dependencies, and the proposed flat target tree.

Deliver:

* current ownership map;
* target ownership map;
* files to merge;
* files to delete;
* symbols to delete;
* external modules that must be adapted.

### Agent C — Call-site and migration auditor

Search the full repository for all evaluation symbols, import paths, schemas, stage contexts, artifact names, YAML fields, fixtures, and reporting consumers.

Deliver:

* complete impact map;
* all callers requiring direct migration;
* obsolete imports;
* stale field names;
* old paths that must disappear;
* any hidden coupling that could break after flattening.

### Agent D — Polars and numerical-correctness auditor

Inspect DataFrame schemas, joins, group operations, null handling, finite-value handling, AUROC grouping, concatenation, ordering, quantiles, variance, Jensen–Shannon divergence, and Python boundary crossings.

Deliver:

* correctness defects;
* inefficient UDFs;
* schema inconsistencies;
* numerical edge cases;
* native Polars replacements;
* required regression tests.

### Agent E — Typing, models, and enum auditor

Inspect Pydantic models, dataclasses, optional-field bags, raw strings, status/value pairs, identifiers, dictionary contracts, immutability, strictness, and serialization boundaries.

Deliver:

* proposed enum list;
* Pydantic boundary models;
* internal dataclasses/value objects;
* invalid states currently representable;
* redundant classes;
* typing violations;
* opportunities to remove boilerplate.

### Agent F — Test and quality-gate auditor

Inspect all existing evaluation tests and directly affected downstream tests.

Deliver:

* current coverage map;
* misleading or duplicate tests;
* missing regression tests;
* obsolete tests to delete;
* target test tree;
* exact focused and final validation commands.

Additional agents may cover dependency reuse, stage architecture, artifact I/O, or independent review.

## 5.2 Editing ownership

After the plan passes both plan audits:

* assign disjoint production files to agents;
* assign test files separately where safe;
* prevent simultaneous edits to the same file;
* require each agent to review all direct callers of its owned file;
* require a second agent to review each completed workstream;
* let only the coordinator resolve integration conflicts and approve deletion of old modules.

Subagents must not independently introduce incompatible local architectures.

---

# 6. Idempotent Working State

Use:

```text
.tmp/evaluation-refactor/
```

for temporary planning and state only.

Maintain:

```text
.tmp/evaluation-refactor/inventory.md
.tmp/evaluation-refactor/impact-map.md
.tmp/evaluation-refactor/plan.md
.tmp/evaluation-refactor/checklist.md
.tmp/evaluation-refactor/findings.md
.tmp/evaluation-refactor/tool-status.md
```

These files exist only for crash recovery and coordination.

On rerun:

1. inspect the current repository state;
2. validate each previously checked item against the actual code;
3. discard stale conclusions;
4. resume from the first unsatisfied gate;
5. do not repeat completed edits unnecessarily;
6. do not restore deleted legacy structures;
7. do not create duplicated solutions.

Delete `.tmp/evaluation-refactor/` after all final audits pass.

---

# 7. Required Target Architecture

The final source tree is:

```text
src/datp_core/evaluation/
├── __init__.py
├── enums.py
├── specs.py
├── models.py
├── operating_points.py
├── diagnostics.py
├── distributions.py
└── stage.py
```

This target is locked unless a hard repository constraint makes one additional module unavoidable. Any deviation requires:

1. concrete evidence;
2. explicit justification in the plan;
3. approval from both independent plan audits;
4. proof that the deviation reduces rather than increases ownership fragmentation.

The final `__init__.py` must be a package marker only. It must not import or re-export package symbols.

The following old subpackages must be removed after all callers are migrated:

```text
src/datp_core/evaluation/definitions/
src/datp_core/evaluation/distributions/
src/datp_core/evaluation/execution/
src/datp_core/evaluation/metrics/
```

Do not leave their `__init__.py` files, redirect files, deprecated paths, or compatibility imports.

## 7.1 File ownership

### `enums.py`

Own only behaviorally interpreted vocabularies, including the applicable subset of:

```text
MetricStatus
MetricDirection
MetricRole
MetricUnit
ZeroDenominatorPolicy
MissingClassPolicy
QuantileEstimator
WeightingMode
ComparisonUnit
RoundingMode
MissingThresholdPolicy
EvaluationArtifactKey
```

Before defining a new enum, search for an existing canonical project enum. Reuse it when its semantics match exactly.

Use `StrEnum` for YAML/Parquet-facing vocabulary unless repository standards require a different canonical base.

Do not turn free-form documentation or formulas into enums.

### `specs.py`

Own strict configuration and serialization-boundary models, including:

```text
MetricBundleSpec
ScalarMetricSpec
RatioMetricSpec
QuantileMetricSpec
DispersionMetricSpec
InvariantMetricSpec
CrossClientAggregationSpec
ThresholdEstimationSpec
HeterogeneityDiagnosticSpec
ClusterDiagnosticSpec
PrecisionPolicySpec
MetricDefinitions
EvaluationResultContract
```

Names may be adjusted to match established repository naming rules, but ownership and separation must remain.

Use an existing project-wide strict frozen Pydantic base model when one exists.

Otherwise introduce one canonical shared base in the appropriate existing core/configuration location, not a duplicate evaluation-only base, using strict configuration equivalent to:

```text
frozen = true
strict = true
extra = forbid
```

Do not keep the current broad `MetricFormulaRecord` optional-field bag.

### `models.py`

Own immutable runtime values, such as:

```text
MetricValue
FprDispersion
CdfPoint
ThresholdPosition
ClientScoreDistribution
ThresholdTradeoff
QuantileVarianceTerms
```

Prefer frozen, slotted, keyword-only dataclasses for internal values that do not require Pydantic parsing or external serialization.

Every per-client runtime model must carry a typed `client_id`.

### `operating_points.py`

Own:

```text
evaluate_operating_points
operating-point Polars expressions
per-client AUROC computation
eligible-client metric computation
ineligible-client operating-point construction
canonical evaluation-result schema assembly
```

There must be one production implementation for confusion-derived metrics.

### `diagnostics.py`

Own:

```text
calculate_fpr_dispersion
assert_auroc_invariant
calculate_pairwise_js_divergence
calculate_calibration_variance
```

Keep deterministic metric diagnostics here. Do not place inferential statistics or manuscript-level statistical tests here.

### `distributions.py`

Own:

```text
client_score_distributions
empirical CDF construction
threshold positions
threshold trade-offs
```

### `stage.py`

Own only the evaluation stage handler.

The handler must perform:

* typed context access;
* artifact reads;
* canonical validation;
* pure evaluation call;
* artifact writes;
* outcome translation.

It must not contain metric formulas, eligibility branching, AUROC logic, or schema construction.

---

# 8. Mandatory Correctness Fixes

The following defects are blocking. Verify them against the actual current code, fix them, and add regression tests.

## 8.1 Mixed eligible/ineligible schema defect

The current eligible and ineligible metric constructors produce incompatible schemas and are concatenated vertically.

Create one canonical output schema covering all clients.

Requirements:

* one row per scored client;
* exact, stable column names;
* exact, stable dtypes;
* no duplicate columns after joins;
* eligible and ineligible rows share the same schema;
* unavailable values use explicit metric statuses;
* deterministic client ordering;
* schema validation after assembly.

Do not solve this using relaxed diagonal concatenation or nullable untyped catch-all columns. Build the correct schema deliberately.

## 8.2 AUROC grouping defect

The current grouped AUROC computation can lose `client_id` while the caller later joins on `client_id`.

Replace the current `map_groups()` pattern.

Requirements:

* preserve typed client identity;
* avoid Python grouped DataFrame UDFs;
* use native Polars grouped aggregation where possible;
* use a narrow scalar function only where `roc_auc_score` is required;
* produce exactly one AUROC row per client;
* preserve deterministic ordering;
* explicitly handle single-class clients;
* validate finite scores before computation.

## 8.3 AUROC eligibility coupling

AUROC is threshold-independent.

Requirements:

* compute AUROC for every scored client;
* do not mark AUROC unavailable merely because threshold calibration is ineligible;
* use single-class status only when the test labels genuinely contain one class;
* preserve AUROC for threshold-ineligible clients with both classes;
* join AUROC into the canonical result without duplicate status columns.

## 8.4 Hidden missing-threshold behavior

Remove the implicit behavior based on an unrelated optional context field such as `calibration_sample_count is None`.

Introduce an explicit enum-backed missing-threshold policy, for example:

```text
MissingThresholdPolicy.FAIL
MissingThresholdPolicy.MARK_INELIGIBLE
```

The exact names must match repository naming standards.

Requirements:

* configure or derive the policy explicitly from the validated context;
* no boolean guessing;
* no `None`-driven behavioral branch;
* tests for every policy;
* invalid combinations rejected during context/config validation.

## 8.5 Optional threshold-policy identity

`threshold_policy_id` must be mandatory for an evaluation stage.

Requirements:

* make invalid context construction impossible;
* remove fallback-to-`None`;
* fail at validation time rather than during output construction;
* update all contexts, planners, tests, and callers.

## 8.6 Non-finite values

Validate:

* null;
* NaN;
* positive infinity;
* negative infinity.

Apply validation consistently to:

* scores;
* thresholds;
* metric inputs;
* CDF values;
* variance inputs;
* diagnostic arrays;
* relevant output values.

Do not silently drop non-finite rows.

## 8.7 Configured `ddof`

Trace `standard_deviation_ddof` from configuration to calculation.

Requirements:

* use the configured value in FPR dispersion;
* validate allowed values;
* test at least `ddof=0` and the configured nonzero case when supported;
* remove the configuration field only if the active roadmap proves it is obsolete;
* do not leave an unused scientific setting.

## 8.8 Variance decomposition

Implement and test the explicitly defined decomposition:

```text
total = within + between
between_ratio = between / (within + between)
```

Requirements:

* validate finite input;
* validate nonempty input;
* define behavior when total variance is zero;
* do not depend on an indirect pooled-variance shortcut;
* add identity/property tests.

---

# 9. Mandatory Structural Transformations

## 9.1 Remove barrel APIs

Delete broad exports from all current `__init__.py` files.

Update every caller to import from the canonical owning module.

Final verification must find no repository import from deleted paths.

## 9.2 Replace the generic optional-field metric record

The current metric specification permits unrelated combinations of:

* formula;
* unit;
* direction;
* zero-denominator behavior;
* missing-class behavior;
* quantile estimator;
* comparison unit;
* weighting;
* invariance checks;
* denominator stabilizers;
* client-count constraints.

Replace it with narrow typed specifications.

A ratio metric must not accept quantile-only fields. An invariant must not accept denominator behavior unless scientifically applicable. Invalid combinations must fail Pydantic validation.

Use discriminated variants only where necessary for YAML parsing.

Do not create a generic dictionary payload as a replacement.

## 9.3 Replace raw behavioral strings

Replace interpreted strings with canonical enums or identifiers.

At minimum, inspect:

```text
metric statuses
direction
unit
role
zero-denominator behavior
missing-class behavior
quantile estimator
weighting
comparison unit
rounding
missing-threshold policy
artifact keys
metric identifiers
client identifiers
result identifiers
```

Do not enum arbitrary human-readable formulas.

## 9.4 Remove duplicated metric implementations

The production confusion-derived metrics must have one implementation.

Inspect `ClientConfusionMatrix` and the vectorized Polars implementation.

Delete `ClientConfusionMatrix` if it merely duplicates production formulas and has no independent domain purpose.

Tests must exercise the production implementation instead of validating a parallel implementation that can drift.

## 9.5 Merge AUROC result semantics

Delete the redundant AUROC-specific value/status wrapper when `MetricValue` already models availability correctly.

Support constructors such as:

```text
MetricValue.available(...)
MetricValue.unavailable(...)
```

Do not maintain two separate value/status abstractions.

## 9.6 Replace metric value/status pairs

Replace fields such as:

```text
false_positive_rate
false_positive_rate_status
true_positive_rate
true_positive_rate_status
balanced_accuracy
balanced_accuracy_status
macro_f1
macro_f1_status
```

inside runtime domain models with typed `MetricValue` fields.

Ensure serialization, artifact generation, and reporting projections remain explicit and typed.

## 9.7 Eliminate dictionary-based domain outputs

Replace public domain outputs such as:

```text
dict[str, ClientScoreDistributionRecord]
dict[str, ThresholdTradeoffEntry]
```

with deterministic typed collections such as:

```text
tuple[ClientScoreDistribution, ...]
tuple[ThresholdTradeoff, ...]
```

Each record must contain `client_id`.

Use mappings only as private local indexes when they genuinely simplify an algorithm. Do not expose them as the domain contract.

## 9.8 Minimize Python crossings from Polars

Refactor distribution and metric code to:

* validate frames first;
* join data in Polars;
* aggregate in Polars;
* sort deterministically;
* avoid repeated per-client filtering;
* avoid `to_dicts()` for normal processing;
* avoid grouped `map_groups()`;
* avoid unnecessary NumPy conversion;
* cross into Python only when constructing final immutable records or calling a library function that requires arrays.

Do not sacrifice readability merely to remove every loop. Remove loops that duplicate DataFrame work or cause repeated scans.

## 9.9 Use appropriate libraries

Check existing dependencies before adding anything.

Preferred existing tools:

* Polars for DataFrame operations;
* Pydantic v2 for validated boundary schemas;
* NumPy for numerical arrays where necessary;
* scikit-learn for `roc_auc_score`;
* SciPy for Jensen–Shannon computation when already available or acceptable under dependency policy.

When using `scipy.spatial.distance.jensenshannon`, remember that it returns distance. Square it when the scientific contract requires divergence.

Do not introduce Pingouin in this package. Pingouin belongs in inferential analysis, not deterministic evaluation metric construction.

Do not add a dependency for trivial functionality.

## 9.10 Centralize artifact I/O correctly

Inspect the artifact-store abstraction.

If canonical Parquet read/write methods already exist, use them.

If the repository repeatedly duplicates `BytesIO` Parquet handling and the artifact layer owns serialization, add narrowly scoped canonical methods such as:

```text
read_parquet(...)
write_parquet_atomic(...)
```

only after auditing all affected callers.

Do not create an evaluation-specific codec or wrapper merely to hide two lines.

## 9.11 Replace runtime assertions

Do not use `assert` for context or runtime validation.

Use:

* typed generic stage contracts where available;
* Pydantic validation;
* explicit domain validation;
* precise stage failure outcomes.

Assertions may remain only for impossible internal invariants that are already guaranteed by validated input and are not user/runtime error handling.

## 9.12 Exceptions

Search for existing canonical project exceptions before adding new ones.

Reuse them when semantics match.

Add at most a small, meaningful evaluation exception surface such as:

```text
EvaluationContractError
EvaluationInvariantError
```

only if existing errors cannot express the failure.

Do not create one exception per metric or a bloated exception hierarchy.

## 9.13 Comments and naming

Remove comments that narrate implementation history, including statements such as:

```text
Polars unique before Python bridge
Column-based access instead of row iteration
Polars-native aggregation eliminates...
```

Do not add inline comments.

Keep only concise docstrings required by repository standards.

Use precise names. Remove aliases such as `stable`, `_thresh`, `values`, or `shifted` when their meaning is ambiguous.

---

# 10. Planning Protocol

Do not edit production code before the planning protocol passes.

## Phase P1 — Inventory

Produce a complete inventory containing:

* current source tree;
* line count per file;
* class/function list;
* imports and exports;
* external call sites;
* configuration fields;
* runtime artifact schemas;
* test coverage;
* architecture rules;
* duplicate calculations;
* dead symbols;
* existing quality failures.

Run baseline focused checks before editing and record the exact results.

Do not fix anything during the inventory phase.

## Phase P2 — Initial plan

Create a file-by-file plan containing, for every touched file:

* current responsibility;
* final responsibility;
* symbols retained;
* symbols renamed;
* symbols merged;
* symbols deleted;
* imports updated;
* callers updated;
* configuration changes;
* tests adapted;
* focused command to validate the change;
* cleanup action.

The plan must include the exact order in which old modules can be deleted without leaving redirect paths.

## Phase P3 — Independent plan audit A

Have an architecture/typing agent audit the plan for:

* ownership clarity;
* unnecessary modules;
* enum misuse;
* excessive models;
* wrapper classes;
* compatibility leakage;
* dead code;
* dictionary contracts;
* Pydantic/dataclass boundary;
* dependency bloat;
* target-tree compliance.

All findings must be either fixed in the plan or rejected with concrete repository evidence.

## Phase P4 — Replan

Rewrite the plan after Audit A. Do not append vague notes. Integrate the decisions into the actual steps and checklists.

## Phase P5 — Independent plan audit B

Have a scientific/runtime/testing agent audit the revised plan for:

* scientific drift;
* roadmap conflicts;
* configuration ownership;
* metric formulas;
* eligibility behavior;
* AUROC semantics;
* DataFrame schemas;
* numerical edge cases;
* migration completeness;
* test sufficiency;
* stage integration;
* output compatibility as a scientific contract, not backward compatibility.

## Phase P6 — Final replan and gate

Integrate Audit B findings.

Implementation may begin only when:

* both audit agents return no unresolved blocker;
* every target file has explicit ownership;
* every old file has a delete/migrate decision;
* every external caller is mapped;
* every mandatory defect has a planned regression test;
* the final tree is explicit;
* no compatibility layer is planned.

---

# 11. Implementation Loop

Process the implementation in controlled workstreams.

For each production file or tightly coupled pair of files:

1. inspect the full current file;
2. inspect every direct caller;
3. inspect corresponding tests;
4. restate the local contract in the checklist;
5. implement the canonical replacement;
6. update all direct imports and callers immediately;
7. update, remove, or add the corresponding tests;
8. run formatting and lint on touched files;
9. run the smallest meaningful focused tests;
10. run focused typing checks where supported;
11. have a second agent review the completed workstream;
12. fix every review finding;
13. rerun the focused checks;
14. mark the item complete only after the second review passes;
15. proceed to the next workstream.

Do not postpone test adaptation until the end.

Do not leave old and new implementations side by side longer than necessary.

Test files may be processed in parallel when they cover disjoint behavior. Production files with shared schemas must not be edited concurrently without explicit ownership boundaries.

---

# 12. Recommended Implementation Order

Use this order unless the audited dependency graph proves a safer equivalent.

## Workstream 1 — Enums and specifications

* identify existing canonical enums;
* create missing evaluation enums;
* replace stringly typed configuration fields;
* split metric specification variants;
* make models strict and frozen;
* make `threshold_policy_id` mandatory;
* introduce explicit missing-threshold behavior;
* update YAML/config loading and tests;
* remove unused configuration fields.

## Workstream 2 — Runtime models

* consolidate `MetricValue`;
* remove redundant `ClientAuroc`;
* remove duplicate confusion-matrix implementation if unused;
* replace status/value field pairs;
* add typed `client_id` to per-client records;
* replace dictionary domain outputs with ordered tuples;
* add model invariants and focused tests.

## Workstream 3 — Operating-point evaluation

* define canonical input and output schemas;
* implement one complete `evaluate_operating_points`;
* fix mixed eligibility;
* compute AUROC independently;
* remove grouped DataFrame UDFs;
* enforce finite-value checks;
* use explicit statuses;
* produce deterministic output;
* add exhaustive eligibility and AUROC tests.

## Workstream 4 — Diagnostics

* apply configured `ddof`;
* implement exact FPR-dispersion semantics;
* implement explicit variance decomposition;
* simplify JS divergence using an approved library or clear vectorized implementation;
* preserve shared histogram-edge semantics;
* test numerical boundaries and identities.

## Workstream 5 — Distribution projections

* consolidate CDF, threshold-position, and trade-off logic;
* avoid repeated client scans;
* return deterministic typed tuples;
* preserve empty benign/attack behavior;
* test duplicates, ordering, missing metrics, and population mismatch.

## Workstream 6 — Stage handler and artifact integration

* make the handler thin;
* remove hidden eligibility branching;
* use canonical artifact I/O;
* use typed context validation;
* remove runtime assertions;
* ensure exact output validation;
* update stage registration, contexts, planners, and integration tests.

## Workstream 7 — Delete old structure

Only after all imports and tests use canonical modules:

* delete old modules;
* delete nested `__init__.py` files;
* search for all deleted import paths;
* remove obsolete fixtures and tests;
* remove stale documentation paths;
* verify no redirect remains.

---

# 13. Required Test Tree

Target:

```text
tests/unit/evaluation/
├── test_specs.py
├── test_operating_points.py
├── test_diagnostics.py
├── test_distributions.py
└── test_stage.py

tests/integration/evaluation/
└── test_stage_artifacts.py
```

Adapt naming to established test layout only when repository structure requires it. Do not create unnecessary nested packages.

Delete tests that:

* test deleted compatibility behavior;
* mirror implementation details;
* validate duplicate metric formulas;
* preserve obsolete imports;
* assert broad Pydantic field bags;
* exist only for redirects or re-exports.

Keep or add behavior-focused tests.

## 13.1 Specification tests

Cover:

* strict validation;
* unknown-field rejection;
* frozen behavior;
* discriminated metric variants;
* invalid field combinations;
* enum parsing;
* mandatory threshold-policy identity;
* explicit missing-threshold policy;
* configured `ddof`;
* no silent defaults for scientific fields.

## 13.2 Operating-point tests

Cover:

* all clients eligible;
* mixed eligible and ineligible clients;
* every client ineligible;
* missing threshold configured as failure;
* missing threshold configured as ineligible;
* exact `score > threshold` behavior;
* score exactly equal to threshold;
* benign-only client;
* attack-only client;
* both classes;
* no rows;
* duplicate client rows;
* AUROC available for threshold-ineligible clients with both classes;
* AUROC unavailable only for genuine single-class clients;
* finite-value rejection;
* exact output columns;
* exact output dtypes;
* exact output row count;
* deterministic ordering;
* no duplicate AUROC columns;
* stable status semantics.

## 13.3 Diagnostic tests

Cover:

* empty FPR population;
* one-client population;
* configured `ddof=0`;
* configured nonzero `ddof` where supported;
* zero mean FPR;
* near-zero mean FPR;
* CV instability threshold;
* IQR;
* range;
* worst-client FPR;
* finite-value rejection;
* AUROC invariance pass;
* AUROC invariance failure;
* identical-distribution JS divergence equals zero;
* JS symmetry;
* deterministic shared histogram bins;
* minimum-client requirement;
* zero total variance;
* within-only variance;
* between-only variance;
* `total = within + between`;
* `between_ratio = between / total`.

## 13.4 Distribution tests

Cover:

* deterministic client ordering;
* empty benign score list;
* empty attack score list;
* duplicate score CDF semantics;
* threshold below all scores;
* threshold above all scores;
* threshold equal to duplicated scores;
* missing metric row;
* missing threshold row;
* client filter success;
* unavailable client filter;
* incompatible trade-off client populations;
* unavailable metric delta;
* client identity retained in every output record.

## 13.5 Stage tests

Cover:

* successful artifact read/evaluate/write;
* strict context validation;
* missing required input;
* malformed threshold artifact;
* malformed score artifact;
* non-finite values;
* explicit missing-threshold policies;
* exact output artifact schema;
* atomic write;
* precise failure outcome;
* no partial output after failure;
* deterministic repeated execution.

## 13.6 Property-based testing

Use Hypothesis where it materially improves confidence.

Good candidates:

* confusion-count identities;
* metric range constraints;
* CDF monotonicity;
* CDF final probability;
* JS symmetry and non-negativity;
* variance decomposition;
* deterministic sorting;
* schema stability.

Do not add property tests that simply reproduce library behavior or create excessive test complexity.

---

# 14. Validation Strategy

## 14.1 Tool discovery

Before running checks, inspect:

```text
pyproject.toml
tox.ini
noxfile.py
Makefile
justfile
.github/workflows/
```

Determine the repository’s canonical commands.

Check availability of:

* Ruff;
* Pyright;
* Pylance checks or configured equivalent;
* Pylint;
* pytest;
* pytest-xdist;
* import-linter;
* SonarCloud tooling;
* CodeScene tooling;
* Graphify.

Do not invent command names.

## 14.2 During implementation

After each file/workstream, run:

* formatter on touched files;
* lint on touched files;
* relevant unit tests;
* relevant type checks;
* relevant import-contract checks when boundaries changed.

Do not run the entire test suite after every small edit.

## 14.3 After package implementation is structurally complete

Run, in this order:

1. all evaluation unit tests;
2. all directly impacted downstream unit tests;
3. evaluation integration tests;
4. directly impacted pipeline/stage tests;
5. Ruff formatting check;
6. Ruff lint;
7. Pyright;
8. Pylance-configured analysis where available;
9. Pylint using repository configuration;
10. import-linter;
11. dependency/unused-import checks;
12. package structure scan;
13. no-backward-compatibility scan;
14. comment and clutter scan.

Fix every failure before continuing.

## 14.4 Full repository validation

Run the full suite only after the package and impacted tests are complete.

Use the repository’s configured pytest-xdist mode when safe.

Do not reduce batch sizes or alter scientific/runtime configuration merely to make tests cheaper.

Tests requiring CUDA must explicitly check CUDA availability and skip only when the test contract permits it. Do not hide genuine failures behind unconditional skips.

Run configured SonarCloud and CodeScene checks when accessible. Fix all issues in touched scope, including duplication, maintainability, naming, and complexity findings. Retry unavailable external checks before final completion.

---

# 15. Mandatory Audit Loop

After all implementation and tests appear green, begin the audit loop.

Each audit must inspect actual code, not merely trust previous reports.

## Audit 1 — Target structure and ownership

Checklist:

* [ ] Final source tree matches the locked target.
* [ ] Every module has one clear responsibility.
* [ ] No unnecessary package layer remains.
* [ ] No broad `__init__.py` exports remain.
* [ ] No wrapper-only module remains.
* [ ] No duplicate owner exists for a metric or model.
* [ ] No dead symbol remains.
* [ ] No avoidable fragmentation remains.

## Audit 2 — Clean-break migration

Checklist:

* [ ] No old evaluation import path remains.
* [ ] No shim remains.
* [ ] No redirect remains.
* [ ] No alias preserves an old symbol.
* [ ] No deprecated configuration key remains.
* [ ] No compatibility test remains.
* [ ] No old and new implementation coexist.
* [ ] Every caller uses the canonical API directly.

## Audit 3 — Scientific integrity

Checklist:

* [ ] Roadmap prediction rule is preserved exactly.
* [ ] Benign-only calibration semantics are preserved.
* [ ] AUROC is threshold-independent.
* [ ] AUROC remains a control metric.
* [ ] Eligibility behavior is explicit.
* [ ] Missing-class behavior is explicit.
* [ ] Zero-denominator behavior is explicit.
* [ ] `ddof` comes from validated configuration.
* [ ] Quantile and variance definitions match the roadmap.
* [ ] No scientific value was invented.
* [ ] No hardcoded scientific default was introduced.
* [ ] No output metric was silently substituted.
* [ ] No scope drift was introduced.

## Audit 4 — Runtime and numerical correctness

Checklist:

* [ ] Eligible/ineligible schemas are identical.
* [ ] AUROC preserves `client_id`.
* [ ] All scored clients receive an AUROC result/status.
* [ ] Non-finite values are rejected.
* [ ] Empty and single-class cases are defined.
* [ ] Sorting is deterministic.
* [ ] All joins have validated cardinality.
* [ ] No duplicate metric columns are possible.
* [ ] Variance decomposition identity holds.
* [ ] JS divergence semantics are correct.
* [ ] CDF semantics are correct for duplicate scores.
* [ ] DataFrame operations avoid unnecessary Python UDFs.

## Audit 5 — Types and models

Checklist:

* [ ] No unjustified `Any` remains.
* [ ] No raw dictionary is exposed as a domain contract.
* [ ] Every behavioral vocabulary uses the correct enum/value object.
* [ ] Every per-client record contains typed client identity.
* [ ] Pydantic is restricted to boundaries.
* [ ] Runtime values use lightweight immutable models.
* [ ] Invalid configuration combinations are unrepresentable.
* [ ] Optional fields are genuinely optional.
* [ ] No redundant value/status abstraction remains.
* [ ] No duplicate formula implementation remains.

## Audit 6 — Boilerplate and dependencies

Checklist:

* [ ] Repeated Pydantic configuration is centralized.
* [ ] Repeated Parquet I/O is removed where ownership permits.
* [ ] Repeated status construction is centralized.
* [ ] Custom numerical code is retained only when clearer or scientifically necessary.
* [ ] No unnecessary dependency was added.
* [ ] No dependency is used merely to hide trivial logic.
* [ ] No excessive abstraction replaced simple typed code.
* [ ] No unused dependency remains after refactoring.

## Audit 7 — Tests

Checklist:

* [ ] Every mandatory defect has a regression test.
* [ ] Tests assert behavior, not old structure.
* [ ] Obsolete tests are deleted.
* [ ] No compatibility behavior is tested.
* [ ] Edge cases are covered.
* [ ] Output schema is tested exactly.
* [ ] Scientific invariants are protected.
* [ ] Stage artifact behavior is covered.
* [ ] Focused tests pass.
* [ ] Impacted tests pass.
* [ ] Full suite passes.

## Audit 8 — Naming, comments, and cleanliness

Checklist:

* [ ] No vague variable names remain.
* [ ] No refactor-history comments remain.
* [ ] No commented-out code remains.
* [ ] No debug prints remain.
* [ ] No temporary report remains outside `.tmp`.
* [ ] No random root file was created.
* [ ] No stale test fixture remains.
* [ ] No unused import remains.
* [ ] No unused configuration field remains.
* [ ] No `.tmp/evaluation-refactor` content remains after completion.

## Audit 9 — Preexisting and adjacent issues

Inspect every touched file and direct caller for issues not explicitly listed in this prompt.

Checklist:

* [ ] Existing typing defects are fixed.
* [ ] Existing lint defects are fixed.
* [ ] Existing architecture violations are fixed.
* [ ] Existing duplicated logic is fixed.
* [ ] Existing misleading names are fixed.
* [ ] Existing stale comments are removed.
* [ ] Existing schema inconsistencies are fixed.
* [ ] Existing missing validation is fixed.
* [ ] Existing test weaknesses in touched behavior are fixed.
* [ ] No newly discovered issue was deferred merely because it predated this task.

---

# 16. Repeat-Until-Clean Rule

After the first full audit round:

1. collect every finding;
2. reopen the implementation checklist;
3. assign findings to disjoint agents;
4. fix all findings;
5. rerun focused checks;
6. rerun impacted checks;
7. rerun all package checks;
8. rerun the complete audit round.

When one complete audit round passes, perform a second cold audit using agents that did not own the corresponding implementation work.

The second audit must begin from the code and roadmap, not from the first audit’s conclusions.

Completion requires:

```text
two consecutive complete audit rounds
with zero unresolved findings
and no production-code changes between the final green audit and final report
```

If the second audit finds any issue, return to implementation and restart the two-clean-audit requirement.

Do not stop because the package “looks good,” tests pass, or most checklist items pass.

---

# 17. Final Acceptance Criteria

The task is finished only when all of the following are true:

* [ ] All roadmap and governance files were read.
* [ ] The full evaluation dependency graph was inspected.
* [ ] The initial plan was independently audited.
* [ ] The plan was revised.
* [ ] The revised plan received a second independent audit.
* [ ] The package matches the target source tree.
* [ ] Old subpackages are deleted.
* [ ] No compatibility mechanism remains.
* [ ] All repository callers use canonical direct imports.
* [ ] The optional-field metric bag is removed.
* [ ] Behavioral strings are replaced appropriately.
* [ ] Domain dictionary outputs are removed.
* [ ] Duplicate metric implementations are removed.
* [ ] AUROC grouping and identity are correct.
* [ ] AUROC is independent of threshold eligibility.
* [ ] Mixed eligibility uses one exact schema.
* [ ] Missing-threshold behavior is explicit.
* [ ] Threshold-policy identity is mandatory.
* [ ] Non-finite values are rejected.
* [ ] Configured `ddof` is honored.
* [ ] Variance decomposition is explicit and tested.
* [ ] Polars work is vectorized where appropriate.
* [ ] Stage orchestration is thin.
* [ ] Artifact I/O follows canonical ownership.
* [ ] Every directly affected test is adapted.
* [ ] Obsolete tests are deleted.
* [ ] Mandatory regression tests exist.
* [ ] Ruff passes.
* [ ] Pyright passes.
* [ ] Pylance-configured checks pass where available.
* [ ] Pylint passes.
* [ ] Import-linter passes.
* [ ] Focused tests pass.
* [ ] Impacted tests pass.
* [ ] Full test suite passes.
* [ ] Configured SonarCloud/CodeScene checks pass when accessible.
* [ ] Two consecutive complete audits pass.
* [ ] Temporary work files are deleted.
* [ ] The final tree is clean and contains no dead code.

---

# 18. Final Response

Do not provide a premature status update as the final answer.

The final response must contain:

1. final verdict: `COMPLETE` or an honest blocking verdict;
2. final source tree;
3. files created;
4. files merged;
5. files deleted;
6. external callers/configuration/tests adapted;
7. correctness defects fixed;
8. architectural and boilerplate reductions;
9. exact validation commands executed;
10. exact pass/fail results;
11. results of both final audit rounds;
12. confirmation that no compatibility layer, shim, redirect, deprecated alias, or legacy import remains;
13. confirmation that `.tmp/evaluation-refactor/` was removed;
14. any genuine external tool that could not run, including the exact reason.

Do not claim `COMPLETE` while any checklist item is unresolved.

Do not ask whether to continue. Continue working until the acceptance criteria are met or a genuine external blocker makes further progress impossible. Even when an external blocker exists, complete every other actionable item before reporting it.

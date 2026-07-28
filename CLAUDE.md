# CLAUDE.md — DATP-Core Engineering and Scientific Contract

## 1. Purpose

DATP-Core is the clean journal-extension implementation of Device-Aware Threshold Personalization for non-IID federated IoT anomaly detection.

The repository must remain:

* scientifically faithful;
* configuration-driven;
* strongly typed;
* deterministic;
* minimal;
* reusable;
* auditable;
* free of legacy compatibility layers;
* aligned with the existing project structure.

This file governs all implementation, refactoring, testing, configuration, validation, and cleanup work performed in this repository.

---

## 2. Scientific Source of Truth

Before making any scientifically meaningful change, read:

```text
/home/naslouby/Projects/datp-core/docs/Journal_Extension_Master_Roadmap.md
```

This roadmap is the authoritative source for:

* scientific identity;
* experimental scope;
* datasets and regimes;
* policy and comparator semantics;
* confirmatory and supportive claims;
* experiment definitions;
* seed requirements;
* split semantics;
* threshold rules;
* evaluation metrics;
* statistical procedures;
* claim gates;
* boundary conditions;
* exclusions;
* terminology;
* interpretation of null, weak, mixed, and negative results.

Do not rely on memory, comments, test names, old outputs, previous implementations, or inferred intent when the roadmap provides an answer.

### 2.1 Authority order

When sources disagree, apply this order:

1. `docs/Journal_Extension_Master_Roadmap.md`
2. Explicit, validated repository configuration
3. Current typed domain contracts
4. Current implementation
5. Tests
6. Comments, old outputs, filenames, and historical conventions

Tests and implementation must be corrected to match the roadmap. The roadmap must never be silently changed to justify existing code.

### 2.2 Missing scientific information

Never invent or infer missing scientific values.

Do not guess:

* seeds;
* split ratios;
* thresholds;
* quantiles;
* client counts;
* dataset capabilities;
* experiment membership;
* statistical significance rules;
* fallback behavior;
* checkpoint rules;
* calibration sizes;
* aggregation parameters;
* hardware assumptions;
* claim wording.

When the roadmap and configuration do not define a required value, stop that part of the implementation and report the missing decision clearly.

Do not hide missing information behind a default.

---

## 3. Locked Scientific Identity

All work must preserve the scientific identity defined in the roadmap.

At minimum, continuously verify that:

* the core DATP causal ladder studies threshold-calibration scope rather than model selection;
* the trained detector remains fixed wherever the roadmap requires a fixed detector;
* the same eligible score artifacts are reused across threshold-policy comparisons where required;
* calibration remains benign-only;
* attack data remain evaluation-only unless the roadmap explicitly defines another role;
* threshold construction does not access test labels or test outcomes;
* AUROC remains a model-quality control rather than the threshold-policy verdict;
* per-client FPR disparity remains the central operating-point concern where specified;
* confirmatory, supportive, exploratory, stress-test, mechanism, and boundary-condition evidence remain clearly separated;
* training-side comparators remain outside the controlled threshold-scope ladder;
* no result is promoted beyond the claim tier permitted by the roadmap;
* negative, mixed, null, or absorption outcomes are reported rather than suppressed;
* out-of-scope research directions do not leak into the implementation.

Do not turn DATP-Core into a generic federated intrusion-detection benchmark.

Do not introduce attacks, defenses, privacy mechanisms, dynamic behavior, adaptive behavior, deployment claims, or new scientific modules unless they are already present in the roadmap or explicitly requested.

---

## 4. Existing Source Tree Is Closed

The existing `src` file tree has already been designed and is authoritative.

### 4.1 Absolute rule

Do not create any new file or directory under:

```text
src/
```

This includes:

* modules;
* packages;
* helper files;
* utility files;
* compatibility modules;
* adapter modules;
* temporary implementations;
* duplicated “clean” replacements;
* versioned alternatives;
* experimental copies.

Implement every change within the responsibilities of the existing files.

### 4.2 Structural changes

Do not rename or relocate existing source files unless explicitly instructed.

Deleting obsolete source files is allowed only when:

* their responsibility is genuinely unnecessary;
* all callers have been migrated;
* no compatibility redirect is retained;
* imports, tests, configurations, and documentation are updated;
* the resulting structure still matches the established project tree.

Do not create a new module merely because an existing module is large. First reduce duplication, remove dead paths, simplify abstractions, and reuse existing domain boundaries.

### 4.3 Responsibility discipline

Before editing a file:

1. Identify its established responsibility.
2. Confirm that the requested behavior belongs there.
3. Search for an existing implementation or abstraction.
4. Inspect all relevant callers and tests.
5. Extend the existing canonical path rather than creating a parallel path.

Do not place code in a convenient file when it belongs to another existing responsibility.

---

## 5. Reuse-First Rule

Never add a method, class, model, validator, enum, helper, fixture, factory, or abstraction before searching for reusable code.

Before adding anything:

1. Search the entire repository for equivalent behavior.
2. Search for similar names, concepts, fields, validation rules, and transformations.
3. Inspect existing enums and domain models.
4. Inspect configuration schemas.
5. Inspect nearby call sites.
6. Inspect existing library usage.
7. Inspect tests and fixtures.
8. Determine whether the behavior can be expressed by extending or composing an existing implementation.

Prefer, in order:

1. direct reuse;
2. parameterization of an existing implementation;
3. consolidation into an existing canonical implementation;
4. a focused extension to an existing abstraction;
5. new code only when no existing responsibility can correctly provide the behavior.

When duplication is discovered, remove it rather than adding another variation.

Do not create:

* pass-through wrappers;
* one-call helper methods;
* aliases for existing functions;
* duplicate validators;
* duplicate conversions;
* duplicate serializers;
* duplicate factories;
* parallel orchestration paths;
* alternate implementations selected by hidden fallbacks;
* abstractions with only one trivial caller and no domain value.

A new method must represent a real, reusable responsibility—not merely shorten one call site.

---

## 6. Deletion and Simplification Bias

Prefer deleting code over adding code when the same behavior already exists elsewhere.

Every change must look for opportunities to remove:

* duplicated logic;
* dead branches;
* unused parameters;
* obsolete abstractions;
* redundant models;
* compatibility paths;
* stale exports;
* unnecessary wrappers;
* manual boilerplate already supported by a library;
* redundant conversions;
* defensive fallbacks that conceal invalid state;
* tests for behavior that no longer exists;
* comments that merely narrate the code.

Do not retain unused code “for later.”

Do not preserve old APIs unless explicitly requested.

There is no backward-compatibility requirement.

---

## 7. No Backward Compatibility

Do not add or retain:

* compatibility shims;
* deprecated aliases;
* redirect modules;
* legacy import paths;
* dual schema support;
* old configuration key support;
* silent field renaming;
* compatibility serializers;
* adapter layers whose only purpose is preserving removed behavior;
* deprecated enum members;
* temporary migration branches;
* “legacy mode” switches.

When a contract changes:

1. update the canonical implementation;
2. migrate all callers;
3. update configuration;
4. update or remove affected tests;
5. delete the obsolete path.

Do not make the new implementation conform to stale tests. Adapt the tests to the correct contract.

---

## 8. Enum-First Domain Modeling

Use enums for every closed categorical domain.

Examples include:

* dataset identifiers;
* experiment identifiers;
* stages;
* threshold policies;
* comparator types;
* metric identifiers;
* split roles;
* artifact types;
* output categories;
* status values;
* capability types;
* statistical profile identifiers;
* model families;
* aggregation strategies;
* evaluation scopes;
* claim classifications.

### 8.1 Enum rules

* Reuse an existing enum before creating another.
* Never duplicate the same vocabulary in multiple enums.
* Prefer descriptive member names.
* Preserve roadmap identifiers only when the roadmap explicitly locks them.
* Do not compare enum-backed concepts using raw strings.
* Do not scatter enum `.value` comparisons through domain logic.
* Convert serialized values to enums at the boundary.
* Reject unknown values immediately.
* Do not add alias members for old names.
* Do not use plain strings as substitutes for known enum domains.
* Do not use booleans where an explicit multi-state enum communicates the domain more accurately.
* Use `StrEnum` for serialized textual categories where appropriate.
* Use numeric enums only when the numeric ordering has actual domain meaning.

Do not create an enum for arbitrary free text, measurements, paths, or unbounded values.

---

## 9. Strong Typing

All code must be explicitly and meaningfully typed.

### 9.1 Forbidden typing shortcuts

Do not introduce:

* `Any`;
* `dict[str, Any]`;
* `Mapping[str, object]` as a domain contract;
* untyped nested dictionaries;
* arbitrary JSON bags;
* `object` used to avoid proper modeling;
* unexplained unions;
* broad casts;
* unchecked type assertions;
* `# type: ignore`;
* blanket static-analysis suppressions.

Do not weaken an existing type merely to satisfy a new caller.

### 9.2 Typed boundaries

Use typed models for:

* configuration;
* experiment definitions;
* dataset capabilities;
* stage inputs and outputs;
* artifact coordinates;
* metric records;
* statistical results;
* threshold results;
* manifests;
* reporting structures;
* orchestration plans.

Dictionaries must not act as domain models.

When an external library requires a dictionary:

1. isolate the dictionary at the library boundary;
2. construct it from a typed model;
3. immediately convert external output back into a typed model;
4. do not propagate the dictionary through the application.

### 9.3 Model selection

Prefer the repository’s established modeling approach.

Typical roles are:

* Pydantic v2 models for configuration, validation, serialization, and external boundaries;
* frozen dataclasses or existing immutable value objects for internal domain state;
* enums for closed vocabularies;
* protocols or abstract interfaces only when multiple real implementations exist;
* standard library or established project libraries instead of handwritten boilerplate.

Do not introduce a second modeling framework for the same responsibility.

### 9.4 Immutability

Scientific plans, resolved configurations, coordinates, manifests, and result records should be immutable after validation.

Avoid:

* mutable global state;
* in-place mutation of shared scientific objects;
* hidden mutation during serialization;
* mutable default values;
* stateful helpers whose lifecycle is unclear.

---

## 10. Configuration-Driven Behavior

All scientific, experimental, runtime, and dataset-specific values must come from validated configuration unless the roadmap explicitly defines them as structural invariants.

### 10.1 No hardcoded values

Do not hardcode:

* seeds;
* split ratios;
* thresholds;
* quantiles;
* calibration sizes;
* client counts;
* cluster counts;
* experiment lists;
* dataset names;
* feature names;
* label values;
* round budgets;
* local epochs;
* batch sizes;
* checkpoint rules;
* statistical confidence levels;
* bootstrap settings;
* metric sets;
* path fragments;
* output folder names;
* device assumptions;
* resource limits;
* retry counts;
* timeout values;
* fallback policies.

Do not move hardcoded values from one Python file to another. Move them to the correct validated configuration or existing domain definition.

### 10.2 No defaults

Required behavior must be explicit.

Do not introduce:

* Pydantic defaults for required scientific or runtime values;
* default arguments containing scientific settings;
* `.get(key, fallback)` for required fields;
* `value or fallback`;
* implicit environment fallbacks;
* automatic dataset selection;
* automatic experiment selection;
* default seeds;
* default paths;
* default thresholds;
* default policies;
* silent null replacement;
* library-dependent behavior left unspecified when it affects reproducibility.

A value may be optional only when “absent” has explicit domain meaning and is validated as such.

Missing required configuration must fail immediately with a precise error.

### 10.3 No hidden fallbacks

Never recover silently from:

* unknown enum values;
* missing configuration;
* unsupported dataset capabilities;
* unavailable columns;
* absent timestamps;
* missing device identifiers;
* invalid experiment-policy combinations;
* incomplete artifacts;
* incompatible schemas;
* failed scientific preconditions.

Do not substitute a weaker experiment, another dataset, a pseudo-client definition, a fallback metric, or an alternate algorithm unless the roadmap explicitly permits it.

---

## 11. Dataset and Capability Integrity

Dataset behavior must be capability-driven, not assumption-driven.

Before implementing dataset-specific behavior, verify the actual typed dataset capabilities and the roadmap.

Do not infer that a dataset supports:

* natural clients;
* devices;
* families;
* timestamps;
* chronological splits;
* attack metrics;
* calibration roles;
* external validation;
* temporal analysis;
* cross-dataset analysis.

Unsupported capability combinations must fail validation before execution.

Do not create pseudo-identities, synthetic timestamps, row-order time, filename-derived time, or inferred device groups unless the roadmap explicitly defines them.

Do not silently drop unavailable metrics. Resolve metric eligibility from typed capabilities and report exclusions explicitly.

---

## 12. Determinism and Reproducibility

Scientific execution must be deterministic wherever the roadmap requires determinism.

Ensure that:

* all seed cohorts come from configuration;
* training, analysis, sampling, and poisoning seeds remain distinct where applicable;
* every random operation receives an explicit seed;
* iteration order is stable;
* filesystem traversal is sorted;
* client ordering is deterministic;
* experiment expansion is deterministic;
* output coordinates are deterministic;
* serialization ordering is stable where relevant;
* repeated planning produces identical plans;
* repeated formatting and generation produce no unnecessary churn;
* GPU determinism settings are preserved when required;
* checkpoint selection follows the locked protocol;
* outputs contain sufficient provenance for reproduction.

Never choose a seed, checkpoint, policy, or result based on favorable downstream performance.

---

## 13. Libraries and Boilerplate

Use existing dependencies before implementing custom infrastructure.

Before writing custom logic, inspect whether the repository already uses an appropriate library for:

* validation;
* serialization;
* tabular processing;
* statistical testing;
* effect sizes;
* multiple-comparison correction;
* confidence intervals;
* graph or DAG orchestration;
* CLI handling;
* structured logging;
* file locking;
* hashing;
* data validation;
* immutable modeling;
* deep comparison;
* artifact storage.

Do not add a dependency merely to replace a few clear lines.

A new dependency is acceptable only when it:

* removes meaningful custom complexity;
* has a clear maintained API;
* fits the existing architecture;
* does not duplicate an installed dependency;
* improves scientific correctness, validation, or maintainability;
* is used in more than one trivial location or replaces substantial fragile code.

Do not write custom statistical routines when an established, already-approved library provides the required method with the correct semantics.

Library output must still be converted into the project’s typed domain models.

---

## 14. Functions, Classes, and Abstractions

Keep implementations direct and cohesive.

### 14.1 Functions

A function should:

* perform one coherent responsibility;
* receive explicit typed inputs;
* return an explicit typed result;
* avoid hidden configuration access;
* avoid global state;
* avoid unrelated side effects;
* fail clearly on invalid state.

Do not create a function only to rename another function call.

Do not add boolean-flag-heavy functions. Prefer explicit enum-backed strategies or separate existing domain operations when behavior is genuinely distinct.

### 14.2 Classes

Create or retain a class only when it owns meaningful state, validation, lifecycle, or polymorphic behavior.

Do not create:

* manager classes with unrelated methods;
* service classes containing only static wrappers;
* abstract interfaces with one implementation and no extension requirement;
* factories that only call one constructor;
* configuration objects that duplicate Pydantic models;
* “utils” containers.

### 14.3 Error handling

* Use existing domain-specific exceptions.
* Add a new exception only when callers can act on that distinction.
* Do not catch broad `Exception`.
* Do not swallow failures.
* Do not log and continue after a scientific invariant fails.
* Do not convert invalid state into empty results.
* Preserve exception context.
* Fail before writing partial final artifacts when possible.

---

## 15. Orchestration and Stage Boundaries

Respect the existing pipeline and stage contracts.

Do not:

* bypass a stage by directly reading another stage’s internal files;
* duplicate orchestration in a handler;
* let reporting recompute scientific results;
* let analysis alter primary experiment artifacts;
* let evaluation reconstruct thresholds independently;
* let serialization decide scientific behavior;
* let CLI code contain domain logic;
* let configuration resolution perform execution;
* let stage handlers exchange untyped dictionaries.

Each stage must consume typed, validated inputs and produce typed, auditable outputs.

Reuse existing artifact and coordinate abstractions. Do not invent secondary output layouts.

---

## 16. Artifact and Output Discipline

Outputs must be deterministic, isolated, and attributable to a single experiment or campaign unit.

Do not introduce:

* run IDs without scientific meaning;
* random output directory names;
* duplicate manifests;
* hidden caches;
* ambiguous “latest” folders;
* temp files in final output directories;
* partial outputs marked complete;
* output reuse across scientifically incompatible experiments.

An existing completed output may be skipped only according to the repository’s explicit execution semantics.

When overwrite is explicitly requested, remove the target output safely before re-execution. Never merge new results into an incompatible previous output.

Completion markers must be written only after all required artifacts pass validation.

Temporary work must use the repository’s existing temporary mechanism. When none exists, use an external temporary directory rather than adding files under `src`.

Remove temporary artifacts before completion.

---

## 17. Tests

Tests exist to protect contracts and scientific invariants—not to maximize test count.

### 17.1 Do not add tests blindly

Do not create a new test merely because:

* a new method exists;
* coverage could increase;
* every branch can technically be asserted;
* another implementation has a similarly named test;
* generated code suggests one;
* a private helper lacks direct coverage.

Before adding a test:

1. Find the existing test covering the nearest public behavior.
2. Determine whether the behavior is already covered indirectly.
3. Determine whether an existing parametrized case can be extended.
4. Reuse existing fixtures and factories.
5. Confirm that the test protects a real regression, invariant, or contract.

### 17.2 Tests worth adding

Add or adapt tests when they protect:

* a scientific invariant;
* configuration validation;
* capability validation;
* deterministic planning;
* a public domain contract;
* a previously observed defect;
* serialization round trips;
* stage-boundary behavior;
* artifact completion semantics;
* an important failure mode;
* a changed behavior that could regress silently.

### 17.3 Test quality

Tests must:

* assert public behavior rather than private implementation;
* remain deterministic;
* use explicit typed fixtures;
* avoid duplicated setup;
* avoid hardcoded scientific values that belong in configuration;
* avoid reproducing production algorithms inside assertions;
* use parametrization where cases share a contract;
* verify both success and relevant failure behavior;
* avoid mock-heavy tests that merely restate call order;
* avoid brittle snapshots of unordered or environment-dependent data.

When production behavior is removed, delete or rewrite obsolete tests. Do not preserve dead production code to keep stale tests passing.

### 17.4 Test execution order

Use this order:

1. directly impacted tests;
2. related package tests;
3. architecture and import-contract tests;
4. full test suite;
5. repeat critical deterministic tests when scientific execution logic changed.

Use the project’s configured parallel test execution where safe.

Do not reduce scientific batch sizes, sample sizes, seeds, experiment scope, or validation strictness merely to make tests pass.

Do not weaken assertions to accept incorrect behavior.

---

## 18. Static Analysis and Quality Gates

Use the repository’s configured tools and settings. Do not create competing configuration.

For every meaningful change, run the relevant available checks, including:

* formatting verification;
* Ruff;
* Pyright;
* Pylance-compatible type validation;
* Pylint where configured;
* import-linter or architecture contracts;
* impacted tests;
* full tests before declaring repository-wide completion.

Fix root causes.

Do not add:

* `noqa`;
* blanket ignores;
* per-file exclusions;
* type-checker suppressions;
* disabled rules;
* inflated complexity thresholds;
* coverage exclusions;
* test skips;
* expected failures used to hide defects.

Do not modify quality configuration simply to make new violations disappear.

---

## 19. Comments and Documentation

Do not add AI-style comments.

Do not add comments that:

* narrate obvious code;
* restate the function name;
* explain basic syntax;
* announce that code is “clean,” “robust,” or “optimized”;
* describe the editing process;
* mention prompts, agents, refactoring phases, or generated code;
* preserve deleted behavior as commented-out code;
* contain temporary TODOs without an owner and explicit requirement.

Prefer expressive names, enums, types, and small cohesive functions over comments.

Retain or add documentation only when it captures:

* a non-obvious scientific invariant;
* an external protocol requirement;
* a subtle mathematical definition;
* a necessary library constraint;
* a domain distinction that cannot be expressed through types.

Any such documentation must be concise, factual, and human-written in tone.

Delete stale or misleading comments encountered in edited areas.

---

## 20. Naming

Names must express scientific and domain meaning.

Prefer:

* descriptive policy names;
* descriptive experiment names;
* explicit stage names;
* explicit metric names;
* domain-specific result types;
* positive boolean predicates;
* clear units in measurement names.

Avoid:

* generic `data`, `item`, `result`, `info`, `config`, or `value` when a more specific name exists;
* unexplained abbreviations;
* numbered implementation names;
* `new`, `old`, `legacy`, `v2`, `temp`, `final`, or `fixed`;
* ambiguous B/A/C naming unless the roadmap explicitly locks the identifier;
* names that imply stronger scientific claims than the evidence permits.

Do not rename roadmap-locked scientific identifiers casually.

---

## 21. Performance and Resource Discipline

Do not optimize speculatively.

When performance matters:

1. identify the actual bottleneck;
2. measure it;
3. reuse existing vectorized or batched operations;
4. preserve scientific equivalence;
5. add a benchmark only when the performance contract matters.

Do not:

* reduce batch sizes without explicit instruction;
* replace vectorized operations with Python loops;
* load complete datasets into memory unnecessarily;
* duplicate large tables;
* repeatedly deserialize the same artifact;
* introduce unbounded caches;
* sacrifice determinism for speed;
* change numerical precision silently;
* move execution from GPU to CPU without an explicit protocol reason.

Performance changes must not change experiment semantics.

---

## 22. Git and Repository Safety

Unless explicitly requested:

* do not commit;
* do not push;
* do not open pull requests;
* do not rebase;
* do not reset;
* do not stash;
* do not modify branches;
* do not rewrite history;
* do not add generated artifacts to version control.

`git status` and `git diff` may be used to inspect the current worktree.

Do not use git history as scientific truth.

Do not revert unrelated user changes.

Do not overwrite files outside the requested scope.

Avoid mass-edit scripts and broad regex replacements. Make targeted edits and inspect every changed region.

---

## 23. Required Workflow for Every Task

### Phase 1 — Understand

* Read the user request completely.
* Read this file.
* Read the relevant roadmap sections.
* Inspect the existing source tree.
* Inspect relevant configuration.
* Inspect existing domain models and enums.
* Inspect relevant tests.
* Identify scientific and architectural constraints.

### Phase 2 — Search and Reuse

* Search for existing implementations.
* Search for duplicate concepts and names.
* Inspect all callers.
* Inspect available library support.
* Decide what can be reused, consolidated, or deleted.
* Confirm that no new `src` file is required.

### Phase 3 — Plan

Define:

* exact existing files to edit;
* code to reuse;
* code to remove;
* contracts that change;
* configuration implications;
* scientific invariants affected;
* tests to adapt, add, or delete;
* validation commands to run.

Prefer the smallest coherent change that fully solves the task.

### Phase 4 — Implement

* Make targeted edits.
* Preserve the existing architecture.
* Use enums and typed models.
* Remove obsolete paths.
* Keep configuration explicit.
* Avoid defaults and fallbacks.
* Avoid comments.
* Update all callers rather than adding compatibility layers.
* Keep temporary artifacts outside `src`.

### Phase 5 — Validate

Run:

* formatting;
* linting;
* static typing;
* architecture checks;
* impacted tests;
* related tests;
* full tests when the change is repository-wide;
* deterministic reruns for planning or scientific logic.

### Phase 6 — Audit

Perform separate final audits for:

1. scientific drift;
2. roadmap compliance;
3. architecture and file-tree compliance;
4. reuse and duplication;
5. enum and typing quality;
6. configuration completeness;
7. hardcoded values and defaults;
8. hidden fallbacks;
9. test quality;
10. dead code and stale documentation.

Fix every confirmed issue before declaring completion.

---

## 24. Parallel Agent Rules

For broad tasks, parallel agents may be used for independent read-only analysis such as:

* roadmap compliance;
* architecture inspection;
* duplicate-code discovery;
* typing review;
* configuration review;
* test review;
* scientific drift review.

Do not allow multiple agents to edit overlapping files concurrently.

The primary agent remains responsible for:

* resolving disagreements;
* integrating changes;
* preserving architecture;
* verifying the final diff;
* running final checks;
* ensuring scientific consistency.

Parallel agents must not independently invent scientific decisions.

---

## 25. Forbidden Behaviors

Never:

* add a new file under `src`;
* invent a scientific value;
* add a hidden default;
* hardcode a configurable value;
* create a compatibility layer;
* retain a deprecated alias;
* duplicate an enum or domain model;
* use raw strings for established categorical domains;
* introduce `Any`;
* pass untyped dictionaries between layers;
* add a method without searching for reuse;
* create a wrapper with no domain responsibility;
* add tests solely to increase test count;
* retain dead code for stale tests;
* weaken a test to accept incorrect behavior;
* suppress a lint or typing error instead of fixing it;
* add AI-generated narration comments;
* change scientific scope through implementation convenience;
* silently substitute an unsupported dataset capability;
* treat exploratory evidence as confirmatory;
* choose favorable outputs post hoc;
* edit quality settings to hide violations;
* commit or push without explicit permission.

---

## 26. Completion Standard

A task is complete only when all applicable checklist items pass.

### Architecture

* [ ] No new file or directory was added under `src`.
* [ ] Every change fits an existing file responsibility.
* [ ] No parallel implementation path was introduced.
* [ ] No compatibility shim, redirect, alias, or legacy branch remains.
* [ ] Obsolete code and imports were removed.
* [ ] Existing architectural boundaries remain intact.

### Reuse and simplicity

* [ ] The repository was searched before adding each new symbol.
* [ ] Existing code and libraries were reused where appropriate.
* [ ] Duplicate behavior was consolidated.
* [ ] No unnecessary wrapper, factory, helper, or abstraction was introduced.
* [ ] The final implementation is smaller or no more complex than necessary.

### Enums and typing

* [ ] Closed categorical domains use existing or canonical enums.
* [ ] No duplicate enum vocabulary was introduced.
* [ ] No raw-string domain comparisons were added.
* [ ] No `Any`, untyped domain dictionary, broad cast, or suppression was added.
* [ ] Public and stage-boundary inputs and outputs are typed.
* [ ] Scientific records remain immutable where required.

### Configuration

* [ ] No scientific or runtime value was hardcoded.
* [ ] No required value received a default.
* [ ] No hidden fallback was introduced.
* [ ] Missing or unsupported configuration fails clearly.
* [ ] Configuration is validated before execution.
* [ ] Dataset capabilities are resolved explicitly.

### Scientific integrity

* [ ] Relevant roadmap sections were read.
* [ ] The change preserves the fixed scientific identity.
* [ ] Calibration, evaluation, and artifact boundaries remain valid.
* [ ] No test-data or label leakage was introduced.
* [ ] Claim tiers and experiment roles remain separated.
* [ ] No unsupported scientific interpretation was introduced.
* [ ] Determinism and provenance remain sufficient.
* [ ] Null and negative outcomes remain representable.

### Tests

* [ ] Existing tests were searched before adding tests.
* [ ] Tests were added only for meaningful contracts or regressions.
* [ ] Obsolete tests were deleted or adapted.
* [ ] Fixtures and parametrization were reused.
* [ ] Tests assert behavior rather than private implementation.
* [ ] Impacted tests pass.
* [ ] Related tests pass.
* [ ] The full suite passes when required.
* [ ] No test was weakened, skipped, or hidden.

### Quality

* [ ] Formatting passes.
* [ ] Ruff passes.
* [ ] Pyright passes.
* [ ] Pylance-compatible typing remains clean.
* [ ] Pylint passes where configured.
* [ ] Import and architecture contracts pass.
* [ ] No suppression comment was added.
* [ ] No AI-style comment or stale documentation remains in edited areas.

### Repository hygiene

* [ ] No unrelated file was modified.
* [ ] No temporary artifact remains.
* [ ] No generated output was accidentally added.
* [ ] No commit or push was performed unless explicitly requested.
* [ ] The final diff was inspected manually.

---

## 27. Final Response Format

At the end of a task, report only concrete outcomes:

### Changed

List the existing files changed and their responsibility-level changes.

### Reused or removed

State what existing code was reused, consolidated, or deleted.

### Scientific verification

State which roadmap rules and scientific invariants were checked.

### Validation

List the checks executed and their results.

### Remaining issues

Report only genuine unresolved blockers. Do not claim completion while known violations remain.

Do not provide inflated claims such as “production-ready,” “perfect,” “fully robust,” or “scientifically proven” unless the actual evidence and validation justify them.

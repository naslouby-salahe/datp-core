# DATP-Core — Mandatory Development Contract

This file defines binding repository rules. Terms such as **must**, **must not**, **required**, and **forbidden** are literal. Do not reinterpret them as suggestions, postpone them without a concrete blocker, or declare completion while any applicable rule is violated.

## 1. Authority and Scientific Identity

DATP-Core is a scientifically controlled journal-extension implementation of Device-Aware Threshold Personalization for non-IID federated IoT anomaly detection. It is not a generic FL-IDS framework.

When sources conflict, use this authority order:

1. Current files under `roadmap/`.
2. Validated files under `configs/`.
3. Canonical typed domain contracts that agree with the roadmap and configuration.
4. Executable behavior, tests, documentation, and comments only when they agree with the sources above.

Never invent or infer an unresolved scientific decision. This includes seeds, cohorts, splits, thresholds, datasets, experiment membership, statistical rules, fallback behavior, metrics, model settings, checkpoint rules, or claim boundaries. Stop that path with a precise blocker instead of choosing a convenient value.

Passing tests does not prove scientific correctness. Every affected experiment path must also be audited against the roadmap and validated configuration.

## 2. Non-Negotiable Scientific Rules

- Preserve the fixed-model threshold-calibration identity of the core DATP ladder.
- Preserve causal separation between dataset preparation, splitting, training, checkpoint selection, score generation, calibration subsampling, threshold construction, evaluation, statistical analysis, reporting, and export.
- Calibration must be benign-only wherever required. Attack data must never influence threshold fitting.
- Test data, test labels, and test scores must never influence training, normalization fitting, model selection, calibration, threshold selection, configuration resolution, or stopping decisions.
- Reuse the same trained model, selected checkpoint, score artifacts, seeds, and splits across policies whenever threshold scope is the intended experimental variable.
- Treat AUROC as a threshold-independent model-quality control where specified. Never substitute it for threshold-dependent operating-point metrics.
- Enforce dataset capability boundaries. A dataset must not produce claims, labels, metrics, partitions, or analyses it cannot scientifically support.
- Preserve configured seed cohorts, deterministic flags, split manifests, artifact provenance, checkpoint rules, and statistical decision rules exactly.
- Every scientific value must originate from validated configuration or an explicit typed scientific object. Scientific magic numbers and hidden defaults are forbidden.
- Trace every configured experiment through the complete stage chain before calling it executable.
- Do not weaken, reinterpret, or silently broaden claims to accommodate implementation limitations.

## 3. Dictionaries Are Forbidden as Domain Design

Raw dictionaries are not an acceptable design for DATP-Core.

The following are forbidden in configuration, domain models, pipeline contracts, stage inputs or outputs, manifests, experiment plans, metrics, results, registries, public APIs, persistence contracts, and internal cross-module communication:

- `dict` used as a domain object;
- `dict[str, object]`, `dict[str, Any]`, or equivalent weakly typed bags;
- `Mapping[str, object]` used to avoid writing a real model;
- nested dictionaries representing structured scientific data;
- `TypedDict` used instead of a proper validated or immutable model;
- arbitrary `**kwargs` for domain or scientific parameters;
- string-key access such as `value["policy"]` for known structured fields;
- dictionary-based dispatch where an enum-backed registry or strategy contract is appropriate;
- returning multiple scientific values in an anonymous dictionary;
- passing dictionaries between pipeline stages;
- storing configuration fragments for later interpretation.

Allowed dictionary use is limited to unavoidable external boundaries, such as a third-party API, YAML/JSON parsing, serialization, dataframe construction, or library callback. At such a boundary:

1. Convert the mapping immediately into a validated Pydantic model, dataclass, enum-backed value object, or other concrete typed structure.
2. Do not let the raw mapping escape the boundary function.
3. Do not retain it as the internal source of truth.
4. Convert typed objects back to mappings only at the final serialization boundary.

Use concrete alternatives:

- Pydantic v2 models for validated configuration and external input;
- frozen dataclasses or immutable value objects for domain state;
- enums for closed vocabularies;
- dedicated result models for outputs;
- tuples or named records only for genuinely small fixed structures;
- protocols or abstract interfaces for behavior;
- typed registries for extension points.

When a raw dictionary already exists in an affected path, replacing it is part of the task. Do not preserve it merely to reduce scope.

## 4. Enums Are Mandatory for Closed Vocabularies

Every finite, named set of values must have one canonical enum. This includes datasets, experiments, regimes, stages, policies, metrics, artifact kinds, split kinds, statuses, modes, objectives, statistical profiles, failure categories, path categories, and report sections.

Forbidden:

- repeated string literals for a known finite concept;
- string-based `if` or `match` dispatch for concepts that require enums;
- duplicate enums representing the same concept;
- local mini-enums created because importing the canonical enum is inconvenient;
- accepting arbitrary strings and validating them later when an enum can validate them at the boundary;
- enum aliases, deprecated names, compatibility members, or legacy spellings;
- converting enums to strings early and then passing strings through the system.

Required:

- define the enum once in the correct owning capability;
- use enum members from configuration parsing through execution and reporting;
- keep dispatch enum-backed and exhaustive;
- fail clearly on unsupported enum values;
- update every caller, test, configuration model, serializer, and report when canonical enum ownership changes;
- merge overlapping enums instead of adding adapters.

Enums must improve correctness and extensibility, not become a dumping ground. Do not create an enum for open-ended user text, numeric measurements, file contents, or values that are not a closed vocabulary.

## 5. Configuration Is the Runtime Source of Truth

- All scientific and experiment-specific values must be explicit in YAML and validated through Pydantic v2.
- Code must not duplicate configurable values as constants, literals, constructor defaults, fallback expressions, or environment-dependent guesses.
- Scientific defaults in Python are forbidden.
- `dict.get(..., default)`, `getattr(..., default)`, `or fallback`, silent coercion, and equivalent fallback patterns are forbidden for required configuration.
- Missing, inconsistent, unknown, or scientifically invalid configuration must fail at startup with a precise error.
- Do not silently normalize invalid enum names, paths, metric names, or experiment identifiers.
- Do not maintain two configuration representations that can drift.
- Resolved configuration must become immutable typed structures before execution.
- Do not read YAML throughout the codebase. Configuration loading and resolution belong at a controlled boundary.
- Every stage must consume resolved typed values, not re-interpret raw configuration.

Operational defaults may exist only when they are non-scientific, harmless, explicit, and centralized. When uncertain, require configuration rather than inventing a default.

## 6. Architecture Must Be Clean and Open to Extension

The design must remain open to legitimate journal-scope extensions without becoming a speculative framework.

A new dataset, threshold policy, stage implementation, metric, statistical procedure, artifact kind, or experiment should normally require:

1. a typed implementation of the relevant contract;
2. validated configuration;
3. explicit registration in the owning registry or composition root;
4. focused tests;
5. no edits to unrelated scientific logic.

Forbidden architecture:

- large `if`/`elif` or `match` chains spread across packages;
- central god objects that know every dataset, policy, stage, metric, and artifact;
- stage handlers with multiple unrelated responsibilities;
- files grouped by historical accident;
- vague modules such as `utils`, `helpers`, `common`, `misc`, or `shared` containing unrelated behavior;
- pass-through services, manager classes, façade layers, wrapper functions, and adapters that add no invariant or abstraction;
- one-file-per-trivial-class fragmentation;
- duplicate models, validators, conversions, path logic, or dispatch logic;
- circular imports, dependency inversion violations, and cross-package internal imports;
- public exposure of implementation details;
- abstractions created only for hypothetical future requirements.

Required architecture:

- capability-oriented packages with clear ownership;
- one clear responsibility per module;
- cohesive files rather than artificially tiny files;
- splitting of god files when responsibilities are genuinely separable;
- merging of redundant files and types when separation adds no value;
- orchestration separated from scientific computation, configuration, storage, and presentation;
- composition performed in an explicit composition root;
- extension through typed strategies, registries, protocols, or abstract interfaces;
- stable domain contracts with implementation details hidden behind them;
- centralized typed path construction and artifact naming;
- import boundaries that match architectural ownership.

“Open to extension” never means preserving obsolete APIs, adding generic plugin machinery without a real use case, or weakening types.

## 7. Boilerplate, Duplication, and Bloat Must Be Removed

Every task must include an inspection for nearby boilerplate and duplication. Do not add new code on top of an unnecessarily bloated design.

Mandatory removals include:

- repeated validation already expressible in Pydantic, Pandera, or an existing canonical validator;
- repeated serialization and deserialization logic;
- repeated enum-to-string conversions;
- repeated dataframe schemas or column lists;
- repeated path building;
- repeated stage setup or teardown;
- repeated error translation;
- repeated result assembly;
- copy-pasted scientific formulas or metric calculations;
- wrappers that only forward arguments;
- constructors that only copy fields;
- duplicate test fixtures and near-identical parameterized tests;
- audit-era helpers, temporary compatibility code, obsolete comments, and dead branches.

Prefer a well-supported project dependency when it clearly removes custom boilerplate and preserves scientific transparency. Do not introduce a dependency for a trivial operation or hide core scientific logic behind an opaque library call.

Do not reduce line count by compressing logic, creating clever generic machinery, or combining unrelated responsibilities. Debloating must improve clarity, ownership, typing, and testability.

## 8. No Backward Compatibility Surface

Backward compatibility is not a goal inside this repository unless explicitly requested for a specific external contract.

Forbidden:

- compatibility re-export modules;
- redirects;
- deprecated aliases;
- old import paths;
- proxy functions;
- temporary wrappers;
- dual APIs;
- legacy enum members;
- comments explaining where code used to live;
- keeping obsolete files because tests or internal callers still import them.

Move to one canonical implementation, update every caller and test, and delete the obsolete surface completely.

## 9. Strict Typing

- `Any` is forbidden.
- Untyped dictionaries, JSON bags, broad `object` containers, and unchecked casts are forbidden.
- Avoid `cast()` unless a library boundary makes it unavoidable and the invariant is validated immediately.
- Avoid broad unions when a discriminated model or protocol expresses the contract better.
- Do not use `# type: ignore`, Pyright suppressions, Pylint suppressions, or lint exclusions to hide defects.
- Public functions and methods require precise parameter and return types.
- Stage boundaries, artifact payloads, configuration, and results require explicit models.
- Prefer immutability for resolved configuration, experiment plans, identifiers, manifests, and result records.
- Make invalid states unrepresentable where practical.
- Exhaustively handle enum variants. An unreachable branch must fail loudly rather than silently returning a fallback.

## 10. Code Quality and Naming

- Use precise scientific and domain terminology.
- Temporary, vague, numbered, audit-oriented, or generated-looking names are forbidden.
- Do not add explanatory, historical, migration, audit, or change-log comments to source code.
- Remove stale, obvious, misleading, or generated-looking comments and docstrings encountered in affected code.
- Keep docstrings only where they define a public contract or non-obvious scientific invariant.
- Do not use broad exception handlers, silent fallbacks, hidden retries, or swallowed errors.
- Do not catch exceptions merely to log and continue.
- Fix root causes rather than suppressing lint, typing, test, coverage, or static-analysis findings.
- Do not hardcode user-specific paths, credentials, machine details, secrets, or local environment assumptions.
- Prefer readable explicit logic over clever compression.

## 11. Data, GPU, and Runtime Integrity

- Preserve `data/raw` as a symlink. Never replace it, copy raw datasets into the repository, or commit generated raw data.
- Never reduce batch size, rounds, seeds, samples, clients, precision, or workload merely to make code or CI pass.
- GPU-required execution must not silently fall back to CPU when this changes the protocol.
- CUDA-specific tests must check availability and skip only the genuinely CUDA-specific case with an explicit reason.
- Determinism settings must remain active where required.
- Artifacts must be attributable to exact code revision, validated configuration, experiment, dataset, seed, split manifest, and checkpoint.
- Partial artifacts must never be treated as complete evidence.
- Writes that establish completion must be atomic or safely staged.

## 12. Experiment and Campaign Semantics

- One experiment owns one canonical output directory.
- Existing completed output is skipped unless an explicit override requests replacement.
- Override must safely remove the target experiment output before recomputation. Never merge old and new artifacts.
- Campaign resumption must locate the first incomplete experiment, remove only that incomplete output, and resume from it using the same command.
- Do not add run IDs or job IDs when the experiment output directory is the canonical identity.
- Completion markers may be written only after all required artifacts and schemas validate.
- Never delete valid outputs, datasets, or caches unless the task explicitly requires it.
- Execution order and prerequisite reuse must follow the configured experiment plan, not incidental filesystem state.

## 13. Tests Are Scientific Contracts

Tests must validate behavior and scientific invariants, not preserve obsolete implementation.

Required coverage includes, where applicable:

- configuration rejection and resolution;
- enum exhaustiveness and dispatch;
- stage input and output contracts;
- benign-only calibration;
- split and leakage invariants;
- deterministic seed and sweep expansion;
- threshold arithmetic with hand-checkable examples;
- metric calculations and statistical decision rules;
- dataset capability restrictions;
- checkpoint and artifact provenance;
- output ownership, override, interruption, and campaign resumption;
- end-to-end pipeline wiring for every configured experiment family;
- failure behavior, not only success paths.

Forbidden test behavior:

- weakening assertions to match broken code;
- deleting valuable coverage to make refactoring easier;
- marking failures as expected without a real protocol reason;
- broad skipping;
- testing private implementation details instead of contracts;
- trivial tests that merely mirror the implementation;
- giant duplicated fixtures;
- audit-only tests and historical regression names with no current contract;
- dependence on test order, existing outputs, local absolute paths, network access, or an unmarked GPU requirement.

Adapt and debloat tests whenever production architecture changes. Test structure should follow production capabilities where practical.

## 14. Mandatory Work Method

Before editing:

1. Read the relevant roadmap sections and configuration.
2. Inspect the complete affected call chain, not only the named file.
3. Map affected imports, callers, registries, models, artifacts, configs, tests, and experiment stages.
4. Identify existing duplication, dictionaries, missing enums, weak typing, boilerplate, architecture violations, and scientific drift in the affected area.
5. Record the plan and audit checklist under `.tmp/`.

While editing:

- Make controlled, reviewable changes.
- Do not use blind bulk replacement, mass-generated patches, or large one-off Python scripts to restructure the repository.
- Do not leave temporary adapters or compatibility layers.
- Update production code, configuration contracts, tests, and documentation together.
- Re-check the full experiment path after structural changes.
- Fix directly encountered pre-existing defects in the affected path instead of working around them.
- Keep the result idempotent.

After editing:

1. Re-audit the affected architecture and scientific path from scratch.
2. Search again for raw dictionaries, magic strings, duplicate enums, hardcoded configurable values, hidden defaults, boilerplate, compatibility code, and dead code.
3. Verify that extension points remain typed and do not require unrelated edits.
4. Run focused validation for the changed behavior.
5. Run the full configured quality gates after the coherent change set is complete.
6. Remove `.tmp/` material created for the task when it is no longer needed.
7. Repeat the audit-and-fix cycle until no applicable violation remains.

Do not stop because tests pass. Do not stop after the first implementation pass. Do not declare a problem “out of scope” when it is a direct consequence of the current change.

## 15. Validation Gates

Run all repository-configured gates applicable to the task:

- formatting;
- Ruff;
- strict Pyright;
- Pylance-compatible typing;
- Pylint when configured;
- import-boundary checks;
- focused tests;
- the complete pytest suite;
- configuration validation;
- experiment catalogue resolution;
- full pipeline-plan resolution;
- artifact schema and provenance validation;
- static analysis such as SonarCloud when the task explicitly includes it.

Do not label findings as false positives to avoid fixing them. Remove the underlying issue whenever a safe correction exists.

## 16. Definition of Done

Completion is forbidden unless all applicable statements are true:

- The implementation matches the current roadmap and validated configuration.
- The entire affected experiment path has been manually traced and audited.
- No scientific leakage, drift, unsupported assumption, or hidden fallback remains.
- No raw dictionary remains as a domain, configuration, pipeline, manifest, result, registry, or public API contract.
- Every closed vocabulary uses its canonical enum.
- No duplicate or overlapping enum, model, validator, schema, path builder, calculation, or source of truth remains.
- No configurable scientific value is hardcoded or defaulted in Python.
- No unnecessary boilerplate, wrapper, adapter, pass-through layer, duplicated fixture, or dead code remains in the affected area.
- The architecture is cohesive, typed, and open to legitimate extension without edits to unrelated logic.
- No compatibility shim, redirect, alias, re-export, obsolete API, or legacy path remains.
- Production code and tests use the canonical structure.
- Typing, formatting, linting, import boundaries, configuration validation, and tests pass.
- Every affected configured experiment resolves through all required stages.
- Artifacts retain deterministic identity and complete provenance.
- Temporary files are removed.
- Remaining blockers are concrete, externally caused, and reported precisely.
- No unsupported `GO`, readiness, completion, or scientific claim is made.

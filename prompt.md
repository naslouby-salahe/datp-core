# DATP-Core Simplification — Complete Idempotent Implementation Goal

Work directly in:

```text
/home/naslouby/Projects/datp-core
```

The authoritative implementation roadmap is:

```text
/home/naslouby/Projects/datp-core/docs/DATP-Core Simplification.md
```

Read the entire roadmap before editing anything. Treat its scientific invariants, target architecture, phase order, deletion ledger, library-adoption rules, scientific-equivalence matrix, quality targets, and final `GO FOR EXPERIMENTS` checklist as mandatory.

Your job is not merely to audit, propose changes, or partially implement the roadmap. Analyze the actual repository, establish a reliable baseline, plan the work, implement every applicable roadmap phase, continuously clean and simplify the touched code, adapt the tests, and continue until the roadmap is fully implemented and the repository truthfully qualifies for the final verdict:

```text
GO FOR EXPERIMENTS
```

Do not stop after producing a plan, after completing only the main architectural changes, after making tests pass, or after reporting remaining work. Continue implementing, validating, auditing, fixing, and revalidating until every final acceptance condition is satisfied.

---

## 1. Core Operating Rules

### 1.1 Work autonomously and continuously

Do not ask for approval between phases, files, migrations, deletions, test updates, or architectural decisions that are already resolved by the roadmap.

Do not stop because the task is large. Break it into deterministic phases and continue.

Do not leave TODOs, FIXMEs, placeholders, deferred cleanup, temporary compatibility layers, partial migrations, or “follow-up” tasks.

Any existing TODO, FIXME, workaround, stale comment, incomplete branch, placeholder, or obvious defect encountered in the affected scope must be investigated and resolved rather than preserved.

When an unexpected problem appears:

1. Inspect the repository evidence.
2. Determine the scientifically safe correction.
3. Implement it.
4. Adapt the affected tests.
5. Re-run the relevant checks.
6. Continue the roadmap.

Never invent repository facts, APIs, experiment semantics, dataset capabilities, configuration fields, paths, or scientific values. Inspect the actual code and configuration first.

### 1.2 Idempotence and crash-safe resumption

Use only this ignored working area for temporary tracking:

```text
/home/naslouby/Projects/datp-core/.tmp/datp-core-simplification/
```

Maintain compact machine-readable or Markdown state there containing:

* baseline fingerprints and inventories;
* roadmap phase status;
* the currently processed package and file;
* completed migrations;
* pending deletions;
* commands executed and their outcomes;
* impacted tests per file;
* phase-level validation results;
* scientific-equivalence comparisons;
* external-tool failures that must be retried;
* final checklist status.

Do not place audit reports, temporary scripts, scratch files, progress files, generated notes, or agent-specific artifacts elsewhere in the repository.

On every invocation:

1. Re-read the roadmap.
2. Inspect the current repository state.
3. Read the temporary progress state if it exists.
4. Verify completed work against the actual code instead of trusting the tracker blindly.
5. Resume from the first incomplete or invalid phase.
6. Reprocess any partially migrated file or phase from a clean, deterministic state.

Running this same goal again must converge toward the same final architecture without duplicate files, duplicate abstractions, duplicate tests, repeated migrations, or formatting churn.

### 1.3 No mass-edit shortcuts

Do not use broad regex rewrites, uncontrolled codemods, repository-wide replacement scripts, generated migration scripts, or mass edits that bypass file-level reasoning.

Process each production file intentionally. For each file, inspect its responsibility, callers, dependencies, configuration use, types, tests, and scientific role before editing it.

Test files may be processed in parallel when their scopes are independent, but every test change must remain traceable to a production contract or a scientific invariant.

External coding assistants or subagents are optional. When used, restrict each one to the current file and the directly affected contracts. Independently inspect and validate every result before accepting it.

---

## 2. Source-of-Truth and Scientific Locks

The architectural roadmap controls the structural migration. The repository’s scientific source-of-truth documents and validated configuration control scientific meaning.

Do not change scientific behavior to make the refactor easier.

The following are immutable:

* B1–B4 causal isolation;
* the same frozen detector, scores, calibration records, and test records within each seed;
* benign-only calibration;
* attack-labelled data excluded from threshold construction, checkpoint selection, eligibility, and comparator tuning;
* Regime A, B1 versus B2, `CV(FPR)`, ten paired seeds, and 95% BCa confidence interval as the sole confirmatory endpoint;
* checkpoint selection by the configured lowest federated-averaging-weighted benign validation reconstruction error;
* configured seed cohorts;
* `CV(FPR)` with `ddof=0`, no epsilon stabilizer, and undefined behavior when mean FPR is zero;
* AUROC as a model-quality control rather than the thresholding verdict;
* Edge-IIoTset capability restrictions;
* CICIoT2023 file-defined clients not being presented as physical devices;
* B3 requiring family taxonomy;
* canonical B4 `K=3`;
* threshold formulas, statistical procedures, dataset contracts, sweep values, training profiles, checkpoint semantics, report semantics, and experiment catalogue meaning;
* Dagster as the canonical orchestrator;
* the existing batch sizes and GPU execution behavior.

Never reduce a configured batch size, weaken determinism, alter a seed, change a threshold parameter, reduce an experiment matrix, disable a scientific gate, or replace a real execution path with a mock merely to make checks pass.

Protect the `data/raw` symlink. Do not replace it, copy the raw datasets into the repository, dereference it into generated repository content, or reorganize the underlying data.

Before accepting any change that touches planning, training, thresholding, evaluation, analysis, reporting, datasets, configuration, or execution, explicitly check for scientific drift.

---

## 3. Mandatory Initial Analysis

Before editing:

1. Read the complete simplification roadmap.
2. Read all repository-local scientific source-of-truth and roadmap files referenced by it.
3. Inspect `CLAUDE.md`, `pyproject.toml`, `noxfile.py`, `importlinter.ini`, CI workflows, Sonar configuration, CodeScene configuration, README, Makefile, configuration files, package structure, and tests.
4. Verify the roadmap’s stated current paths and counts against the actual repository.
5. Identify changes already completed, partially completed, obsolete, or contradicted by the present repository.
6. Map every roadmap phase to the actual current files.
7. Build a dependency-aware execution plan.
8. Record the plan in the temporary tracking directory.

Do not blindly recreate something that already exists correctly. Verify it against the roadmap’s final contract and mark it complete only when it passes.

Do not reject a roadmap requirement merely because filenames or line numbers have changed. Preserve the requirement’s architectural and scientific intent and apply it to the current repository structure.

---

## 4. Baseline Lock Before Refactoring

Complete Phase 0 before structural edits.

Record:

* source and test file inventories;
* source line counts;
* package structure;
* configuration checksums;
* scientific fingerprint;
* execution fingerprint;
* plans for every configured experiment;
* stage keys, dependencies, and output paths;
* representative threshold outputs;
* representative metric and statistical outputs;
* current Sonar and CodeScene baselines;
* all current static-check and test outcomes.

Run the repository’s real baseline gates, including at least:

```bash
datp-core config validate
nox -s lint
nox -s typecheck
nox -s imports
nox -s tests
```

Also run Pylint, Pylance-compatible checking, scientific-invariant checks, formatting verification, and any additional quality sessions already defined by the repository.

If a pre-existing failure prevents a trustworthy baseline:

1. Record the original failure without hiding it.
2. Diagnose it.
3. Fix it without scientific drift.
4. Adapt the affected tests.
5. Re-run the baseline.
6. Lock the baseline only after the repository is stable enough for meaningful equivalence comparisons.

Do not begin major structural migration while the scientific or execution baseline is unknown.

---

## 5. Required Phase Order

Execute the roadmap in dependency order. Do not skip a phase merely because later tests happen to pass.

### Phase 0 — Baseline and scientific lock

Establish the verified baseline and fingerprints before changing architecture.

### Phase 1 — Core types, enums, and model-system consolidation

Complete the Pydantic v2 migration described by the roadmap.

Required outcomes include:

* `ResolvedProjectConfiguration` is a frozen, strict Pydantic model;
* validated domain records use Pydantic where required;
* closed vocabularies use enums or typed identifiers;
* untyped `Mapping[str, ...]` domain fields are replaced with explicit models;
* `cattrs` serialization is removed;
* attrs is retained only where the roadmap explicitly permits lightweight identifier value objects;
* all migrated models preserve validation and serialization behavior;
* no OmegaConf, dictionaries, or raw strings leak into domain contracts.

### Phase 2 — Hydra configuration composition and experiment compilation

Implement real Hydra composition without turning Hydra into a service locator or runtime framework.

Required outcomes include:

* Hydra composes authored YAML;
* Pydantic validates composed documents;
* OmegaConf remains inside the configuration boundary;
* no CLI `os.environ` mutation is needed for configuration overrides;
* no hidden Python defaults replace explicit configuration;
* each experiment is resolved once into a typed `CompiledExperiment`;
* planning and handlers no longer repeatedly navigate the full resolved project configuration;
* compilation is deterministic and scientifically equivalent.

### Phase 3 — Centralized path authority

Create and enforce one `ExperimentPaths` authority.

All semantic output, shared-stage, training, checkpoint, score, calibration, threshold, evaluation, analysis, freeze, report, diagnostic, temporary execution, and completion paths must be built through this authority.

Delete replaced path helpers and inline path construction after all callers are migrated.

Do not create a path registry or artifact framework.

### Phase 4 — Typed context families

Replace the oversized nullable `StageJobContext` with the four focused typed context families required by the roadmap.

No stage should receive irrelevant optional coordinates.

Use explicit identifiers and enums rather than raw strings.

Merge redundant context modules and delete them once no callers remain.

### Phase 5 — One experiment-plan builder

Create one `ExperimentPlanBuilder` used by:

* standalone execution;
* campaign execution;
* CLI plan inspection;
* diagnostics;
* Dagster;
* tests.

Single-experiment and campaign planning must not contain separate competing logic.

All configured experiments must compile and produce plans equivalent to the Phase 0 baseline.

Delete the replaced `jobs.py` implementation after migration.

### Phase 6 — Dataset adapters and preprocessing cleanup

Preserve dataset-specific adapters and their legitimate differences.

Centralize only genuinely shared preprocessing.

Audit all adapters for:

* duplicated normalization or encoding;
* row-wise Python iteration;
* untyped outputs;
* hidden defaults;
* unused configuration;
* unreliable client identity;
* split leakage;
* unsupported metric claims;
* unnecessary files and wrappers.

Preserve all dataset boundaries and materialization equivalence.

### Phase 7 — Learning, checkpoint selection, and scoring cleanup

Handlers must receive compiled, task-specific inputs rather than the full project configuration.

Preserve:

* GPU behavior;
* configured batch sizes;
* deterministic seed derivation;
* model architecture;
* optimizer and loss semantics;
* FedAvg, FedProx, and Ditto behavior;
* SafeTensors checkpoints;
* checkpoint selection evidence;
* score equivalence.

Use ordinary factories for models, optimizers, and losses. Do not create forbidden registries or factory hierarchies.

### Phase 8 — Thresholding simplification

Delete the central `isinstance` dispatch chain.

Create a `ThresholdEstimatorRegistry` keyed by `ThresholdPolicyKind`, with thin estimator implementations delegating to the existing pure estimation functions.

Preserve all configured threshold policy families and numeric behavior.

Add or adapt focused tests for:

* every policy kind;
* policy ownership;
* eligibility;
* required columns;
* deterministic behavior;
* fallback behavior;
* invalid combinations;
* numeric equivalence against the Phase 0 baseline.

Do not replace one large dispatch chain with several hidden dispatch chains.

### Phase 9 — Evaluation and metric authority

Evaluation must remain the only authority that computes evaluation metrics.

Analysis and reporting must consume persisted canonical metric artifacts rather than recomputing formulas.

Use Polars native expressions for DataFrame operations. Remove `.iter_rows()`, `.rows()`, `.to_list()`, or Python row loops in data-processing hot paths unless an unavoidable external-library boundary is demonstrated.

Preserve metric definitions and undefined behavior exactly.

### Phase 10 — Analysis, comparisons, Pingouin, and Polars

Use Pingouin for supported procedures where verified equivalent, including Spearman correlation, linear regression, descriptive statistics, Wilcoxon, rank-biserial correlation, and multiplicity correction as applicable.

Retain SciPy or statsmodels only for procedures Pingouin does not equivalently provide, including BCa bootstrap, leverage diagnostics, or leave-one-out diagnostics.

Do not alter statistical results while replacing implementation boilerplate.

Analysis must consume canonical evaluation artifacts, use typed contexts, use explicit handler registration, and avoid import-time side effects.

Run every configured analysis kind and compare its output to the baseline.

### Phase 11 — Result freezing, tables, and plots

Replace dictionary-driven report definitions with typed report specifications.

Preserve real persisted artifacts, including all configured Markdown, LaTeX, PNG, PDF, SVG, Parquet, and CSV outputs.

Frozen results must be typed models. Do not retain dictionary access disguised behind helper functions.

Preserve table values, figure data, units, labels, directions, and report-profile behavior.

### Phase 12 — Standalone experiment lifecycle

Implement one atomic `ExperimentRunner` owning fresh, skip, override, incomplete, corrupt, failure, completion-marker, and cleanup semantics.

Existing completed outputs are authoritative unless explicit override is requested.

An incomplete experiment must be safely removed and rerun.

A corrupt completed experiment must not be silently skipped.

Do not retain parallel lifecycle logic in a compatibility wrapper.

Delete the replaced execution use-case file when migration is complete.

### Phase 13 — Campaign simplification

Consolidate campaign ordering and lifecycle execution into one `CampaignRunner`.

Required campaign behavior:

* deterministic canonical ordering;
* anchors and prerequisites handled explicitly;
* same command resumes interrupted campaigns;
* completed compatible experiments are skipped;
* the first incomplete or corrupt experiment is cleaned and rerun;
* prerequisite scientific and execution fingerprints are checked;
* minimal sharing is permitted only when fingerprints and artifact semantics match;
* no run ID or job ID becomes a competing source of truth;
* experiment output directories remain authoritative;
* override-all safely removes campaign and shared outputs;
* typed statuses and frozen-result models replace string and dictionary logic.

Do not introduce a campaign framework or separate campaign domain package.

### Phase 14 — Dagster, diagnostics, CLI, and composition

Dagster remains canonical.

Generate stage-level Dagster operations from the canonical `ExperimentPlan`, with real upstream dependencies and stage visibility.

Remove:

* the opaque one-operation-per-experiment wrapper;
* hardcoded repository paths;
* direct planning imports from CLI;
* CLI infrastructure logic;
* CLI and diagnostics `os.environ` mutation;
* duplicate orchestration paths.

The CLI must only parse arguments, call application use cases, render typed results, and map typed failures to exit codes.

Configuration-only commands must remain lightweight and must not initialize CUDA, DuckDB, training handlers, datasets, or the full application unnecessarily.

### Phase 15 — Debloating and legacy removal

Perform the roadmap’s full deletion and consolidation ledger.

Delete replaced files only after all callers and tests have migrated.

Audit every remaining source and test file for:

* `Any`;
* untyped domain dictionaries;
* raw closed-vocabulary strings;
* implicit scientific defaults;
* unused configuration;
* unused enum values;
* dead records or dataclasses;
* dead branches;
* unnecessary inheritance;
* trivial wrappers;
* single-function files that should be merged;
* duplicated formulas;
* duplicate path construction;
* compatibility aliases;
* redirects;
* deprecated exports;
* stale comments or docstrings;
* AI-generated narration;
* vague names;
* repeated fixture boilerplate;
* duplicate tests;
* over-mocking;
* architecture that is open to extension only through editing central conditionals.

Fix all issues found rather than merely listing them.

Net simplification must be real: fewer authorities, fewer files, fewer lines, fewer nullable fields, fewer lookups, and easier navigation. Do not meet the roadmap by adding more abstractions than are removed.

### Phase 16 — Full scientific and execution verification

Execute every verification required by the roadmap:

* configuration validation;
* repeated resolution and fingerprint comparison;
* all dataset source and materialization checks;
* plans for every configured experiment;
* stage-key, dependency, and path comparison;
* representative FedAvg, FedProx, and Ditto execution;
* checkpoint equivalence;
* every threshold policy family;
* every metric;
* every configured analysis;
* every report profile;
* standalone lifecycle scenarios;
* campaign fresh/resume/blocking/sharing/corrupt/override scenarios;
* stage-level Dagster execution;
* diagnostic execution;
* all quality gates;
* final cleanup.

Do not declare success based only on tests. Compare the scientific and execution evidence to the locked Phase 0 baseline.

---

## 6. Per-File Work Loop

For each production file in the current phase:

1. Read the entire file.
2. Identify its exact responsibility.
3. Inspect all direct callers and directly affected dependencies.
4. Locate its tests.
5. Identify the roadmap requirement affecting it.
6. Record a concise per-file checklist in `.tmp`.
7. Audit before editing for:

   * scientific semantics;
   * architecture;
   * naming;
   * typing;
   * enums;
   * dictionaries;
   * defaults;
   * duplication;
   * comments and docstrings;
   * configuration use;
   * test coverage;
   * opportunities to delete or merge code.
8. Implement the complete correction.
9. Adapt, remove, consolidate, or add tests immediately.
10. Run the smallest relevant test set and static checks.
11. Re-read the complete modified file.
12. Audit the checklist a second time.
13. Verify no stale caller, import, alias, file, fixture, or documentation remains.
14. Record completion and move to the next file.

Do not modify several unrelated production files and postpone all tests until later.

Do not run the full repository test suite after every small edit. Use:

* impacted tests after a file or tightly coupled group;
* package-level tests after completing a package;
* phase-level gates after completing a phase;
* the full suite at baseline, cross-cutting integration gates, and final verification.

---

## 7. Test Requirements

Tests are part of the architecture and must evolve with the implementation.

For every changed production contract:

* inspect the corresponding existing tests;
* remove tests for deleted behavior;
* update tests for intentionally changed architecture;
* retain scientific regression coverage;
* add missing contract, failure, boundary, and integration coverage;
* remove duplicate tests;
* parameterize repeated policy or strategy tests;
* avoid enormous fixture dictionaries;
* replace raw protocol dictionaries with typed builders or models;
* avoid mocking pure functions and simple data structures;
* test externally observable behavior rather than private implementation details;
* keep deterministic seeds explicit;
* test invalid states and fail-fast behavior;
* test serialization and round trips where models cross boundaries;
* test that configuration-only paths avoid CUDA and heavy-service initialization.

Tests must not preserve obsolete APIs merely to avoid updating them.

Do not add compatibility re-exports for tests. Update the tests to the final architecture.

No `Any` is allowed in tests.

At the end, unit, integration, scientific, lifecycle, campaign, CLI, configuration, reporting, and Dagster tests must all pass.

---

## 8. Cleaning and Architecture Rules

Apply these rules throughout the work, not only in Phase 15.

### Mandatory

* Clear single responsibility per file.
* Explicit types at module boundaries.
* Enums for closed vocabularies.
* Typed IDs for identities.
* Pydantic v2 for validated boundary and persisted models.
* Frozen dataclasses for lightweight internal coordinates where validation is unnecessary.
* Configuration-driven scientific and runtime values.
* No hidden fallback behavior.
* No mutable defaults.
* No unused configuration.
* No raw dictionaries where a typed object is appropriate.
* No `Any`.
* No vague names such as `data`, `info`, `item`, `obj`, `tmp`, `result_dict`, or `config_map` when a precise domain name exists.
* No duplicate scientific formulas.
* No duplicate path-building logic.
* No import-time registry mutation.
* Explicit composition in `app.py`.
* Architecture must support extension through local additions rather than central branching where the roadmap requires registries.
* Every abstraction must remove more complexity than it introduces.

### Forbidden

* Backward-compatibility shims.
* Redirect modules.
* Deprecated aliases.
* Compatibility re-exports.
* Old and new APIs existing simultaneously.
* Service locators.
* Dependency-injection frameworks.
* Generic plugin systems.
* Registries not permitted by the roadmap.
* Wrapper classes without meaningful behavior.
* One-record packages.
* Arbitrary base classes.
* Dictionary-based service communication.
* Hidden global state.
* Hardcoded repository paths.
* Hardcoded scientific parameters.
* Silent fallback to defaults.
* Catching broad exceptions and continuing with corrupt state.
* Comments that narrate obvious code.
* Banner comments.
* AI-generated explanatory comments.
* Dead commented-out code.
* “Temporary” production branches.
* Disabling lint, typing, tests, or scientific checks to obtain green output.

Preserve or add a comment only when it explains a genuinely non-obvious scientific, statistical, security, or interoperability decision that the code itself cannot express.

---

## 9. Tool and Quality-Gate Handling

Before relying on a tool, verify that it exists and understand how the repository invokes it.

Check at least:

* Ruff;
* formatter verification;
* Pyright;
* Pylance-compatible configuration;
* Pylint;
* pytest;
* pytest-xdist where appropriate;
* import-linter;
* nox;
* Hydra;
* Dagster;
* SonarQube or SonarCloud integration;
* CodeScene;
* Graphify or equivalent architecture visualization tooling when useful.

Graph tooling may be used to understand imports, dependencies, stage graphs, and architecture. It must not generate decorative repository clutter.

If an external service is unavailable, unauthenticated, rate-limited, or quota-limited:

1. Record the exact failure in `.tmp`.
2. Continue all independent local implementation and validation.
3. Retry the external check before final completion.
4. Do not declare the corresponding gate passed without evidence.
5. Do not dismiss findings as false positives.
6. Fix all actionable findings in touched scope.
7. Ensure global Sonar issues do not increase and CodeScene hotspots do not worsen.
8. Where access permits, resolve all remaining actionable open issues rather than accepting them.

Do not stop the entire implementation merely because one external service is temporarily unavailable.

---

## 10. Documentation Synchronization

Update README, Makefile, CLI documentation, configuration documentation, diagrams, and architecture documentation only when actual commands, paths, configuration composition, output layouts, or responsibilities change.

Documentation must describe the final architecture only.

Do not document transitional APIs or deleted paths.

Do not add progress logs, audit dates, agent narratives, or implementation diaries to permanent documentation.

Do not mark the simplification roadmap as complete until Phase 16 and the final checklist have passed.

---

## 11. Required Audits

Perform repeated audits throughout the work.

At minimum:

1. Baseline scientific audit before changes.
2. Architecture and dependency audit after core compilation, paths, contexts, and planning are migrated.
3. Scientific pipeline audit after learning, thresholding, and evaluation changes.
4. Statistical and reporting audit after analysis and reporting changes.
5. Execution audit after standalone lifecycle, campaign, and Dagster changes.
6. Final repository-wide scientific, architectural, typing, duplication, configuration, testing, and cleanup audit.

For each experiment, manually trace the complete pipeline:

```text
configuration
→ experiment compilation
→ plan construction
→ dataset materialization
→ training
→ checkpoint selection
→ scoring
→ calibration subsampling
→ threshold construction
→ evaluation
→ statistical analysis
→ result freezing
→ reporting
→ finalization
```

Verify that artifacts, contexts, paths, dependencies, seeds, configurations, and scientific invariants remain correct at every boundary.

Do not rely exclusively on test coverage to establish pipeline correctness.

---

## 12. Completion Is Binary

You may report:

```text
GO FOR EXPERIMENTS
```

only when every roadmap completion checklist and every item in the final `GO FOR EXPERIMENTS` checklist is verified with evidence.

The final state must include all of the following:

* the target architecture is implemented;
* all replaced architecture is deleted;
* one resolved configuration authority exists;
* each experiment compiles once;
* one plan builder exists;
* one path authority exists;
* four typed context families replace the nullable context;
* threshold dispatch is registry-based by policy kind;
* evaluation owns metrics;
* analysis consumes canonical metrics;
* reporting is typed and persists all required formats;
* standalone lifecycle is atomic;
* campaign resumption and sharing are deterministic and fingerprint-safe;
* Dagster has stage-level visibility and uses the canonical plan;
* CLI is thin;
* no compatibility artifacts remain;
* no prohibited attrs or cattrs usage remains;
* no untyped domain dictionaries remain;
* no `Any` remains in source or tests;
* no hidden defaults or hardcoded scientific values remain;
* no duplicate formulas or path authorities remain;
* every configured experiment compiles and plans;
* scientific fingerprints match the baseline;
* execution fingerprints match the baseline;
* threshold, metric, statistical, checkpoint, materialization, planning, and reporting outputs match the baseline;
* all unit, integration, scientific, lifecycle, campaign, CLI, reporting, and Dagster tests pass;
* all static checks pass;
* configuration validates;
* Sonar issues have not increased;
* CodeScene hotspots have not worsened;
* the final repository is measurably smaller and simpler;
* `.tmp` contains no stale state that should be cleaned after the final report;
* no generated clutter remains elsewhere.

Any numeric change in a locked scientific value, threshold, cluster assignment, checkpoint selection, `CV(FPR)`, BCa interval, statistical result, experiment plan, or artifact semantics is a blocker unless the change fixes a proven pre-existing scientific defect. Such a correction must be documented with exact before/after evidence and reconciled with the scientific source of truth before completion.

Passing tests with unfinished migration, obsolete files, compatibility layers, duplicated architecture, scientific uncertainty, or skipped required validation is not completion.

---

## 13. Final Verification Commands

Use the repository’s actual supported sessions, but the final verification must cover at least:

```bash
datp-core config validate
datp-core config fingerprint
datp-core config explain-scientific-drift
nox -s lint
nox -s typecheck
nox -s pylint
nox -s imports
nox -s scientific_invariants
nox -s tests
nox -s quality
```

Also run:

* formatter check;
* package-specific test groups;
* full test suite;
* all configured experiment-plan generation;
* standalone lifecycle matrix;
* campaign lifecycle matrix;
* Dagster graph and execution checks;
* reporting generation;
* Sonar analysis;
* CodeScene analysis.

Use parallel test execution only where isolation and determinism are preserved.

Do not conceal skipped commands. A required command may be skipped only when genuinely impossible, and an impossible required gate prevents `GO FOR EXPERIMENTS`.

---

## 14. Final Response Format

The final response must contain:

1. **Verdict**

   * `GO FOR EXPERIMENTS`, or
   * `NOT READY` when a mandatory external or environmental blocker genuinely remains.

2. **Implemented roadmap**

   * each phase and its verified result.

3. **Architecture result**

   * final authorities, deleted files, merged files, and simplified responsibilities.

4. **Scientific-equivalence evidence**

   * fingerprints and the major baseline comparisons.

5. **Tests and quality gates**

   * exact commands and outcomes.

6. **Cleanup result**

   * deleted compatibility code, dead code, duplicate tests, stale files, comments, and temporary artifacts.

7. **Measured simplification**

   * before/after file count, source lines, path authorities, context nullability, configuration lookups, dispatch chains, and model-system usage.

8. **External checks**

   * Sonar and CodeScene results.

9. **Remaining blockers**

   * this section must state `None` for `GO FOR EXPERIMENTS`.

Do not provide a list of recommended future fixes while claiming completion.

Begin now by reading the full roadmap and repository, establishing the Phase 0 baseline, creating the resumable state under `.tmp/datp-core-simplification/`, and then execute every phase until the final verdict is justified.

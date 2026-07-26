You are working directly inside:

```text
/home/naslouby/Projects/datp-core
```

Your objective is to perform a complete, repository-wide scientific, architectural, technical, and runtime audit and refactoring of `datp-core` until the repository is genuinely ready for full experiments.

Work directly on `main`. Do not create a branch or worktree.

This task is not limited to fixing failing tests, addressing obvious defects, formatting code, or performing a superficial review. You must inspect, understand, refactor, validate, and scientifically audit the repository package by package and file by file.

You must continue the audit–fix–validate loop until the only defensible final verdict is:

```text
GO FOR EXPERIMENTS
```

Do not stop early because:

* Tests pass once.
* Static analysis is green once.
* One package looks clean.
* Most files have been processed.
* SonarCloud reports fewer issues.
* CodeScene reports improvement.
* Diagnostics start successfully.
* The architecture merely looks better than before.
* A previous agent already changed a file.
* A file was previously marked complete.
* A defect appears to be pre-existing.
* A finding appears minor.
* A scientific path is difficult to inspect.
* An external tool temporarily reaches its quota.

The process must be idempotent and crash-safe. Re-running this exact prompt must inspect previous progress, verify already completed work, resume safely, and converge to the same final repository state without duplicate edits, repeated churn, or conflicting architecture.

---

# 1. Verify Every Required Tool Before Changing Anything

Before making any source-code change, verify the repository environment and every required tool.

Confirm:

* Git is installed and functional.
* The repository is valid.
* The current branch is `main`.
* Repository remotes are correct.
* Authentication works.
* Direct push permission to `main` exists.
* SonarCloud connectivity works.
* The latest SonarCloud analysis can be retrieved.
* SonarCloud commit association can be inspected.
* SonarCloud issues, bugs, vulnerabilities, security hotspots, duplication blocks, coverage conditions, and Quality Gate status can be retrieved.
* CodeScene is installed and authenticated.
* CodeScene Delta is installed and usable against this repository.
* Graphify is installed and can inspect:

  * Package dependencies.
  * File dependencies.
  * Imports.
  * Symbols.
  * Callers and callees.
  * Test relationships.
  * Cycles.
  * Architectural coupling.
* Ruff is installed.
* Formatting validation is available.
* Pyright is installed.
* The strict Pylance-compatible configuration is usable.
* Pylint is installed.
* pytest is installed.
* pytest-xdist is installed.
* import-linter is installed.
* Every repository-specific architecture command is available.
* Every repository-specific scientific validation command is available.
* CUDA is visible.
* The configured GPU is supported.
* PyTorch can use CUDA.
* Deterministic PyTorch behavior can be enabled and verified.
* Required packages and runtime dependencies are installed.
* The raw-data symlink is valid.
* The raw-data symlink target exists and is readable.

The raw-data symlink must not be:

* Replaced.
* Copied into the repository.
* Converted into a real directory.
* Deleted.
* Recreated unnecessarily.
* Modified.
* Followed by cleanup logic that can delete its target.

Record inside `.tmp`:

* Tool name.
* Exact command.
* Version.
* Availability.
* Authentication status where applicable.
* Validation result.
* Any limitation or failure.

Do not silently skip a required tool.

Do not silently replace a required tool with an assumed equivalent.

## Temporary external-tool failure handling

If SonarCloud, CodeScene, Graphify, or another external service is temporarily unavailable because of:

* Quota exhaustion.
* Rate limiting.
* Temporary service outage.
* Authentication-session expiration.
* Temporary network failure.
* Delayed analysis availability.

Then:

1. Record the exact command and exact failure.
2. Record which acceptance gate is temporarily blocked.
3. Continue all unrelated local analysis, refactoring, tests, diagnostics, commits, and pushes.
4. Do not claim the unavailable tool passed.
5. Retry the tool after later package pushes.
6. Retry it again during the final acceptance loop.
7. Do not issue `GO FOR EXPERIMENTS` until every mandatory external check has eventually completed successfully.

Temporary quota exhaustion must not stop independent work.

---

# 2. Read and Lock the Scientific Source of Truth

Before refactoring, study the complete scientific and implementation source of truth.

Read all relevant files in:

```text
roadmap/
configs/
```

Study, at minimum:

* Scientific identity.
* Scope.
* Claim hierarchy.
* Decision rules.
* Experiment catalogue.
* Evaluation protocol.
* Reporting protocol.
* Implementation roadmap.
* Reviewer risks.
* Audit and decision records.
* Dataset definitions.
* Population definitions.
* Split rules.
* Seed cohorts.
* Threshold-policy definitions.
* Model and training rules.
* Checkpoint-selection rules.
* Calibration rules.
* Statistical-analysis rules.
* Artifact contracts.
* Availability semantics.
* Configuration files.
* Configuration schemas.
* Reporting requirements.
* Claim boundaries.

Build a traceability map connecting every configured experiment to:

* Experiment identity.
* Dataset.
* Dataset capability.
* Client definition.
* Population.
* Split.
* Seed cohort.
* Sweep dimensions.
* Model.
* Federated training protocol.
* Local training protocol.
* Participation semantics.
* Aggregation.
* Checkpoint-selection rule.
* Score-generation artifacts.
* Calibration inputs.
* Calibration restrictions.
* Threshold policies.
* Evaluation metrics.
* Metric availability.
* Statistical analyses.
* Report outputs.
* Final artifacts.
* Claim tier.
* Claim boundary.

Record all non-negotiable scientific invariants before editing code.

Do not invent:

* Scientific values.
* Defaults.
* Missing parameters.
* Dataset semantics.
* Split semantics.
* Seed semantics.
* Fallback behavior.
* Availability behavior.
* Statistical behavior.
* Threshold behavior.
* Experiment relationships.
* Unsupported claims.

Do not alter the roadmap or configuration merely to make incorrect implementation behavior pass.

Implementation must conform to the scientific source of truth.

---

# 3. Create Durable, Crash-Safe, Idempotent Progress Tracking

Create and use:

```text
.tmp/
```

Use it only as a working directory for:

* Checklists.
* Graphify outputs.
* Findings.
* Diagnostics.
* Tool results.
* Package state.
* File state.
* Unresolved risks.
* Changelog entries.
* Scientific traceability notes.
* Validation results.
* External-analysis results.

Maintain a machine-readable progress ledger covering every production package and every production or test file processed.

For every file, record:

* Original path.
* Final path.
* Initial responsibility.
* Final responsibility.
* Package responsibility.
* Graphify imports.
* Graphify importers.
* Callers.
* Callees.
* Related production files.
* Direct corresponding tests.
* Indirect corresponding tests.
* Experiments affected.
* Pipeline stages affected.
* First technical checklist result.
* First scientific checklist result.
* Defects found.
* Refactoring decision.
* Changes performed.
* Tests changed.
* Targeted commands executed.
* Targeted validation results.
* Second technical checklist result.
* Second scientific checklist result.
* Changelog entry.
* Remaining dependencies.
* Final status.

Update progress immediately after each completed file.

After an interruption or crash, resume from the ledger rather than restarting blindly.

When a file is already marked complete:

1. Verify that it still exists in the recorded state.
2. Verify later changes did not invalidate it.
3. Verify its tests still pass.
4. Verify its architecture remains coherent.
5. Verify its scientific assumptions remain valid.
6. Reopen it if any later package change affected its contracts.

Do not trust a previous completion marker without verification.

---

# 4. Maintain a Dedicated Refactoring Changelog

Create a chronological refactoring changelog inside `.tmp` before processing files.

Add an entry immediately after every production file is completed.

Each file entry must include:

* Path before the change.
* Path after the change.
* Whether it was:

  * Retained.
  * Renamed.
  * Moved.
  * Merged.
  * Split.
  * Deleted.
* Architectural responsibility.
* Main defects identified.
* Main scientific risks identified.
* Main changes made.
* Corresponding tests changed.
* Scientific invariants reviewed.
* Targeted commands executed.
* Validation results.
* Dependencies affected.
* Remaining follow-up work.
* First technical checklist result.
* First scientific checklist result.
* Second technical checklist result.
* Second scientific checklist result.
* Final completion state.

Do not move to the next production file before completing the current file’s changelog entry.

When a test file is independently optimized, add its own changelog entry.

When a completed file must later be revisited, create a new changelog entry rather than rewriting historical evidence.

---

# 5. Create Production Diagnostic Commands Before Main Refactoring

Before starting the package-by-package architecture work, ensure the repository provides:

1. A production command that diagnoses one experiment using one configured seed.
2. A production command that diagnoses the complete campaign using one configured seed per experiment.

Diagnostics must execute the real production pipeline.

Do not create:

* Mock diagnostic pipelines.
* Simplified duplicate implementations.
* Shortcut stage runners.
* Diagnostic-only scientific logic.
* Separate orchestration semantics.
* Fake artifact writers.
* Reduced pipeline copies.

Diagnostics must cover the actual path through:

1. Configuration loading.
2. Configuration validation.
3. Experiment resolution.
4. Campaign planning.
5. Dataset materialization.
6. Split resolution.
7. Training.
8. Checkpoint selection.
9. Score generation.
10. Calibration or subsampling.
11. Threshold construction.
12. Evaluation.
13. Statistical analysis.
14. Reporting.
15. Finalization.
16. Artifact validation.

Diagnostic outputs must be isolated from official experiment outputs.

---

# 6. Preserve Dagster as the Canonical Orchestrator

Dagster is the canonical orchestration implementation.

The following must all delegate to the same Dagster-backed production pipeline:

* CLI commands.
* Single-experiment execution.
* Campaign execution.
* Diagnostics.
* Resumption.
* Stage dependency resolution.
* Resource binding.
* Artifact transitions.
* Finalization.

Do not retain or introduce:

* A second manual pipeline runner.
* A diagnostic-only runner.
* A separate campaign engine.
* Duplicate stage-transition logic.
* Duplicate orchestration state machines.
* Parallel orchestration implementations.
* Independent scientific execution paths outside Dagster.

Domain logic may remain independent of Dagster where appropriate, but orchestration must have one canonical production path.

If parallel orchestration paths already exist:

* Identify them.
* Determine the canonical responsibility.
* Consolidate them.
* Update CLI commands.
* Update diagnostics.
* Update tests.
* Update imports.
* Remove obsolete runners.
* Do not preserve compatibility wrappers.

---

# 7. Lock Campaign Execution Semantics

The following campaign behavior is mandatory.

## Execution identity

Do not introduce or depend on:

* `runId`.
* `jobId`.
* Random execution IDs.
* Synthetic execution identity layers.
* Duplicate manifest identities unrelated to the experiment.

The per-experiment output directory is the authoritative execution state.

## Completed experiment behavior

When an experiment output is complete and valid:

* Skip it by default.
* Do not recompute it.
* Do not modify it.
* Do not partially overwrite it.

## Override behavior

When an explicit override is requested:

* Delete only the selected experiment’s output directory.
* Recreate only that experiment.
* Do not delete unrelated completed experiments.
* Do not clear the full campaign.
* Do not touch raw data.
* Do not touch symlink targets.

## Campaign resumption

The normal campaign command is also the resume command.

Do not create a separate resume workflow.

After interruption:

1. Detect every completed experiment.
2. Preserve all valid completed experiments.
3. Identify the first incomplete experiment.
4. Remove only that incomplete experiment’s output.
5. Restart from that experiment.
6. Continue through later experiments.

## Completion semantics

A completion marker must be written:

* Atomically.
* Last.
* Only after every required artifact is finalized.
* Only after every required artifact is validated.
* Only after the experiment is truly complete.

Partial artifacts must never be interpreted as completion.

Campaign cleanup must never delete:

* Completed experiments.
* Official results.
* Raw data.
* Symlink targets.
* Unrelated output roots.

Test skip, override, interruption, cleanup, and automatic resumption through the normal production command.

---

# 8. Create Mandatory Checklists

Before processing packages or files, create two mandatory checklists.

## Technical and architectural checklist

It must cover:

* File responsibility.
* Package responsibility.
* Naming.
* Typing.
* `Any`.
* Broad `object`.
* Dictionary usage.
* Mapping usage.
* Enum usage.
* Dataclass usage.
* Value-object usage.
* Pydantic boundary use.
* Configuration use.
* Hardcoded values.
* Hidden defaults.
* Stringly typed dispatch.
* Dynamic `getattr`.
* Duplication.
* Complexity.
* Coupling.
* Dependency direction.
* Circular imports.
* Extensibility.
* Overengineering.
* Boilerplate.
* Error handling.
* Availability semantics.
* Artifact safety.
* Atomic writes.
* Cleanup safety.
* Comments.
* Dead code.
* Thin wrappers.
* Giant modules.
* Tiny unnecessary modules.
* Test quality.
* Test duplication.
* Test architecture.
* Determinism.

## Scientific-integrity checklist

It must cover:

* Dataset identity.
* Dataset capability.
* Client identity.
* Population identity.
* Split rules.
* Partition identity.
* Seed identity.
* Seed pairing.
* Sweep identity.
* Replicate identity.
* Training semantics.
* Aggregation semantics.
* Participation semantics.
* Checkpoint selection.
* Frozen-model requirements.
* Calibration restrictions.
* Benign-only requirements.
* Threshold construction.
* Metric definitions.
* Metric denominators.
* Metric availability.
* Statistical units.
* Statistical pairing.
* Artifact provenance.
* Scientific fingerprints.
* Leakage prevention.
* Claim boundaries.
* Reporting semantics.
* Unsupported-claim prevention.

Apply both checklists:

* To every production file.
* At least twice per production file.
* To each package after all files are complete.
* At least twice per package.

The first file-level comparison occurs before and during refactoring.

The second file-level comparison occurs after implementation and targeted validation.

The first package-level comparison occurs after all package files are assembled.

The second package-level comparison occurs after the full suite and diagnostics pass.

Passing tests alone is never sufficient.

---

# 9. Use Graphify Before Processing Each Package

Before processing each package:

1. Generate or refresh the package dependency graph.
2. Inspect:

   * Import direction.
   * Symbol usage.
   * Callers.
   * Callees.
   * Entry points.
   * Test relationships.
   * Cycles.
   * Central files.
   * High-coupling files.
   * Orphaned modules.
   * Duplicate-responsibility clusters.
   * Cross-package leakage.
3. Identify:

   * Artificial package boundaries.
   * Fragmented responsibilities.
   * Overloaded files.
   * Misplaced files.
   * Duplicate implementations.
   * Thin wrapper chains.
   * Hidden orchestration paths.
4. Determine a safe file-processing order.
5. Prefer foundational domain files before dependent orchestration, interfaces, reporting, and CLI code where practical.

After completing the package, rerun Graphify.

Verify that:

* Coupling improved.
* Cycles were removed or reduced.
* Responsibilities became clearer.
* Duplicate implementations were removed.
* Problems were not merely moved elsewhere.
* New central bottlenecks were not introduced.
* Test architecture remains coherent.

---

# 10. Plan a Clear but Restrained Target Architecture

Freely:

* Move files.
* Rename files.
* Merge files.
* Split files.
* Delete files.
* Move responsibilities between packages.
* Rename packages.
* Merge packages.
* Remove unnecessary packages.

Do not preserve an unsuitable structure merely because current imports depend on it.

Do not preserve old imports through:

* Re-export modules.
* Redirect modules.
* Compatibility wrappers.
* Deprecated aliases.
* Forwarding modules.
* Migration shims.

Keep the total package count controlled.

Prefer a limited number of capability-oriented packages with explicit responsibilities.

Avoid:

* Excessive nesting.
* One-class modules without justification.
* One-function modules without justification.
* Directories containing only thin wrappers.
* Giant packages mixing unrelated concerns.
* Giant files mixing domain, orchestration, IO, analysis, reporting, and CLI behavior.
* Artificial interfaces with one implementation.
* Abstract factories without genuine variation.
* Speculative extension points.
* Duplicate domain models.
* Duplicate path logic.
* Duplicate artifact parsing.
* Duplicate pipeline transitions.

Every package and file must have a defensible reason to exist.

Architecture changes must update all affected:

* Imports.
* Tests.
* Configurations.
* CLI commands.
* Dagster definitions.
* Diagnostics.
* Artifact paths.
* Documentation that is directly affected.

Repository-support files outside production packages and tests may be skipped unless they are:

* Directly affected by the refactor.
* Required for validation.
* Responsible for a detected failure.
* Necessary to preserve build, packaging, typing, lint, orchestration, or runtime correctness.

Do not expand the task into unrelated repository documentation cleanup.

---

# 11. Process Exactly One Production Package at a Time

Select one production package.

Audit its:

* Complete purpose.
* Scientific purpose.
* Public API.
* Internal responsibilities.
* Dependencies.
* Dependents.
* Configuration contracts.
* Artifact contracts.
* Dagster responsibilities.
* Callers.
* Tests.
* Experiment relationships.
* Pipeline-stage relationships.

Decide whether the package should:

* Remain unchanged structurally.
* Be renamed.
* Be merged.
* Be split internally.
* Absorb another responsibility.
* Move responsibilities elsewhere.
* Be deleted.

Complete the entire package before moving to the next package.

Do not leave known package-level problems for a later generic cleanup phase.

Do not commit or push while the package is incomplete.

---

# 12. Iterate Through Production Files One File at a Time

Within the active package, select exactly one active production file.

The active file represents the current responsibility being resolved.

The one-file rule does not prohibit the minimum atomic edits required to:

* Move the file.
* Merge it into another file.
* Split it.
* Delete it.
* Update directly affected imports.
* Update directly affected contracts.
* Keep the repository coherent.

When the active file requires touching another production file:

1. Limit changes to the minimum coherent affected surface.
2. Record every additionally touched production file.
3. Record why it had to be touched.
4. Do not treat the additionally touched file as fully processed automatically.
5. Process that file independently with its own checklist passes, tests, validation, and changelog entry before marking it complete.

Do not concurrently refactor multiple unrelated production files.

For the active file:

1. Read the entire file.
2. Understand every public symbol.
3. Understand every internal symbol.
4. Understand every dependency.
5. Understand every caller.
6. Understand every output.
7. Understand every side effect.
8. Understand every artifact.
9. Understand every scientific assumption.
10. Locate every corresponding test.

Use Graphify or the relevant graph slice to identify:

* Every importer.
* Every imported dependency.
* Every symbol caller.
* Every downstream consumer.
* Every related test.
* Every strongly coupled neighbor.
* Every architecture contract affected.

Create the first technical checklist result.

Create the first scientific checklist result.

Decide whether the file should:

* Remain.
* Move.
* Rename.
* Merge.
* Split.
* Be deleted.

Refactor only:

* The active file.
* Its corresponding tests.
* The minimum directly affected production surface required for coherence.

Then:

1. Run targeted validation.
2. Perform the second technical checklist pass.
3. Perform the second scientific checklist pass.
4. Complete the changelog entry.
5. Update the progress ledger.
6. Mark the file complete.
7. Only then select the next file.

---

# 13. Scope Subagents to the Active Production File

Subagents may be used only relative to the active production file and code or tests it directly touches.

Codex use is optional, not mandatory.

When Codex is used, treat it as a subagent governed by the same scope restrictions.

Do not assign unrelated production files from the same package to parallel subagents.

Do not allow subagents to independently redesign unrelated packages.

Appropriate file-scoped subagent tasks include:

* Inspecting callers.
* Inspecting dependencies.
* Auditing scientific assumptions.
* Reviewing corresponding tests.
* Identifying duplication involving the active file.
* Auditing typing.
* Auditing configuration use.
* Reviewing the proposed file-level architecture.
* Performing an independent checklist review.

The primary agent must reconcile all findings against:

* The roadmap.
* Configuration.
* Graphify output.
* Actual source code.
* Tests.
* Production behavior.

Subagents must not:

* Make overlapping edits to the same production file.
* Independently mark a file complete.
* Independently authorize moving to another file.
* Independently mark checklist items passed.
* Perform broad repository rewrites.

Subagent output is advisory until verified.

---

# 14. Allow Parallel Work Only for Test Files

Test files may be processed in parallel only after the relevant production behavior and expected interfaces are understood.

Divide parallel test work by:

* Non-overlapping test files.
* Non-overlapping responsibilities.

Each test subagent must receive:

* Relevant production behavior.
* Public interfaces.
* Scientific invariants.
* Expected final contracts.
* Test architecture rules.
* Naming rules.
* Typing rules.
* No-dictionary rules.
* No-comment rules.

Do not allow multiple subagents to edit the same:

* Fixture module.
* Shared helper.
* Builder.
* Test configuration.
* Shared test data file.

Reconcile shared changes centrally.

After merging parallel test work, run:

* Formatting.
* Ruff.
* Typing.
* Targeted tests.

Parallel test work must not create:

* Duplicate builders.
* Conflicting fixtures.
* Multiple competing test architectures.
* Excessive abstraction.
* Hidden scientific values.
* Inconsistent naming.
* Conflicting mocks.

---

# 15. Optimize and Debloat Every Test File

Inspect every test file, not only failing tests.

Remove:

* Duplicate tests.
* Repeated setup.
* Redundant assertions.
* Excessive parameterization.
* Obsolete compatibility tests.
* Implementation-coupled tests.
* Tests of irrelevant internal details.
* Giant fixture modules.
* Unnecessary helper frameworks.
* Generic factories that hide scientific values.
* Excessive mocking.
* Dead tests.
* Redundant snapshot data.
* Duplicate builders.

Replace dictionary-based fixtures with:

* Typed builders.
* Dataclasses.
* Enums.
* Value objects.
* Explicit domain records.

Prefer:

* Small explicit fixtures.
* Deterministic inputs.
* Temporary paths.
* Real lightweight domain objects.
* Realistic artifacts.
* Explicit scientific values.
* Typed result objects.

Add justified tests for:

* Public behavior.
* Scientific invariants.
* Invalid configuration.
* Missing artifacts.
* Incomplete artifacts.
* Population mismatch.
* Seed mismatch.
* Leakage.
* Unsupported capability combinations.
* Interrupted execution.
* Idempotent resumption.
* Explicit metric unavailability.
* Campaign skip.
* Campaign override.
* Campaign restart.
* Completion-marker semantics.
* Dagster production execution.

Ensure every configured:

* Policy.
* Stage.
* Analysis family.
* Dataset capability.
* Meaningful failure branch.

Has justified coverage.

Test code must meet the same quality standards as production code.

---

# 16. Apply Strict Architecture and Code Rules

Apply these rules to every active file, including pre-existing code.

## Compatibility

* No backward compatibility.
* No redirects.
* No re-export modules.
* No deprecated aliases.
* No migration shims.
* No forwarding wrappers.
* No legacy import preservation.
* No obsolete APIs retained solely to keep old tests passing.

## Dictionaries and dynamic structures

Do not use generic dictionaries for:

* Domain entities.
* Pipeline inputs.
* Pipeline outputs.
* Contexts.
* Artifacts.
* Configuration.
* Dispatch.
* Statistics.
* Scientific results.
* Cross-package communication.

Replace arbitrary mappings with explicit typed structures.

A temporary mapping may exist only where required by an external library or serialization boundary. It must not become the canonical internal representation.

## Enums

Use enums for closed vocabularies such as:

* Experiments.
* Datasets.
* Populations.
* Pipeline stages.
* Threshold policies.
* Metrics.
* Artifact types.
* Availability statuses.
* Failure reasons.
* Modes.
* Objectives.
* Decisions.
* Paths.

Remove stringly typed dispatch.

Remove repeated string comparisons.

## Dataclasses and domain models

Use immutable dataclasses or equivalent typed records for stable domain concepts.

Merge duplicate or overlapping dataclasses.

Maintain one canonical representation for each scientific concept.

Use Pydantic v2 at external configuration and validation boundaries.

Do not spread Pydantic models throughout internal scientific logic when immutable domain records are clearer.

## Typing

Remove:

* `Any`.
* Broad `object`.
* Arbitrary nested mappings.
* Unchecked casts.
* Dynamic scientific dispatch.
* Weak protocols.
* Silent fallback typing.
* Dynamic configuration probing.

Replace dynamic `getattr` configuration access with explicit typed interfaces.

## Configuration

Remove hidden defaults.

Remove implicit scientific assumptions.

Move configurable scientific and runtime values into validated configuration where appropriate.

Remove unused configuration fields.

Every configured field must:

* Be validated.
* Be consumed.
* Affect real execution.
* Be traceable.

Do not leave decorative configuration.

## Extensibility

Replace large condition chains with:

* Typed strategies.
* Registries.
* Composition.

Only where this improves extension without excessive boilerplate.

Keep real extension points clear for:

* Threshold policies.
* Datasets.
* Experiments.
* Metrics.
* Analyses.
* Sweep dimensions.

Do not add speculative abstractions.

## Boilerplate and structure

Remove:

* Abstract factories with no meaningful variation.
* Interfaces with one pointless implementation.
* Thin wrappers.
* Tiny files with no useful separation.
* Duplicate validators.
* Duplicate calculations.
* Repeated path logic.
* Repeated artifact parsing.
* Parallel pipeline implementations.
* Dead code.
* Unreachable branches.
* Unused exports.

Split oversized files only along defensible responsibility boundaries.

Merge tiny related files when separation adds no value.

## Orchestration

Dagster must remain the single canonical orchestration implementation.

Remove or consolidate:

* Parallel manual stage runners.
* Duplicate campaign engines.
* Diagnostic-only pipelines.
* Duplicate orchestration transitions.

## Dependencies

Enforce dependency direction.

Prevent circular imports.

Keep scientific domain logic independent from:

* CLI.
* Storage.
* Reporting.
* External orchestration adapters.

## Errors and availability

Use domain-specific exceptions.

Do not use generic `ValueError` for every failure.

Never silently skip invalid:

* Inputs.
* Clients.
* Policies.
* Artifacts.
* Metrics.

Never replace unavailable values with:

* Zero.
* Empty collections.
* Fabricated defaults.

Model these states explicitly:

* Available.
* Unavailable.
* Undefined.
* Invalid.
* Empty.

## State and determinism

Remove:

* Unnecessary mutable state.
* Global state.
* Hidden caches.
* Non-deterministic ordering.

Preserve deterministic:

* Seeds.
* Manifests.
* Ordering.
* Fingerprints.
* Provenance.
* Plans.
* Artifacts.

## Artifact safety

Artifact writes must be:

* Atomic.
* Deterministic.
* Validated.
* Safe under interruption.

Cleanup must never delete:

* Raw data.
* Symlink targets.
* Completed experiments.
* Unrelated outputs.

## Comments

Remove all pre-existing:

* Low-value comments.
* Inline narration.
* Historical notes.
* Migration notes.
* AI-style comments.
* Commented-out code.
* Stale TODOs.
* Comments that restate implementation.

Retain a comment only when it explains an indispensable external or scientific constraint that cannot be expressed through:

* Types.
* Naming.
* Validation.
* Structure.

Do not replace comments with bloated docstrings.

## No mass-edit scripts

Do not use:

* Large one-off Python rewrite scripts.
* Repository-wide regex replacements.
* Blind bulk search-and-replace.
* Generated sweeping patches.
* Mechanical transformations that bypass file understanding.

Make deliberate file-scoped edits.

Small read-only inventory or analysis scripts are allowed.

Small narrowly scoped transformations are allowed only when every resulting file is individually inspected and validated.

---

# 17. Adapt Corresponding Tests While Each File Is Active

Before changing the active production file:

* Locate all directly corresponding tests.
* Locate all indirectly corresponding tests.
* Use Graphify.
* Search imports.
* Search symbols.
* Inspect test discovery.
* Inspect fixtures and builders.

Update production implementation and corresponding tests as one file-level unit.

When production responsibilities move:

* Move tests.
* Rename tests.
* Reorganize fixtures.

Delete tests for removed compatibility behavior.

Add tests for newly explicit typed contracts and failure semantics.

Do not postpone all test adaptation until package completion.

A production file cannot be marked complete while corresponding tests are:

* Stale.
* Duplicated.
* Bloated.
* Skipped without justification.
* Weakly typed.
* Architecturally misplaced.
* Testing obsolete behavior.

---

# 18. Use Controlled Validation After Each File

For each active file, run only targeted validation.

Run:

* Relevant tests.
* Impacted test subset.
* Targeted Ruff.
* Targeted formatting.
* Targeted Pyright.
* Targeted Pylance-compatible validation.
* Targeted Pylint.
* Relevant import-linter contracts.
* Relevant architecture checks.
* Relevant experiment diagnostics when the file participates in an executable scientific path.

Do not run the complete repository suite after every file.

Fix all local failures before marking the file complete.

Then:

1. Perform the second technical checklist pass.
2. Perform the second scientific checklist pass.
3. Update the changelog.
4. Update the ledger.
5. Move to the next file.

---

# 19. Perform Scientific Tracing for Every Affected File

Determine which experiments and pipeline stages depend on the active file.

Trace its behavior through:

1. Dataset preparation.
2. Split manifest generation.
3. Training.
4. Checkpoint selection.
5. Score generation.
6. Calibration or subsampling.
7. Threshold construction.
8. Evaluation.
9. Statistical analysis.
10. Reporting.
11. Finalization.

Verify preservation of:

* Dataset identity.
* Client identity.
* Population identity.
* Seed identity.
* Sweep identity.
* Replicate identity.
* Partition identity.
* Policy identity.
* Artifact-generation identity.

Verify:

* No training leakage.
* No calibration leakage.
* No test leakage.
* No cross-client leakage.
* Frozen-model comparisons remain frozen where required.
* Threshold scope remains the sole variable where required.
* Checkpoint selection does not depend on evaluation outcomes.
* Metric denominators are correct.
* Metric availability is explicit.
* Statistical comparisons use compatible populations.
* Statistical comparisons use compatible seeds.
* Statistical comparisons use compatible policies.
* Statistical comparisons use compatible artifacts.
* Report fields derive from canonical artifacts.
* Claim boundaries remain respected.

Fix scientific drift immediately within the active file and affected contracts.

---

# 20. Complete Every File Before Completing the Package

Every production file must have:

* First technical checklist pass.
* First scientific checklist pass.
* Corresponding test adaptation.
* Targeted validation.
* Second technical checklist pass.
* Second scientific checklist pass.
* Graphify inspection.
* Changelog entry.
* Progress-ledger completion.

Every test file in the package must be reviewed, optimized, and debloated.

Reconcile all parallel test work.

Rerun Graphify for the package.

Review:

* Package responsibility.
* Public API.
* Coupling.
* Imports.
* File count.
* Architecture.
* Scientific boundaries.

---

# 21. Run the Full Suite Only After the Package Is Complete

Do not run the complete repository test suite during incomplete package work.

After every production and test file in the active package is complete, run:

* Repository-wide formatting validation.
* Ruff.
* Pyright.
* Strict Pylance-compatible validation.
* Pylint.
* import-linter.
* Architecture contracts.
* Complete pytest suite.
* pytest-xdist where safe and deterministic.
* Diagnostics for every experiment affected by the package.

Fix:

* Newly introduced failures.
* Pre-existing failures.
* Architecture failures.
* Typing failures.
* Test failures.
* Diagnostic failures.

Repeat until the completed package and full repository suite are green.

---

# 22. Perform Two Package-Level Checklist Passes

After assembling the package:

1. Run the complete technical and architectural checklist.
2. Run the complete scientific-integrity checklist.

After the full suite and diagnostics pass:

3. Perform a second independent technical and architectural package audit.
4. Perform a second independent scientific package audit.

Do not commit while any package checklist item remains unresolved.

---

# 23. Commit and Push After Every Completed Package

Create a package-scoped commit only after:

* Every production file is complete.
* Every corresponding test is complete.
* Test files are optimized.
* Both file-level checklist passes are complete.
* Both package-level checklist passes are complete.
* Graphify confirms the structure.
* The full suite passes.
* Diagnostics pass.

Push directly to `main`.

Record:

* Commit hash.
* Remote hash.
* Push status.
* Package name.
* Validation state.

Confirm the remote commit matches the locally validated state.

---

# 24. Run SonarCloud After Every Package Push

After every package push:

1. Confirm SonarCloud analyzes the exact pushed commit.
2. Retrieve:

   * Bugs.
   * Vulnerabilities.
   * Security hotspots.
   * Code smells.
   * Duplication blocks.
   * Maintainability findings.
   * Coverage conditions.
   * Quality Gate status.
3. Fix both:

   * Newly introduced findings.
   * Pre-existing findings affecting the package or repository architecture.
4. Rerun local validation.
5. Commit and push the fixes.
6. Inspect the matching SonarCloud analysis.
7. Repeat until acceptance conditions pass.

Do not:

* Suppress findings.
* Exclude files.
* Lower rules.
* Mark findings as false positives.
* Add explanatory comments instead of fixing code.
* Manipulate coverage requirements.

SonarCloud acceptance requires:

* Analysis commit exactly matches the pushed commit.
* Quality Gate passes.
* Zero open bugs.
* Zero open vulnerabilities.
* Zero unresolved security hotspots.
* Zero open code smells.
* Zero duplicated blocks.
* Every mandatory coverage condition passes.
* No suppression, exclusion, false-positive marking, or rule weakening was used.

Continue until all conditions are satisfied.

---

# 25. Run CodeScene Delta After Every Package Push

Record the correct baseline commit.

Run CodeScene Delta against the package’s final commit.

Inspect:

* Code health.
* Hotspots.
* Complexity.
* Temporal coupling.
* Change coupling.
* Knowledge concentration.
* Fragmented responsibilities.
* Architectural degradation.
* Test-code health.

Refactor new or worsened hotspots.

Rerun Graphify after CodeScene-driven changes.

Rerun tests and quality checks.

Commit and push fixes.

CodeScene Delta acceptance requires:

* No new hotspot.
* No worsened hotspot.
* No code-health regression in changed code.
* No architectural degradation.
* No increased temporal coupling.
* No increased change coupling.
* No test-code-health regression relative to the recorded baseline.

Repeat until every condition passes.

---

# 26. Close Each Package Through a Non-Stopping Loop

For each package, execute this loop:

1. Package graph and responsibility audit.
2. Select one production file.
3. Inspect its Graphify slice.
4. Perform file-scoped subagent audits where useful.
5. Perform first checklist passes.
6. Refactor the file.
7. Adapt corresponding tests.
8. Perform non-overlapping test cleanup in parallel where useful.
9. Run targeted validation.
10. Perform second checklist passes.
11. Add the changelog entry.
12. Update the ledger.
13. Select the next production file.
14. Repeat until every production file is processed.
15. Review and optimize every test file.
16. Rerun package Graphify analysis.
17. Perform first package-level checklist passes.
18. Run the full repository suite.
19. Run affected experiment diagnostics.
20. Perform second package-level checklist passes.
21. Commit.
22. Push.
23. Run the SonarCloud loop.
24. Run the CodeScene Delta loop.
25. Rerun final package validation.

Do not move to the next package while any known:

* Defect.
* Scientific drift.
* Failing test.
* Typing issue.
* Architecture failure.
* Stale test.
* SonarCloud issue.
* CodeScene regression.
* Incomplete checklist.
* Incomplete changelog entry.
* Incomplete ledger entry.

Remains.

If an external quota temporarily prevents SonarCloud or CodeScene completion, record the blocked gate, continue independent package work, and retry the blocked checks later. Do not falsely mark the package’s external gate as passed.

---

# 27. Perform a Second Complete Repository Pass

After all packages have been processed, revisit the entire repository package by package.

Within every package, revisit every production file individually.

Rerun Graphify across the final repository.

Reapply both checklists.

Reinspect all test files and shared test infrastructure.

Detect and fix:

* Cross-package duplication.
* Duplicate enums.
* Duplicate dataclasses.
* Parallel scientific representations.
* Remaining generic dictionaries.
* Dynamic scientific dispatch.
* Hidden defaults.
* Unused configuration.
* Excess package fragmentation.
* Giant files.
* Thin wrappers.
* Circular dependencies.
* Stale comments.
* Dead tests.
* Duplicate fixtures.
* Scientific drift introduced by later changes.
* Parallel orchestration paths.
* Non-Dagster campaign logic.
* Campaign-semantic violations.

Use the same file-by-file and package-completion loop.

Create new changelog entries for revisited files.

Do not assume earlier completion remains valid.

---

# 28. Run Final Experiment Diagnostics

Run every experiment individually using one configured seed.

Run the complete campaign using one configured seed per experiment.

Validate:

* Real configuration loading.
* Experiment resolution.
* Planning.
* Dataset materialization.
* Training.
* Checkpoint selection.
* Score generation.
* Calibration.
* Thresholding.
* Evaluation.
* Statistical analysis.
* Reporting.
* Finalization.
* Artifact contracts.
* Output isolation.
* Skip behavior.
* Override behavior.
* Interruption behavior.
* Cleanup behavior.
* Automatic resumption.
* Completion-marker behavior.
* Dagster orchestration.

Diagnostics must not contaminate official outputs.

---

# 29. Compare Reproducibility Explicitly

Do not merely assert determinism.

Run an identical single-experiment diagnostic twice using:

* The same configuration.
* The same experiment.
* The same seed.
* Separate clean diagnostic output roots.

Run the identical complete one-seed campaign diagnostic twice using:

* The same configuration.
* The same experiment ordering.
* The same seeds.
* Separate clean diagnostic output roots.

Compare the repeated runs for:

* Resolved plans.
* Stage ordering.
* Dataset identities.
* Population identities.
* Split identities.
* Seed identities.
* Policy identities.
* Sweep identities.
* Checkpoint-selection decisions.
* Manifests.
* Scientific fingerprints.
* Threshold values.
* Metric values.
* Statistical input identities.
* Artifact inventories.
* Scientific artifact contents.
* Completion state.

Ignore only explicitly non-scientific runtime metadata such as:

* Timestamps.
* Process IDs.
* Temporary directory names.
* Isolated host-specific runtime details.

Any unexplained difference is a reproducibility failure.

Fix the cause and repeat both runs until the comparison is clean.

---

# 30. Perform Bounded Real-Execution Validation

Launch every experiment through the real production path for approximately 5–10 minutes.

Do not modify:

* Batch size.
* Model size.
* Scientific values.
* Seeds.
* Pipeline stages.
* Dataset definitions.
* Runtime semantics.

Merely to make execution pass.

For every experiment, validate:

* GPU use.
* Batching.
* Data loading.
* Determinism.
* Memory stability.
* Checkpoint writing.
* Artifact creation.
* Stage transitions.
* Error handling.
* Cleanup.
* Interruption.
* Resumption.

Fix every runtime failure.

Repeat the affected experiment.

Delete diagnostic and partial bounded-run outputs after validation.

Do not touch:

* Raw data.
* Symlink targets.
* Official completed results.
* Unrelated outputs.

A bounded run validates operational startup and runtime behavior. Do not falsely claim it proves completion of later stages when the experiment did not reach them within the bounded interval.

---

# 31. Run the Final Acceptance Loop

Continue the final acceptance loop until the only honest verdict is `GO FOR EXPERIMENTS`.

Repeat:

1. Recheck every required local tool.
2. Retry every previously blocked external tool.
3. Rerun Graphify across the final repository.
4. Rerun formatting.
5. Rerun Ruff.
6. Rerun Pyright.
7. Rerun strict Pylance-compatible validation.
8. Rerun Pylint.
9. Rerun import-linter.
10. Rerun architecture contracts.
11. Rerun the complete pytest suite.
12. Rerun all experiment diagnostics.
13. Rerun campaign diagnostics.
14. Rerun reproducibility comparisons.
15. Recheck technical checklists.
16. Recheck scientific checklists.
17. Recheck every changelog entry.
18. Recheck every ledger entry.
19. Recheck every production package.
20. Recheck every production file.
21. Recheck every test file.
22. Recheck:

    * Dictionaries.
    * Enums.
    * Dataclasses.
    * Configuration use.
    * Hardcoded values.
    * Hidden defaults.
    * Comments.
    * Naming.
    * Typing.
    * Artifacts.
    * Dependency direction.
    * Dagster orchestration.
    * Campaign semantics.
23. Push the final validated state.
24. Confirm SonarCloud analyzes the exact final commit.
25. Resolve every remaining SonarCloud finding.
26. Run CodeScene Delta against the exact final commit.
27. Resolve every remaining CodeScene regression.
28. Repeat the complete final loop after every change.

Do not stop because:

* Tests pass once.
* One audit is clean.
* Architecture appears improved.
* Most files are complete.
* A tool has not yet retried after quota recovery.
* Diagnostics only start successfully.
* The campaign works only in the happy path.
* Repeated runs have not been compared.

Stop only when:

* Repeated execution is idempotent.
* Every production package has been processed.
* Every production file has been independently processed.
* Every test file has been optimized and debloated.
* Both checklist passes remain clean.
* Graphify confirms coherent architecture.
* Dagster is the sole canonical orchestrator.
* Campaign semantics match the locked contract.
* Full diagnostics pass.
* Reproducibility comparisons pass.
* Bounded executions expose no unresolved runtime error.
* SonarCloud acceptance conditions pass on the exact final commit.
* CodeScene Delta acceptance conditions pass on the exact final commit.
* No known technical risk remains.
* No known scientific drift remains.
* No known architectural defect remains.
* No known test defect remains.
* No required gate remains blocked or unverified.

Only then report:

```text
GO FOR EXPERIMENTS
```

Otherwise report:

```text
NO-GO
```

And explicitly list every unresolved blocker without weakening or hiding it.

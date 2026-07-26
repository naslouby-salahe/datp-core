# DATP-Core — Strict Continuation, Parallel Remediation, and Experiment-Readiness Prompt

Resume work from the repository’s **current state**.

Do not restart blindly, revert completed improvements, recreate already completed work, or assume the previous attempt was correct. Inspect the live repository, existing `.tmp/` records, current configuration, tests, documentation, and working tree. Reconstruct the actual remaining state from evidence.

This task is idempotent. Continue auditing, fixing, reviewing, and validating until the repository truthfully reaches:

```text
GO FOR EXPERIMENTS
```

Do not stop after planning, auditing, refactoring one package, passing a partial test set, starting one experiment, or reporting remaining work.

You are the primary orchestrator. You must actively coordinate Claude Code subagents and Codex agents, use genuine parallel execution, review their work, resolve disagreements, and continue until no actionable blocker or unresolved implementation risk remains.

---

# 1. Hard execution requirements

The following requirements are mandatory.

Failure to satisfy any of them blocks the final verdict.

## 1.1 Codex usage is mandatory

Codex must be used during this continuation.

At the beginning, verify the actual installation:

```bash
command -v codex
codex --version
codex --help
```

Use the discovered CLI behavior. Do not guess unsupported Codex flags or invocation syntax.

Codex must perform real repository work, not merely answer a trivial question.

At minimum, use Codex for all of the following independent assignments:

1. scientific implementation and drift audit;
2. architecture, duplication, complexity, and dead-code audit;
3. tests, typing, configuration usage, and quality audit;
4. final independent readiness review after implementation.

At least one Codex assignment must inspect the complete affected source paths, not only a copied summary.

At least one Codex assignment must review changes authored by Claude agents.

At least one Claude agent must independently review findings or changes produced by Codex.

Codex findings must be incorporated into the central issue ledger and resolved or explicitly disproven with code-level evidence.

Do not invoke Codex only to satisfy the wording of this prompt.

Do not silently skip Codex.

If Codex invocation initially fails:

* record the exact command and error;
* diagnose and correct invocation or environment issues;
* continue all other independent work in parallel;
* retry Codex after the correction;
* do not declare `GO FOR EXPERIMENTS` until successful Codex audit evidence exists.

Codex usage evidence must appear in the final report.

## 1.2 Genuine parallel subagents are mandatory

Use multiple subagents concurrently.

“Parallel” means independent agents running at the same time on non-overlapping investigation or implementation assignments. Sequentially calling several agents does not satisfy this requirement.

For every major work wave, launch at least four concurrent subagents where the environment supports it.

Each major wave must include:

* at least one Codex agent;
* at least two Claude Code subagents;
* at least one independent reviewer not responsible for the implementation under review.

Use at least three parallel waves:

### Wave 1 — Discovery

Run independent parallel audits of:

* scientific conformance;
* configuration-to-execution traceability;
* architecture and code quality;
* pipeline, artifact, and resumption behavior;
* tests and quality tooling;
* B4 fingerprint, thresholds, metrics, and statistics.

### Wave 2 — Implementation

Assign non-overlapping coherent remediation packages in parallel.

Examples:

* threshold and policy extensibility;
* configuration and typed domain contracts;
* pipeline and artifact handling;
* test-suite cleanup;
* tooling and documentation;
* package structure and duplication.

Never let two agents edit the same file concurrently.

The orchestrator must define file ownership before parallel edits begin.

### Wave 3 — Independent review

After implementation, use new agents that did not author the changes to review:

* scientific correctness;
* architecture;
* configuration coverage;
* tests and quality;
* pipeline behavior;
* experiment readiness.

A review cannot be performed only by the agent that implemented the code.

## 1.3 Maintain an agent activity ledger

Under:

```text
.tmp/datp-core-readiness/
```

maintain:

```text
agent_activity.md
```

For every agent invocation, record:

* tool: Claude or Codex;
* role;
* exact assignment;
* start status;
* files or packages inspected;
* files permitted for modification;
* findings;
* implementation performed;
* validation evidence;
* reviewer;
* disposition of every finding.

The final verdict is blocked unless the ledger proves that Codex and multiple concurrent agents were genuinely used.

Do not add this ledger to the permanent repository.

---

# 2. Source of truth

Read the complete current versions of:

```text
docs/roadmap/SCIENTIFIC_SOURCE_OF_TRUTH.md
docs/roadmap/00_ROADMAP_INDEX.md
docs/roadmap/01_SCIENTIFIC_IDENTITY_AND_SCOPE.md
docs/roadmap/02_CLAIMS_AND_DECISION_RULES.md
docs/roadmap/03_EXPERIMENT_CATALOGUE.md
docs/roadmap/04_EVALUATION_AND_REPORTING_PROTOCOL.md
docs/roadmap/05_IMPLEMENTATION_ROADMAP.md
docs/roadmap/06_REVIEWER_RISKS_AND_READINESS.md
docs/roadmap/07_AUDIT_AND_DECISION_LOG.md
```

Use the following precedence:

1. `SCIENTIFIC_SOURCE_OF_TRUTH.md`;
2. scientific identity and scope;
3. claims and decision rules;
4. experiment catalogue;
5. evaluation and reporting protocol;
6. implementation roadmap;
7. reviewer readiness and audit log.

Do not modify `SCIENTIFIC_SOURCE_OF_TRUTH.md`.

Do not weaken scientific requirements to preserve current code.

Do not use git history, blame, previous commits, old branches, deleted files, or earlier repository structures to decide what the implementation should be.

Do not create compatibility with historical code.

The current source of truth and current live repository are authoritative.

---

# 3. Resume safely

Before making changes:

1. inspect the current working tree;
2. inspect existing `.tmp/` work records;
3. identify work already completed correctly;
4. identify incomplete, incorrect, duplicated, or abandoned partial work;
5. validate current architecture instead of trusting previous summaries;
6. update the issue ledger;
7. assign remaining work to parallel agents.

Do not reset the repository.

Do not discard valid current work.

Do not preserve partial work merely because it already exists.

Remove unfinished abstractions, temporary compatibility code, dead intermediate architecture, stale tests, and abandoned refactor remnants.

Do not create a branch or worktree.

Do not commit or push unless separately requested.

---

# 4. Temporary control files

Use:

```text
.tmp/datp-core-readiness/
```

Maintain:

```text
plan.md
issue_ledger.md
agent_activity.md
scientific_traceability.md
configuration_usage.md
architecture_inventory.md
pipeline_matrix.md
experiment_matrix.md
quality_status.md
review_status.md
```

Every issue must include:

* identifier;
* category;
* severity;
* evidence;
* affected files;
* scientific or technical consequence;
* assigned agent;
* planned correction;
* implementation status;
* targeted validation;
* independent review;
* closure evidence.

Do not close an issue because code was changed.

Close it only after:

* the root cause was removed;
* relevant tests were added or corrected;
* targeted validation passed;
* an independent reviewer accepted the correction.

Remove `.tmp/datp-core-readiness/` at final completion.

---

# 5. Absolute zero-comment rule

Do not add explanatory inline comments to production code, tests, configuration, Nox, Makefile recipes, or scripts.

This includes:

```python
# explain what this does
value = compute()  # explanation
```

It also includes:

* audit comments;
* migration comments;
* historical comments;
* “temporary” comments;
* AI narration;
* comments explaining obvious code;
* comments describing a previous implementation;
* comments saying why a refactor happened;
* commented-out code;
* TODO, FIXME, HACK, NOTE, or WORKAROUND markers;
* prose comments used instead of clear naming;
* code-region banners;
* step-number comments;
* comments that restate the following line.

No agent may add comments merely because a section is scientifically complex.

Scientific meaning must be expressed through:

* precise names;
* enums;
* typed value objects;
* validated configuration;
* small functions;
* explicit formulas;
* tests;
* permanent scientific documentation outside implementation code.

Concise public API docstrings may remain only where required to explain a public contract. Do not add narration-style docstrings to private functions or obvious classes.

Retain only unavoidable legal headers or narrowly required tool pragmas. Do not introduce a pragma to silence a quality problem.

Before accepting every implementation batch, inspect all added lines for comments.

Create a read-only validation under `.tmp/` that detects newly added code comments. It must fail the batch when an agent adds an ordinary `#` comment or commented-out code.

The final diff must contain no new explanatory inline code comments.

Also audit existing code comments. Remove existing comments that are:

* weird;
* obsolete;
* historical;
* obvious;
* noisy;
* audit-related;
* compensation for unclear code.

Rewrite the code clearly instead.

Any newly added forbidden comment blocks final completion.

---

# 6. Strategic execution

Do not run the complete test suite or every expensive quality tool immediately.

First:

* understand the current architecture;
* read the source of truth;
* inventory configuration;
* trace scientific values;
* trace experiment pipelines;
* inspect existing partial refactors;
* identify root causes;
* create a coherent plan.

Use targeted validation while major architecture work is in progress.

Run broad tests and static gates after coherent architecture batches are integrated.

Do not repeatedly run the complete suite after every small edit.

Do not make unrelated micro-edits across the repository.

Perform cohesive batches, then review and validate them.

Do not use giant scripts or broad regex replacements to rewrite the codebase.

---

# 7. Required scientific audit

Build a bidirectional traceability map.

For every locked scientific requirement:

```text
source-of-truth rule
→ validated configuration
→ resolved typed value
→ execution consumer
→ artifact field
→ metric or analysis
→ invariant test
```

For every result-affecting execution value:

```text
executed value
→ configuration field or explicit source-of-truth rule
```

Fix every break in either direction.

Audit at minimum:

* fixed detector across B1–B4;
* identical score artifacts across B1–B4;
* benign-only calibration;
* calibration/test separation;
* client eligibility;
* eligible-population equality;
* attack-evaluable versus FPR-evaluable populations;
* B1 arithmetic mean of eligible local quantiles;
* B2 local quantile semantics;
* B3 family constraints;
* B4 exact fingerprint and clustering semantics;
* quantile interpolation;
* metric formulas;
* `ddof` values;
* checkpoint selection;
* seed domains;
* BCa analysis;
* target attainment;
* external metric unavailability;
* temporal leakage protection;
* stress-test separation;
* output and result provenance.

Do not accept configuration that is loaded but unused.

Do not accept implementation values that bypass configuration.

Do not accept configuration fields that only alter a manifest or fingerprint while behavior remains hardcoded.

---

# 8. B4 and fingerprint correction

Perform a dedicated independent B4 audit using both Claude and Codex.

Canonical B4 must enforce exactly:

* fingerprint features:

  * mean reconstruction error;
  * standard deviation with `ddof = 1`;
  * uncorrected Fisher–Pearson moment skewness;
  * linearly interpolated p95;
* fewer than two scores:

  * standard deviation `0.0`;
  * skewness `0.0`;
* non-finite skew:

  * replace with `0.0`;
* other non-finite fingerprint values:

  * typed failure;
* current eligible clients only;
* ascending client identifier order before fitting;
* standardization:

  * mean `0`;
  * variance convention `ddof = 0`;
  * unit scale;
  * constant dimensions scale to `1`;
* k-means:

  * `K = 3`;
  * k-means++;
  * Lloyd;
  * 10 initializations;
  * 300 iterations;
  * tolerance `1e-4`;
  * configured canonical clustering seed;
* fewer clients than K:

  * typed unavailability;
* fewer than two distinct fingerprints:

  * typed unavailability;
* cluster threshold:

  * arithmetic mean of member local thresholds;
* canonical labels:

  * ascending cluster threshold;
  * smallest member identifier as tie-break;
* complete cluster diagnostics;
* alternative K values isolated as exploratory artifacts.

Persist pre-aggregation local thresholds so within-cluster local-threshold dispersion is meaningful.

Do not compute “within-cluster threshold dispersion” from final shared cluster thresholds and present the resulting zero as scientific evidence.

Use distinct typed terminology for:

* scientific/configuration fingerprints;
* execution fingerprints;
* source fingerprints;
* artifact checksums;
* B4 client-distribution fingerprints.

Do not use one generic `fingerprint` structure for unrelated concepts.

---

# 9. Technical remediation

Audit and correct all of the following.

## 9.1 Architecture

* random file names;
* vague package names;
* excessive package depth;
* one-file packages;
* giant modules;
* giant stage handlers;
* cyclic imports;
* mixed responsibilities;
* duplicated orchestration;
* unnecessary wrappers;
* compatibility modules;
* re-export modules;
* redirect modules;
* dead abstractions;
* premature plugin frameworks;
* excessive factories and managers.

Merge cohesive tiny modules.

Split only genuinely unrelated responsibilities.

Do not optimize for file count alone.

## 9.2 Dataclasses and models

Inventory:

* dataclasses;
* attrs records;
* Pydantic models;
* named tuples;
* result wrappers;
* configuration records.

Merge duplicate records representing the same concept.

Remove one-field and pass-through wrappers without invariants.

Avoid authored/resolved/domain copies when no real transformation exists.

Use:

* Pydantic v2 for external validation and discriminated configuration;
* one consistent immutable slotted record mechanism for internal domain data;
* explicit artifact schemas at persistence boundaries.

Do not mix record frameworks arbitrarily.

## 9.3 Dictionary removal

Remove raw dictionaries from:

* domain models;
* stage inputs;
* stage outputs;
* artifact contracts;
* result contracts;
* threshold results;
* configuration overrides;
* test fixture APIs.

Replace them with typed records, enums, value objects, discriminated unions, and typed collections.

A private dictionary is acceptable only when mapping behavior is intrinsic and it does not cross a boundary.

Remove JSON-like bags, `Any`, dynamic `.get()` chains, broad `Mapping[str, object]`, `JsonValue` domain structures, and `getattr()`-based dispatch.

## 9.4 Enum usage

Use enums for closed vocabularies:

* policies;
* stages;
* statuses;
* evidence roles;
* regimes;
* split roles;
* metric statuses;
* failure reasons;
* artifact types;
* estimator types;
* runtime profiles;
* checkpoint selectors.

Remove duplicate enums and raw string aliases.

Do not create pointless enums for unrestricted values.

## 9.5 Hardcoded values

Find and remove:

* scientific number literals;
* protocol values;
* seed literals;
* path literals;
* threshold grids;
* checkpoint rounds;
* eligibility values;
* cluster settings;
* statistical settings;
* runtime defaults;
* hidden fallback values.

All result-affecting values must originate from validated configuration or an explicitly centralized source-of-truth representation.

Do not add defaults for required scientific fields.

Do not use `.get(..., default)`, optional constructor defaults, `or fallback`, or `getattr(..., default)` to hide missing scientific configuration.

## 9.6 Naming

Rename unclear:

* variables;
* classes;
* modules;
* fixtures;
* tests;
* functions;
* stages;
* artifacts.

Names must reveal domain meaning, scope, population, unit, and lifecycle.

Avoid generic names such as:

```text
data
info
item
value
result2
manager
processor
handler_impl
helper
utils
misc
common
temp
```

Use standard scientific abbreviations consistently where appropriate.

## 9.7 Duplication

Detect exact and semantic duplication.

Remove:

* duplicate seed derivation;
* repeated metric formulas;
* repeated path building;
* repeated policy dispatch;
* duplicate validators;
* duplicate result conversion;
* repeated orchestration;
* repeated fixture assembly;
* copy-pasted statistical logic.

Do not merge scientifically different procedures merely because their code resembles each other.

## 9.8 Complexity

Reduce:

* deep nesting;
* broad conditional dispatch;
* long argument lists;
* mutable global state;
* dynamic type inspection;
* broad exception handling;
* hidden I/O;
* stage responsibilities mixed with formulas.

Prefer small typed functions, composition, early validation, and pure calculations.

---

# 10. Threshold-policy extensibility

Refactor threshold construction so adding a supported policy does not require modifying unrelated pipeline stages.

Use a clear typed strategy architecture with:

* policy kind enum;
* discriminated configuration per policy family;
* common threshold-estimator protocol;
* one implementation per scientific estimator;
* typed request;
* typed result;
* explicit registry;
* centralized validation;
* thin orchestration dispatch.

Adding a new threshold policy must require only:

1. its typed identity;
2. its configuration;
3. its implementation;
4. registry entry;
5. focused tests.

It must not require editing:

* training;
* score generation;
* general evaluation;
* unrelated analyses;
* several giant `if/elif` blocks;
* report path reconstruction.

Add a contract test proving this extension behavior.

Do not create an oversized generic framework.

---

# 11. Pipeline and artifact correctness

Trace every configured experiment through:

```text
preflight
→ source validation
→ client assignment
→ split construction
→ preprocessing
→ training
→ checkpoint selection
→ score generation
→ calibration subsampling
→ threshold construction
→ evaluation
→ statistical analysis
→ reporting
→ finalization
```

Every stage must have:

* typed inputs;
* typed outputs;
* direct declared dependencies;
* one responsibility;
* explicit terminal status;
* deterministic paths;
* atomic writes;
* independently testable behavior.

No stage may discover ambiguous “latest” artifacts.

No analysis may recreate upstream paths manually.

No downstream stage may silently recompute upstream scientific logic.

Campaign execution must:

* use one command for initial execution and resumption;
* validate complete experiments before skipping;
* identify the first incomplete or incompatible experiment;
* delete only that experiment’s incomplete output;
* restart it from preflight;
* preserve completed validated experiments;
* require explicit override before deleting completed outputs.

---

# 12. Data symlink and paths

The data directory is a symlink.

Before cleanup, record:

* symlink path;
* resolved target;
* expected repository behavior.

Never:

* replace it;
* dereference it during cleanup;
* move its target;
* delete through it;
* copy external data into the repository;
* run recursive cleanup following symlinks.

Use `pathlib.Path`.

Centralize semantic paths through typed path configuration and path builders.

Do not hardcode:

* repository root;
* home directory;
* dataset paths;
* output paths;
* result paths;
* user-specific paths.

---

# 13. Outputs and results

Maintain separate concepts.

## `outputs/`

Machine-oriented experiment artifacts:

* checkpoints;
* scores;
* thresholds;
* metrics;
* stage manifests;
* execution logs;
* smoke artifacts.

## `results/`

Paper-facing frozen derivatives:

```text
results/tables/
results/figures/
results/statistics/
results/manifests/
```

Do not place smoke results in `results/`.

Do not manually copy values into paper tables or plots.

Reports must trace to frozen manifests.

At task completion:

* verify no paper result depends on smoke output;
* verify `outputs/` is not a symlink;
* safely delete task-generated `outputs/`;
* preserve `results/`;
* remove smoke files accidentally placed in `results/`;
* preserve the data symlink.

---

# 14. Test-suite cleanup

Audit all tests.

Delete or replace tests that exist only for:

* old architecture;
* old compatibility behavior;
* previous audits;
* deleted wrappers;
* migration steps;
* private implementation details;
* historical bug labels.

Use behavior-focused names.

Organize tests by:

* scientific formulas;
* domain behavior;
* stage contracts;
* pipeline integration;
* scientific invariants;
* end-to-end synthetic execution;
* real-data smoke readiness.

Tests must not:

* duplicate production formulas as expected values;
* rely on execution order;
* use sleeps;
* use real output folders as fixtures;
* depend on git history;
* overmock;
* weaken scientific assertions;
* hide failures with skips or expected failures.

Use hand-computed cases for formulas.

Use property-based testing where valuable.

Add regression coverage for every corrected scientific or architectural root cause.

CUDA tests must check runtime capability appropriately. CI without CUDA must not fail merely because CUDA is absent, but a GPU-required scientific runtime must still reject execution clearly.

---

# 15. Nox, Makefile, README, and CI

Use Nox as the primary source of quality commands.

Required sessions:

```text
format
lint
typecheck
pylint
contracts
scientific-invariants
tests-targeted
tests-full
smoke-synthetic
smoke-experiments
sonar
quality
```

Keep the Makefile thin and delegate to Nox.

Required Make targets should include:

```text
help
install
format
lint
typecheck
pylint
test
test-full
contracts
scientific-audit
smoke
sonar
quality
clean
```

Cleanup must preserve the data symlink and `results/`.

README must accurately explain:

* scientific identity;
* setup;
* authoritative configuration;
* data symlink;
* execution;
* campaign resumption;
* outputs versus results;
* quality commands;
* GPU requirements;
* adding a threshold policy;
* smoke limitations.

Do not add strange Markdown reports to the repository.

CI must invoke the same Nox sessions.

Do not duplicate long command sequences in CI, README, Makefile, and Nox.

---

# 16. Quality gates

After major architecture work is integrated, run and repair:

* formatting;
* Ruff;
* strict Pyright;
* Pylance-compatible configuration;
* Pylint;
* import-boundary checks;
* duplication detection;
* dead-code detection;
* targeted tests;
* contract tests;
* scientific invariant tests;
* full tests;
* SonarCloud.

Use the configured Sonar project.

Fix all applicable Sonar findings and duplication.

Do not label issues false positives merely to close them.

Do not add broad suppressions, exclusions, ignores, or warning filters.

Any suppression requires a narrow unavoidable reason and independent review.

Do not claim Sonar passed without an analysis corresponding to the current code.

---

# 17. Experiment smoke validation

Only after architecture, tests, and static gates stabilize:

1. run a complete synthetic end-to-end pipeline;
2. validate every experiment family’s complete stage plan;
3. run each executable mandatory experiment against real data for approximately 5–10 minutes using a typed smoke runtime profile.

The smoke profile must:

* remain separate from scientific configuration;
* not change canonical scientific values;
* not reduce configured scientific batch size;
* not overwrite production configs;
* mark all artifacts as smoke;
* never produce paper results;
* terminate cleanly;
* exercise the real configuration and pipeline path.

For each smoke execution verify:

* configuration resolution;
* preflight;
* data symlink safety;
* client assignment;
* split handling;
* GPU handling;
* training startup;
* atomic artifacts;
* cancellation;
* completion markers;
* restart/resumption behavior;
* no pollution of `results/`.

A smoke run is not a completed experiment.

If a smoke run fails unexpectedly:

* identify the root cause;
* fix it;
* add a regression test;
* rerun targeted gates;
* rerun the smoke;
* review affected experiments;
* continue until no unexpected failure remains.

Scientifically expected infeasibility is acceptable only when represented with the exact typed status and reason required by the source of truth.

---

# 18. Mandatory review loop

After each major implementation wave:

1. authoring agents report changes;
2. orchestrator reviews source and diff;
3. comment detector checks newly added comments;
4. independent Claude reviewer audits the batch;
5. independent Codex reviewer audits the batch;
6. findings enter the ledger;
7. all valid findings are fixed;
8. targeted validation reruns;
9. batch is closed only after review acceptance.

At final state, run independent audits for:

* scientific conformance;
* B4 and statistical correctness;
* configuration usage;
* architecture and clean code;
* dictionary and enum discipline;
* pipeline and provenance;
* tests and quality;
* experiment readiness.

Use agents that did not implement the reviewed area.

Continue until every final audit returns no actionable issue.

---

# 19. Forbidden stopping conditions

Do not stop because:

* one agent says the repository is clean;
* tests pass;
* Pyright passes;
* Sonar passes;
* a smoke experiment starts;
* the previous agent already modified many files;
* the remaining findings appear minor;
* the task is large;
* work has taken many iterations;
* only architecture cleanup remains;
* only naming or comments remain;
* only documentation remains;
* only experiment smoke coverage remains.

Continue until every mandatory gate passes.

Do not replace implementation work with recommendations.

Do not leave fixable risks for a later pass.

Do not end with:

```text
mostly ready
partially complete
ready except
good enough
no major blockers
```

---

# 20. Final gate

The verdict may be:

```text
GO FOR EXPERIMENTS
```

only when all of the following are proven:

* Codex was successfully used for meaningful audits and review;
* multiple subagents were run genuinely in parallel;
* independent Claude and Codex reviews were completed;
* the agent activity ledger proves this;
* no forbidden inline comment was added;
* obsolete existing comments were cleaned;
* no scientific drift remains;
* all configuration values are consumed or removed;
* no hidden scientific defaults remain;
* B4 matches the exact scientific contract;
* threshold policies are cleanly extensible;
* dictionaries do not cross domain or stage boundaries;
* closed vocabularies use canonical enums;
* hardcoded scientific and path values are removed;
* dataclasses and records are consolidated;
* duplicate and dead code are removed;
* architecture is clear and navigable;
* pipeline stages have typed contracts;
* output and result handling is correct;
* data symlink is preserved;
* tests are clean and behavior-focused;
* Nox, Makefile, README, and CI are aligned;
* formatting, Ruff, Pyright, Pylint, import checks, duplication, dead-code checks, tests, and Sonar pass;
* synthetic end-to-end execution passes;
* every executable mandatory experiment has successful real-data smoke evidence;
* every experiment family has complete contract coverage;
* all unexpected experiment failures are fixed;
* task-generated `outputs/` is safely deleted;
* `results/` contains no smoke artifacts;
* every issue in the ledger is closed with evidence;
* final independent reviews find no actionable blocker.

Any failed item means the work continues.

---

# 21. Final response

Only after all gates pass, provide:

```text
GO FOR EXPERIMENTS
```

Then report concisely:

1. Claude and Codex agents used;
2. parallel execution waves completed;
3. major scientific corrections;
4. B4 and fingerprint corrections;
5. architecture and type-system corrections;
6. dictionary, enum, hardcoded-value, naming, and comment remediation;
7. pipeline and provenance corrections;
8. test-suite cleanup;
9. Nox, Makefile, README, and CI status;
10. exact quality commands and outcomes;
11. Sonar analysis status;
12. experiment smoke matrix;
13. outputs cleanup;
14. results preservation;
15. data symlink preservation;
16. accepted scientific limitations remaining by design.

Provide evidence rather than assurances.

Resume now from the live repository state. Start by validating Codex, launching the first genuinely parallel audit wave, and updating the temporary ledgers. Do not stop until the final verdict is truthful.

# AI Catalogue — DATP Journal Extension

This catalogue defines the shared AI operating rules for the DATP journal-extension repository.

The repository must stay small, explicit, typed, clean, and scientifically disciplined.

The project scope is the DATP journal extension only. The core identity is a fixed-encoder, fixed-federated-model, threshold-calibration-scope study where B1–B4 vary threshold scope while preserving the same trained model and score artifacts. Stress tests, comparators, external validation, threshold variants, and mechanism analyses support the journal extension but do not replace the core causal ladder.

Poisoning, Dynamic DATP, privacy guarantees, deployment profiling, backdoor, evasion, full drift detection, generic FL-IDS expansion, and unrelated thesis work remain out of scope unless explicitly requested as future-work wording.

The default engineering mode is greenfield-clean. There is no backward-compatibility mode unless explicitly requested in the task contract.

---

## 1. Global Operating Principles

| Principle                              | Rule                                                                                                                                                                              |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Scope first                            | Every task starts by defining what may change and what must not change.                                                                                                           |
| No backward compatibility by default   | Do not preserve old APIs, old names, old paths, old configs, aliases, redirects, shims, wrappers, or compatibility behavior unless the task contract explicitly requires it.      |
| Clean break over compatibility clutter | When a concept is renamed or redesigned, update the code, tests, docs, configs, outputs, and references directly. Do not keep old names alive.                                    |
| No shims                               | Redirect modules, alias classes, compatibility adapters, compatibility configs, and fake migration wrappers are forbidden.                                                        |
| No fake stability                      | Do not keep broken or stale interfaces just so old commands appear to work.                                                                                                       |
| Science is protected                   | No agent may change threshold semantics, metric meaning, seed meaning, dataset role, claim strength, or stress-test status without an explicit protocol-impact note and approval. |
| Structure is quality                   | A task is not done if the code works but leaves ugly folders, duplicate modules, random files, stale docs, or unclear ownership.                                                  |
| Clean code blockers are real blockers  | Stale comments, weak typing, weird names, raw protocol dictionaries, hidden defaults, compatibility clutter, and useless tests must be fixed in touched scope.                    |
| Tests are targeted                     | Run impacted tests after code changes. Run broad tests only when shared behavior changed or the contract requires it.                                                             |
| Final reports are uniform              | Every agent must report changed files, checks run, cleanup result, remaining risks, and skipped checks.                                                                           |

---

## 2. Agents

| Agent                        | Purpose                                                                                                                                                                               |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `roadmap_orchestrator`       | Coordinates work, splits tasks into safe phases, prevents scope creep, selects the workflow, and decides which gates must pass before completion.                                     |
| `datp_protocol_guardian`     | Protects DATP journal identity: fixed encoder, fixed federated model, threshold-scope-only B1–B4 ladder, benign-only calibration, AUROC as control only, and no generic FL-IDS drift. |
| `architecture_cleaner`       | Enforces clean structure, direct modules, clear ownership, no redirects, no shims, no fake compatibility, and no wrapper classes without real behavior.                               |
| `compatibility_blocker`      | Blocks backward-compatibility clutter, alias APIs, legacy names, transitional wrappers, compatibility configs, redirects, and migration scaffolding unless explicitly approved.       |
| `naming_auditor`             | Blocks weird, vague, stale, misleading, abbreviated, overloaded, or over-engineered names in files, modules, classes, functions, variables, configs, experiments, and outputs.        |
| `threshold_policy_engineer`  | Owns threshold-policy semantics: B0, B1, B2, B3, B4, `B-FedStatsBenign`, `τ-shrink`, calibration fallback, and `B2-conf`.                                                             |
| `implementation_engineer`    | Implements clean code with explicit typing, clear variables, minimal boilerplate, no hidden defaults, no raw dict-heavy protocol design, and no compatibility clutter.                |
| `experiment_engineer`        | Builds and validates configs, runners, seed logic, artifact naming, output layout, provenance, and experiment readiness.                                                              |
| `statistics_auditor`         | Audits metrics, seed pairing, CV(FPR), IQR, max-min FPR, P10 Macro-F1, BCa CI, Wilcoxon, Cliff’s δ, q-sensitivity, and statistical interpretation.                                    |
| `claim_evidence_auditor`     | Ensures every claim maps to evidence and is correctly classified as confirmatory, supportive, mechanism, stress test, boundary condition, exploratory, or future work.                |
| `literature_novelty_auditor` | Checks novelty and overlap against related thresholding, federated-threshold, personalization, conformal, and quantile-estimation literature.                                         |
| `reviewer2_red_team`         | Attacks the work like a harsh reviewer: B2 tautology, only 9 devices, Laridi overlap, model-personalization absorption, weak external validation, and overclaiming.                   |
| `manuscript_editor`          | Cleans Markdown/LaTeX/README prose, removes hype, stale wording, AI-generated language, unsupported claims, and bloated explanations.                                                 |
| `reproducibility_auditor`    | Checks configs, outputs, manifests, README, Makefile, result traceability, stale files, untracked junk, and rerun clarity.                                                            |
| `graphify_assistant`         | Converts dense workflows, dependency logic, experiment matrices, and claim hierarchies into Mermaid/Graphviz diagrams only when they reduce text and improve clarity.                 |

---

## 3. Skills

| Skill                                   | Purpose                                                                                                                                                               |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `datp_journal_scope_guard`              | Blocks work outside DATP journal scope.                                                                                                                               |
| `threshold_policy_semantics`            | Defines the locked meaning of B0, B1, B2, B3, B4, `B-FedStatsBenign`, `τ-shrink`, calibration fallback, and `B2-conf`.                                                |
| `confirmatory_claim_guard`              | Enforces the sole confirmatory endpoint: Regime A, B1 vs B2, CV(FPR), 10 paired seeds, BCa CI, positive delta excluding zero.                                         |
| `stress_test_boundary_check`            | Ensures FedProx, model personalization, and other stress tests stay outside the core B1–B4 causal ladder.                                                             |
| `experiment_readiness_check`            | Verifies dataset role, client definition, seed list, config completeness, output paths, expected metrics, and artifact provenance before experiments.                 |
| `statistical_validity_check`            | Validates paired seed design, metric direction, BCa CI, Wilcoxon, Cliff’s δ, sign consistency, q-sensitivity, and fallback wording.                                   |
| `claim_evidence_map`                    | Maps each claim to a table, figure, result artifact, config, protocol rule, or literature source.                                                                     |
| `literature_overlap_check`              | Checks novelty risk and citation honesty against related federated-threshold, thresholding, personalization, conformal, and quantile work.                            |
| `reviewer_attack_check`                 | Produces reviewer objections, severity, missing evidence, already-handled status, exact fix, and safe manuscript wording.                                             |
| `naming_clarity_check`                  | Blocks unclear, weird, abbreviated, overloaded, stale, or misleading names. Requires direct, readable names.                                                          |
| `no_backward_compatibility_check`       | Blocks compatibility aliases, legacy paths, deprecated APIs, redirect modules, compatibility config keys, old output names, old CLI flags, and transitional wrappers. |
| `no_redirect_shim_wrapper_check`        | Blocks redirect modules, shim classes, fake compatibility layers, alias wrappers, pass-through wrappers, and unnecessary adapter classes.                             |
| `typed_protocol_state_check`            | Requires Enum/Literal/frozen dataclass-style modeling for protocol state that crosses module boundaries.                                                              |
| `avoid_raw_dict_defaults_check`         | Blocks raw dict-heavy protocol design, mutable defaults, hidden defaults, implicit fallback behavior, and unclear optional parameters.                                |
| `official_library_simplification_check` | Checks whether a standard or official library can remove custom boilerplate while keeping the design clearer.                                                         |
| `comment_docstring_hygiene_check`       | Blocks AI-generated comments, stale docstrings, banner comments, decorative comments, misleading comments, and bloated explanations.                                  |
| `test_quality_check`                    | Blocks bloated, trivial, duplicated, implementation-detail, or low-value tests. Keeps tests focused on behavior, metrics, configs, artifacts, and regressions.        |
| `repo_structure_cleanliness_check`      | Blocks ugly folders, duplicated modules, redirects, shims, temp reports, root clutter, stale docs, and unclear ownership.                                             |
| `readme_makefile_sync_check`            | Ensures README commands, Makefile targets, config names, output paths, and documented workflows match the repo.                                                       |
| `graphify_when_useful`                  | Suggests Mermaid/Graphviz diagrams for flows, matrices, dependencies, and hierarchies when diagrams reduce text volume.                                               |
| `manuscript_integrity_check`            | Blocks unsupported “robust,” “privacy-preserving,” “deployment-ready,” “first,” or overgeneralized wording.                                                           |
| `git_hygiene_check`                     | Checks diff cleanliness, unrelated changes, untracked clutter, accidental formatting churn, removed meaningful comments, and generated junk.                          |

---

## 4. Hooks

| Hook                             | Trigger                                                                                       | Purpose                                                                                                                                         | Blocking                               |
| -------------------------------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| `contract_gate`                  | Start of every task                                                                           | Requires task, scope, forbidden actions, scientific boundaries, test plan, definition of done, and final report format.                         | Yes                                    |
| `pre_edit_hook`                  | Before file edits                                                                             | Reads task contract, checks scope, identifies allowed files/modules, checks repo state, and blocks forbidden actions before work begins.        | Yes                                    |
| `post_edit_hook`                 | After file edits                                                                              | Audits changed files for naming, structure, shims, wrappers, comments, docstrings, typing, defaults, boilerplate, docs drift, and temp clutter. | Yes                                    |
| `no_backward_compatibility_hook` | After any rename, restructure, API change, config change, CLI change, or output-layout change | Blocks compatibility aliases, deprecated paths, old config keys, redirects, shims, migration wrappers, and old-name preservation.               | Yes                                    |
| `test_hook`                      | After code changes                                                                            | Runs impacted tests only unless the contract explicitly requires broader tests. Blocks completion when impacted tests fail.                     | Yes                                    |
| `structure_hook`                 | After edits and before final report                                                           | Blocks ugly folders, duplicated modules, redirect files, shim layers, fake compatibility, random root files, and unclear module boundaries.     | Yes                                    |
| `comment_hook`                   | After edits                                                                                   | Blocks AI-generated comments, stale docstrings, banner comments, decorative comments, misleading explanations, and bloated comments.            | Yes                                    |
| `typing_hook`                    | After code edits                                                                              | Blocks protocol-level raw strings/dicts/defaults when Enum/Literal/dataclass/frozen dataclass modeling is more appropriate.                     | Yes                                    |
| `dependency_hook`                | After implementation                                                                          | Checks whether official or standard libraries can reduce boilerplate and simplify custom code. Obvious avoidable boilerplate must be fixed.     | Yes for obvious cases                  |
| `naming_hook`                    | After edits                                                                                   | Blocks weird names, vague variables, stale labels, unclear config keys, misleading class names, and overloaded terminology.                     | Yes                                    |
| `readme_makefile_hook`           | After command/config/output changes                                                           | Blocks completion when README or Makefile no longer matches actual commands, config names, output paths, or workflow.                           | Yes when touched behavior affects docs |
| `claim_evidence_hook`            | After docs/manuscript/result summaries                                                        | Blocks unsupported claims, claim inflation, causal wording for supportive experiments, and unsupported generalization.                          | Yes                                    |
| `statistics_hook`                | After result/stat code changes                                                                | Blocks incorrect metric direction, seed pairing errors, BCa CI misuse, sign-consistency mistakes, and weak/null misinterpretation.              | Yes                                    |
| `cleanup_hook`                   | End of every task                                                                             | Blocks temp files, scratch files, audit leftovers, agent reports, duplicate reports, generated clutter, and random root artifacts.              | Yes                                    |
| `final_report_hook`              | Before final response                                                                         | Verifies contract completion, changed files, tests run, checks performed, cleanup, risks, and remaining issues.                                 | Yes                                    |

---

## 5. Hook Behavior Rules

| Rule                                               | Meaning                                                                                                                                                                                                              |
| -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hooks protect scope and quality                    | Hooks must block messy structure, stale comments, weak typing, unsupported claims, backward-compatibility clutter, and scientific drift.                                                                             |
| Hooks do not silently change scientific meaning    | No hook may alter threshold semantics, experiment logic, statistical interpretation, claim strength, dataset role, or stress-test status without an explicit protocol-impact note.                                   |
| Clean code issues are blockers                     | Stale comments, stale docstrings, AI-generated comments, weird names, shims, redirects, fake wrappers, raw protocol strings, raw protocol dicts, hidden defaults, and bloated tests must be fixed before completion. |
| Backward compatibility is forbidden by default     | Old APIs, old configs, old CLI flags, old paths, old output names, aliases, redirects, deprecation layers, and compatibility wrappers must not be kept unless the task contract explicitly allows them.              |
| Impacted tests first                               | The test hook runs relevant tests after code changes. Broader tests run only when the contract requires them.                                                                                                        |
| No hidden cleanup                                  | Cleanup must report what was removed when removing non-trivial clutter.                                                                                                                                              |
| Structure is part of completion                    | A task is not done if the code works but leaves ugly folders, duplicate modules, shims, temp reports, stale docs, compatibility clutter, or confusing ownership.                                                     |
| Dependency simplification is required when obvious | When custom boilerplate clearly duplicates an official/standard library and the library improves clarity, the boilerplate must be replaced or explicitly justified.                                                  |
| Graphs are used for compression, not decoration    | Mermaid/Graphviz diagrams are used only when they reduce text and clarify relationships.                                                                                                                             |

---

## 6. Contracts

Each task must begin with a contract.

### 6.1 Contract Template

| Section                           | Required content                                                                                                         |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `Task`                            | What is being changed or checked.                                                                                        |
| `Workflow`                        | One selected workflow from this catalogue.                                                                               |
| `Scope`                           | Exact files, folders, modules, configs, docs, or outputs that may change.                                                |
| `Forbidden actions`               | Actions that must not happen.                                                                                            |
| `Backward-compatibility position` | Default must be: no backward compatibility, no aliases, no old names, no shims, no redirects.                            |
| `Scientific boundaries`           | DATP-specific boundaries relevant to the task.                                                                           |
| `Implementation rules`            | Naming, typing, structure, default handling, dict usage, library usage, comment/docstring rules, and test-quality rules. |
| `Test plan`                       | Impacted tests to run; broader tests only when justified.                                                                |
| `Definition of done`              | What must be true before final report.                                                                                   |
| `Audit checklist`                 | What must be verified before completion.                                                                                 |
| `Final report format`             | What the final answer must include.                                                                                      |

### 6.2 Standard Contract Fields

| Field                             | Standard rule                                                                                                                                                                                             |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Scope`                           | Only edit files explicitly needed for the task. Do not restructure unrelated areas.                                                                                                                       |
| `Forbidden actions`               | No temp files, no audit clutter, no shims, no redirects, no fake compatibility, no compatibility aliases, no wrapper classes without real behavior, no bloated comments, no stale docs, no useless tests. |
| `Backward-compatibility position` | Backward compatibility is forbidden by default. Replace old concepts directly and update all impacted code, tests, docs, configs, and outputs.                                                            |
| `Scientific boundaries`           | Do not change DATP scope, threshold semantics, dataset roles, seed meaning, metric meaning, claim strength, or stress-test status without approval.                                                       |
| `Implementation rules`            | Use clear names, explicit types, Enum/Literal/dataclass for protocol state, no raw dicts when a typed object is better, no hidden defaults, no mutable defaults, no stale comments/docstrings.            |
| `Test plan`                       | Run impacted tests after code changes. Run broader tests only when core shared behavior changed or when explicitly requested.                                                                             |
| `Definition of done`              | Impacted tests green, lint/type checks green where relevant, clean structure, no stale comments/docs, no temp files, no compatibility clutter, no unsupported claims, no useless test bloat.              |
| `Audit checklist`                 | Scope respected, no forbidden actions, no backward compatibility clutter, naming clean, structure clean, comments/docstrings clean, typing clean, impacted tests run.                                     |
| `Final report`                    | Changed files, why they changed, tests/checks run, cleanup result, unresolved risks, skipped checks with reason.                                                                                          |

---

## 7. Backward-Compatibility Policy

Backward compatibility is off by default.

This repository is allowed to make clean breaking changes when they improve clarity, correctness, scientific discipline, naming, structure, or reproducibility.

| Rule                       | Required behavior                                                                                                          |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| No legacy aliases          | Do not keep old class names, function names, enum values, config keys, CLI flags, or output names as aliases.              |
| No redirect modules        | Do not create files whose only purpose is importing from a new location.                                                   |
| No shim layers             | Do not add transitional layers that preserve old behavior while hiding the new structure.                                  |
| No fake migration wrappers | Do not create temporary wrappers to avoid updating callers. Update the callers.                                            |
| No stale configs           | Remove old config keys and update all examples, tests, docs, and runners.                                                  |
| No old output layout       | If output layout changes, update the consumers and docs directly. Do not support both old and new layouts.                 |
| No compatibility comments  | Do not leave comments explaining old behavior unless the old behavior is scientifically relevant history in documentation. |
| No deprecation period      | Do not add deprecated APIs. Remove or replace directly.                                                                    |
| No dual semantics          | Do not support two meanings for the same concept. One concept, one name, one location.                                     |
| No silent fallback         | Do not silently accept old values. Validation must fail clearly when stale names or stale config keys are used.            |

Backward compatibility may be allowed only if the task contract explicitly says so and gives a concrete reason. Even then, it must be isolated, time-limited, documented, tested, and removed from the definition of done for a later cleanup task.

---

## 8. Forbidden Actions

| Forbidden action                                                        | Reason                                                    |
| ----------------------------------------------------------------------- | --------------------------------------------------------- |
| Creating temp/audit/report/scratch files outside approved ignored space | Prevents clutter and fake progress artifacts.             |
| Adding redirect modules                                                 | Hides structure problems.                                 |
| Adding shims                                                            | Creates fake compatibility and stale architecture.        |
| Adding wrapper classes without real behavior                            | Bloats code and hides simple logic.                       |
| Adding compatibility aliases                                            | Encourages stale names and unclear semantics.             |
| Keeping old config keys                                                 | Preserves stale protocol language and weakens validation. |
| Keeping old CLI flags                                                   | Makes workflows ambiguous and encourages stale usage.     |
| Keeping old output names                                                | Makes result provenance unclear.                          |
| Supporting old and new behavior simultaneously                          | Creates dual semantics and reviewer risk.                 |
| Adding banner comments                                                  | Looks AI-generated and adds noise.                        |
| Adding obvious comments                                                 | Repeats the code without helping.                         |
| Deleting meaningful existing comments blindly                           | Can remove useful domain knowledge.                       |
| Keeping stale comments                                                  | Misleads future implementation and audits.                |
| Keeping stale docstrings                                                | Misleads future work and reviewers.                       |
| Using raw strings for scientific protocol state                         | Causes typos, stale labels, and semantic drift.           |
| Using raw dicts for structured protocol state                           | Hides required fields and weakens validation.             |
| Using mutable defaults                                                  | Creates hidden bugs.                                      |
| Adding broad defaults without explanation                               | Hides experiment assumptions.                             |
| Adding tests that only check implementation trivia                      | Bloats test suite without protecting behavior.            |
| Keeping duplicate or low-value tests                                    | Slows impacted-test workflow without improving safety.    |
| Moving stress tests into the causal ladder                              | Violates DATP journal identity.                           |
| Strengthening claims beyond evidence                                    | Creates reviewer risk.                                    |
| Creating generated audit documents unless explicitly requested          | Produces clutter and fake progress artifacts.             |
| Touching unrelated files opportunistically                              | Creates diff noise and weakens reviewability.             |

---

## 9. Universal AI Workflow Protocol

Every AI agent must follow this lifecycle for every task.

```text
1. Intake
2. Contract
3. Pre-edit gate
4. Implementation or audit
5. Post-edit gate
6. No-backward-compatibility gate
7. Impacted tests
8. Structure/comment/typing/dependency gates
9. Cleanup
10. Final report
```

No agent may skip the contract, scope check, no-backward-compatibility check, cleanup check, or final report.

---

## 10. Workflow Catalogue

Each task must be assigned exactly one workflow before execution.

### 10.1 Implementation Workflow

Use for code changes.

Required gates:

```text
contract_gate
pre_edit_hook
implementation
post_edit_hook
no_backward_compatibility_hook
naming_hook
typing_hook
comment_hook
dependency_hook
structure_hook
test_hook
cleanup_hook
final_report_hook
```

Completion requires:

| Requirement   | Rule                                                                                   |
| ------------- | -------------------------------------------------------------------------------------- |
| Scope         | Only approved files changed.                                                           |
| Compatibility | No old APIs, aliases, redirects, shims, compatibility configs, or legacy output names. |
| Tests         | Impacted tests pass.                                                                   |
| Lint/type     | Relevant lint/type checks pass or unresolved issues are reported.                      |
| Comments      | No stale comments/docstrings in touched scope.                                         |
| Typing        | Protocol state is explicit and typed.                                                  |
| Structure     | No shims, redirects, wrappers, duplicate modules, or clutter.                          |
| Report        | Final report uses the standard format.                                                 |

---

### 10.2 Experiment Workflow

Use for configs, runners, outputs, seeds, metrics, and experiment readiness.

Required gates:

```text
contract_gate
datp_protocol_guardian
experiment_readiness_check
statistics_hook
artifact_provenance_check
no_backward_compatibility_hook
post_edit_hook
test_hook
cleanup_hook
final_report_hook
```

Completion requires:

| Requirement | Rule                                                      |
| ----------- | --------------------------------------------------------- |
| Dataset     | Dataset role verified.                                    |
| Clients     | Client definition verified.                               |
| Seeds       | Seed list fixed and traceable.                            |
| Metrics     | Metric names, directions, and interpretations verified.   |
| Outputs     | Output layout clear and not duplicated for compatibility. |
| Configs     | Config names clear, current, and validated.               |
| Claims      | No claim inflation.                                       |
| Execution   | No experiment run unless readiness passes.                |

---

### 10.3 Result Audit Workflow

Use for tables, metrics, figures, summaries, and result interpretation.

Required gates:

```text
scope_gate
statistics_hook
claim_evidence_hook
reviewer_attack_check
manuscript_integrity_check
cleanup_hook
final_report_hook
```

Completion requires:

| Requirement  | Rule                                        |
| ------------ | ------------------------------------------- |
| Metrics      | Metric direction verified.                  |
| Seeds        | Seed pairing verified.                      |
| CIs          | Confidence intervals interpreted correctly. |
| Weak results | Null or weak results not exaggerated.       |
| Claims       | Every claim mapped to evidence.             |
| Wording      | Safe wording provided for each result.      |

---

### 10.4 Manuscript Workflow

Use for paper, README, LaTeX, Markdown, captions, abstract, introduction, related work, discussion, and conclusion.

Required gates:

```text
scope_gate
claim_evidence_hook
manuscript_integrity_check
literature_overlap_check
comment_docstring_hygiene_check
reviewer_attack_check
cleanup_hook
final_report_hook
```

Completion requires:

| Requirement    | Rule                                                                                             |
| -------------- | ------------------------------------------------------------------------------------------------ |
| Hype           | No hype.                                                                                         |
| First claims   | No “first” unless verified.                                                                      |
| Privacy        | No privacy guarantee claim unless formally supported.                                            |
| Deployment     | No deployment-readiness claim unless measured.                                                   |
| Robustness     | No robustness claim unless directly tested.                                                      |
| Causality      | No unsupported causal language.                                                                  |
| Style          | No AI-looking filler.                                                                            |
| Classification | Claims classified as confirmatory, supportive, exploratory, mechanism, boundary, or future work. |

---

### 10.5 Cleanup and Refactor Workflow

Use for structure cleanup, naming cleanup, stale-code removal, or simplification.

Required gates:

```text
contract_gate
pre_edit_hook
structure_hook
naming_hook
typing_hook
comment_hook
dependency_hook
no_backward_compatibility_hook
test_hook
cleanup_hook
final_report_hook
```

Completion requires:

| Requirement    | Rule                                                                       |
| -------------- | -------------------------------------------------------------------------- |
| Compatibility  | No compatibility shims, redirects, deprecated aliases, or legacy wrappers. |
| Scope          | No unrelated restructuring.                                                |
| Tests          | Impacted tests pass.                                                       |
| Comments       | Meaningful existing comments are not blindly deleted.                      |
| Stale comments | Stale comments in touched scope are fixed.                                 |
| Structure      | Duplicate modules, ugly folders, wrappers, and root clutter removed.       |

---

### 10.6 Audit-Only Workflow

Use when no files should be changed.

Required gates:

```text
contract_gate
scope_gate
audit_execution
claim_evidence_hook_when_relevant
statistics_hook_when_relevant
final_report_hook
```

Completion requires:

| Requirement | Rule                                                       |
| ----------- | ---------------------------------------------------------- |
| No edits    | No files changed.                                          |
| Findings    | Findings classified by severity.                           |
| Evidence    | Each finding cites the inspected file, command, or result. |
| Fixes       | Required fixes are separated from optional improvements.   |
| Verdict     | Final verdict is PASS, FAIL, or PARTIAL.                   |

---

## 11. Severity System

Every issue must be classified.

| Severity  | Meaning                                                                                                                 | Completion allowed? |
| --------- | ----------------------------------------------------------------------------------------------------------------------- | ------------------- |
| `BLOCKER` | Violates scope, science, typing, structure, comments, tests, claims, reproducibility, or backward-compatibility policy. | No                  |
| `MAJOR`   | Does not break the task but creates reviewer, maintenance, reproducibility, or correctness risk.                        | Only if reported    |
| `MINOR`   | Small cleanup or clarity issue.                                                                                         | Yes, if reported    |
| `NOTE`    | Observation only.                                                                                                       | Yes                 |

The following are always `BLOCKER`:

| Blocker                                                                   | Reason                                         |
| ------------------------------------------------------------------------- | ---------------------------------------------- |
| Stale comments or stale docstrings in touched scope                       | Misleads future work.                          |
| AI-generated comments, banner comments, decorative comments               | Adds noise and weakens code quality.           |
| Weird names, vague names, stale names, misleading names                   | Causes semantic drift.                         |
| Raw protocol strings where Enum/Literal is appropriate                    | Weakens validation.                            |
| Raw dict-heavy protocol state where dataclass/typed object is appropriate | Hides required fields.                         |
| Hidden defaults, mutable defaults, unexplained defaults                   | Hides behavior.                                |
| Shims, redirects, fake compatibility layers                               | Violates clean architecture.                   |
| Compatibility aliases or old config keys                                  | Violates no-backward-compatibility policy.     |
| Wrapper classes without real behavior                                     | Bloats structure.                              |
| Temp files, audit clutter, scratch reports, random root files             | Creates noise.                                 |
| Unsupported scientific claims                                             | Creates reviewer risk.                         |
| Changing threshold semantics without approval                             | Violates DATP identity.                        |
| Moving stress tests into the causal ladder                                | Violates journal protocol.                     |
| Failing impacted tests                                                    | Blocks completion.                             |
| Not running impacted tests after code changes                             | Blocks completion unless explicitly justified. |

---

## 12. Definition of Done

| Area                   | Done means                                                                                                                                 |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Scope                  | Only approved files changed. No unrelated edits.                                                                                           |
| Backward compatibility | No aliases, old APIs, old config keys, old CLI flags, redirects, shims, deprecated paths, legacy wrappers, or compatibility layers remain. |
| Structure              | No ugly folders, duplicates, redirects, shims, wrappers, temp files, or root clutter.                                                      |
| Naming                 | Names are direct, readable, current, and semantically accurate.                                                                            |
| Typing                 | Protocol-level state uses explicit typed structures; raw strings/dicts/defaults are avoided where possible and fixed when found.           |
| Dependencies           | Custom boilerplate reviewed; official/standard libraries used when they make code simpler and clearer.                                     |
| Comments/docstrings    | No AI-generated, stale, decorative, banner, misleading, or bloated comments/docstrings remain.                                             |
| Tests                  | Impacted tests run and pass; no useless tests added or kept when touched.                                                                  |
| Lint/type              | Relevant lint/type checks pass or unresolved issues are explicitly reported.                                                               |
| Docs                   | README/Makefile updated only when needed and kept accurate.                                                                                |
| Claims                 | Any claim touched is evidence-backed and correctly classified.                                                                             |
| Cleanup                | No temp audit/report/scratch artifacts remain.                                                                                             |
| Final report           | Uniform final report provided.                                                                                                             |

---

## 13. Universal Audit Checklist

Before final report, every agent must verify:

```text
Scope
[ ] Did I change only allowed files?
[ ] Did I avoid unrelated cleanup?
[ ] Did I avoid root clutter?

Backward compatibility
[ ] Did I avoid old APIs?
[ ] Did I avoid compatibility aliases?
[ ] Did I avoid old config keys?
[ ] Did I avoid old CLI flags?
[ ] Did I avoid old output names?
[ ] Did I avoid redirects?
[ ] Did I avoid shims?
[ ] Did I avoid compatibility wrappers?
[ ] Did I update callers/tests/docs directly instead of preserving old behavior?

Science
[ ] Did I preserve DATP threshold-scope identity?
[ ] Did I avoid changing threshold semantics without approval?
[ ] Did I keep stress tests outside the causal ladder?
[ ] Did I avoid unsupported claims?

Code quality
[ ] Are names clear and current?
[ ] Are protocol states typed?
[ ] Are raw dicts avoided where typed objects are better?
[ ] Are defaults explicit and justified?
[ ] Are official/standard libraries used where they clearly simplify code?

Structure
[ ] No shims.
[ ] No redirects.
[ ] No fake compatibility.
[ ] No wrapper classes without behavior.
[ ] No duplicate modules.
[ ] No ugly folders.

Comments/docs
[ ] No stale comments.
[ ] No stale docstrings.
[ ] No AI-generated comments.
[ ] No banner comments.
[ ] No decorative comments.
[ ] README/Makefile updated only if behavior changed.

Tests
[ ] Impacted tests run after code changes.
[ ] Broader tests run only when justified.
[ ] No useless tests added.
[ ] No duplicate tests kept in touched scope.

Cleanup
[ ] No temp files.
[ ] No scratch files.
[ ] No generated audit reports unless explicitly requested.
[ ] No random root files.

Final report
[ ] Changed files listed.
[ ] Reason for each change given.
[ ] Checks run listed.
[ ] Cleanup result stated.
[ ] Remaining risks stated.
[ ] Skipped checks stated with reason.
```

---

## 14. Standard Agent Response Formats

All agents must use one of the following formats.

### 14.1 File-Changing Task

```text
Task understood
Goal:
Scope:
Forbidden actions:
Backward-compatibility position:
Scientific boundaries:
Planned workflow:

Contract
Files allowed to change:
Files forbidden to change:
Tests expected:
Completion criteria:

Execution summary
Changed files:
What changed:
Why:

Checks run
Tests:
Lint/type checks:
Structure checks:
Backward-compatibility checks:
Comment/docstring checks:
Typing/default checks:
Dependency simplification check:
Claim/evidence check if relevant:

Cleanup
Temp files:
Audit clutter:
Root clutter:

Remaining risks
Risks:
Skipped checks with reason:
Follow-up needed:
```

### 14.2 Audit-Only Task

```text
Audit scope
What was checked:
Files/modules inspected:
Files/modules not inspected:
No-edit confirmation:

Findings
Blockers:
Major issues:
Minor issues:
Clean areas:

Required fixes
Must fix:
Should fix:
Optional:

Checks run
Commands:
Manual checks:
Limitations:

Final verdict
PASS / FAIL / PARTIAL
Reason:
```

### 14.3 Research or Manuscript Task

```text
Task understood
Goal:
Scope:
Claim boundary:

Evidence used
Internal files:
Results:
Literature:
Unsupported assumptions:

Output
Main changes or recommendations:

Claim safety
Confirmatory claims:
Supportive claims:
Exploratory claims:
Forbidden claims avoided:

Remaining risks
Reviewer risks:
Evidence gaps:
Suggested next check:
```

### 14.4 Experiment Task

```text
Experiment task understood
Goal:
Dataset:
Client definition:
Policies:
Seeds:
Metrics:
Expected outputs:

Readiness gates
Dataset role:
Artifact provenance:
Config completeness:
Metric direction:
Output layout:
Claim boundary:

Execution or preparation summary
Changed files:
What changed:
Why:

Checks run
Tests:
Config validation:
Statistics checks:
Structure checks:
Backward-compatibility checks:
Cleanup:

Remaining risks
Risks:
Skipped checks with reason:
Follow-up needed:
```

---

## 15. Final Report Rules

Every task must end with this compact report.

| Section           | Content                                                                                                                   |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `Changed files`   | Files changed and one-line reason for each.                                                                               |
| `What changed`    | Short explanation of the implemented change.                                                                              |
| `Checks run`      | Impacted tests, lint, type checks, structure checks, backward-compatibility checks, comment checks, and other audits run. |
| `Cleanup`         | Temp files removed or confirmation that none were left.                                                                   |
| `Remaining risks` | Any unresolved risk, skipped check, or follow-up needed.                                                                  |

Forbidden final-report behavior:

| Forbidden behavior        | Rule                                   |
| ------------------------- | -------------------------------------- |
| Long self-congratulation  | Do not include it.                     |
| Vague “all good”          | Report actual checks.                  |
| Hidden skipped tests      | Always state skipped checks.           |
| “Should be fine” language | Use evidence, not confidence phrases.  |
| Huge log dumps            | Summarize and cite commands/results.   |
| Generated audit files     | Do not create them unless requested.   |
| Pretending checks ran     | Never claim a check ran unless it did. |

---

## 16. Repository Catalogue Layout

Recommended layout:

```text
AGENTS.md
ai/
  README.md
  agents/
    roadmap_orchestrator.md
    datp_protocol_guardian.md
    architecture_cleaner.md
    compatibility_blocker.md
    naming_auditor.md
    threshold_policy_engineer.md
    implementation_engineer.md
    experiment_engineer.md
    statistics_auditor.md
    claim_evidence_auditor.md
    literature_novelty_auditor.md
    reviewer2_red_team.md
    manuscript_editor.md
    reproducibility_auditor.md
    graphify_assistant.md
  skills/
    datp_journal_scope_guard.md
    threshold_policy_semantics.md
    confirmatory_claim_guard.md
    stress_test_boundary_check.md
    experiment_readiness_check.md
    statistical_validity_check.md
    claim_evidence_map.md
    literature_overlap_check.md
    reviewer_attack_check.md
    naming_clarity_check.md
    no_backward_compatibility_check.md
    no_redirect_shim_wrapper_check.md
    typed_protocol_state_check.md
    avoid_raw_dict_defaults_check.md
    official_library_simplification_check.md
    comment_docstring_hygiene_check.md
    test_quality_check.md
    repo_structure_cleanliness_check.md
    readme_makefile_sync_check.md
    graphify_when_useful.md
    manuscript_integrity_check.md
    git_hygiene_check.md
  hooks/
    contract_gate.md
    pre_edit_hook.md
    post_edit_hook.md
    no_backward_compatibility_hook.md
    test_hook.md
    structure_hook.md
    comment_hook.md
    typing_hook.md
    dependency_hook.md
    naming_hook.md
    readme_makefile_hook.md
    claim_evidence_hook.md
    statistics_hook.md
    cleanup_hook.md
    final_report_hook.md
  contracts/
    task_contract_template.md
    implementation_contract.md
    experiment_contract.md
    manuscript_contract.md
    audit_contract.md
    cleanup_refactor_contract.md
  workflows/
    implementation_workflow.md
    experiment_workflow.md
    result_audit_workflow.md
    manuscript_workflow.md
    cleanup_refactor_workflow.md
    audit_only_workflow.md
```

No `ops/` folder, no generated audit folder, no temporary report folder, and no root-level clutter unless explicitly requested.

---

## 17. Core Rule

The repository must stay small, typed, explicit, and clean.

Prefer clear names, direct modules, explicit protocol objects, Enum/Literal types, frozen dataclasses, simple functions, useful tests, accurate docs, and strict validation.

Always fix stale comments, stale docstrings, AI-generated comments, weak protocol typing, weird naming, redirects, shims, fake wrappers, hidden defaults, raw dict-heavy protocol design, ugly structure, compatibility clutter, and useless tests when encountered in touched scope.

Avoid raw dicts, hidden defaults, vague variables, redirect modules, shims, fake compatibility layers, compatibility aliases, wrapper classes without behavior, generated audit clutter, bloated comments, stale docstrings, and useless tests.

No backward compatibility is the default. Clean replacement is preferred over preserving stale behavior.

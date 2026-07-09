# AI Operating System

This directory defines the permanent AI governance structure for the DATP journal-extension repository.

## Directory Purpose

- `ai/agents/`: role definitions for agent behavior, ownership, and blockers.
- `ai/skills/`: focused checks that can be applied across workflows.
- `ai/hooks/`: mandatory gates that block completion when quality, scope, science, or cleanup fails.
- `ai/contracts/`: task templates that define scope, forbidden actions, tests, and done criteria before work starts.
- `ai/workflows/`: approved task paths for implementation, experiments, audits, manuscripts, and cleanup.

## Mandatory Task Lifecycle

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

No agent may skip the contract, scope check, no-backward-compatibility check, cleanup check, or final report.

## Universal Rule

A task is not complete because the code works.
A task is complete only when scope, science, structure, naming, typing, comments, tests, claims, cleanup, and final report all pass.

## DATP Boundary

The project is a fixed-encoder, fixed-federated-model, threshold-calibration-scope study. B1-B4 vary threshold scope while preserving the same trained model and score artifacts. Stress tests and comparators support the study but do not replace the causal ladder.

Block drift into poisoning, Dynamic DATP, privacy guarantees, deployment profiling, backdoor, evasion, full drift detection, generic FL-IDS expansion, release work, tag work, or versioning work unless explicitly requested as future-work wording.

## Default Compatibility Position

No backward compatibility. No old aliases, redirects, shims, fake compatibility, deprecated APIs, legacy config keys, legacy CLI flags, or legacy output names. Replace stale behavior directly and update all impacted callers, tests, docs, configs, and outputs.

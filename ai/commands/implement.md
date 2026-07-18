# Command: implement

## Use when

Changing code or behavior.

## Permissions

May edit source in scope · run impacted tests · run the quality gate. Must **not** modify scientific
configuration meaning without roadmap check and task approval · run long experiments · commit.

## Required context

The task request, the target files, the impacted-test set. Read `docs/Architecture/` only if the change
touches layer design, and the roadmap only if it touches scientific meaning.

## Contract

- **Scope:** only the files the change requires.
- **Forbidden:** unrelated refactors, temp/audit files, shims/redirects/aliases/wrappers-without-
  behavior, stale comments, useless tests, release/tag/version work.
- **Scientific boundary:** do not change DATP scope, threshold semantics, dataset role, seed/metric
  meaning, model behavior, artifact meaning, or claim strength without approval.

## Procedure

1. Pass `ai/hooks/pre-edit-gate.md`.
2. Implement with clear names, explicit types, and typed protocol state
   (`ai/skills/typed-immutable-domain.md`, `ai/skills/architecture-and-dependencies.md`).
3. If scientific/execution values are involved, apply `ai/skills/scientific-config.md`; for CUDA code,
   `ai/skills/cuda-safety.md`.
4. Apply `ai/skills/no-backward-compatibility.md` and `ai/skills/code-hygiene.md`.
5. Run the per-change `ai/skills/quality-gate.md`.
6. Pass `ai/hooks/pre-completion-gate.md`.

## Completion criteria

Code works, impacted tests pass (order-independent), types/lint/architecture checks pass, no
compatibility artifacts, structure and names clean.

## Output

`AGENTS.md` final-report headings, plus impacted tests and the compatibility check result.

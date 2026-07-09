# Implementation Contract

## Task
Implement code or behavior changes described by the task.

## Workflow
Use `ai/workflows/implementation_workflow.md`.

## Scope
Only files required by the implementation may change.

## Forbidden actions
No unrelated refactors, temp files, audit clutter, shims, redirects, fake compatibility, compatibility aliases, wrapper classes without behavior, stale comments, useless tests, release work, tag work, or versioning work.

## Backward-compatibility position
No backward compatibility. No old aliases. No redirects. No shims. No fake compatibility. No deprecated APIs. No legacy config keys. No legacy CLI flags. No legacy output names. Update callers, tests, docs, configs, and outputs directly.

## Scientific boundaries
Do not change DATP scope, threshold semantics, dataset role, seed meaning, metric meaning, claim strength, model behavior, or artifact meaning without explicit approval.

## Implementation rules
Use clear names, direct ownership, explicit types, typed protocol state, no raw protocol dicts when typed objects are better, no hidden defaults, no mutable defaults, and no stale comments or docstrings.

## Test plan
Run impacted tests after code changes. Run broad tests only when shared behavior changed or the task requires it.

## Definition of done
Code works, impacted tests pass, structure is clean, no compatibility clutter exists, and cleanup passes.

## Audit checklist
Run pre-edit, post-edit, no-backward-compatibility, naming, typing, comment, dependency, structure, test, cleanup, and final report gates.

## Final report format
Changed files, checks run, cleanup result, remaining risks, and skipped checks with reasons.

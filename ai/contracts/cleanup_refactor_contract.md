# Cleanup Refactor Contract

## Task
Clean structure, naming, stale code, comments, typing, or duplicated logic inside approved scope.

## Workflow
Use `ai/workflows/cleanup_refactor_workflow.md`.

## Scope
List exact cleanup targets and allowed callers, tests, docs, configs, or outputs.

## Forbidden actions
No unrelated restructuring, no migration scaffolding, no legacy preservation, no shims, no redirects, no compatibility aliases, no wrappers without behavior, no temp files, no audit clutter, no release work, tag work, or versioning work.

## Backward-compatibility position
No backward compatibility. No old aliases. No redirects. No shims. No fake compatibility. No deprecated APIs. No legacy config keys. No legacy CLI flags. No legacy output names. Update callers, tests, docs, configs, and outputs directly.

## Scientific boundaries
Cleanup must not change DATP semantics, threshold policy, metric meaning, seed meaning, dataset role, claim strength, or stress-test status without approval.

## Implementation rules
Prefer direct modules, clear names, typed protocol state, explicit defaults, useful tests, and accurate comments. Remove stale comments and docstrings in touched scope.

## Test plan
Run impacted tests for changed behavior. Explain skipped tests when cleanup is documentation-only.

## Definition of done
Structure is cleaner, no compatibility artifacts remain, impacted tests pass or are justified, cleanup passes, and report is complete.

## Audit checklist
Check structure, naming, typing, comments, dependencies, no-backward-compatibility, tests, cleanup, and final report.

## Final report format
Changed files, checks run, cleanup result, remaining risks, and skipped checks with reasons.

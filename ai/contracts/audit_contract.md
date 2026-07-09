# Audit Contract

## Task
Inspect approved files or outputs without editing.

## Workflow
Use `ai/workflows/audit_only_workflow.md`.

## Scope
List files, folders, commands, or artifacts to inspect.

## Forbidden actions
No edits, no temp files, no audit reports, no generated artifacts, no cleanup changes, no release work, tag work, or versioning work.

## Backward-compatibility position
No backward compatibility. No old aliases. No redirects. No shims. No fake compatibility. No deprecated APIs. No legacy config keys. No legacy CLI flags. No legacy output names. Update callers, tests, docs, configs, and outputs directly when a later edit task is approved.

## Scientific boundaries
Do not alter threshold semantics, datasets, seeds, metrics, model behavior, artifacts, or claim strength.

## Implementation rules
Audit only. Classify findings as blocker, major, minor, or note and cite evidence.

## Test plan
Run read-only commands only. Do not run long experiments unless explicitly approved.

## Definition of done
No files changed, findings are evidenced, required fixes are separated from optional improvements, and final verdict is PASS, FAIL, or PARTIAL.

## Audit checklist
Check no-edit status, scope, compatibility, DATP boundaries, claims, statistics when relevant, cleanup, and final report.

## Final report format
Changed files, checks run, cleanup result, remaining risks, and skipped checks with reasons.

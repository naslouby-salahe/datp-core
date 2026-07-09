# Task Contract Template

## Task
State the exact change or audit.

## Workflow
Select one workflow from `ai/workflows/`.

## Scope
List files, folders, modules, configs, docs, or outputs that may change.

## Forbidden actions
No temp files, audit clutter, shims, redirects, fake compatibility, compatibility aliases, wrappers without behavior, bloated comments, stale docs, useless tests, unrelated edits, release work, tag work, or versioning work.

## Backward-compatibility position
No backward compatibility. No old aliases. No redirects. No shims. No fake compatibility. No deprecated APIs. No legacy config keys. No legacy CLI flags. No legacy output names. Update callers, tests, docs, configs, and outputs directly.

## Scientific boundaries
Preserve fixed encoder, fixed federated model, threshold-calibration-scope study, B1-B4 threshold-scope ladder, and same trained model and score artifacts. Keep stress tests supportive.

## Implementation rules
Use clear names, explicit typing, typed protocol state, explicit defaults, direct modules, useful comments only, and focused tests.

## Test plan
List impacted tests. Broader tests require justification.

## Definition of done
Scope, science, structure, naming, typing, comments, tests, claims, cleanup, and final report all pass.

## Audit checklist
Check scope, compatibility, DATP boundaries, naming, structure, comments, typing/defaults, tests, cleanup, and final report.

## Final report format
Use the `AGENTS.md` final report format with Markdown headings and bullet lists. Include changed files, checks run, cleanup result, remaining risks, skipped checks with reasons, and any workflow-specific facts.

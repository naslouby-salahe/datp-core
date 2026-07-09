# Experiment Contract

## Task
Prepare, validate, or change experiment configs, runners, metrics, outputs, or provenance.

## Workflow
Use `ai/workflows/experiment_workflow.md`.

## Scope
List exact experiment files, configs, runners, output definitions, or docs allowed.

## Forbidden actions
No long experiment runs without approval, no model-code drift, no result artifact edits unless approved, no legacy config preservation, no old output names, no temp files, no audit clutter, no release work, tag work, or versioning work.

## Backward-compatibility position
No backward compatibility. No old aliases. No redirects. No shims. No fake compatibility. No deprecated APIs. No legacy config keys. No legacy CLI flags. No legacy output names. Update callers, tests, docs, configs, and outputs directly.

## Scientific boundaries
Preserve fixed encoder, fixed federated model, threshold-scope B1-B4 design, dataset role, client definition, seed meaning, metric direction, and artifact provenance.

## Implementation rules
Use explicit config names, typed protocol state, validated defaults, direct output layout, clear provenance, and no raw dict-heavy protocol state.

## Test plan
Run config validation and impacted tests. Run experiments only after readiness passes and only when approved.

## Definition of done
Dataset, clients, seeds, metrics, configs, outputs, provenance, compatibility gate, tests, cleanup, and report all pass.

## Audit checklist
Check protocol, experiment readiness, statistics, artifact provenance, no-backward-compatibility, post-edit, tests, cleanup, and final report.

## Final report format
Changed files, checks run, cleanup result, remaining risks, and skipped checks with reasons.

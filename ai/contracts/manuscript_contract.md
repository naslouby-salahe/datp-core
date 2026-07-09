# Manuscript Contract

## Task
Edit or audit manuscript, README prose, LaTeX, Markdown, captions, abstracts, discussions, conclusions, or reviewer-facing text.

## Workflow
Use `ai/workflows/manuscript_workflow.md`.

## Scope
List exact prose files or sections allowed.

## Forbidden actions
No unsupported claims, no hype, no AI-looking filler, no stale wording, no scientific meaning changes, no unrelated docs, no generated audit reports, no release work, tag work, or versioning work.

## Backward-compatibility position
No backward compatibility. No old aliases. No redirects. No shims. No fake compatibility. No deprecated APIs. No legacy config keys. No legacy CLI flags. No legacy output names. Update callers, tests, docs, configs, and outputs directly.

## Scientific boundaries
Preserve DATP journal scope, threshold semantics, stress-test status, metric meaning, and claim classification.

## Implementation rules
Use precise claims, evidence-backed wording, current names, no stale comments, no decorative sections, and no bloated explanations.

## Test plan
No code tests unless behavior or commands change. Run claim-evidence, literature, manuscript-integrity, and cleanup checks.

## Definition of done
Claims are classified and evidence-backed, wording is safe, DATP scope is preserved, cleanup passes, and final report is complete.

## Audit checklist
Check claim-evidence, manuscript integrity, literature overlap, reviewer risk, stale wording, cleanup, and final report.

## Final report format
Use the `AGENTS.md` final report format with Markdown headings and bullet lists. Include changed files, checks run, cleanup result, remaining risks, skipped checks with reasons, claim classifications, evidence used, wording constraints, and reviewer risks.

# Command: manuscript

## Use when

Editing or auditing paper prose, README prose, LaTeX, Markdown, captions, abstracts, discussion,
conclusion, or reviewer-facing text.

## Permissions

May edit the prose files in scope. Must **not** change scientific meaning, code behavior, or results;
no release/tag/version work.

## Required context

The prose file/section being edited and its cited tables, figures, results, and related work.

## Contract

- **Scope:** the listed prose files/sections.
- **Forbidden:** unsupported claims, hype, AI-looking filler, stale wording, scientific-meaning
  changes, unrelated docs, generated audit reports.
- **Scientific boundary:** preserve DATP journal scope, threshold semantics, stress-test status, metric
  meaning, and claim classification.

## Procedure

1. Pass `ai/hooks/pre-edit-gate.md`.
2. Apply `ai/skills/evidence-and-statistics.md` (claim↔evidence, confirmatory endpoint, novelty,
   reviewer risk) and `ai/skills/datp-scope-guard.md`.
3. Apply `ai/skills/code-hygiene.md` (no stale wording, no banner/decorative prose) and
   `ai/skills/no-backward-compatibility.md` (no stale command/output names in prose).
4. Pass `ai/hooks/pre-completion-gate.md`.

## Completion criteria

Claims are classified and evidence-backed; wording is precise and hype-free; DATP scope preserved; no
stale command/output name remains.

## Output

`AGENTS.md` final-report headings, plus claim classifications, evidence used, wording constraints, and
remaining reviewer risks.

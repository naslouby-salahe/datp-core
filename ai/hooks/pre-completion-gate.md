# Hook: pre-completion-gate

## Trigger

Before the final response. Cheap, deterministic checklist — checks this task's work, not the whole
repository.

## Pass conditions

- The per-change quality gate ran on the affected files (`ai/skills/quality-gate.md`) and passed, or
  each skipped check has a stated reason.
- Changes stayed inside the selected command's scope; no silent scope expansion; no release/tag/version
  work unless requested.
- No invented scientific value; scientific/output-affecting values trace to their single config owner.
- No backward-compatibility path was added (`ai/skills/no-backward-compatibility.md`).
- The diff is clean: only approved files, no temp/scratch/audit clutter (`ai/skills/code-hygiene.md`).
- The final report uses the exact five `AGENTS.md` headings, each with its own list, and claims no check
  that did not run.

## Failure behavior

Do not finalize until each condition holds or is reported as a blocker with its reason.

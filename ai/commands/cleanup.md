# Command: cleanup

## Use when

Structure, naming, stale-code, stale-comment, typing, or duplication cleanup inside approved scope.

## Permissions

May edit the listed targets and their direct callers/tests/docs/configs · run impacted tests · run the
quality gate. Must not restructure unrelated areas or commit.

## Required context

The exact cleanup targets and their allowed callers/tests/docs/configs.

## Contract

- **Scope:** the listed targets and direct references only.
- **Forbidden:** unrelated restructuring, migration scaffolding, legacy preservation, shims/redirects/
  aliases/wrappers-without-behavior, temp/audit clutter, release/tag/version work.
- **Scientific boundary:** cleanup must not change DATP semantics, threshold policy, metric/seed
  meaning, dataset role, claim strength, or stress-test status without approval.

## Procedure

1. Pass `ai/hooks/pre-edit-gate.md`.
2. Clean up applying `ai/skills/code-hygiene.md`, `ai/skills/typed-immutable-domain.md`,
   `ai/skills/architecture-and-dependencies.md`, and `ai/skills/no-backward-compatibility.md`.
3. Run impacted tests via `ai/skills/quality-gate.md` (explain skips when the change is docs-only).
4. Pass `ai/hooks/pre-completion-gate.md`.

## Completion criteria

Structure is cleaner, no compatibility artifacts remain, impacted tests pass or skips are justified.

## Output

`AGENTS.md` final-report headings, plus the cleanup performed and the compatibility check result.

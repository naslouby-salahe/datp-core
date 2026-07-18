# Command: audit

## Use when

Inspecting code, results, tables, figures, metrics, or provenance **without editing**.

## Permissions

May read files and run read-only checks. **Never edits, never creates files** (no audit report
artifacts). No long experiment runs unless explicitly approved.

## Required context

The exact files/artifacts to inspect and their cited evidence.

## Contract

- **Scope:** the listed files/artifacts only.
- **Forbidden:** any edit, temp file, generated artifact, cleanup change, or release/tag/version work.
- **Scientific boundary:** do not alter threshold semantics, datasets, seeds, metrics, model behavior,
  artifacts, or claim strength (an audit only reports; a later `implement`/`experiment` task fixes).

## Procedure

1. Confirm read-only scope.
2. Inspect, applying the relevant skills: `ai/skills/evidence-and-statistics.md`,
   `ai/skills/datp-scope-guard.md`, `ai/skills/scientific-config.md`,
   `ai/skills/architecture-and-dependencies.md`, `ai/skills/code-hygiene.md`,
   `ai/skills/no-backward-compatibility.md` as applicable.
3. Classify each finding as blocker, major, minor, or note, and cite evidence.

## Completion criteria

No files changed; findings are evidenced and severity-classified; required fixes are separated from
optional improvements; verdict is PASS, FAIL, or PARTIAL.

## Output

`AGENTS.md` final-report headings (Changed Files = `None`), plus audit scope, a no-edit confirmation,
findings by severity, required fixes, limitations, and verdict.

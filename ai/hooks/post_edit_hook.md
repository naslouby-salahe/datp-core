# Post Edit Hook

## Trigger
After file edits.

## Purpose
Audit the complete project for quality and scope, not only the files this task changed.

## Blocking status
Blocks completion.

## Required checks
- The entire repository is scanned, not only the current diff: a defect found anywhere counts, even in a file this task did not touch, even if the defect predates this task, even if another task or agent introduced it.
- Naming, structure, shims, wrappers, comments, docstrings, typing, defaults, boilerplate, docs drift, and temp clutter checked repository-wide.
- No numeric, string, regex, or formula literal is redeclared as a new named constant, under any name, when a named constant for that same value already exists anywhere in the repository; the fix is a reference to the single existing owner, never a second definition.
- No new scientific or execution value that could legitimately vary is introduced as a bare Python constant in `domain/` or `infrastructure/` without a matching schema field in `config/schemas/`, a mapper in `config/mapping/`, and a YAML file under `configs/`, unless the edit documents the specific roadmap or architecture section that locks it as a code-level invariant rather than a config-worthy value.
- DATP scientific meaning preserved.
- No unsupported claims added.

## Failure behavior
Fix an authority-grounded issue wherever it is found, in or out of the current diff, or report a blocker if fixing it would require an edit forbidden by the task contract. A pre-existing, out-of-scope, or previously-introduced defect is never dismissed for any of those reasons alone.

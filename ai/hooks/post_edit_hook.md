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
- DATP scientific meaning preserved.
- No unsupported claims added.

## Failure behavior
Fix an authority-grounded issue wherever it is found, in or out of the current diff, or report a blocker if fixing it would require an edit forbidden by the task contract. A pre-existing, out-of-scope, or previously-introduced defect is never dismissed for any of those reasons alone.

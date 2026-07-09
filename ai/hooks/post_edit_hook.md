# Post Edit Hook

## Trigger
After file edits.

## Purpose
Audit changed files for quality and scope.

## Blocking status
Blocks completion.

## Required checks
- Naming, structure, shims, wrappers, comments, docstrings, typing, defaults, boilerplate, docs drift, and temp clutter checked.
- DATP scientific meaning preserved.
- No unsupported claims added.

## Failure behavior
Fix issues in touched scope or report a blocker if fixing would require forbidden edits.

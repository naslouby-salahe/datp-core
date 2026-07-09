# Pre Edit Hook

## Trigger
Before any file edit.

## Purpose
Confirm the edit is allowed, scoped, and safe.

## Blocking status
Blocks edits.

## Required checks
- Repository path and status inspected.
- Source files and task contract read.
- Allowed files match the requested scope.
- Forbidden actions are avoided.
- No experiment, manuscript, data, model, result, or unrelated doc file will be touched without approval.

## Failure behavior
Stop before editing and report the scope conflict.

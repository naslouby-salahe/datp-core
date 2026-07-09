# Cleanup Hook

## Trigger
End of every task.

## Purpose
Prevent generated clutter and leftover artifacts.

## Blocking status
Blocks completion.

## Required checks
- No temp files.
- No scratch files.
- No generated audit reports unless explicitly requested.
- No random root files.
- No hidden tool-specific folders.
- No duplicate reports or agent leftovers.

## Failure behavior
Delete only task-created clutter inside approved scope or stop if deletion would be unsafe.

# Test Hook

## Trigger
After code changes or behavior-affecting config changes.

## Purpose
Run impacted tests and block failing behavior.

## Blocking status
Blocks completion when relevant tests fail or are skipped without reason.

## Required checks
- Impacted tests identified.
- Broader tests run only when shared behavior changed or the contract requires them.
- Skipped tests have a clear reason.

## Failure behavior
Fix failures in scope or report the failing command and blocker.

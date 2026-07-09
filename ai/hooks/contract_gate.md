# Contract Gate

## Trigger
Start of every task.

## Purpose
Require a written task contract before edits or audits.

## Blocking status
Blocks completion and blocks edits.

## Required checks
- Task, workflow, scope, forbidden actions, scientific boundaries, implementation rules, test plan, definition of done, audit checklist, and final report format are stated.
- Backward-compatibility position is explicit.
- Allowed and forbidden files are clear.

## Failure behavior
Stop before editing and report the missing contract fields.

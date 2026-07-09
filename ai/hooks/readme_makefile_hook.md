# README Makefile Hook

## Trigger
After command, config, output, workflow, or automation changes.

## Purpose
Keep user-facing commands and automation accurate.

## Blocking status
Blocks completion when touched behavior affects docs or automation.

## Required checks
- README commands, Makefile targets, config names, output paths, and documented workflows match current behavior.
- No old CLI flags, old config keys, or old output paths are documented.

## Failure behavior
Update the relevant docs or automation directly, or report why docs were out of scope.

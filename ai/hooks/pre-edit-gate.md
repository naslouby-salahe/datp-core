# Hook: pre-edit-gate

## Trigger

Before the first file edit of a task. Cheap, deterministic checklist — no repository scan, no
full-roadmap read.

## Pass conditions

- A command in `ai/commands/` is selected (or an inline contract with the same fields exists).
- Scope is explicit: the exact files/areas allowed to change, and forbidden actions are named.
- The command's permissions are confirmed (may it edit, run tests, run full checks, modify scientific
  config, commit).
- No experiment, manuscript, data, model, result, or unrelated file will be touched unless the command
  allows it.

## Failure behavior

Stop before editing and report the missing scope, permission, or command selection.

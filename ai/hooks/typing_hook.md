# Typing Hook

## Trigger
After code edits that affect protocol state, configs, metrics, or cross-module data.

## Purpose
Require explicit protocol state.

## Blocking status
Blocks completion for protocol-level issues.

## Required checks
- No raw protocol strings where Enum or Literal is appropriate.
- No raw protocol dicts where typed objects are clearer.
- No hidden defaults, mutable defaults, or unexplained broad defaults.

## Failure behavior
Replace loose state with explicit typed structures or report why the task scope prevents the fix.

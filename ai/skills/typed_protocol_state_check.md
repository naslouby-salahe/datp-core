# Typed Protocol State Check

## Purpose
Make protocol state explicit and validated.

## When to apply
Apply when protocol state crosses module boundaries or controls scientific behavior.

## Blocking rules
Block raw protocol strings, raw protocol dicts, hidden defaults, mutable defaults, vague names, stale names, and unvalidated optional fields.

## Pass criteria
Protocol state uses Enum, Literal, frozen dataclass-style objects, or equivalent typed structures where appropriate.

## Fail criteria
Protocol meaning depends on ad hoc strings, loosely shaped dicts, or implicit fallback behavior.

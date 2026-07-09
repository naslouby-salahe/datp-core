# Official Library Simplification Check

## Purpose
Prefer standard or official library behavior when it clearly simplifies custom code.

## When to apply
Apply after implementation or cleanup that adds parsing, validation, data handling, statistics, formatting, or CLI behavior.

## Blocking rules
Block obvious custom boilerplate that is less clear than a standard or official library and has no justification.

## Pass criteria
Custom code is simpler than the available library path or a clear reason is reported.

## Fail criteria
The implementation keeps avoidable, fragile boilerplate that an official library would remove.

# Avoid Raw Dict Defaults Check

## Purpose
Prevent hidden protocol behavior.

## When to apply
Apply when adding or editing structured settings, defaults, config parsing, or cross-module data.

## Blocking rules
Block raw protocol dicts, mutable defaults, hidden defaults, unexplained defaults, unclear optional parameters, silent fallback for stale values, and duplicate authority — the same named constant or literal value independently redeclared in 2 or more files instead of one file owning it and the others importing it.

## Pass criteria
Structured data has explicit fields, clear defaults, validation, and typed ownership. Every constant or literal value has exactly one named owning declaration; every other module imports it rather than re-literaling it.

## Fail criteria
Behavior is controlled by loose dicts, broad defaults, or missing validation. A constant or literal value is redeclared under the same or a different name in 2 or more files with no single imported owner.

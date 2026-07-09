# Avoid Raw Dict Defaults Check

## Purpose
Prevent hidden protocol behavior.

## When to apply
Apply when adding or editing structured settings, defaults, config parsing, or cross-module data.

## Blocking rules
Block raw protocol dicts, mutable defaults, hidden defaults, unexplained defaults, unclear optional parameters, and silent fallback for stale values.

## Pass criteria
Structured data has explicit fields, clear defaults, validation, and typed ownership.

## Fail criteria
Behavior is controlled by loose dicts, broad defaults, or missing validation.

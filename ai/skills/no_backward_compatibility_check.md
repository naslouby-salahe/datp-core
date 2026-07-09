# No Backward Compatibility Check

## Purpose
Enforce clean replacement over compatibility preservation.

## When to apply
Apply after renames, restructures, API changes, config changes, CLI changes, output-layout changes, or docs updates.

## Blocking rules
Block old aliases, legacy APIs, deprecated APIs, old config keys, old CLI flags, old output names, redirect modules, shims, fake compatibility, compatibility wrappers, migration scaffolding, dual old/new behavior, and silent fallback for stale values.

## Pass criteria
Callers, tests, docs, configs, and outputs are updated directly to the current name or behavior.

## Fail criteria
Any compatibility path remains alive without explicit contract approval.

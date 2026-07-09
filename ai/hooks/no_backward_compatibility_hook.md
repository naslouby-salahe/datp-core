# No Backward Compatibility Hook

## Trigger
After any rename, restructure, API change, config change, CLI change, output-layout change, or documentation update that could preserve stale behavior.

## Purpose
Enforce clean replacement.

## Blocking status
Blocks completion.

## Required checks
- No legacy aliases.
- No deprecated APIs.
- No old CLI flags.
- No old config keys.
- No old output names.
- No redirect modules.
- No shims.
- No compatibility wrappers.
- No migration scaffolding.
- No dual old/new behavior.
- No silent fallback for stale values.
- Callers, tests, docs, configs, and outputs use the current names directly.

## Failure behavior
Remove the compatibility path and update direct callers. If the task contract explicitly permits compatibility, report the exception, reason, tests, and removal condition.

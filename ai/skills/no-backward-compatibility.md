# Skill: no-backward-compatibility

## Trigger

Any rename, restructure, API change, config change, CLI change, output-layout change, or file move.

## Checks

- No legacy aliases, deprecated APIs, old CLI flags, old config keys, or old output names.
- No redirect modules, shims, fake compatibility layers, pass-through/alias wrappers, wrapper classes
  without behavior, or migration scaffolding.
- No dual old/new behavior and no silent fallback for stale values.
- Callers, tests, docs, configs, and outputs are updated directly to the current name or behavior.

## Fail conditions

Any compatibility path remains alive. A file or class exists only to preserve an old path, name, or
behavior.

## On failure

Remove the compatibility path and update direct callers. If a task contract explicitly permits
compatibility, report the exception, its reason, and its removal condition.

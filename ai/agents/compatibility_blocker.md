# Compatibility Blocker

## Purpose
Enforce the default clean-break policy.

## Responsibilities
- Reject old APIs, aliases, redirects, shims, deprecated paths, legacy configs, legacy CLI flags, and legacy output names.
- Require direct updates to callers, tests, docs, configs, and outputs.

## Must Block
- Compatibility aliases.
- Deprecated APIs.
- Silent fallback for stale values.
- Dual old/new behavior.
- Migration scaffolding.

## Must Not Do
- Add compatibility layers.
- Preserve legacy names for convenience.
- Approve wrappers that only hide changed structure.

## Required Checks
- No-backward-compatibility hook.
- No redirect/shim/wrapper check.
- Naming hook.

## Final-Report Expectations
Use the `AGENTS.md` final report format with Markdown headings and bullet lists. State that no backward-compatibility artifacts were added or preserved in touched scope.

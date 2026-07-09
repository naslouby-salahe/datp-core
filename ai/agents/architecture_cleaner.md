# Architecture Cleaner

## Purpose
Keep repository structure direct, owned, and uncluttered.

## Responsibilities
- Remove duplicate ownership in touched scope.
- Prefer direct modules and explicit locations.
- Block redirects, shims, fake compatibility, and wrappers without behavior.

## Must Block
- Redirect modules.
- Shim layers.
- Compatibility wrappers.
- Wrapper classes without real behavior.
- Temp files, audit clutter, and random root files.

## Must Not Do
- Create migration scaffolding.
- Add hidden tool-specific folders.
- Restructure unrelated areas.

## Required Checks
- Structure hook.
- No redirect/shim/wrapper check.
- Cleanup hook.

## Final-Report Expectations
Report structural changes, clutter removed, and any remaining ownership risk.

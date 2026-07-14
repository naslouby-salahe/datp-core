# Dependency Hook

## Trigger
After implementation or cleanup.

## Purpose
Enforce layer-dependency direction and check whether official or standard libraries can simplify custom code.

## Blocking status
Blocks completion for a dependency-direction violation; blocks obvious avoidable boilerplate.

## Required checks
- Import-linter and pytest-archon both pass for every touched file; any forbidden layer-dependency edge (a violation of the layer dependency diagram, including a framework import outside its confined layer) blocks completion outright, whether direct or routed through an intermediate module.
- Custom parsing, validation, statistics, formatting, and CLI code reviewed for simpler official-library paths.
- New dependencies are not added without contract approval; a new dependency is checked against the accepted/rejected library tables before it is added.

## Failure behavior
For a dependency-direction violation: fix the import to respect the layer diagram, or report a blocker if the required direction does not exist in the diagram — never add a contract exception silently. For avoidable boilerplate: use the clearer existing library path or report why custom code is required.

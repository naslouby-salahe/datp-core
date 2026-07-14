# Dependency Direction Check

## Purpose
Keep every import inside its layer's allowed direction.

## When to apply
Apply whenever a new import statement is added anywhere under `src/datp_core`.

## Blocking rules
Block an import that runs against the layer dependency diagram (for example `domain` importing `infrastructure`, or `application` importing a framework directly), and an import routed through an intermediate module solely to bypass a direct-import restriction.

## Pass criteria
Import-linter and pytest-archon both pass for the touched files, and every new import matches an edge that actually exists in the layer dependency diagram.

## Fail criteria
A new import creates a forbidden edge, whether direct or routed through an intermediate module.

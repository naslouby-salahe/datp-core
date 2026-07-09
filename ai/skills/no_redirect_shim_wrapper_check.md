# No Redirect Shim Wrapper Check

## Purpose
Remove fake structure and pass-through compatibility.

## When to apply
Apply after file moves, module splits, API changes, simplification, or cleanup work.

## Blocking rules
Block redirect modules, shims, fake compatibility layers, alias wrappers, pass-through wrappers, wrapper classes without behavior, and migration scaffolding.

## Pass criteria
Ownership is direct and callers use the real implementation location.

## Fail criteria
Files or classes exist only to preserve old paths, old names, or old behavior.

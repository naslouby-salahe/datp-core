# Structure Hook

## Trigger
After edits and before final report.

## Purpose
Keep repository structure clean, owned, and free of forbidden generic modules.

## Blocking status
Blocks completion.

## Required checks
- No module anywhere under `src/datp_core` is named `utils.py`, `common.py`, `base.py`, `misc.py`, `helpers.py`, `manager.py`, `handler.py`, `processor.py`, `context.py`, `payload.py`, or `shared.py`.
- No ugly folders, duplicated modules, redirect files, shim layers, fake compatibility, random root files, hidden agent folders, temp files, or unclear module boundaries.
- A module carries a roughly five-hundred-line soft cap: a warning to split an incohesive module, never permission to keep one, and never a reason to split a cohesive one merely to satisfy a line count.
- Approved layer layout is preserved (dependency direction, enforced separately by the dependency hook).

## Failure behavior
Remove clutter or rename/split the offending module, or stop if the fix would require an edit forbidden by the task contract.

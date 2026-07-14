# README Makefile Hook

## Trigger
After command, config, output, workflow, or automation changes, and before final report on any task (as the repository-wide stale-documentation check).

## Purpose
Keep user-facing commands and automation accurate, and serve as the repository-wide stale-documentation enforcement mechanism.

## Blocking status
Blocks completion.

## Required checks
- README commands, Makefile targets, config names, output paths, and documented workflows match current behavior.
- No old CLI flags, old config keys, or old output paths are documented.
- No stale documentation, stale path, or stale package name anywhere in the repository.
- No retired identifier referenced as if still current.
- No reference to a file that no longer exists.
- No two tracked documents contradict each other about the same fact.
- No inaccurate docstring, and no comment that no longer matches the behavior it describes.
- No copied AI-style explanation, banner comment, separator comment, or verbose narrative comment.
- No misleading status claim (a document must not claim something is done, checked, or passing when it is not).
- No duplicated documentation maintained in two places that can drift apart.
- No undocumented behavior change (a behavior change without a corresponding documentation update).
- No claimed check reported as run when it was not actually run.

## Failure behavior
Update the relevant docs or automation directly, or report why docs were out of scope. A stale or contradictory document is corrected, never left in place because it predates the current task.

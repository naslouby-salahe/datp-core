# CodeScene Quality Check

## Purpose
Keep code health stable or improving; block a change that introduces or worsens a hotspot.

## When to apply
Apply after any edit to a file under `src/datp_core` or `tests/`, before final report.

## Blocking rules
Block a delta analysis reporting any new or worsened Code Health finding; block a function or file crossing from a healthy tier into a warned or problematic tier; block a `.codescene/code-health-rules.json` threshold change that loosens a rule without a recorded reason.

## Pass criteria
`cs delta --error-on-warnings` exits `0` with no finding reported, and the exit reflects a genuinely completed analysis (not a skipped run reported as if it were clean).

## Fail criteria
A new hotspot, a worsened health tier, or a run that could not actually execute (for example because no access token was configured) and was not reported as a blocker.

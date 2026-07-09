# Final Report Hook

## Trigger
Before final response.

## Purpose
Verify completion is reported with evidence.

## Blocking status
Blocks final response.

## Required checks
- Contract completion verified.
- Final response uses Markdown headings and bullet lists.
- Required headings are present: Changed Files, Checks Run, Cleanup Result, Remaining Risks, and Skipped Checks.
- Changed files are listed with reasons.
- Tests and checks are listed accurately.
- Cleanup result is stated.
- Remaining risks and skipped checks are reported with reasons or `None`.

## Failure behavior
Do not finalize until the report follows the required Markdown structure, includes the required facts, and no claimed check is fabricated.

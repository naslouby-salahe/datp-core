# Final Report Hook

## Trigger
Before final response.

## Purpose
Verify completion is reported with evidence, under the exact required headings.

## Blocking status
Blocks final response.

## Required checks
- Contract completion verified.
- Final response uses Markdown headings and bullet lists.
- All five required headings are present as literal Markdown headings, in this exact wording, each with its own bullet list: **Changed Files**, **Checks Run**, **Cleanup Result**, **Remaining Risks**, **Skipped Checks**. Stating "no remaining risks" as free text elsewhere in the report, without the `Remaining Risks` heading itself present, does not satisfy this check — the heading must exist even when its answer is `None`.
- Changed files are listed with reasons.
- Tests and checks are listed accurately.
- Cleanup result is stated under its own heading.
- Remaining risks and skipped checks are each reported under their own heading, with a reason per item or the literal word `None` when there are none.

## Failure behavior
Do not finalize until all five headings are literally present in the required wording, the report includes the required facts under each, and no claimed check is fabricated.

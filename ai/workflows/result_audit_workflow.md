# Result Audit Workflow

## Use when
Use for tables, metrics, figures, summaries, and result interpretation.

## Required gates
`contract_gate`, `pre_edit_hook`, statistics audit, `statistics_hook`, `claim_evidence_hook`, `post_edit_hook`, `no_backward_compatibility_hook`, `reviewer_attack_check`, `cleanup_hook`, `final_report_hook`.

## Completion requirements
The edit is in-scope and approved before it starts, and audited for quality/scope after it lands. Metric direction, seed pairing, confidence interval interpretation, weak/null wording, claim evidence, and safe wording all pass. No stale output name or other backward-compatibility artifact remains in the edited summary.

## Final report requirements
Use the `AGENTS.md` final report format with Markdown headings and bullet lists. Include inspected files or artifacts, findings by severity, evidence, checks run, cleanup status, skipped checks, and verdict.

# Audit Only Workflow

## Use when
Use when no files should be changed.

## Required gates
`contract_gate`, read-only scope check, audit execution, `claim_evidence_hook` when relevant, `statistics_hook` when relevant, `final_report_hook`.

## Completion requirements
Edits are forbidden. No files change. Findings are classified by severity, each finding cites inspected evidence, required fixes are separated from optional improvements, and verdict is PASS, FAIL, or PARTIAL.

## Final report requirements
Report audit scope, files inspected, no-edit confirmation, findings, required fixes, checks run, limitations, skipped checks, and final verdict.

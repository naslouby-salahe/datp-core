# Experiment Workflow

## Use when
Use for configs, runners, outputs, seeds, metrics, artifact provenance, and experiment readiness.

## Required gates
`contract_gate`, `pre_edit_hook`, DATP protocol check, `experiment_readiness_check`, `statistics_hook`, artifact provenance check, `no_backward_compatibility_hook`, `post_edit_hook`, `test_hook`, `cleanup_hook`, `final_report_hook`.

## Completion requirements
Protocol scope, dataset role, client definition, seed list, metric direction, config completeness, output layout, artifact provenance, no-backward-compatibility, tests, cleanup, and claim boundary all pass.

## Final report requirements
Use the `AGENTS.md` final report format with Markdown headings and bullet lists. Include dataset, clients, seeds, metrics, outputs, provenance, checks, tests or skipped tests, cleanup, and risks.

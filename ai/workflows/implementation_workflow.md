# Implementation Workflow

## Use when
Use for code changes.

## Required gates
`contract_gate`, `pre_edit_hook`, implementation, `post_edit_hook`, `no_backward_compatibility_hook`, `naming_hook`, `typing_hook`, `comment_hook`, `dependency_hook`, `structure_hook`, `test_hook`, `cleanup_hook`, `final_report_hook`.

## Completion requirements
Scope is respected, impacted tests pass, relevant lint/type checks pass or are reported, no compatibility artifacts exist, names are clear, protocol state is typed where relevant, comments are current, structure is clean, and no clutter remains.

## Final report requirements
Use the `AGENTS.md` final report format with Markdown headings and bullet lists. Include changed files, checks run, tests, cleanup result, remaining risks, and skipped checks with reasons.

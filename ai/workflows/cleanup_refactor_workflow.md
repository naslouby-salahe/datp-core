# Cleanup Refactor Workflow

## Use when
Use for structure cleanup, naming cleanup, stale-code removal, stale-comment cleanup, typing cleanup, or simplification.

## Required gates
`contract_gate`, `pre_edit_hook`, `structure_hook`, `naming_hook`, `typing_hook`, `comment_hook`, `dependency_hook`, `no_backward_compatibility_hook`, `test_hook`, `cleanup_hook`, `final_report_hook`.

## Completion requirements
No compatibility shims, redirects, deprecated aliases, legacy wrappers, duplicate modules, stale comments, unclear names, temp files, or root clutter remain in touched scope. Impacted tests pass or are justified when no code changed.

## Final report requirements
Use the `AGENTS.md` final report format with Markdown headings and bullet lists. Include changed files, cleanup performed, compatibility check result, tests or skipped tests, remaining risks, and skipped checks with reasons.

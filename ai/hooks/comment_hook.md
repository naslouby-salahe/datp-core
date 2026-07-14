# Comment Hook

## Trigger
After edits to code, tests, configs, examples, prose, or docs.

## Purpose
Keep comments and docstrings accurate, useful, and free of planning-document origin references.

## Blocking status
Blocks completion.

## Required checks
- No stale comments.
- No stale docstrings.
- No AI-generated comments.
- No banner comments.
- No decorative comments.
- No misleading or bloated explanations.
- No occurrence, anywhere in source code, tests, runtime configuration, exception messages, logs, names, comments, or docstrings (planning Markdown under `docs/` is exempt, and this rule's own definition here is exempt), of a ticket identifier matching the pattern `P[0-9]+-T[0-9]+`, or the literal strings `MASTER_TICKET_LOG`, `TICKET_STATUS`, `DATP Core Architecture`, `Journal_Extension_Master_Roadmap`, or `docs/tickets`, or the phrases "implemented for ticket," "required by the roadmap," or "required by the architecture." A comment or docstring must state the actual engineering rule being enforced, never its planning-document origin — including when that reference is disguised inside a `# type: ignore`/`# noqa`/`# pyright: ignore` suppression comment.

## Failure behavior
Remove or correct bad comments, or rewrite a planning-document reference to state the actual rule directly, in touched scope.

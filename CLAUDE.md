# CLAUDE.md

Read `AGENTS.md` first — it is the single source of governance.
Use `ai/` for detailed procedures: `ai/commands/` (task workflows), `ai/skills/` (checks),
`ai/agents/` (roles), `ai/hooks/` (gates).

Claude-specific: subagents are registered in `.claude/agents/`, slash-commands in `.claude/commands/`;
both are thin pointers to `ai/`. Do not duplicate policy in `.claude/`.

Every final response follows the final-report format in `AGENTS.md`.

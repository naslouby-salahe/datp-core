# AI operating system — DATP Core

`ai/` is the source of truth for AI governance. `AGENTS.md` (repo root) is the auto-loaded entry
point and holds the non-negotiable rules; everything here is read on demand. Tool adapters
(`.github/`, `.claude/`, `.agents/`) are thin pointers and never copy policy.

## Layout

- `agents/` — five roles with distinct permissions: `implementation-engineer`, `auditor` (read-only),
  `experiment-engineer`, `manuscript-editor`, `orchestrator`.
- `commands/` — five complete task workflows, each with an embedded contract (scope, permissions,
  forbidden actions, done criteria): `implement`, `audit`, `experiment`, `manuscript`, `cleanup`.
- `skills/` — reusable deterministic checks referenced by commands and agents.
- `hooks/` — two cheap gates: `pre-edit-gate`, `pre-completion-gate`.

## Lifecycle

1. Select a command and confirm scope (`hooks/pre-edit-gate.md`).
2. Work within scope, applying the relevant `skills/`.
3. Run the per-change quality gate (`skills/quality-gate.md`).
4. Pass `hooks/pre-completion-gate.md`.
5. Report using the `AGENTS.md` final-report format.

## Skills index

- `quality-gate.md` — per-change vs checkpoint commands (the one quality workflow).
- `datp-scope-guard.md` — scientific scope, threshold semantics, stress-test boundary.
- `evidence-and-statistics.md` — claim↔evidence mapping, confirmatory endpoint, statistics, reviewer risk.
- `scientific-config.md` — validated-config ownership, no invented values, seeds, no leakage, fixed batches.
- `cuda-safety.md` — serialized deterministic CUDA, no auto batch reduction, no silent CPU fallback.
- `no-backward-compatibility.md` — clean-break replacement.
- `typed-immutable-domain.md` — typed protocol state, immutable domain, artifact identity and reuse.
- `architecture-and-dependencies.md` — layer direction, framework confinement, dependency policy.
- `code-hygiene.md` — naming, comments, structure, tests, diff cleanliness.

A separate agent, skill, command, or hook exists only when it has a distinct, repeated purpose.
Merge or delete anything that duplicates another file.

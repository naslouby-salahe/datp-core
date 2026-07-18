# AGENTS.md — DATP Core

Entry point for every AI agent. This is the only governance file loaded automatically.
`ai/` is the source of truth for detailed procedures; read from it on demand, never copy it here.

## Project identity

DATP Core is a **fixed-encoder, fixed-federated-model, threshold-calibration-scope study**.
A shared FedAvg autoencoder is trained once per seed and frozen; only the *scope* at which the
anomaly threshold is calibrated varies across the ladder B1 (shared), B2 (per-client),
B3 (family), B4 (cluster). The causal question is whether calibration scope changes per-client
FPR dispersion — not model quality. The full scientific definition lives in
`docs/Journal_Extension_Master_Roadmap.md`; system design lives in `docs/Architecture/`.

## Non-negotiable rules

- **Never invent a scientific value.** A missing scientific or execution value is a blocker, not a guess.
- **Scientific and output-affecting settings come from validated configuration** (`config/schemas/` → `config/mapping/` → `configs/`), with exactly one canonical owner per value.
- **Do not change scientific behavior** (threshold semantics, dataset role, seeds, metrics, model behavior, artifact meaning, claim strength) without checking the roadmap and getting explicit task approval.
- **No backward compatibility.** No aliases, redirects, shims, fake compatibility, deprecated APIs, legacy config keys, legacy CLI flags, or legacy output names. Update callers, tests, docs, configs, and outputs directly.
- **Do not reduce batch/chunk sizes automatically** under memory pressure, and **do not silently fall back from required CUDA execution** to CPU. A CUDA OOM terminates the current attempt.
- **No calibration/test leakage.** Calibration is benign-only; attack and test-split data never fit or tune a threshold.
- **Do not expand task scope silently.** Stay inside the selected command's scope. No release, tag, or versioning work unless explicitly requested.
- **Run impacted tests for every change; run full quality checks only at checkpoints** (see `ai/skills/quality-gate.md`).
- **Report exact files changed and validations run** using the final-report format below.

## Choose a command, then read only what it needs

Pick the matching command in `ai/commands/`; it states permissions, scope, procedure, and done criteria.

| Task | Command | Also read |
| --- | --- | --- |
| Change code/behavior | `ai/commands/implement.md` | `ai/skills/` for touched areas |
| Inspect without editing | `ai/commands/audit.md` (read-only) | `ai/skills/evidence-and-statistics.md` |
| Configs, runners, seeds, artifacts | `ai/commands/experiment.md` | roadmap; `ai/skills/scientific-config.md` |
| Paper / README / prose | `ai/commands/manuscript.md` | `ai/skills/evidence-and-statistics.md` |
| Structure/naming/stale cleanup | `ai/commands/cleanup.md` | `ai/skills/code-hygiene.md` |

Read the roadmap or architecture docs **only when the task touches scientific meaning, protocol, or
layer design** — not for every change. If no command fits, define an explicit contract inline using
the field set in `ai/commands/implement.md`.

## Standard workflow

1. Select the command and confirm scope, permissions, and forbidden actions (`ai/hooks/pre-edit-gate.md`).
2. Do the work within scope, using the relevant `ai/skills/` as checks.
3. Run the per-change quality gate on affected files (`ai/skills/quality-gate.md`).
4. Pass `ai/hooks/pre-completion-gate.md`.
5. Write the final report.

## Testing and quality

- Per change: format + lint + type-check the affected files, run impacted tests (twice in different orders for order-independence), and run affected architecture/scientific invariant tests.
- Checkpoint: full lint, type-check, tests, and architecture/config validation.
- Exact commands live in `ai/skills/quality-gate.md`. Sonar and CodeScene run in CI on push.

## AI structure

- `ai/README.md` — index and lifecycle.
- `ai/agents/` — five roles (implementation, audit, experiment, manuscript, orchestrator).
- `ai/skills/` — reusable deterministic checks.
- `ai/commands/` — complete task workflows with embedded contracts.
- `ai/hooks/` — two cheap gates (pre-edit, pre-completion).

Tool adapters (`.github/`, `.claude/`, `.agents/`) are thin pointers to `ai/` and must not duplicate policy.

## Final report format

Every final report uses Markdown headings and bullet lists, with these exact headings, each with its
own list (use `None` when empty): **Changed Files**, **Checks Run**, **Cleanup Result**,
**Remaining Risks**, **Skipped Checks**. Do not claim a check ran unless it did.

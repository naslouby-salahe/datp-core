# Repository AI Entry Point

Every AI agent must read this file first, then read `ai/README.md` and the relevant files under `ai/`.

## Repository AI Rules

- Keep the repository small, explicit, typed, and clean.
- Preserve DATP journal-extension scope: fixed encoder, fixed federated model, threshold-calibration-scope study, B1-B4 vary threshold scope, same trained model and score artifacts preserved.
- Keep stress tests and comparators supportive. They do not replace the B1-B4 causal ladder.
- Block drift into poisoning, Dynamic DATP, privacy guarantees, deployment profiling, backdoor, evasion, full drift detection, generic FL-IDS expansion, release work, tag work, or versioning work unless explicitly requested as future-work wording.
- Do not touch experiment logic, scientific code, model code, result artifacts, manuscript content, datasets, or unrelated documentation unless the task contract allows it.

## Mandatory Workflow Lifecycle

1. Intake
2. Contract
3. Pre-edit gate
4. Implementation or audit
5. Post-edit gate
6. No-backward-compatibility gate
7. Impacted tests
8. Structure/comment/typing/dependency gates
9. Cleanup
10. Final report

## No-Backward-Compatibility Policy

No backward compatibility by default. No old aliases, redirects, shims, fake compatibility, deprecated APIs, legacy config keys, legacy CLI flags, or legacy output names. Update callers, tests, docs, configs, and outputs directly.

## Universal Blocker Checklist

Block completion for stale comments or docstrings, AI-generated comments, banner comments, decorative comments, weird names, vague names, stale names, raw protocol strings, raw protocol dicts, hidden defaults, mutable defaults, redirect modules, shims, fake compatibility, compatibility aliases, wrapper classes without behavior, temp files, audit clutter, unsupported claims, DATP scope drift, or failing impacted tests.

## Final Report Format

Every final report must use Markdown headings and bullet lists.

Required headings:
- Changed Files
- Checks Run
- Cleanup Result
- Remaining Risks
- Skipped Checks

Each changed file, check, risk, and skipped check must be listed as a bullet with a reason or status. Use `None` when a required heading has no items. Do not claim checks ran unless they did.

## AI Operating Structure

- `ai/README.md`: operating overview and lifecycle.
- `ai/agents/`: agent roles and blocker responsibilities.
- `ai/skills/`: reusable checks and pass/fail criteria.
- `ai/hooks/`: mandatory gates and failure behavior.
- `ai/contracts/`: task contract templates.
- `ai/workflows/`: workflow-specific gate order and completion rules.

## Native Adapter Policy

- `ai/` is the single source of truth for governance.
- Tool-specific folders are thin adapters only and must point back to `AGENTS.md` and `ai/`.
- Adapters must not duplicate full governance content or become a second source of truth.
- Hooks under `ai/hooks/` are checklist gates.
- Contracts under `ai/contracts/` are mandatory before work starts.
- Workflows under `ai/workflows/` define approved task paths.
- Allowed native adapter folders are `.github/`, `.claude/`, `.agents/`, and `.codex/`.
- No backward compatibility remains the default.

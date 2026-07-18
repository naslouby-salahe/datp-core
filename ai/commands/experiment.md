# Command: experiment

## Use when

Preparing, validating, or changing experiment configs, runners, seeds, metrics, outputs, or provenance.

## Permissions

May edit experiment configs/runners/output definitions in scope · modify scientific configuration when
the task approves it and the roadmap allows · run config validation and impacted tests. May run
experiments **only after readiness passes and only when explicitly approved**. Must not commit.

## Required context

The experiment configuration under `configs/`, the current artifact catalogue, and the roadmap section
defining the experiment. Do not invent any missing value.

## Contract

- **Scope:** the listed experiment files/configs/output definitions/docs.
- **Forbidden:** long runs without approval, model-code drift, result-artifact edits unless approved,
  legacy config keys / old output names, temp/audit clutter, release/tag/version work.
- **Scientific boundary:** preserve fixed encoder, fixed federated model, B1–B4 threshold-scope design,
  dataset role, client definition, seed meaning, metric direction, and artifact provenance.

## Procedure

1. Pass `ai/hooks/pre-edit-gate.md`.
2. Apply `ai/skills/datp-scope-guard.md` and `ai/skills/scientific-config.md` (values, seeds, single
   owner, no leakage, fixed batches); for training/GPU, `ai/skills/cuda-safety.md`.
3. Confirm readiness: dataset role, clients, seeds, config completeness, output layout, metric
   direction, and artifact provenance are explicit and current.
4. Apply `ai/skills/evidence-and-statistics.md` to any reported metric, and
   `ai/skills/no-backward-compatibility.md`.
5. Run `ai/skills/quality-gate.md` (include config validation); pass `ai/hooks/pre-completion-gate.md`.

## Completion criteria

Dataset, clients, seeds, metrics, configs, outputs, and provenance are explicit; readiness passes; no
compatibility artifacts; tests pass; claim boundary holds.

## Output

`AGENTS.md` final-report headings, plus dataset, clients, seeds, metrics, outputs, and provenance.

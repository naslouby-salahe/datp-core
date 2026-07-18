# Agent: experiment-engineer

## Purpose

Prepare and validate experiment configuration, execution paths, seeds, metrics, outputs, and artifact
provenance for the fixed-model threshold-scope study, including FedAvg/FedProx training and CUDA
determinism.

## Use when

A task touches configs, runners, seeds, metrics, outputs, provenance, or experiment readiness. Follows
`ai/commands/experiment.md`.

## Required context

The experiment configuration under `configs/`, the current artifact catalogue, and the roadmap section
defining the experiment. Never invent a missing value.

## Procedure

1. `ai/hooks/pre-edit-gate.md`.
2. `ai/skills/datp-scope-guard.md` and `ai/skills/scientific-config.md` (values, seeds, single owner,
   no calibration/test leakage, fixed batch/chunk profiles); `ai/skills/cuda-safety.md` for training.
3. Verify readiness (dataset role, clients, seeds, config completeness, output layout, metric
   direction, provenance) and apply `ai/skills/evidence-and-statistics.md` to reported metrics.
4. `ai/skills/no-backward-compatibility.md`, then `ai/skills/quality-gate.md` and
   `ai/hooks/pre-completion-gate.md`.

## Forbidden actions

Running long experiments without explicit approval, retraining the fixed encoder outside an approved
phase, changing aggregation/training semantics silently, auto-reducing batch size, reusing a checkpoint
under a changed execution profile, or preserving legacy config keys / output names.

## Completion criteria

Readiness passes; dataset, clients, seeds, metrics, configs, outputs, and provenance are explicit and
current; no compatibility artifacts; tests pass; claim boundary holds.

## Output

`AGENTS.md` final-report headings, plus dataset, clients, seeds, metrics, outputs, and provenance. If a
run is requested outside an approved phase, escalate to `orchestrator`.

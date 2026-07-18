# Skill: code-hygiene

## Trigger

After any file-changing task, before the final report.

## Checks

- **Naming.** Names are direct, current, and single-concept. No class named the bare word `Data`,
  `Config`, `Result`, `Manager`, `Context`, `Payload`, `Handler`, or `Processor` (name results per
  operation, e.g. `PolicyEvaluationResult`). A schema type is `<Section>Config`; the spec it maps to is
  `<Concept>Spec`. A test module is `test_<behavior>.py`. No old name kept as an alias.
- **Structure.** No module under `src/datp_core` named `utils.py`, `common.py`, `base.py`, `misc.py`,
  `helpers.py`, `manager.py`, `handler.py`, `processor.py`, `context.py`, `payload.py`, or `shared.py`.
  A ~500-line module is a soft signal to split an incohesive module, never a reason to split a cohesive
  one. No duplicated module, redirect, shim, or random root file.
- **Comments and docs.** No stale, AI-generated, banner, decorative, misleading, or bloated comments;
  comments explain non-obvious intent and match current behavior. Do not add explanatory or citation
  comments above locked constants. Docs (README, configs, docstrings, tracked docs) match current
  behavior — no stale path, retired identifier, reference to a missing file, or contradicting statement.
- **Tests.** Tests cover behavior/metrics/configs/artifacts/regressions, not implementation detail or
  trivia; impacted tests are run, and skipped ones have a reason.
- **Diff.** Only approved files changed; no temp files, scratch files, audit clutter, generated junk,
  formatting churn, or unrelated edits. No hidden tool-specific folder outside the sanctioned adapters.

## Fail conditions

A forbidden module/class name is introduced, a comment is stale or generated, a doc is inaccurate, or
the working tree contains unrelated or generated clutter.

## On failure

Rename/split/remove within the approved scope, or stop if the fix needs an out-of-scope edit and report
it as a blocker.

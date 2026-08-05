# Phase 15 — Extension Readiness

## Authority

`docs/Journal_Extension_Master_Roadmap.md` remains the scientific authority. This phase strengthens future extension boundaries without adding current scientific behavior.

## Final ownership

Extension readiness is owned by:

- `src/datp_core/pipeline/preflight.py` for explicit rejection of undeclared future capabilities;
- `src/datp_core/orchestration/hooks.py` for immutable observation-only stage-boundary hooks;
- `src/datp_core/orchestration/resources.py` for typed Dagster resources;
- `tests/unit/pipeline/test_extension_boundaries.py` and `tests/unit/orchestration/test_extension_hooks.py` for behavior and immutability checks.

The deleted `datp_core.experiments` package, orchestration commands, and orchestration stages are not valid owners and must not return.

## Required boundaries

Typed observation points exist:

1. after reusable score generation and before calibration;
2. after calibration and before threshold construction;
3. after threshold construction and before evaluation;
4. after evaluation and before analysis.

Hook contexts and results are frozen. A hook may observe a scientific coordinate and artifact checksum only. It must preserve both exactly. Default hooks are identity operations.

## Prohibited behavior

DATP-Core does not implement:

- calibration poisoning or attack objectives;
- defenses or defense estimators;
- drift detectors, continuous adaptation, or online loops;
- privacy mechanisms;
- additional datasets;
- reflection-based registration, generic plugin discovery, service locators, or string-key dispatch;
- hooks that mutate clean scores, calibration data, thresholds, evaluations, analyses, coordinates, checksums, or completion state.

A future research implementation requires a separately approved scientific protocol and a distinct scientific coordinate. It may not alter current clean artifacts in place.

## Invariants

- Current benign-only calibration remains unchanged.
- Fixed-detector threshold comparisons remain unchanged.
- Anchor, evidence-role, capability, serialization, and publication gates remain mandatory.
- Hook failure prevents downstream completion and leaves existing clean artifacts intact.
- Enabling default hooks produces the same identities and checksums as omitting them.

## Verification

Required tests verify:

- default hooks are no-ops;
- frozen contexts cannot be mutated;
- coordinate or checksum changes are rejected;
- undeclared attacks, defenses, datasets, adaptive behavior, and threshold methods are rejected;
- no future research implementation is present in the current source tree.

## Completion record

Phase 15 is complete only when the typed boundaries above are implemented, current behavior is unchanged, relevant behavioral and architecture tests pass, and no future research behavior has entered DATP-Core.

Formatting, Ruff, Pyright, Pylint, SonarQube, CodeScene, GitHub Actions, and CI are outside this pull request's completion procedure and are not phase gates.

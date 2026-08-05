# Phase 15 — Extension Readiness

## Authority

`docs/Journal_Extension_Master_Roadmap.md` remains the scientific authority. This phase strengthens future extension boundaries without adding current scientific behavior.

## Final ownership

Extension readiness is owned by:

- `src/datp_core/pipeline/preflight.py` for explicit rejection of undeclared future capabilities;
- `src/datp_core/protocols/graph.py` for immutable observation-only scientific graph contracts;
- `src/datp_core/pipeline/execution.py` for invoking declared observation boundaries in the canonical execution path;
- `src/datp_core/orchestration/resources.py` for typed Dagster resources only;
- `tests/unit/pipeline/test_extension_boundaries.py` and `tests/unit/protocols/test_graph.py` for behavior and immutability checks.

Dagster adapters do not own scientific graph contracts. The deleted `datp_core.experiments` package, orchestration commands, orchestration stages, and orchestration-owned observation models are not valid owners and must not return.

## Required boundaries

Typed observation points exist:

1. after reusable score generation and before calibration;
2. after calibration and before threshold construction;
3. after threshold construction and before evaluation;
4. after evaluation and before analysis.

Hook contexts and results are frozen. A hook may observe a scientific coordinate and artifact checksum only. It must preserve both exactly. The identity hook and an omitted hook have identical behavior.

The observation contracts must be invoked by the canonical pipeline execution path before this phase can be declared complete. A disconnected contract exercised only by isolated unit tests is not implementation evidence.

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
- Enabling the identity hook produces the same identities and checksums as omitting it.
- Scientific observation contracts remain independent of Dagster and other runtime adapters.

## Verification

Required tests verify:

- identity hooks are no-ops;
- frozen contexts cannot be mutated;
- coordinate or checksum changes are rejected;
- every declared boundary is reached by the canonical execution path;
- undeclared attacks, defenses, datasets, adaptive behavior, and threshold methods are rejected;
- no future research implementation is present in the current source tree.

## Completion record

Phase 15 is complete only when the typed boundaries above are owned by the protocol graph, invoked by the canonical pipeline path, current behavior is unchanged, relevant behavioral and architecture tests pass, and no future research behavior has entered DATP-Core.

Formatting, Ruff, Pyright, Pylint, SonarQube, CodeScene, GitHub Actions, and CI are outside this pull request's completion procedure and are not phase gates.

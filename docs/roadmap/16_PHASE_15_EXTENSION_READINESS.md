# Phase 15 — Extension Readiness

**Status:** COMPLETE  
**Implementation date:** 2026-08-04  
**Governing source:** `docs/Journal_Extension_Master_Roadmap.md`

## 1. Scope

Phase 15 establishes observation-only graph boundaries for later calibration-channel attacks and defenses without implementing either extension.

The delivered boundaries must not alter:

- client training rows or labels;
- model weights, gradients, aggregation, or checkpoint selection;
- score generation or stored score artifacts;
- evaluation rows, labels, or score values;
- client eligibility or cohort membership;
- threshold methods or current journal claim scope.

## 2. Final ownership

- `src/datp_core/protocols/graph.py`: immutable observation boundary identities, contexts, hook protocol, default no-op behavior, and identity-preservation validation.
- `src/datp_core/pipeline/runner.py`: the canonical invocation owner for every boundary using checksums from real stage artifacts.
- `src/datp_core/pipeline/preflight.py`: rejection of undeclared attack or defense implementations.
- `src/datp_core/cli/run.py`: contains no extension flags or configuration overrides.
- `src/datp_core/orchestration/`: delegates to pipeline entry points and owns no extension logic.

Graph boundaries are protocol contracts because they define where scientific observation may occur. Dagster is only an execution adapter and must not own the boundaries.

## 3. Observation-only boundaries

The canonical execution path invokes four immutable boundaries:

1. after score generation and before calibration construction;
2. after calibration construction and before threshold construction;
3. after threshold construction and before evaluation;
4. after evaluation and before statistical analysis.

Each observation context carries:

- the closed boundary identity;
- the full immutable experiment coordinate;
- the checksum of the stage artifact entering the boundary.

A hook may observe that context only. The returned context must preserve the boundary, coordinate, and checksum exactly. Any attempted mutation raises a scientific contract error and prevents downstream completion.

The score-generation boundary is built from the fixed-score invariant, the calibration boundary from the eligible benign calibration score collection, the threshold boundary from the typed threshold result, and the evaluation boundary from the completed evaluation digest. These are real execution artifacts, not test-only placeholders.

## 4. Extension preflight

Attack and defense identities are not part of the current closed experiment enumeration. Preflight therefore rejects both extension kinds as undeclared. No extension output directory is created, and no current claim becomes attack- or defense-aware.

Current operational commands expose no attack, defense, poisoning, mutation, or extension mode flag.

## 5. Scientific safeguards

The extension seam is observation-only:

- fixed-detector identity remains unchanged;
- preprocessing, checkpoint, calibration rows, evaluation rows, labels, and score checksums remain unchanged;
- threshold policies remain the only current experimental intervention;
- attacks and defenses remain separate future experiments;
- current anchor, confirmatory, supportive, mechanism, external, temporal, and exploratory claim boundaries remain unchanged.

The boundary implementation contains no mutable dictionary contract, arbitrary callback payload, string-key dispatch, hidden global hook registry, compatibility wrapper, or alternate execution path.

## 6. Verification

Meaningful tests cover:

- stable no-hook behavior;
- rejection of coordinate mutation;
- rejection of checksum mutation;
- rejection of boundary mutation;
- canonical-runner wiring of every declared boundary;
- preflight rejection of undeclared attacks;
- preflight rejection of undeclared defenses;
- absence of extension flags in CLI and orchestration surfaces.

## 7. Completion record

Phase 15 is complete only when all four boundaries are immutable protocol-owned contracts, every boundary is invoked by the authoritative execution path with a real artifact checksum, undeclared attacks and defenses fail closed, adapters expose no extension override, and relevant behavioral, architecture, and scientific tests pass.

Formatting, Ruff, Pylance, Pyright, Pylint, Black, isort, Sonar, CodeScene, GitHub Actions, hosted CI, and external quality gates are outside this pull request's completion procedure.

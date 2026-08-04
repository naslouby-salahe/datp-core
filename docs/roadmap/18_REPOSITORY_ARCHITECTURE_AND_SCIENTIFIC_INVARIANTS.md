# Repository Architecture and Scientific-Invariant Refactor

## Authority and scope

This document records the cross-cutting repository refactor applied after the phase implementations. It changes ownership, module boundaries, publication mechanics, and regression enforcement. It does **not** change the scientific programme, experiment catalogue, datasets, numerical grids, metric definitions, checkpoint rule, threshold algorithms, or evidence tiers defined by `docs/Journal_Extension_Master_Roadmap.md`.

The refactor is intentionally incompatible with the previous internal module layout. No aliases, redirects, deprecated imports, or compatibility barrels are retained.

## Scientific invariants preserved

The refactor must preserve all of the following for every threshold-policy comparison within one training coordinate:

- one selected detector checksum;
- one preprocessing-state checksum;
- one split-manifest checksum;
- one calibration score-set checksum;
- one evaluation score-set checksum;
- one evaluation-label and source-row inventory;
- one client population and eligibility cohort;
- AUROC invariance over unchanged scores;
- benign-only calibration;
- fixed-terminal, non-test checkpoint selection;
- strict separation of the centralized reference from federated training, scoring, and thresholding.

Only threshold construction and assignment may vary across the core ladder.

## Implemented package boundaries

### Neutral pipeline infrastructure

`datp_core.pipeline` owns branch-neutral mechanics only:

- `pipeline/checkpoints/` — shared checkpoint file validation and neutral checkpoint records;
- `pipeline/scoring/` — score-frame extraction, construction, persistence validation, and generic score-artifact structure;
- `pipeline/publication/atomic.py` — single-directory locking, staging, replacement, cleanup, and reuse outcome;
- `pipeline/publication/codec.py` — typed `write`, `validate`, `load`, and `rebase` lifecycle;
- `pipeline/publication/related.py` — atomic publication of related directory sets with rollback.

The package may not import centralized, federated-scoring, thresholding, evaluation, analysis, reporting, orchestration, or CLI packages.

### Federated checkpoint bounded context

The former `learning/federated/checkpointing.py` monolith was deleted. Ownership is split into:

- `checkpoints/identities.py` — closed persisted asset and manifest identities;
- `checkpoints/documents.py` — strict persisted documents;
- `checkpoints/history.py` — training-history persistence and validation;
- `checkpoints/candidates.py` — candidate tensor naming, retention, validation, and rebasing;
- `checkpoints/selection.py` — fixed-terminal non-test selection and leakage guards;
- `checkpoints/publication.py` — branch-specific artifact writing;
- `checkpoints/reuse.py` — trusted persisted loading and provenance validation.

All production and test imports target the owning module directly. The deleted path cannot return.

### Publication ownership

Artifact publication follows one lifecycle:

1. `write` produces a complete artifact in a caller-owned staging location;
2. `validate` proves the artifact is reusable and scientifically compatible;
3. `load` reconstructs the typed persisted result;
4. `rebase` replaces staging paths with final paths after publication.

Centralized training, scoring, threshold construction, and evaluation use this lifecycle. Federated training and scoring use the same lifecycle. Population, split, analysis, and threshold-stage publication call the neutral atomic service directly or through a codec rather than through `artifacts.store`.

`artifacts.store` is now artifact-specific processed-data publication code. It does not re-export neutral atomic functions.

### Related Ditto publication

Ditto global and personalized model families form one related publication. Both directory trees are staged and validated before commit. The related-publication service commits them under one lock and restores prior destinations if a replacement fails. A completed global artifact cannot be accepted while the linked personalized artifact is absent or incompatible.

## Serialization boundary

`artifacts.serialization` is the sole canonical JSON implementation. It owns:

- recursive canonical value projection;
- deterministic canonical mappings;
- canonical JSON text;
- canonical checksums;
- strict JSON-model persistence;
- trusted estimator persistence and reload.

`domain.provenance` contains provenance records only. Direct `json.dumps`, `model_dump_json`, and duplicate canonical serializers outside the artifact boundary are forbidden.

Persisted JSON documents inherit `StrictModel`. Runtime objects carrying DataFrames, tensors, live estimators, or transient model state remain dataclasses and are not Pydantic persistence documents.

## Threshold-result structure

Shared threshold structure is represented explicitly without merging scientific payloads into a giant optional-field model. Common context and assignment contracts are reusable; shared, local, family, grouped, pooled, weighted, shrinkage, conformal, and federated-statistics results retain their method-specific evidence and validation.

## Enforced architecture regressions

Architecture tests must fail when any of the following returns:

- direct JSON serialization outside `artifacts.serialization`;
- the deleted federated checkpoint monolith or imports from it;
- neutral publication functions imported from `artifacts.store`;
- branch/application imports inside `pipeline`;
- `Any` in the neutral pipeline package;
- direct `BaseModel` inheritance outside `StrictModel`;
- persisted `*Document` classes not based on `StrictModel`;
- Pydantic documents containing runtime DataFrame or tensor payloads;
- duplicate import-linter configuration;
- opaque numbered threshold identities in implementation source.

Import-linter remains the repository-wide dependency-direction authority. The architecture tests complement it with AST-level ownership and serialization checks.

## Scientific regression tests

The fixed-detector scientific suite verifies that every threshold method reads identical:

- model checksum;
- calibration score-set checksum;
- evaluation score-set checksum;
- preprocessing checksum;
- split checksum;
- score files and row order;
- AUROC values.

Checkpoint tests verify that held-out metrics and attack labels cannot enter selection and that only `CheckpointProtocol.maximum_round` receives selected status.

## No-backward-compatibility decision

The following compatibility surfaces are intentionally absent:

- no `learning.federated.checkpointing` redirect;
- no re-export of neutral publication primitives from `artifacts.store`;
- no aliases for moved canonical serialization helpers;
- no deprecated threshold or population identifiers;
- no compatibility payload dictionaries;
- no fallback loaders for superseded artifact shapes.

Callers and tests were migrated to the owning modules instead.

## Unchanged unresolved scientific values

This refactor does not invent missing scientific decisions:

- the FedProx primary coefficient promotion rule remains unresolved; the complete declared grid is retained;
- the size-aware shrinkage function remains unresolved and returns typed unavailability;
- absent population-specific traffic-rate evidence continues to suppress alert-burden claims.

## Validation record

The PR contains focused unit, integration, scientific, and architecture coverage for the new boundaries. The implementation must not be marked accepted until the current PR head has run:

- Ruff format and lint;
- Pyright;
- Pylint;
- import-linter;
- architecture tests;
- impacted unit and integration tests;
- scientific invariant tests;
- the complete pytest suite.

At the time this record was added, no GitHub Actions run had been observed for the then-current PR head. Therefore this document records the implemented architecture, not a final green-CI claim.

## Acceptance criteria

The refactor is accepted only when:

- the deleted compatibility surfaces remain absent;
- all publication paths have one authoritative atomic owner;
- related Ditto artifacts pass rollback and reuse tests;
- direct serialization bypass count is zero;
- fixed-detector and checkpoint-leakage scientific tests pass;
- the complete suite and static-analysis gates pass on the final head;
- no scientific value, metric, cohort, score, threshold, or claim tier changes relative to the master roadmap.

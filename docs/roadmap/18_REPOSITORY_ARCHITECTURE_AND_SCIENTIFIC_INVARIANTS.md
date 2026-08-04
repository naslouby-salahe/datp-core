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
- `pipeline/coordinates.py` — branch-neutral pipeline coordinate mechanics shared by checkpoint, scoring, and publication services;
- `pipeline/scoring/` — score-frame extraction, construction, persistence validation, and generic score-artifact structure;
- `pipeline/publication/atomic.py` — single-directory and related-directory locking, staging, rollback, replacement, cleanup, and reuse outcomes;
- `pipeline/publication/codec.py` — typed single-directory and related-directory `write`, `validate`, `load`, `rebase`, and publication lifecycles;
- `pipeline/publication/reuse.py` — side-effect-free artifact-existence and completion-marker predicates.

The package may not import centralized, federated-scoring, thresholding, evaluation, analysis, reporting, orchestration, or CLI packages.

### Orchestration boundary

`datp_core.orchestration.commands` owns typed application requests and stage results. `datp_core.orchestration.stages` remains intentionally present because it is the composition layer named in the approved target tree.

A stage may:

- bind a typed command to an owning domain or pipeline service;
- select a publication codec;
- resolve runtime infrastructure such as the declared CUDA device;
- map a published domain result into a typed stage result.

A stage may not:

- implement training, scoring, threshold, metric, inference, dataset, population, or preprocessing algorithms;
- define persisted scientific documents;
- duplicate publication, reuse, checksum, frame-validation, checkpoint-selection, or threshold formulas;
- introduce scientific defaults or branch-specific compatibility behavior.

Therefore `orchestration/stages` does not duplicate `pipeline`: pipeline owns reusable mechanics, while stages own application composition. Any scientific or persistence logic found in a stage must be moved to its bounded-context owner.

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

### Analysis bounded contexts

The former `analysis/models.py`, `analysis/mechanisms.py`, and `analysis/inference/paired.py` aggregates were deleted.

Analysis ownership is split into:

- `analysis/contrasts.py` — paired contrast and supplementary analysis-plan contracts;
- `analysis/descriptive.py` — descriptive summaries and sign consistency;
- `analysis/decisions.py` — scientific decisions and analysis publication documents;
- `analysis/inference/bootstrap.py` — paired BCa intervals;
- `analysis/inference/wilcoxon.py` — Wilcoxon and rank-biserial inference;
- `analysis/inference/multiplicity.py` — multiplicity plans and Holm adjustment;
- `analysis/mechanisms/association.py` — heterogeneity-benefit association;
- `analysis/mechanisms/clustering.py` — persisted cluster-partition stability;
- `analysis/mechanisms/dispersion.py` — grouped threshold and FPR dispersion;
- `analysis/mechanisms/divergence.py` — explicitly blocked or available divergence evidence;
- `analysis/mechanisms/movement.py` — threshold and operating-point movement;
- `analysis/mechanisms/absorption.py` — model-personalization absorption decisions.

`analysis/__init__.py` is a package marker, not a re-export barrel. `analysis/mechanisms/__init__.py` owns only the closed `MechanismEvidence` union required by analysis publication; concrete algorithms are imported from their owning modules.

### Publication ownership

Artifact publication follows one lifecycle:

1. `write` produces a complete artifact in a caller-owned staging location;
2. `validate` proves the artifact is reusable and scientifically compatible;
3. `load` reconstructs the typed persisted result;
4. `rebase` replaces staging paths with final paths after publication.

Centralized training, scoring, threshold construction, and evaluation use this lifecycle. Federated training and scoring use the same lifecycle. Population, split, analysis, and threshold-stage publication call the neutral atomic service directly or through a codec rather than through `artifacts.store`.

`artifacts.store` is now artifact-specific processed-data publication code. It does not re-export neutral atomic functions.

### Related Ditto publication

Ditto global and personalized model families form one related publication. `pipeline/publication/codec.py` defines the typed related-artifact codec and publication request. `pipeline/publication/atomic.py` stages, commits, rolls back, and restores all related directories under one lock.

Both directory trees are written and validated before commit. A completed global artifact cannot be accepted while the linked personalized artifact is absent or incompatible.

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

## Remaining target-tree convergence

The following repository-wide ownership migrations remain open until their callers and tests are migrated in the same PR:

- split the legacy `domain/enums.py` and `domain/values.py` warehouses into `domain/identity.py` and bounded `domain/values/` modules;
- split `protocols/models.py` into seeds, splits, training, thresholding, inference, populations, experiments, anchor, runtime, and graph owners;
- move dataset-wide validation and materialization into `datasets/core/` and retain only dataset-specific behavior in dataset packages;
- split remaining population model warehouses into identities, capabilities, manifests, feasibility, allocation, splitting, and frame owners;
- remove temporary branch packages whose responsibilities are represented in the approved target tree, including top-level scoring and centralized-reference service ownership, after exact replacements exist;
- verify that calibration, preprocessing, evaluation, and experiment contracts have one target-tree owner and no duplicated service implementation;
- replace legacy primitive-leakage baselines with zero-tolerance ratchets after the warehouse splits are complete.

These are structural migrations only. They may not alter the fixed-detector, benign-calibration, eligibility, threshold, metric, checkpoint, dataset, or evidence-tier contracts.

## Enforced architecture regressions

Architecture tests must fail when any of the following returns:

- direct JSON serialization outside `artifacts.serialization`;
- the deleted federated checkpoint monolith or imports from it;
- the deleted analysis aggregate modules or imports from them;
- neutral publication functions imported from `artifacts.store`;
- branch/application imports inside `pipeline`;
- `Any` in the neutral pipeline package;
- direct `BaseModel` inheritance outside `StrictModel`;
- persisted `*Document` classes not based on `StrictModel`;
- Pydantic documents containing runtime DataFrame or tensor payloads;
- duplicate import-linter configuration;
- opaque numbered threshold identities in implementation source.

Import-linter remains the repository-wide dependency-direction authority. The architecture tests complement it with AST-level ownership, duplication, primitive-leakage, and serialization checks.

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
- no deleted analysis-module redirects;
- no re-export of neutral publication primitives from `artifacts.store`;
- no aliases for moved canonical serialization helpers;
- no deprecated threshold or population identifiers;
- no compatibility payload dictionaries;
- no fallback loaders for superseded artifact shapes.

Callers and tests are migrated to the owning modules before superseded modules are deleted.

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

No completed test/check status is currently visible for the active PR head through the available connector. Therefore this document records implemented architecture and explicit remaining convergence work, not a final green or merge-ready claim.

## Acceptance criteria

The refactor is accepted only when:

- the target-tree convergence list is empty;
- the deleted compatibility surfaces remain absent;
- all publication paths have one authoritative atomic owner;
- related Ditto artifacts pass rollback and reuse tests;
- direct serialization bypass count is zero;
- fixed-detector and checkpoint-leakage scientific tests pass;
- the complete suite and static-analysis gates pass on the final head;
- no scientific value, metric, cohort, score, threshold, or claim tier changes relative to the master roadmap.

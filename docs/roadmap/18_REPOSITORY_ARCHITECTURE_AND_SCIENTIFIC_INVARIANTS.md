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

`datp_core.orchestration` is a thin Dagster adapter and contains only assets, definitions, jobs, hooks, and runtime resources. The deleted `orchestration.commands` and `orchestration.stages` packages must not return.

Dagster assets may select and call typed pipeline entry points, project deterministic completion identities, and expose runtime resources. They may not implement training, scoring, thresholding, evaluation, analysis, reporting, persistence, checkpoint selection, campaign recovery, or scientific defaults.

`datp_core.cli.app` follows the same rule. CLI and Dagster are two adapters over one pipeline execution spine; neither is an alternative application layer.

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

The production dependency-direction migrations are complete enough for the architecture and full pytest suites to pass. The PR remains open because final acceptance work is still required:

- align all Phase 12–16 roadmap ownership statements with the pipeline-first tree — **done** in this pass (see `01_PHASE_MASTER_LOG.md` Phase 12–16 entries);
- implement the dedicated Phase 16 `tests/e2e/` acceptance layer — **done**; 11 files present and passing;
- run and record Ruff, Pyright, Pylint, import-linter, architecture, scientific, integration, E2E, and repeated full-suite gates on the final head — **done**; see `01_PHASE_MASTER_LOG.md` Phase 12–13 entries for exact results;
- resolve actionable SonarQube and CodeScene findings, or record credential or external-service blockers without weakening code or tests — **partially done**: SonarQube secrets scan is clean (`totalIssues=0`) and its Vortex agentic service returns organization-side `403 Forbidden` for every file (not a credential failure — matches the pattern recorded for Phases 09–11); CodeScene delta against `origin/main` flagged one regression this pass introduced (`pipeline/planning.py::_planned_entry`, 7 arguments against a 4-argument threshold), which was fixed by bundling the swept per-cell dimensions into a `_SweptCell` record; the other 28 files it flags predate this pass's own changes (pre-existing complexity/duplication in code this pass did not author) and are recorded as a known follow-up rather than remediated here, to avoid unrelated-scope refactoring of already-tested code;
- run repeated deterministic tiny campaigns and verify identical manifests, outputs, cleanup, and reuse — **partially done**: `python -m datp_core.cli.app plan build` was run twice and produced identical plan/campaign digests (`9320` entries); no concrete `StageRunner`/`ExperimentOutputStore` is wired to real stage code yet, so a full campaign execution (not just planning) could not be exercised;
- record the final Phase 16 acceptance verdict in `01_PHASE_MASTER_LOG.md` and only then mark the PR ready for review — no `GO_FOR_FULL_EXPERIMENTS` verdict is recorded; see the Phase 16 entry for why.

These tasks may not change scientific values, algorithms, metrics, evidence roles, dataset boundaries, checkpoint rules, or fixed-detector semantics.

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

GitHub Actions and other hosted-CI results are explicitly outside this pull request's completion procedure (see each Phase 12–16 doc's carve-out) and are not cited here as acceptance evidence; a prior version of this record cited a GitHub Actions run as partial completion evidence, which predated that carve-out and has been removed as stale. The authoritative local validation record for the current head is `docs/roadmap/01_PHASE_MASTER_LOG.md`'s Phase 12–16 entries: `ruff format --check`, `ruff check`, `pyright`, `lint-imports` (10/10 contracts), `pylint`, and the full `pytest` suite all pass locally. This does not complete Phase 16: the final master-log `GO_FOR_FULL_EXPERIMENTS` verdict remains blocked on Phase 08's undeclared FedProx primary coefficient, Phase 09's undeclared size-aware shrinkage function, and Phase 11's outstanding real external/CIC/temporal execution.

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

# Architecture, duplication, and debloat audit

Scope: all production packages under `src/datp_core`, with particular inspection of registries, dispatchers, package re-exports, publication/repository layers, execution helpers, and science-facing adapter boundaries.  Classifications are constrained by the journal contract in `00_JOURNAL_CONTRACT.md`: a layer that locks the frozen-detector comparison, benign-only calibration, provenance, persistence, chronology, or claim boundaries is retained even when small.

## Evidence basis

- Graphify inventory: `graphify-out/graph.json` (6,396 nodes) used for import/call navigation; conclusions below were verified by direct source inspection and repository-wide import/caller search.
- Registry/dispatch inspection: `data/registry.py`, `experiments/registry.py`, `thresholds/dispatch.py`, CLI application, and recipe/engine routes.
- Re-export inspection: every non-empty package `__init__.py`. The experiment package re-exports are production-used from `app/recipes.py`; `analysis.mechanisms` and `detector.training.models` are also production-used facades. They are not stale redirects.
- Focused dataset/preprocessing verification previously passed: `126 passed` for unit dataset, unit preprocessing, and integration dataset suites.

## Architecture map and assessment

```text
app/cli -> app campaign/recipes/planning -> experiment registry/routes
  -> execution context/workspace -> data registry/population/split/preprocessing
  -> detector training/checkpoint/scoring -> thresholds -> analysis -> presentation
                         \-> artifact repositories/publication/serializers
```

The registry layers are not redundant: dataset/population bindings encode the locked five-population catalogue and capabilities; experiment/threshold dispatch distinguish confirmatory, supportive, stress, temporal, external, and unavailable responsibilities.  Atomic publication and related-artifact wrappers protect reusable provenance rather than merely forwarding calls.  Small execution helpers also bind protocol constants and score/checkpoint provenance, so folding them into callers would reduce traceability without reliable code reduction.

## Confirmed finding

### AD-001 — obsolete parallel in-memory preprocessing architecture

| Field | Evidence |
| --- | --- |
| ID | AD-001 |
| Severity | MEDIUM |
| Disposition | MERGE_DUPLICATE |
| File | `src/datp_core/data/preprocessing/contracts.py`, `fitting.py`, `transforms.py`, `validation.py` |
| Symbol | The entire legacy `PreprocessingProtocol`/`FittedPreprocessingState` family, including `fit_federated_preprocessing`, `fit_centralized_preprocessing`, `transform_federated_preprocessing`, and `transform_centralized_preprocessing` |
| Roadmap requirement | Preprocessing is part of frozen detector state: correct protocol identity, benign train-only fitting, fitted-state persistence, transform-only partitions, finite handling, and serialization-equivalence checks are required. |
| Roadmap section | §2.2.1; §3.1–§3.2 |
| Graphify evidence | The four files form an isolated import component. `contracts.py` is imported only by `fitting.py`, `transforms.py`, and `validation.py`; repository-wide searches found no production or test importer of any of the four files. |
| Direct source evidence | The live path is `preprocessing/service.py -> federated.py|centralized.py -> artifact_validation.py -> publication.py/state.py`; it owns identity dispatch, train-only fitting, skops persistence, reload equivalence, transformed assets, and manifests. The legacy path owns parallel in-memory types and fitting/transformation only. |
| Current callers | Internal island only. |
| Current callees | sklearn in-memory scalers and island-local validation. |
| Production reachable | NO |
| Test-only reachable | NO |
| Scientifically required | NO; its responsibility is correctly implemented by the live persisted pipeline. |
| Problem | A full former implementation remains as a parallel conceptual model. Its duplicate `PreprocessingFitScope`, protocol/state records, fitting, and transformation code make the authoritative scientific path ambiguous. |
| Scientific consequence | None while unreachable. Retaining it increases the chance that a future caller selects an in-memory path that bypasses required artifact/provenance/reload checks. |
| Runtime consequence | None currently. |
| Architecture consequence | Four modules and a second terminology/type system without a caller. |
| Correct final state | Remove the island as a single intentional deletion; retain the persisted scientific pipeline. Do not replace it with aliases or compatibility re-exports. |
| Affected callers | None in repository. |
| Affected callees | Only the deleted island imports. |
| Affected tests | None found. |
| Affected artifacts | None. |
| Confidence | CONFIRMED |

## Candidate considered and retained

`data.materialization_lifecycle`, `data.publication`, the generic artifact publication codecs, `detector.training.federated_publication`, `detector.training.ditto_publication`, and execution checkpoint/score helpers can look wrapper-like in isolation. They each add a material contract: cache validity/atomic replacement, reusable-complete markers, joint Ditto global/personalized publication, fixed one-epoch protocol validation, or score/checkpoint provenance. They should be kept. Likewise, package-level re-exports observed in production imports are usable facades, not compatibility shims.

## No other confirmed architecture finding

No other confirmed stale re-export, unnecessary registry, forwarding-only production layer, misplaced scientific responsibility, or safe cross-package merge was found. The repository is highly modular, but the remaining boundaries largely encode journal-required distinctions (especially confirmatory versus stress/anchor/external work and persisted detector-state provenance). Further broad consolidation would be speculative and risks flattening those distinctions.

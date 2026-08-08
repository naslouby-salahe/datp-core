# Dataset, population, preprocessing, and materialization audit

Scope: every production module below `src/datp_core/data/`, plus its production callers in execution context and the materialization entrypoints.  Authority read before classification: `docs/Journal_Extension_Master_Roadmap.md` and `docs/graphify_audit/00_JOURNAL_CONTRACT.md`.

## Evidence and runtime coverage

Graphify output was used as navigation evidence (`graphify-out/graph.json`, 6,396 nodes) and every conclusion below was checked against source.  Textual caller tracing establishes these real paths:

```text
CLI/campaign or experiment engine
  -> data.service.materialize_datasets
  -> data.registry.dataset_binding
  -> NBaIoTMaterializer | CICIoT2023Materializer | EdgeIIoTsetMaterializer
  -> materialization_lifecycle.materialize_canonical
  -> canonical cache reuse or atomic canonical publication

experiment execution.context.resolve_execution_context
  -> construct_declared_population + preprocess_federated              (N-BaIoT paths)
  -> construct_published_population + construct_published_split
     + preprocess_published_federated                                  (CIC/Edge bounded-evidence paths)
  -> client partition extraction -> train-only estimator fit
  -> skops persistence/reload-equivalence check -> transformed assets
```

The main implementation is live: `data.registry.construct_population` dispatches all five declared populations; `data.preprocessing.service.preprocess_federated` is reached from execution context and the FedProx stress runner; `preprocess_published_federated` is reached from bounded CIC/Edge execution; centralized preprocessing is reached from the centralized reference implementation.

Source checks found the expected journal-aligned controls:

- N-BaIoT keeps nine exact physical-device identities, records independent device families, and rejects non-finite feature rows at materialization (`nbaiot/reader.py`, `nbaiot/populations.py`).
- CIC preserves canonical rows losslessly, then applies the recognized-label and finite-feature gate when creating file-defined pseudo-clients; it rejects physical-device and family interpretations (`ciciot2023/materialize.py`, `ciciot2023/populations.py`).
- Edge retains unassigned attack traffic, uses benign sensor-group membership for FPR-only analysis, validates PCAP-backed chronology before temporal population construction, and excludes Modbus from temporal construction (`edge_iiotset/materialize.py`, `edge_iiotset/populations.py`, `edge_iiotset/chronology.py`).
- Split construction allocates train/calibration/evaluation separately from attack rows, rejects attack data in train/calibration, and validates stable-row conservation and temporal direction (`populations/splits.py:95-102, 139-241, 371-410`).
- Federated preprocessing maps the confirmatory identity to client-local `StandardScaler` and the supportive identity to pooled `MinMaxScaler`; fitting verifies benign train-only labels and finite matrices, persists skops states, reload-checks at the configured tolerance, and transforms without clipping (`preprocessing/service.py`, `models.py`, `artifact_validation.py:230-368`, `state.py`).

Focused verification passed:

```text
.venv/bin/python -m pytest tests/unit/datasets tests/unit/preprocessing tests/integration/datasets -q
126 passed in 4.79s
```

## Confirmed findings

### DP-001 — isolated legacy preprocessing implementation island

| Field | Evidence |
| --- | --- |
| Severity | MEDIUM |
| Disposition | DELETE_DEAD |
| File | `src/datp_core/data/preprocessing/contracts.py`, `fitting.py`, `transforms.py`, `validation.py` |
| Symbol | Entire legacy `PreprocessingProtocol` / `FittedPreprocessingState` implementation family, including `fit_federated_preprocessing`, `fit_centralized_preprocessing`, `transform_federated_preprocessing`, and `transform_centralized_preprocessing` |
| Roadmap requirement | Roadmap §2.2.1 preprocessing and normalization lock; §3.1–3.2 benign-only fitting and isolation |
| Roadmap section | §2.2.1, §3.1, §3.2 |
| Graphify evidence | The Graphify source inventory contains this self-contained import component; direct import/caller searches show `contracts.py` is imported only by `fitting.py`, `transforms.py`, and `validation.py`. No production module imports any of those four modules. |
| Direct source evidence | The live path imports `data.preprocessing.models`, `artifact_validation`, `federated`, `centralized`, `service`, and `state`; no live caller references `fitting.py` or `transforms.py`. `fit_federated_preprocessing`, `fit_centralized_preprocessing`, `transform_federated_preprocessing`, and `transform_centralized_preprocessing` have no callers outside that island. |
| Current callers | Internal island only: fitting/transforms/validation. No production caller; no test caller found. |
| Current callees | sklearn scalers and its island-local validation/contracts. |
| Production reachable | NO |
| Test-only reachable | NO |
| Scientifically required | NO — the responsibility is already implemented by the live, persisted pipeline. |
| Problem | A former in-memory preprocessing pipeline remains alongside the authoritative persisted preprocessing implementation, duplicating protocol/state concepts and fitting/transform responsibilities. |
| Scientific consequence | None while unreachable. Retention creates a material future risk of accidentally wiring a pipeline that lacks the live publication/provenance/reload-validation chain. |
| Runtime consequence | None at present. |
| Architecture consequence | Four modules and parallel types obscure the authoritative preprocessing contract. |
| Correct final state | Delete the four-module island after confirming no non-repository consumer treats these modules as public API; retain the live `models.py`/`artifact_validation.py`/`federated.py`/`centralized.py` pipeline only. |
| Affected callers | None in repository. |
| Affected callees | The island-local imports only. |
| Affected tests | None found; add no compatibility shim. |
| Affected artifacts | None. |
| Why unreachable? | Repository-wide source search found no import of the island from production or tests; its only edges are internal. |
| Why scientifically unnecessary? | The live pipeline performs the required train-only fitting, finite checks, skops persistence, reload equivalence, transformed-partition publication, and identity-specific dispatch. |
| Superseding implementation | `preprocessing/service.py`, `federated.py`, `centralized.py`, `artifact_validation.py`, `models.py`, and `state.py`. |
| Production behavior after removal | No behavior change expected. |
| Confidence | CONFIRMED |

## Suspected finding requiring a remediation decision

### DP-002 — N-BaIoT execution recomputes the same split rather than consuming one shared artifact

| Field | Evidence |
| --- | --- |
| Severity | LOW |
| Disposition | SIMPLIFY |
| File | `src/datp_core/experiments/execution/context.py:135-164`; `src/datp_core/data/preprocessing/service.py:68-141`; `src/datp_core/data/populations/construction.py:186-239` |
| Symbol | `resolve_execution_context`, `preprocess_federated`, `build_preprocessing_handoff` |
| Roadmap requirement | Fixed detector: one predefined split must be held constant across the score and threshold ladder. |
| Roadmap section | §2.1–2.2.1, §3.2 |
| Graphify evidence | Both `construct_declared_population` and `preprocess_federated` are live from `resolve_execution_context`; the former calls `split_membership`, and the latter constructs the population again before `build_preprocessing_handoff` calls `split_membership` again. |
| Direct source evidence | `context.py:135-164` derives `split_checksum` from `construct_declared_population`; `service.py:82-96` constructs the same population again; `construction.py:218-228` creates fresh assignments. Both use the same declared seed/protocol, but the preprocessing request neither receives nor verifies the first assignment checksum. |
| Current callers | Production N-BaIoT natural and controlled execution context. |
| Current callees | `construct_population`, `split_membership`, feature join, client preprocessing publication. |
| Production reachable | YES |
| Test-only reachable | NO |
| Scientifically required | YES — fixed split identity; the duplicate implementation itself is not required. |
| Problem | One execution has two computations of a scientifically critical split, with no direct equality assertion across their outputs. Current deterministic code should make them equal, and no observed mismatch was found. |
| Scientific consequence | A later change to either branch could silently cause the recorded split checksum and the preprocessing/training rows to differ, violating the fixed-detector comparison evidence chain. |
| Runtime consequence | Duplicate work; no observed failure. |
| Architecture consequence | Two owners effectively reconstruct the same split. |
| Correct final state | Pass the already constructed assignments/manifest or a published split handoff into preprocessing, or add a hard equality/checksum assertion before fitting. Do not alter split semantics. |
| Affected callers | `resolve_execution_context`; N-BaIoT experiment paths. |
| Affected callees | `preprocess_federated`, `build_preprocessing_handoff`, `split_membership`. |
| Affected tests | Add an integration assertion that the preprocessing rows/checksum equal the execution split checksum. |
| Affected artifacts | Training provenance and preprocessed partition assets. |
| Confidence | HIGH (hardening/simplification finding, not a demonstrated present scientific-drift defect). |

## No issue found

No confirmed dataset-boundary, calibration/evaluation leakage, non-finite-value policy, preprocessing-identity, canonical-publication, population-capability, or temporal-ordering defect was found in the audited scope.  In particular, no journal-required dataset/population/preprocessing implementation was found disconnected.

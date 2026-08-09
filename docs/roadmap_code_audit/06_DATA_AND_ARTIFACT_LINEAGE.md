# 06 — Data and Artifact Lineage

## Population → split → preprocessing → detector → checkpoint → score chain (verified per population)

| Population | Client unit | Chronology | Family taxonomy | Split protocol | Preprocessing identity |
|---|---|---|---|---|---|
| NBAIOT_NATURAL_DEVICES | 9 physical devices | UNAVAILABLE (no source timestamps) | 5 families (static lookup) | NON_TEMPORAL_EQUAL_THIRDS (1/3,1/3,1/3) | FEDERATED_CLIENT_LOCAL_STANDARD |
| NBAIOT_DIRICHLET_CLIENTS | 20 synthetic clients | UNAVAILABLE | NOT_APPLICABLE | NON_TEMPORAL_EQUAL_THIRDS | FEDERATED_CLIENT_LOCAL_STANDARD |
| CICIOT_FILE_CLIENTS | 63 file-defined pseudo-clients | UNAVAILABLE (pseudo-time forbidden, none synthesized) | UNAVAILABLE | NON_TEMPORAL_EQUAL_THIRDS | FEDERATED_POOLED_MIN_MAX |
| EDGE_SENSOR_GROUPS | 10 static benign sensor groups | UNAVAILABLE (static) | UNAVAILABLE | RANDOM_FRACTIONAL_STATIC_REFERENCE | FEDERATED_POOLED_MIN_MAX |
| EDGE_TEMPORAL_GROUPS | 9 PCAP-verified groups | SUPPORTED (PCAP-aligned; Modbus address-literal rows excluded) | UNAVAILABLE | TEMPORAL_HISTORICAL_FUTURE (55/15/10/20) | FEDERATED_POOLED_MIN_MAX |
| Centralized reference | pooled | UNAVAILABLE | N/A | NON_TEMPORAL_EQUAL_THIRDS | CENTRALIZED_POOLED_MIN_MAX (never reuses federated state — `reject_federated_preprocessing_for_training()`) |

Row conservation and disjointness verified via `data/populations/integrity.py` (`validate_no_partition_overlap`, `validate_no_future_history_leakage`, uniqueness of `STABLE_ROW_ID`). Benign-only train/calibration gate verified in `data/populations/splits.py` (attack rows routed to EVALUATION only) and re-checked at preprocessing fit time (`data/preprocessing/artifact_validation.py::_assert_split_invariants`, raises `LeakageError`).

## Score/checkpoint/preprocessing identity binding

`FixedScoreInvariant` (`detector/scoring/contracts.py`) binds: `model_checksum`, `coordinate_checksum`, `calibration_score_set_checksum`, `evaluation_score_set_checksum`, `preprocessing_state_set_checksum`, `split_manifest_checksum`, optional `future_recalibration_score_set_checksum`. Completion markers use exact SHA-256 string equality (`artifact_completion_marker_matches`), never numeric tolerance — the 1e-12 tolerance found elsewhere is isolated to preprocessing transform serialization/reload equivalence only (`data/preprocessing/state.py`), confirming the AMBIG-004 SCIENTIFIC_ARTIFACT_IDENTITY vs NUMERICAL_RELOAD_EQUIVALENCE separation is actually implemented, not just documented.

An existing integration test (`tests/integration/thresholding/test_threshold_methods_reuse_scores.py::test_every_threshold_method_reads_the_same_frozen_score_artifact_unchanged`) asserts byte-identical score files and identical `score_set_checksum` across every threshold method dispatched against one manifest.

## Artifact repository / reuse semantics

| Reuse class | Enforcement mechanism |
|---|---|
| `MUST_REUSE_IDENTICAL_ARTIFACT` (same seed/regime/training-baseline/preprocessing across compared threshold policies) | checksum-validated `*_is_reusable()` gates before any regeneration |
| `MUST_REGENERATE` (different seed/severity/training-baseline) | structurally enforced by `ExperimentCoordinate` participating in every artifact path (`stable_key`) — different dimension ⇒ different path, not merely a naming convention |
| `MUST_REMAIN_SEPARATE` (FedAvg/FedProx/Ditto/Centralized) | `TrainingModelId` + `model_coefficient` fields, `__post_init__` validation forbids a coefficient on non-coefficient training models |

Completion semantics are fail-closed: `artifact_completion_marker_matches()` returns `False` (not an exception, not a silent pass) on a missing/unreadable marker, forcing regeneration rather than accepting a partial run as complete. `--overwrite` performs a scoped `rmtree` of only the owning artifact directory.

## Confirmed deviation from the canonical file-level tree (see `08_FINDINGS.md` ARCH-001/ARCH-002)

`artifacts/repositories/` lacks dedicated `populations.py`/`preprocessing.py`/`checkpoints.py`/`scores.py` modules (that persistence logic is colocated with its owning domain package instead); `artifacts/serializers/` lacks `safetensors.py`/`skops.py` wrapper modules (used inline). Checksums/provenance themselves remain single-sourced through `artifacts/provenance.py` regardless of this file-location question — no duplicate or conflicting hashing implementation was found.

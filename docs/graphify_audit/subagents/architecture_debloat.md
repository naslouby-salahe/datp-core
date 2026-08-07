# Architecture / Duplication / Dead-Code Audit — DATP-Core

Scope: `src/datp_core/**` (production). Line numbers current at audit time.
Legend: `file:line — finding — duplicates/overlaps — action`.

## Dead code (module-level)

- `src/datp_core/pipeline/workflows/centralized.py:1` — entire 145-line module (`run_centralized_reference_seed`, `centralized_reference_directory`, `CentralizedReferenceArtifactDirectory`) — never imported by any src or test module; tests re-implement the centralized-reference flow from lower-level modules (`pipeline/decision/centralized.py`, `pipeline/scoring/centralized.py`) — delete module.
- `src/datp_core/runtime/logging.py:1` — `PipelineLogContext`, `bind_pipeline_logger` — no production consumer; referenced only by `tests/unit/runtime/test_logging.py`; production logging is done via direct `structlog` in `preprocessing/client_partitions.py:5,231` — delete module + its test.
- `src/datp_core/analysis/mechanisms/__init__.py:170` — `cluster_mechanism_bundle` — defined and exported in `__all__` but zero consumers (src or tests) — delete.
- `src/datp_core/analysis/mechanisms/__init__.py:217` — `heterogeneity_association_from_observations` — one-line wrapper over `heterogeneity_benefit_association`; zero consumers — delete.

## Duplicated logic

- `src/datp_core/datasets/contracts.py:579` — `complete_digest` — byte-identical copy also at `pipeline/publication/service.py:266` and `preprocessing/publication.py:69` (`checksum_text(f"{manifest}\n{schema}")`) — move to `domain/values/checksums.py`; 3 modules import it.
- `src/datp_core/domain/provenance.py:82` — `serialize_json_model` — duplicate at `pipeline/publication/service.py:372`; both = `canonical_json_text` + write + `checksum_text`; publication copy additionally uses `write_text_atomically` — consolidate into one (prefer provenance, adopt atomic write).
- `src/datp_core/pipeline/workflows/confirmatory.py:692` — `_required_metric` — identical function at `external.py:184` (`return population_metric(document, metric)`) — hoist to a shared evaluation helper.
- `src/datp_core/pipeline/workflows/confirmatory.py:696` — `_evaluation_path` — near-identical at `external.py:188` (same dir/asset resolution, differs only in coordinate helper + signature) — parameterize once.
- `src/datp_core/thresholding/publication.py:111` — `threshold_result_checksum` — re-implements `checksum_text(canonical_json_text(result))`; identical semantics to `pipeline/decision/centralized.py:388` which uses `canonical_checksum` — reuse `domain/provenance.canonical_checksum`.
- `src/datp_core/evaluation/threshold_evidence.py:47` — `_verify_score_rows` — same provenance/schema/row verification on the same `HeldOutBenignScore`/`FederatedScoreRecord` types as `evaluation/conformal_coverage.py:195` (`_verify_score_rows` + `_verify_record_rows`) — extract one shared verifier.
- `src/datp_core/datasets/partitioning/integrity.py:287` — `_require_columns` — same missing-column check as `pipeline/scoring/frames.py:199` (different error type) — consolidate or delegate to a shared column-presence helper.
- `src/datp_core/pipeline/decision/centralized.py:388` vs `thresholding/publication.py:111` — see above.

## Parallel dataset-module pattern (structural duplication)

- `src/datp_core/datasets/{ciciot2023,edge_iiotset,nbaiot}/schema.py` — `_canonical_columns` (schema.py:135/142/99) and `source_relative_path` (schema.py:214/250/203) — same construction/derivation shapes, dataset-specific column tables — acceptable parallelism, but shared builders (`canonical_provenance_column`, `canonical_name`) already exist; keep, do not merge.
- `src/datp_core/datasets/{ciciot2023,edge_iiotset,nbaiot}/materialize.py` — `publish`/`materialize`/`write_assets`/`_prepare_publication`/`_validation_report` (materialize.py:50/56/94/82/162, 81/95/132/148/224, 44/51/121/76/--) — same staging/validation/publish lifecycle per dataset — shared lifecycle primitives already live in `runtime/filesystem.py` + `datasets/canonical_cache.py`; extend those rather than new copies.
- `src/datp_core/datasets/{ciciot2023,edge_iiotset,nbaiot}/materialize.py` — `canonical_directory` methods (materialize.py:47/78/41) — one-line wrappers over `datasets/canonical_cache.py:92 canonical_directory(canonical_root, schema)` — wrappers bind schema; acceptable but thin (project rule discourages one-call wrappers).

## Thin wrappers

- `src/datp_core/analysis/mechanisms/__init__.py:223` — `jensen_shannon_from_client_scores` — single-line delegate to `jensen_shannon_divergence`; single caller `pipeline/workflows/confirmatory.py:241` — inline the call, drop wrapper.
- `src/datp_core/analysis/mechanisms/__init__.py:109` — `threshold_movements_from_evaluations` — real assembly logic (not a pure wrapper); keep, but it is domain logic living in a `__init__.py` — consider moving to a module under `analysis/mechanisms`.

## Barrel re-exports (unused export surface)

- `src/datp_core/analysis/mechanisms/__init__.py:68` — `__all__` of 37 names; 21 never imported by any module (`AssociationResult`, `ClusterEvidenceAvailability`, `ClusterEvidenceRecord`, `ClusterStabilityResult`, `DivergenceBlocker`, `DivergenceResult`, `GroupDispersionObservation`, `GroupedDispersionResult`, `ThresholdMovement`, `ThresholdMovementMultiSeedUncertainty`, `ThresholdMovementSeedSummary`, `ThresholdOperatingPoint`, `blocked_jensen_shannon_divergence`, `cluster_mechanism_bundle`, `decide_model_absorption`, `empty_cluster_evidence_record`, `grouped_dispersion`, `heterogeneity_association_from_observations`, `jensen_shannon_divergence`, `summarize_threshold_movements`, `threshold_movement`) — trim `__all__` to consumed names.
- `src/datp_core/pipeline/workflows/__init__.py` — `__all__` exports 22 names; 8 never imported from the package (`AnchorCommandResult`, `CampaignRunResult`, `ExperimentRunResult`, `ExperimentStatusRecord`, `PreprocessResult`, `ProgrammeStatusReport`, `ReportResult`, `ValidationResult`) — consumers import these directly from `workflows.campaign` — trim barrel.
- `src/datp_core/learning/federated/models/__init__.py` — `__all__` includes `validate_client_preprocessing_match` (records.py:18) — never imported from the barrel — trim.

## God modules / size (LOC, top-level symbols)

- `src/datp_core/pipeline/workflows/personalization.py` — 977 LOC, 32 symbols — ditto + fedprox stress, absorption, coefficient selection, all in one module — candidate to split by campaign type.
- `src/datp_core/reporting/export.py` — 900 LOC, 27 symbols — all markdown/publication rendering (`_render_*`) — single responsibility, large but cohesive; low priority.
- `src/datp_core/pipeline/workflows/temporal.py` — 885 LOC, 38 symbols — temporal campaign orchestration — candidate split: campaign execution vs provenance validation.
- `src/datp_core/pipeline/workflows/campaign.py` — 783 LOC, 45 symbols — dispatch/report/status registry — high symbol count but coherent registry; low priority.
- `src/datp_core/datasets/partitioning/contracts.py` — 736 LOC, 62 symbols — highest symbol density in a contracts module — consider splitting contracts from validators (`validate_manifest`, `validate_diagnostics`).
- `src/datp_core/datasets/contracts.py` — 647 LOC, 65 symbols — highest symbol count repo-wide — consider splitting schema contracts from publication helpers.

## Dependency graph

- No circular dependencies at module level (verified via AST import graph).
- Highest fan-out (imports): `protocols/validation.py` (12), `protocols/graph.py` (10), `datasets/partitioning/construction.py` (5).
- Highest fan-in (imported by): `protocols/seeds.py`, `datasets/partitioning/contracts.py`, `datasets/edge_iiotset/schema.py` (5 each).
- `runtime/filesystem.py` is the single authoritative atomic-I/O source — correctly reused; no duplication found there.
- `cli/app.py` is the live console-script entry (`[project.scripts] datp-core`); not dead despite no src importer.

## Positive notes

- No unused imports in `src` (ruff `F401` clean, excluding intentional `__init__.py` barrel re-exports).
- Value-object machinery in `domain/values/base.py` is well-factored via shared helpers.
- Checksum primitives centralized in `domain/values/checksums.py` (except the `complete_digest` triple).

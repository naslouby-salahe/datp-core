# REVIEWER_2 — Report purity, single-pass campaign

## Findings

- [SEV-LOW] src/datp_core/pipeline/workflows/campaign.py:657-668 — `_generate_campaign_report` catches `(ReportEvidenceError, ScientificContractError, MissingPrerequisiteError)` per experiment and records `item:missing(...)`, then continues; `generate_report(None)` and therefore `run_campaign`'s final report return success even when zero experiments have reportable evidence. The missing state is not silent (it is surfaced in `CampaignRunResult.detail` and `ReportResult.detail`), so this is a deliberate best-effort aggregation, not a WR-006/WR-007 regression. Evidence: `except (ReportEvidenceError, ScientificContractError, MissingPrerequisiteError) as error: details.append(f"{item.value}:missing({error})"); continue`. Note only; the per-handler and per-loader typed-error contract is intact.

No SEV-HIGH/SEV-MED findings in the report-purity / single-pass dimension.

Verified-fixed defects:

- [OK] WR-006 — report handlers load evidence only, never train.
  - campaign.py:708-745 `_report_ditto_absorption_stress_test` no longer calls `run_ditto_absorption_campaign`; imports only `load_fedavg_cv_fpr_effect` (confirmatory), `analyze_ditto_absorption` + `load_ditto_stress_test_evidence` (personalization). Training entry point `run_ditto_absorption_campaign` deleted from personalization.py; grep of `src/` and `tests/` for `run_ditto_absorption_campaign` and `run_temporal_campaign` returns nothing.
  - campaign.py:748-760 `_report_edge_one_shot_recalibration` no longer calls `run_temporal_campaign`; imports only `TemporalCampaignResult`, `analyze_temporal_campaign`, `load_temporal_campaign_seeds`.
  - Every other handler is load/analyze-only: `_report_confirmatory_family` (671) -> `analyze_confirmatory_campaign` (confirmatory.py:168, loads gate artifacts + evaluation docs only); `_report_edge_benign_equity_validation` (684) / `_report_ciciot_file_client_boundary` (692) -> `analyze_external_validation_campaign` / `analyze_ciciot_boundary_campaign` (external.py:76/83 -> `_analyze_bounded_external_campaign`, load/analyze/export only); `_report_fedprox_absorption_stress_test` (700) -> `_report_fedprox_absorption` (787) -> select/write/analyze + loaders only.
  - The only `run_*_seed` / `execute_declared_experiment_seed` references in campaign.py are inside the execution dispatch handlers (lines 266-390) and `reproduce_anchor` (541-555); none are reachable from any `_report_*_handler` (lines 671-828).

- [OK] WR-007 — single-pass campaign.
  - campaign.py:507-527 `run_campaign`: the per-experiment loop (515-516) calls only `run_experiment`; the in-loop `generate_report(experiment_id, overwrite=overwrite)` was removed by this diff. A single final `generate_report(None, overwrite=overwrite)` is invoked at line 522 after the completion marker. CLI entry (cli/execution.py:48) calls `run_campaign` once; the `report` command (cli/app.py:114) is a standalone invocation, not part of the loop.

- [OK] Missing report evidence fails with typed errors; no training fallback.
  - personalization.py:170-198 `load_ditto_stress_test_evidence` raises `ScientificContractError` on missing `seed.json`/`COMPLETE` (179-184), on unreadable/invalid JSON (188-192), and on checksum mismatch against the marker (193-197).
  - temporal.py:272-299 `_load_temporal_seed_evidence` raises `ScientificContractError` on missing files (280-285), invalid JSON (289-293), and checksum mismatch (294-298).
  - campaign.py:787-828 `_report_fedprox_absorption` wraps missing selection evidence: `select_primary_fedprox_coefficient_from_artifacts` -> `collect_fedprox_coefficient_terminal_losses` -> `read_terminal_aggregate_training_loss` (personalization.py:613-625, ArtifactIntegrityError from `read_parquet` history.py:71-83 converted to ScientificContractError) -> caught at campaign.py:823-827 and re-raised as `ReportEvidenceError`.

- [OK] Evidence persistence.
  - Ditto: `run_ditto_stress_test_seed` (personalization.py:262) -> `_persist_ditto_evidence` (157-167) writes slim `DittoStressTestEvidence` (personalization.py:148, coordinate + shared/local metrics + evaluation cohort manifest) as `seed.json` plus a `COMPLETE` marker holding `canonical_checksum(evidence).value`, under `ditto_directory(..., DittoArtifactBranch.EVIDENCE, output_root)` (ditto_directory 1012-1025 = `{output_root}/ditto_stress_test/{population}/{seed}/{reg}/evidence`). `load_ditto_stress_test_evidence` (170-198) checksum-verifies the COMPLETE marker against `canonical_checksum(evidence)`.
  - Temporal: `run_temporal_seed` (temporal.py:188) -> `_persist_temporal_seed_evidence` (264-269) writes full `TemporalSeedResult` as `seed.json` plus `COMPLETE` checksum marker under `_temporal_seed_evidence_directory` (248-262) = `{output_root}/bounded_evidence/{exp}/{population}/{role}/{seed}/evidence`. `load_temporal_campaign_seeds` (218-224) loads the full declared seed cohort; missing any seed fails via `_load_temporal_seed_evidence`.

- [OK] Report registry exactly covers registered workflows.
  - campaign.py:763-771 `_EXPERIMENT_REPORT_HANDLERS` keys = the 7 `REGISTERED_WORKFLOW_EXPERIMENTS`; enforced by `_require_dispatch_covers_registry(_EXPERIMENT_REPORT_HANDLERS, name="experiment report")` at line 772 (exact set equality, campaign.py:88-90). `_ANALYSIS_MARKER_CHECKS` (974-984) likewise enforces exact equality with `!=`, and now includes FedProx/Ditto/Temporal markers (929-971) closing the WR-009 gap for status derivation.

## Verdict

All five required defect classes are verified FIXED: (WR-006) every `_report_*_handler` body imports only load/analyze functions and no training entry point is reachable, and the training entry points `run_ditto_absorption_campaign`/`run_temporal_campaign` are fully deleted from the codebase; (WR-007) `run_campaign` executes each coordinate exactly once and only the single final `generate_report(None)` runs; missing report evidence fails closed with `ScientificContractError` (ditto/temporal loaders) or `ReportEvidenceError` (fedprox selection wrap) and never silently executes training; Ditto slim evidence and full TemporalSeedResult are persisted with checksum-verified COMPLETE markers at the required coordinates; and the report handler registry is enforced to cover exactly `REGISTERED_WORKFLOW_EXPERIMENTS`. The only observation is the SEV-LOW best-effort aggregation in `_generate_campaign_report` (missing evidence recorded in detail rather than failing the aggregate report), which is explicit, not silent, and does not violate the report-purity contract. Report purity and single-pass campaign semantics are sound in the reviewed working tree.

# CLI, Orchestration, and Wiring Audit — datp-core

Scope: `src/datp_core/cli/*`, `src/datp_core/pipeline/planning.py`,
`src/datp_core/pipeline/coordinates.py`, `src/datp_core/pipeline/workflows/*`,
`src/datp_core/pipeline/execution/{engine,models}.py`.

Format: `file:line — finding — severity`

## CLI commands — end-to-end trace

| Command | Entry | Calls | End-to-end? |
|---|---|---|---|
| `validate` | app.py:36 | `validate_programme` (workflows/__init__.py:124) | Complete |
| `plan` | app.py:57 | `build_programme_plan` (workflows/__init__.py:160) | Complete |
| `preprocess` | app.py:70 | `preprocess_datasets` (workflows/__init__.py:197) | Complete |
| `smoke` | app.py:85 | `run_smoke` (campaign.py:304) | Partial — see findings |
| `report` | app.py:101 | `generate_report` (campaign.py:480) | Partial — see findings |
| `status` | app.py:117 | `programme_status` (campaign.py:634) | Complete |
| `run experiment` | execution.py:16 | `run_experiment` (campaign.py:178) | Partial — see findings |
| `run campaign` | execution.py:36 | `run_campaign` (campaign.py:341) | Partial — see findings |
| `anchor reproduce` | anchor.py:15 | `reproduce_anchor` (campaign.py:364) | Complete |
| `anchor verify` | anchor.py:31 | `verify_anchor_programme` (campaign.py:426) | Complete |
| `anchor status` | anchor.py:42 | `anchor_status` (campaign.py:456) | Complete |

## Findings

### High

- `src/datp_core/pipeline/workflows/campaign.py:228-234` — `_dispatch_edge_benign_equity_validation` deletes `output_root`/`overwrite` and calls `run_external_validation_seed(seed)`; seed writes to real `OUTPUTS_ROOT` even in smoke, and `execute_declared_campaign` writes a single-seed-plan completion record into the production tree; later full-cohort run sees `COMPLETE_INVALID` (engine.py:118-119) and raises `ValueError` — smoke poisons real runs — HIGH
- `src/datp_core/pipeline/workflows/campaign.py:237-243` — `_dispatch_ciciot_file_client_boundary` same `del output_root, overwrite`; CICIoT smoke single-seed writes production completion records; poisons future full runs — HIGH
- `src/datp_core/pipeline/workflows/campaign.py:246-254` — `_dispatch_fedprox_absorption_stress_test` `del seeds`; smoke runs the FULL grid (all confirmatory seeds x all coefficients) not one canonical seed; violates smoke single-seed contract (app.py:90) — HIGH
- `src/datp_core/pipeline/workflows/campaign.py:257-263` — `_dispatch_ditto_absorption_stress_test` `del output_root, overwrite`; smoke single-seed and full runs both write to real `OUTPUTS_ROOT`; `--overwrite` never clears ditto artifacts — HIGH
- `src/datp_core/pipeline/workflows/campaign.py:266-272` — `_dispatch_edge_one_shot_recalibration` `del output_root, overwrite`; temporal smoke writes to `OUTPUTS_ROOT` via `bounded_evidence_seed_directory(..., OUTPUTS_ROOT)`; overwrite ignored — HIGH
- `src/datp_core/pipeline/workflows/campaign.py:557-563` — `_report_edge_one_shot_recalibration` calls `run_temporal_campaign()` which re-runs full execution (score/threshold/evaluate per seed), not report-from-evidence; violates "no training" report contract (app.py:105, campaign.py:480-481) — HIGH
- `src/datp_core/pipeline/workflows/campaign.py:542-554` — `_report_ditto_absorption_stress_test` calls `run_ditto_absorption_campaign()` which re-runs `run_ditto_stress_test_seed` for every seed (full training); report regenerates by re-executing — HIGH
- `src/datp_core/pipeline/workflows/campaign.py:341-361` — `run_campaign` in-loop `generate_report(experiment_id)` re-executes Ditto/Temporal experiments a 2nd time; final `generate_report(None)` adds a 3rd; Ditto/Temporal executed 3x per campaign; other experiments analyzed twice — HIGH
- `src/datp_core/pipeline/workflows/centralized.py:45` — `run_centralized_reference_seed` has no caller in any CLI command, dispatch table, or report handler; dead workflow from wiring perspective — HIGH

### Medium

- `src/datp_core/pipeline/workflows/campaign.py:324-325` — `run_smoke` swallows `AnchorReproductionError`/`ScientificContractError`/`MissingPrerequisiteError` from `reproduce_anchor`/`verify_anchor_programme`; smoke silently continues past anchor gate failure — MEDIUM
- `src/datp_core/pipeline/workflows/campaign.py:493-502` — `_generate_campaign_report` catches `ReportEvidenceError`/`ScientificContractError`/`MissingPrerequisiteError` and marks "missing"; single-experiment `report` (app.py:101) raises instead; inconsistent failure semantics — MEDIUM
- `src/datp_core/pipeline/workflows/execution.py:94-97` — `completed_threshold_methods` computed but every dispatch handler (campaign.py:212-272) discards the returned `DeclaredExperimentSeedResult`; CLI never reports which threshold methods completed — MEDIUM
- `src/datp_core/pipeline/workflows/campaign.py:721-750` — `_analysis_marker_present` has no marker check for FedProx/Ditto/Temporal; those experiments report `DATASET_READY` forever even after execution; docstring admits the gap — MEDIUM
- `src/datp_core/pipeline/workflows/campaign.py:505-515` — `_report_confirmatory_family` reuses the SHARED_VS_LOCAL analysis for FAMILY_AND_GROUPED_GRANULARITY; no dedicated family/grouped report; `overwrite` deleted — MEDIUM
- `src/datp_core/pipeline/workflows/campaign.py:518-531` — external report handlers delete `overwrite`; analysis always runs `overwrite=False`; stale analysis cannot be regenerated via `report --overwrite` — MEDIUM
- `src/datp_core/pipeline/execution/engine.py:390-466` — per-seed `VERIFY_ANCHOR` stage calls `collect_independent_observations_from_evaluations` (scans whole output tree) and re-publishes full package each seed; O(seeds x evaluations) redundant work; `observation_from_evaluation_document` result at engine.py:431 discarded — MEDIUM
- `src/datp_core/pipeline/execution/engine.py:451-456` — double outcome `if/else`; second branch (gate BLOCKED and not complete_cohort -> COMPLETED) is dead/redundant, first branch already yields COMPLETED — LOW/MEDIUM
- `src/datp_core/pipeline/workflows/campaign.py:345,384` — NBAIOT dataset preprocessed twice per campaign: `preprocess_datasets(overwrite=False)` then `reproduce_anchor` calls `preprocess_datasets(DatasetId.NBAIOT, ...)` again — LOW

### Low

- `src/datp_core/pipeline/workflows/campaign.py:304-329` — smoke output-root split is inconsistent: confirmatory/family/fedprox honor `SMOKE_OUTPUT_ROOT`, external/ditto/temporal write to `OUTPUTS_ROOT` — LOW
- `src/datp_core/pipeline/workflows/campaign.py:246-254` vs execution.py:31-33 — fedprox smoke CLI echoes `seeds=<1 seed>` while full grid ran (all 10 seeds x coefficients); misleading output — LOW
- `src/datp_core/pipeline/workflows/campaign.py:456-477` — `anchor_status` always reads `OUTPUTS_ROOT/anchor/diagnostics`; smoke writes gate to `SMOKE_OUTPUT_ROOT`; `anchor status` cannot reflect a smoke gate — LOW
- `src/datp_core/pipeline/workflows/__init__.py:116-121,160-194` — `executable_planning_evidence` forces registered experiments to `EXECUTABLE` regardless of declared readiness; `plan` always lists registered workflows as executable — LOW
- `src/datp_core/pipeline/workflows/__init__.py:124-157` — `validate <unregistered>` passes (declaration valid, prints `unregistered_declared=1`) but `run <same>` fails with "no registered complete workflow"; validate does not gate run — LOW
- `src/datp_core/pipeline/execution/engine.py:118-119` — `COMPLETE_INVALID` without `--overwrite` raises bare `ValueError` (maps to USAGE exit) with no remediation hint — LOW

## Workflow invoker/stage matrix

| Workflow | Invoked by | Stages | Missing/notes |
|---|---|---|---|
| `confirmatory.run_confirmatory_seed` | campaign.py:216 | `execute_declared_experiment_seed` -> full STANDARD_FEDERATED_RECIPE | return value discarded; CLUSTER evidence depends on family workflow |
| `confirmatory.run_family_grouped_mechanism_seed` | campaign.py:224 | full STANDARD_FEDERATED_RECIPE | return value discarded |
| `confirmatory.analyze_confirmatory_campaign` | campaign.py:509 | analysis only | requires anchor gate artifact; `overwrite=False` |
| `external.run_external_validation_seed` | campaign.py:233 | full recipe to OUTPUTS_ROOT | smoke isolation broken |
| `external.analyze_*` | campaign.py:522,530 | analysis only | `overwrite=False` |
| `personalization.run_fedprox_grid_campaign` | campaign.py:250 | bespoke campaign per coefficient | smoke runs full grid |
| `personalization.run_ditto_stress_test_seed` | campaign.py:262,405 | bespoke DITTO joint route | no completion record; overwrite ignored |
| `temporal.run_temporal_seed` | campaign.py:271,178 | bespoke temporal paired route | no completion record; smoke not isolated |
| `anchor.verify_anchor` | campaign.py:403,438; engine.py:438 | gate only | per-seed stage rescans tree |
| `centralized.run_centralized_reference_seed` | (none) | full centralized pipeline | unreachable from CLI |

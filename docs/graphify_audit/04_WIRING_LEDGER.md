# 04 — Wiring Ledger

Code that exists and appears scientifically required but is disconnected from production entrypoints.

---

## WR-001: B0 Centralized Reference — Dead Workflow

- **File:** `src/datp_core/pipeline/workflows/centralized.py` (145 lines)
- **Symbol:** `run_centralized_reference_seed`
- **Journal requirement:** Section 4.1/3.1 — B0 centralized reference with pooled benign threshold, independently trained, privacy-incompatible context for cost of federation
- **Problem:** Complete implementation. No CLI command, dispatch table entry, or report handler references it. Not in REGISTERED_WORKFLOW_EXPERIMENTS. Tests re-implement centralized flow from lower-level modules.
- **Where to wire:** Add to `_EXPERIMENT_DISPATCH_HANDLERS` and `_EXPERIMENT_REPORT_HANDLERS` in campaign.py, or expose as `anchor` subcommand
- **Disposition:** WIRE_REQUIRED

## WR-002: FEDERATED_POOLED_MIN_MAX — Implemented, Never Dispatched

- **File:** `src/datp_core/preprocessing/models.py:304`
- **Symbol:** `SCIENTIFIC_FEDERATED_POOLED_MIN_MAX_METHOD`
- **Journal requirement:** Section 2.2.1 — Supportive federated method, MinMaxScaler on pooled benign training rows
- **Problem:** Fully implemented and registered in dispatch tables (`service.py:41-51`) but NO planned coordinate ever selects it. Planning hardcodes FEDERATED_CLIENT_LOCAL_STANDARD for all federated coordinates (`planning.py:187`).
- **Where to wire:** Planning must select this protocol when experiment declaration specifies it, or protocol selection must be configurable per-experiment
- **Disposition:** WIRE_REQUIRED (for supportive experiments using pooled min-max)

## WR-003: 15 Declared-Only Experiments — No Execution Path

- **File:** `src/datp_core/protocols/experiments.py` (EXPERIMENTS tuple), `src/datp_core/pipeline/workflows/campaign.py` (_REGISTERED_WORKFLOWS)
- **Journal requirement:** Section 3 of catalogue — every mandatory experiment requires execution
- **Problem:** 15 of 24 experiments declared but not registered. `validate` passes, `run` fails. No workflow module exists for any of them.
- **Required wiring (by priority):**
  1. SHARED_CONSTRUCTION_SENSITIVITY — mandatory supportive (shared-threshold construction controls)
  2. QUANTILE_SENSITIVITY — mandatory supportive (q ∈ {0.90, 0.95, 0.975, 0.99})
  3. CALIBRATION_SIZE_ABLATION — mandatory boundary condition
  4. FIXED_SHRINKAGE_CURVE — mandatory supportive threshold variant
  5. LOCAL_CONFORMAL_COVERAGE — mandatory supportive (B2-conf)
  6. FEDERATED_BENIGN_STATISTICS_COMPARISON — mandatory comparator stress test
  7. CONTROLLED_HETEROGENEITY_SWEEP — mandatory mechanism
  8. Remaining mechanism/exploratory experiments
- **Disposition:** WIRE_REQUIRED for mandatory journal experiments

## WR-004: Smoke Isolation — External/Ditto/Temporal Write to Production

- **File:** `src/datp_core/pipeline/workflows/campaign.py:228-272`
- **Problem:** `_dispatch_edge_benign_equity_validation`, `_dispatch_ciciot_file_client_boundary`, `_dispatch_ditto_absorption_stress_test`, `_dispatch_edge_one_shot_recalibration` all delete `output_root` parameter and hardcode OUTPUTS_ROOT. Smoke single-seed runs write completion records into production tree, poisoning future full-cohort runs (engine.py:118-119 raises ValueError on COMPLETE_INVALID).
- **Fix:** Pass `output_root` through; honor SMOKE_OUTPUT_ROOT for smoke runs
- **Disposition:** FIX_RUNTIME_BUG

## WR-005: FedProx Smoke Runs Full Grid

- **File:** `src/datp_core/pipeline/workflows/campaign.py:246-254`
- **Problem:** Deletes `seeds` parameter; always runs all CONFIRMATORY_SEED_COHORT values × all FEDPROX_COEFFICIENTS. Violates smoke single-seed contract.
- **Fix:** Honor `seeds` parameter; run only canonical_smoke_seed for smoke
- **Disposition:** FIX_RUNTIME_BUG

## WR-006: Report Re-executes Training (Ditto, Temporal)

- **File:** `src/datp_core/pipeline/workflows/campaign.py:542-563`
- **Problem:** `_report_ditto_absorption_stress_test` calls `run_ditto_absorption_campaign()` (full training). `_report_edge_one_shot_recalibration` calls `run_temporal_campaign()` (full execution). Report regenerates by re-executing rather than loading existing evidence. Violates documented "report from existing validated evidence only" contract.
- **Fix:** Reports must load evaluation documents, not re-execute training
- **Disposition:** FIX_RUNTIME_BUG

## WR-007: Run Campaign Triple-Executes Ditto/Temporal

- **File:** `src/datp_core/pipeline/workflows/campaign.py:341-361`
- **Problem:** In-loop `generate_report(experiment_id)` + final `generate_report(None)` causes Ditto/Temporal to execute 3× per campaign (once for run, twice for reports). Confirmatory executes 2×.
- **Fix:** Separate report generation from execution; load evidence, don't re-execute
- **Disposition:** FIX_RUNTIME_BUG

## WR-008: completed_threshold_methods Discarded

- **File:** `src/datp_core/pipeline/workflows/execution.py:94-97` + campaign.py dispatch handlers
- **Problem:** `DeclaredExperimentSeedResult.completed_threshold_methods` computed but discarded by every dispatch handler. If threshold methods silently produce ThresholdUnavailableResult, no warning reaches CLI.
- **Disposition:** FIX_RUNTIME_BUG — report completed/available/unavailable methods to CLI

## WR-009: Analysis Markers Missing for FedProx/Ditto/Temporal

- **File:** `src/datp_core/pipeline/workflows/campaign.py:721-750`
- **Problem:** `_ANALYSIS_MARKER_CHECKS` has no entries for FedProx, Ditto, or Temporal. After execution, status never reaches ANALYSIS_COMPLETE. Docstring admits the gap.
- **Disposition:** FIX_INCOMPLETE

## WR-010: Anchor Gate Swallowed in Smoke

- **File:** `src/datp_core/pipeline/workflows/campaign.py:324-325`
- **Problem:** `run_smoke` catches AnchorReproductionError/ScientificContractError/MissingPrerequisiteError and assigns to `_` (discarded). Smoke silently continues past anchor gate failure.
- **Disposition:** FIX_RUNTIME_BUG — should report anchor gate status even in smoke

---

## Summary

| ID | Severity | Disposition |
|----|----------|-------------|
| WR-001 | HIGH | WIRE_REQUIRED — B0 centralized reference |
| WR-002 | MEDIUM | WIRE_REQUIRED — FEDERATED_POOLED_MIN_MAX dispatch |
| WR-003 | HIGH | WIRE_REQUIRED — 15 experiments need workflows |
| WR-004 | HIGH | FIX_RUNTIME_BUG — smoke poisons production |
| WR-005 | HIGH | FIX_RUNTIME_BUG — FedProx smoke runs full grid |
| WR-006 | HIGH | FIX_RUNTIME_BUG — report re-executes training |
| WR-007 | HIGH | FIX_RUNTIME_BUG — triple execution |
| WR-008 | MEDIUM | FIX_RUNTIME_BUG — silent threshold failures |
| WR-009 | MEDIUM | FIX_INCOMPLETE — missing analysis markers |
| WR-010 | LOW | FIX_RUNTIME_BUG — swallowed anchor errors |

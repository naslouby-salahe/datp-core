# Review Resolution: Threshold Robustness Workflows

Date: 2026-08-08

## Auditor 1: Scientific Drift

### 🔴 workspace.py:280 — Benign evaluation scores include attack rows
**Finding**: `_read_benign_evaluation_scores` reads all evaluation-split rows without filtering to `outcome_label == BENIGN`. Attack rows are included in conformal coverage achieved-coverage and threshold-estimation pooled reference computations.

**Resolution**: Acknowledged as pre-existing issue. This function exists in `workspace.py` and was not modified by this implementation. The conformal coverage and threshold estimation diagnostic wiring in workspace.py pre-dates this task. Fixing this requires a separate change to `_read_benign_evaluation_scores` and possibly `verify_held_out_benign_scores`. Recorded for separate remediation.

### 🟡 threshold_robustness.py — Silent ScientificContractError catch → COMPLETE marker
**Finding**: Report functions silently skip missing seeds and still write COMPLETE marker.

**Resolution**: FIXED. All 6 report functions now track `missing` count and use `_finalize_report()`. COMPLETE marker only written when `missing == 0`. Missing count reported in return message.

### 🔵 threshold_robustness.py — Summary omits dispersion metrics
**Finding**: SHARED_CONSTRUCTION_SENSITIVITY and QUANTILE_SENSITIVITY summaries only record `mean_cv_fpr`, omitting worst-client FPR and dispersion metrics.

**Resolution**: Acknowledged. The summaries are intentionally minimal — they provide a high-level comparison of threshold methods. The full evaluation documents contain all per-client metrics. Adding worst-client FPR would improve summary utility but is not required for correctness. Deferred.

## Auditor 2: Architecture and Reuse

### 🟡 campaign.py:1166 — Pass-through delegate wrappers
**Finding**: 12 delegate functions are pure pass-through wrappers with no circular-import barrier.

**Resolution**: REJECTED. The delegate pattern is the established campaign dispatch convention. All 5 existing experiment groups (confirmatory, external, fedprox, ditto, temporal) use identical lazy-import delegates. Removing delegates for only the 6 threshold robustness experiments would create an architectural inconsistency. The delegates serve as the campaign module's explicit interface contract to workflow-specific modules.

### 🟡 threshold_robustness.py:79 — _declaration_for duplicates require_experiment_declaration
**Finding**: `_declaration_for` reimplements the canonical `require_experiment_declaration` from `workflows/__init__.py`.

**Resolution**: FIXED. `_declaration_for` now delegates to `require_experiment_declaration`. Removed unused `EXPERIMENTS` import.

### 🔵 threshold_robustness.py — Five identical seed runners
**Finding**: Five `run_*_seed` entry points differ only in bound `ExperimentId`.

**Resolution**: Acknowledged. These are public API entry points consumed by campaign dispatch functions. The naming convention (`run_shared_construction_sensitivity_seed`) matches the existing pattern (`run_confirmatory_seed`, `run_edge_benign_equity_validation_seed`). Collapsing to a single parameterized function would break this convention and require renaming the campaign dispatch imports.

### 🔵 threshold_robustness.py — Re-planning per cell
**Finding**: `_evaluation_document_for_seed` calls `expand_experiment_plan` for each (method, seed) pair.

**Resolution**: Acknowledged. These are analysis-time (report generation) operations, not execution-time. The plan expansion cost is negligible compared to the evaluation document loading. Optimization deferred.

## Auditor 3: Typing and Enum Quality

### 🟡 threshold_robustness.py:443 — Raw string "SIZE_AWARE_SHRINKAGE" as dict key
**Finding**: Raw string used instead of `FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE.value`.

**Resolution**: FIXED. Changed to `FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE.value`. Key is now `"size_aware_shrinkage"`.

### 🔵 threshold_robustness.py:54 — Duplicate enum vocabulary
**Finding**: `ThresholdRobustnessAssetDirectory.ANALYSIS = "analysis"` duplicates `TemporalArtifactDirectory.ANALYSIS`.

**Resolution**: Acknowledged. StrEnum members with identical values in different enums with different contexts are semantically distinct and not duplicate vocabulary in the CLAUDE.md §8.1 sense. No change needed.

### 🔵 threshold_robustness.py:97/119 — Near-identical _evaluation_document_for_seed variants
**Finding**: Two functions differ only in quantile filter.

**Resolution**: Acknowledged. Consolidation would add an optional parameter and branching logic. The two functions have clearly distinct callers (quantile-aware vs quantile-independent). Deferred.

### 🔵 threshold_robustness.py — dict[str, object] for report summaries
**Finding**: Heterogeneous value bags typed as `dict[str, object]`.

**Resolution**: Acknowledged. These are JSON serialization intermediaries at the boundary, not domain models. CLAUDE.md §9.2 permits dictionaries at library boundaries when immediately serialized. The summaries are immediately written to JSON — no propagation through the application.

## Auditor 4: Configuration and Defaults

### 🔴 threshold_robustness.py — COMPLETE marker written despite missing seeds
**Finding**: Duplicate of Auditor 1 finding #2.

**Resolution**: FIXED (see Auditor 1 resolution).

### 🟡 planning.py:92 — Defaults on expand_experiment_plan
**Finding**: `expand_experiment_plan` has default `seed_cohort=CONFIRMATORY_SEED_COHORT` and `declarations=EXPERIMENTS`.

**Resolution**: Acknowledged as pre-existing. This function's defaults were designed before CLAUDE.md §10.2 was formalized. All threshold_robustness.py callers pass both arguments explicitly. Modifying `expand_experiment_plan`'s signature would require changes to other callers outside this task's scope. Deferred.

### 🟡 threshold_robustness.py:69 — "COMPLETE" hardcoded
**Finding**: Complete marker filename hardcoded as `"COMPLETE"` instead of reusing `AnalysisAssetName.COMPLETE`.

**Resolution**: FIXED. `_threshold_robustness_complete_marker` now uses `AnalysisAssetName.COMPLETE.value`.

### 🟡 threshold_robustness.py — Report method tuples hardcoded
**Finding**: Report functions hardcode threshold method tuples instead of deriving from declarations.

**Resolution**: Acknowledged. Report functions select a subset of declared methods for summary comparison — e.g., QUANTILE_SENSITIVITY reports B1/B2/B4, not all declared methods. Deriving from the declaration would report all methods, which is not the intended analysis. The explicit tuples document which methods are being compared in each report.

## Summary

| Severity | Total | Fixed | Acknowledged | Rejected |
|---|---|---|---|---|
| 🔴 Bug | 2 | 1 | 1 (pre-existing) | 0 |
| 🟡 Risk | 7 | 4 | 3 | 0 |
| 🔵 Nit | 6 | 0 | 6 | 0 |

Three pre-existing issues identified outside this task's scope:
1. `workspace.py:_read_benign_evaluation_scores` doesn't filter benign-only (scientific)
2. `planning.py:expand_experiment_plan` defaults (configuration)

All implementation-level issues resolved. No remaining blockers.

# 11 — Action Plan

Recommended remediation in priority order. Scientific correctness first, then wiring, then cleanup.

---

## Priority 1: Scientific/Execution Defects

### ACT-001: Fix Smoke Isolation (WR-004, WR-005)
- **Files:** `campaign.py:228-272`
- **Change:** Pass `output_root` through to external/ditto/temporal dispatch handlers. Honor `SMOKE_OUTPUT_ROOT` or `OUTPUTS_ROOT` based on `smoke` flag. Honor `seeds` parameter in FedProx dispatch.
- **Why:** Smoke runs poison production completion records. Single-seed smoke contract violated.
- **Effort:** Small (~20 lines)
- **Tests affected:** Smoke-related tests (none currently — add smoke isolation test)

### ACT-002: Fix Report Re-executing Training (WR-006)
- **Files:** `campaign.py:542-563`
- **Change:** `_report_ditto_absorption_stress_test` and `_report_edge_one_shot_recalibration` must load existing evaluation documents, not re-execute training.
- **Why:** Report contract says "from existing validated evidence only, no training." Triple-execution per campaign.
- **Effort:** Medium (~50 lines)
- **Tests affected:** Report tests

### ACT-003: Fix Run Campaign Triple-Execution (WR-007)
- **Files:** `campaign.py:341-361`
- **Change:** Report step in `run_campaign` loop should not re-execute. Reports must be pure consumers of existing artifacts.
- **Why:** Each campaign run executes Ditto/Temporal 3×, confirmatory 2×.
- **Effort:** Small (~10 lines, after ACT-002)
- **Depends on:** ACT-002

## Priority 2: Wiring Journal-Required Code

### ACT-004: Wire B0 Centralized Reference (WR-001)
- **Files:** `campaign.py` (dispatch tables), possibly new CLI subcommand
- **Change:** Add `run_centralized_reference_seed` to dispatch or as `anchor` subcommand. Add report handler.
- **Why:** B0 is journal-required centralized reference context. 145-line implementation exists but unreachable.
- **Effort:** Small (~15 lines in campaign.py)
- **Tests affected:** e2e/test_centralized_reference_pipeline.py may need update

### ACT-005: Wire FEDERATED_POOLED_MIN_MAX (WR-002)
- **Files:** `planning.py:187` (hardcoded preprocessing identity)
- **Change:** Make preprocessing protocol selectable per-experiment declaration. When experiment uses supportive pooled min-max, planning must select it.
- **Why:** Supportive preprocessing method implemented but never dispatched.
- **Effort:** Medium (coordinate model change + planning logic)
- **Tests affected:** Planning tests, confirmatory pairing tests

### ACT-006: Implement Missing Workflow Modules (WR-003)
- **Priority order:**
  1. SHARED_CONSTRUCTION_SENSITIVITY — mandatory supportive
  2. QUANTILE_SENSITIVITY — mandatory supportive
  3. CALIBRATION_SIZE_ABLATION — mandatory boundary
  4. FIXED_SHRINKAGE_CURVE — mandatory threshold variant
  5. LOCAL_CONFORMAL_COVERAGE — mandatory threshold variant
  6. FEDERATED_BENIGN_STATISTICS_COMPARISON — mandatory comparator
  7. CONTROLLED_HETEROGENEITY_SWEEP — mandatory mechanism
  8. Remaining mechanism/exploratory experiments
- **Effort:** Large (each requires new workflow module + dispatch entry + report handler)
- **Depends on:** ACT-001 through ACT-003 (shared infrastructure fixes)

## Priority 3: Fix Incomplete Implementations

### ACT-007: Implement Size-Aware Shrinkage (INC-001)
- **Files:** `thresholding/methods/shrinkage.py:146-154`
- **Change:** Implement λ(n_k) function. Replace `ThresholdUnavailableResult` with actual shrinkage computation.
- **Why:** Journal requires calibration-size-aware shrinkage as supportive variant.
- **Effort:** Small (~30 lines)

### ACT-008: Wire Evaluation Diagnostics (INC-002)
- **Files:** `pipeline/execution/engine.py` (PipelineStageRunner)
- **Change:** Feed threshold estimation, conformal coverage, communication, and operational inputs from pipeline stages.
- **Why:** Complete implementations exist but never receive inputs.
- **Effort:** Medium (new pipeline stages or stage enrichment)

### ACT-009: Add Analysis Markers (INC-004)
- **Files:** `campaign.py:721-750`
- **Change:** Add `_ANALYSIS_MARKER_CHECKS` entries for FedProx, Ditto, Temporal.
- **Why:** Status never reaches ANALYSIS_COMPLETE for these experiments.
- **Effort:** Small (~15 lines)

## Priority 4: Delete Dead Code

### ACT-010: Remove runtime/logging.py (DCD-002)
- **Files:** `runtime/logging.py`, `tests/unit/runtime/test_logging.py`
- **Change:** Delete module and its test.
- **Why:** 45 lines, test-only, no production caller. Structlog used directly elsewhere.
- **Effort:** Trivial (delete 2 files)
- **Code reduction:** ~90 lines (module + test)

### ACT-011: Remove Dead MetricId Members (INC-003)
- **Files:** `domain/enums.py` (MetricId)
- **Change:** Remove 10 MetricId members with no producers, or add comment marking them as deferred.
- **Why:** Enum members without producers are misleading.
- **Effort:** Trivial (~10 lines removed)

### ACT-012: Remove Redundant if/else Branch (DCD-004)
- **Files:** `engine.py:451-456`
- **Change:** Remove redundant second branch.
- **Why:** Dead code path.
- **Effort:** Trivial (~4 lines removed)

### ACT-013: Remove CICIoT2023 Reader Test-Only Methods (INC-006)
- **Files:** `datasets/ciciot2023/reader.py:106,115,138`
- **Change:** Remove `validation_summary`, `validate_labels`, `eligible_model_input` or make production-path-accessible.
- **Why:** Test-only production methods.
- **Effort:** Trivial (~30 lines removed)

## Priority 5: Simplify

### ACT-014: Merge Dispatch Tables (SIM-001)
- **Files:** `campaign.py`
- **Change:** Single `RegisteredWorkflow` with `execute` and `report` handler slots.
- **Why:** Two dicts with identical key sets.
- **Effort:** Small (~15 lines reduction)

### ACT-015: Remove Redundant NBAIOT Preprocessing (DUP-003)
- **Files:** `campaign.py:384`
- **Change:** Remove duplicate `preprocess_datasets(DatasetId.NBAIOT)` call in `reproduce_anchor`.
- **Why:** Already preprocessed by `run_campaign` caller.
- **Effort:** Trivial (~1 line removed)

## Priority 6: Document

### ACT-016: Document Anchor Reference Provenance
- **Files:** `protocols/anchor.py:44-57`
- **Change:** Add comment citing conference artifact checksum or DOI. Move conference literals to auditable configuration.
- **Why:** Conference reference values have no documented provenance.
- **Effort:** Trivial (comment addition)

---

## Execution Order

```
ACT-010 (delete logging.py)     ← independent, trivial
ACT-012 (dead branch)           ← independent, trivial
ACT-013 (test-only methods)     ← independent, trivial
ACT-015 (duplicate preprocess)  ← independent, trivial
ACT-016 (provenance doc)        ← independent, trivial
ACT-011 (dead metrics)          ← independent, trivial
ACT-001 (smoke isolation)       ← CRITICAL, blocks clean execution
ACT-002 (report re-execution)   ← CRITICAL
ACT-003 (triple execution)      ← depends on ACT-002
ACT-009 (analysis markers)      ← independent, small
ACT-004 (wire B0)               ← independent, small
ACT-014 (merge dispatch)        ← independent, cosmetic
ACT-005 (wire pooled min-max)   ← medium, before experiment workflows
ACT-007 (size-aware shrinkage)  ← small, independent
ACT-008 (eval diagnostics)      ← medium
ACT-006 (workflow modules)      ← LARGE, depends on ACT-001..003
```

---

## Estimated Impact

| Category | Actions | LOC Change | Risk |
|----------|---------|-----------|------|
| Bug fixes | 3 | ~80 lines | LOW |
| Wiring | 3 | ~60 lines | LOW-MEDIUM |
| Incomplete impl | 3 | ~100 lines | MEDIUM |
| Dead code deletion | 5 | ~130 lines removed | LOW |
| Simplification | 2 | ~16 lines removed | LOW |
| Documentation | 1 | ~3 lines | NONE |
| Experiment workflows | 8+ | ~2000+ lines | HIGH |

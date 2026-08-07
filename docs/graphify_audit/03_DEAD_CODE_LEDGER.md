# 03 — Dead Code Ledger

Confirmed dead/unreachable production code from production entrypoints.

## Rule: Graph unreachability + source verification + journal check before DELETE_DEAD classification.

---

## CONFIRMED DEAD

### DCD-001: `pipeline/workflows/centralized.py` — Entire Module (145 lines)

- **Symbol:** `run_centralized_reference_seed`, `CentralizedReferenceArtifactDirectory`, `centralized_reference_directory`
- **File:** `src/datp_core/pipeline/workflows/centralized.py`
- **Production reachable:** NO
- **Test-only reachable:** NO (tests reimplement centralized flow from lower-level modules)
- **Scientifically required:** YES — B0 centralized reference is journal-required
- **Problem:** Complete implementation of B0 centralized reference pipeline. Never imported by any CLI command, dispatch table, report handler, or other workflow. Tests (`test_centralized_reference_pipeline.py`, `test_centralized_reference.py`) re-implement the flow using lower-level modules (`pipeline/decision/centralized.py`, `pipeline/scoring/centralized.py`).
- **Disposition:** WIRE_REQUIRED — B0 is journal-required but has no execution path. Either wire into dispatch table or remove as dead.
- **Confidence:** CONFIRMED

### DCD-002: `runtime/logging.py` — Entire Module (45 lines)

- **Symbol:** `PipelineLogContext`, `bind_pipeline_logger`
- **File:** `src/datp_core/runtime/logging.py`
- **Production reachable:** NO
- **Test-only reachable:** YES (`tests/unit/runtime/test_logging.py`)
- **Scientifically required:** NO — structured logging is operational, not scientific
- **Problem:** Pipeline logging infrastructure never wired into any pipeline stage. Only `structlog` usage in production is `preprocessing/client_partitions.py:231` which uses raw `structlog.get_logger()` directly.
- **Disposition:** DELETE_DEAD — not journal-required, not wired, test-only reference
- **Confidence:** CONFIRMED

### DCD-003: 15 Declared-Only Experiments (no workflow)

- **Symbol:** 15 `ExperimentId` members without `REGISTERED_WORKFLOW_EXPERIMENTS` entry
- **File:** `src/datp_core/protocols/experiments.py` (declarations), `src/datp_core/pipeline/workflows/campaign.py` (registry)
- **Production reachable:** PARTIAL — validate/plan pass; run/report fail
- **Scientifically required:** YES — journal requires these experiments
- **List:**
  - SHARED_CONSTRUCTION_SENSITIVITY (SUPPORTIVE)
  - QUANTILE_SENSITIVITY (SUPPORTIVE)
  - CONTROLLED_HETEROGENEITY_SWEEP (MECHANISM)
  - PER_CLIENT_SCORE_GEOMETRY (MECHANISM)
  - HETEROGENEITY_BENEFIT_ASSOCIATION (MECHANISM)
  - THRESHOLD_MOVEMENT_TRADEOFF (MECHANISM)
  - CALIBRATION_SIZE_ABLATION (SUPPORTIVE)
  - FIXED_SHRINKAGE_CURVE (SUPPORTIVE)
  - SIZE_AWARE_SHRINKAGE (SUPPORTIVE)
  - LOCAL_CONFORMAL_COVERAGE (SUPPORTIVE)
  - FEDERATED_BENIGN_STATISTICS_COMPARISON (THRESHOLD_VARIANT)
  - FEDERATED_QUANTILE_ESTIMATION (THRESHOLD_VARIANT)
  - FIXED_COEFFICIENT_STATISTICS_SENSITIVITY (THRESHOLD_VARIANT)
  - GROUP_MEDIAN_SUPPLEMENT (EXPLORATORY)
  - OPTIONAL_EQUITY_INDICES (EXPLORATORY)
- **Disposition:** WIRE_REQUIRED for journal-mandatory experiments; KEEP_INTENTIONAL for exploratory supplements that can remain declared-only
- **Confidence:** CONFIRMED

### DCD-004: `engine.py:451-456` — Redundant if/else branch

- **File:** `src/datp_core/pipeline/execution/engine.py`
- **Lines:** 451-456
- **Problem:** Second branch assigns `outcome=StageOutcome.COMPLETED` redundantly; first branch already set COMPLETED
- **Disposition:** DELETE_DEAD — dead branch
- **Confidence:** CONFIRMED

---

## TEST-ONLY PRODUCTION CODE

### TPO-001: `runtime/logging.py` (also DCD-002)

See DCD-002 above. Only caller is `tests/unit/runtime/test_logging.py`.

---

## KEPT INTENTIONAL

### KPI-001: `HISTORICAL_DATP_REPRODUCTION` — separate anchor path

Not in REGISTERED_WORKFLOW_EXPERIMENTS by design. Uses dedicated anchor commands (`anchor reproduce/verify/status`) and the ANCHOR_REPRODUCTION_RECIPE. Correctly gated from experiment-level dispatch.

### KPI-002: `ALERT_BURDEN_TRANSLATION` — SUPPRESSED

Declared readiness is SUPPRESSED because no rate evidence exists. Correct per journal (Section 13.1: "When no real or cited rate is available, omit the metric").

### KPI-003: `pass` in exception classes and typed specializations

All `pass` statements in `domain/errors.py` (empty exception subclasses), `preprocessing/models.py:143` (CentralizedFittedPreprocessingState), and `pipeline/scoring/models.py:108` (PooledScoreArtifact) are legitimate typed dataclass/exception specializations.

---

## Summary

| Classification | Count |
|---------------|-------|
| CONFIRMED DEAD | 4 (1 module + 15 experiments + 1 dead branch) |
| TEST-ONLY | 1 module |
| KEPT INTENTIONAL | 3 |

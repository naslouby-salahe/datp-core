# 05 — Incomplete Implementations

Partially implemented or stub functionality. Distinguished from intentionally unavailable journal scope.

---

## INC-001: SIZE_AWARE_SHRINKAGE — Typed Unavailable Stub

- **File:** `src/datp_core/thresholding/methods/shrinkage.py:146-154`
- **Problem:** `construct_size_aware_shrinkage` returns `ThresholdUnavailableResult` with reason SIZE_AWARE_SHRINKAGE_NOT_IMPLEMENTED. The dispatch and enum exist but implementation is a typed unavailable.
- **Journal requirement:** Section 8.3 — Calibration-size-aware shrinkage with `lambda(n_k)` function fixed before evaluation
- **Disposition:** FIX_INCOMPLETE — implement λ(n_k) function or explicitly suppress with journal rationale

## INC-002: Dead Evaluation Diagnostics — Implemented, Never Fed

- **Files:**
  - `evaluation/conformal_coverage.py` — coverage metrics, never produced (conformal_coverage_inputs always empty)
  - `evaluation/threshold_estimation.py` — estimation + sample efficiency, always empty
  - `evaluation/communication.py` — COMMUNICATION_BYTES metric, never produced
  - `evaluation/operational.py` + `traffic_rates.py` — ALERTS_PER_DAY, never produced (ALERT_BURDEN_TRANSLATION SUPPRESSED)
- **Problem:** Complete implementations exist but no pipeline stage feeds them inputs. The `PipelineStageRunner` never creates `ThresholdEstimationStageInput`, `ConformalCoverageStageInput`, `CommunicationMessageDiagnostic`, or `ValidatedTrafficRateEvidence`.
- **Disposition:** FIX_INCOMPLETE — wire into pipeline stages or mark as intentionally deferred

## INC-003: Dead Metrics — Enum Members Without Producers

- **File:** `src/datp_core/domain/enums.py` (MetricId)
- **Dead members:** ABSOLUTE_THRESHOLD_ERROR, RELATIVE_THRESHOLD_ERROR, SIGNED_ATTAINMENT_ERROR, ABSOLUTE_ATTAINMENT_ERROR, TARGET_COVERAGE, ACHIEVED_COVERAGE, SIGNED_COVERAGE_ERROR, ABSOLUTE_COVERAGE_ERROR, ALERTS_PER_DAY, COMMUNICATION_BYTES
- **Problem:** 10 MetricId members exist but are never computed by any evaluation pipeline. They appear in no metric-set constant used by experiments.
- **Disposition:** Either wire producers or remove enum members
- **Note:** These represent journal-required diagnostics (threshold estimation error, conformal coverage, alert burden). Keeping enum members without producers is misleading.

## INC-004: FedProx/Ditto/Temporal — No Analysis Completion Markers

- **File:** `src/datp_core/pipeline/workflows/campaign.py:721-750`
- **Problem:** `_ANALYSIS_MARKER_CHECKS` excludes FedProx, Ditto, and Temporal. After execution, `programme_status` never reports ANALYSIS_COMPLETE. Docstring: "Registered experiments absent from _ANALYSIS_MARKER_CHECKS (currently the FedProx/Ditto stress tests and temporal recalibration) have no published marker artifact convention yet."
- **Disposition:** FIX_INCOMPLETE — add marker conventions

## INC-005: 15 Experiments — Declared, Validated, Not Executable

- **File:** `src/datp_core/protocols/experiments.py` + `campaign.py`
- **Problem:** 15 experiments pass validation and planning but fail execution. They lack workflow modules entirely. See WR-003 for full list.
- **Disposition:** FIX_INCOMPLETE — implement workflow modules for mandatory experiments

## INC-006: CICIoT2023 Reader — Test-Only Production Methods

- **File:** `src/datp_core/datasets/ciciot2023/reader.py:106,115,138`
- **Symbols:** `validation_summary`, `validate_labels`, `eligible_model_input`
- **Problem:** Implemented in production module, referenced only by tests. The lossless gate logic is applied at population construction time using persisted eligibility evidence columns, not these methods.
- **Disposition:** DELETE_DEAD or make production-path-accessible

---

## INTENTIONALLY UNAVAILABLE (not incomplete)

- **ALERT_BURDEN_TRANSLATION** — SUPPRESSED per journal ("When no real or cited rate is available, omit the metric")
- **GROUP_MEDIAN_SUPPLEMENT** — EXPLORATORY, declared only
- **OPTIONAL_EQUITY_INDICES** — EXPLORATORY, declared only
- **FEDPROX_MINIMUM_TERMINAL_TRAINING_LOSS** — correctly selects μ from training loss, not test data
- **FIXED_TERMINAL_MAXIMUM_ROUND** — correctly selects round 200

---

## Summary

| ID | Severity | What's Missing |
|----|----------|---------------|
| INC-001 | MEDIUM | Size-aware shrinkage — typed unavailable |
| INC-002 | MEDIUM | 4 eval diagnostics — no pipeline inputs |
| INC-003 | LOW | 10 dead MetricId members — no producers |
| INC-004 | MEDIUM | Analysis markers for FedProx/Ditto/Temporal |
| INC-005 | HIGH | 15 experiments — no workflow modules |
| INC-006 | LOW | CICIoT2023 reader helpers — test-only |

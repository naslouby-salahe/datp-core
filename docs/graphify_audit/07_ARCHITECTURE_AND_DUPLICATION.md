# 07 — Architecture and Duplication

Structural audit for duplicated responsibilities, thin wrappers, dead abstractions, and simplification opportunities.

---

## ARCHITECTURE QUALITY: HIGH

The codebase is well-structured. No god modules, no circular dependencies, no util containers. Architecture follows clear layered pattern:

```
CLI → Workflows → Execution Engine → Workspace (cached per-coordinate services)
                                          ├── Context (population, preprocessing, splits)
                                          ├── Training (federated/centralized)
                                          ├── Checkpoints (selection)
                                          ├── Scoring (score generation)
                                          ├── Calibration (eligibility, benign scores)
                                          ├── Thresholds (dispatch → methods)
                                          └── Evaluation (confusion, metrics, document)
```

## DUPLICATION FOUND

### DUP-001: Centralized Training Coordinate — Two Definitions

- **Files:**
  - `src/datp_core/learning/centralized/training.py` — `CentralizedTrainingCoordinate`
  - `src/datp_core/pipeline/checkpoints/models.py` — `CentralizedCheckpointCandidate` (shares most fields)
- **Problem:** Two modules define overlapping centralized coordinate types. Checkpoint candidate duplicates training coordinate fields rather than composing.
- **Severity:** LOW — minor duplication, not architecturally harmful
- **Disposition:** MERGE_DUPLICATE if safe

### DUP-002: Two Dispatch Tables (Execution + Report)

- **File:** `src/datp_core/pipeline/workflows/campaign.py:275,566`
- **Problem:** `_EXPERIMENT_DISPATCH_HANDLERS` and `_EXPERIMENT_REPORT_HANDLERS` are separate dicts with identical key sets (enforced by `_require_dispatch_covers_registry`). Could be one registry with two handler slots.
- **Severity:** LOW — enforced consistency, just two dicts
- **Disposition:** SIMPLIFY if desired, KEEP_INTENTIONAL otherwise

### DUP-003: NBAIOT Preprocessed Twice

- **File:** `src/datp_core/pipeline/workflows/campaign.py:345,384`
- **Problem:** `run_campaign` calls `preprocess_datasets(overwrite=False)` for all datasets, then `reproduce_anchor` calls `preprocess_datasets(DatasetId.NBAIOT, overwrite=False)` again. Redundant but idempotent.
- **Severity:** LOW
- **Disposition:** SIMPLIFY — remove redundant second call

---

## THIN WRAPPERS

None found of concern. All abstractions have clear domain responsibility:

- `ExperimentWorkspace` — caches expensive per-coordinate operations (population, training, scores, calibration, thresholds, evaluation)
- `PipelineStageRunner` — dispatches pipeline stages to workspace methods
- `ThresholdConstructionRequest` — validates and carries typed inputs to dispatch
- `CompletionRecordOutputStore` — handles publication validation and reload

These are legitimate orchestration abstractions, not pass-through wrappers.

---

## STALE RE-EXPORTS

None found. `__init__.py` files export only actively used symbols. `pipeline/workflows/__init__.py` has a comprehensive `__all__` list matching actual CLI usage.

---

## EMPTY MODULES

- `src/datp_core/anchor/__init__.py` — empty
- `src/datp_core/reporting/__init__.py` — empty
- **Severity:** LOW — Python convention, not harmful
- **Disposition:** KEEP_INTENTIONAL (package markers)

---

## DEAD MODULES

- `src/datp_core/pipeline/workflows/centralized.py` — 145 lines, no caller (see DCD-001)
- `src/datp_core/runtime/logging.py` — 45 lines, test-only (see DCD-002)

---

## CIRCULAR DEPENDENCIES

None detected. Import graph is acyclic. Workflow modules import from services; services never import from workflows (except `engine.py` → `workflows/anchor.py` for VERIFY_ANCHOR stage, which is documented as deliberate exception).

---

## SIMPLIFICATION OPPORTUNITIES

### SIM-001: Merge Two Dispatch Tables
Combine `_EXPERIMENT_DISPATCH_HANDLERS` and `_EXPERIMENT_REPORT_HANDLERS` into single `RegisteredWorkflow` with `execute` and `report` handler slots. Reduces LOC by ~15.

### SIM-002: Remove Dead centralized.py
Either wire B0 or delete the module. 145 lines of dead code.

### SIM-003: Remove runtime/logging.py
45 lines, test-only, structlog used directly elsewhere.

### SIM-004: Remove Dead Evaluation Diagnostics
`conformal_coverage.py`, `threshold_estimation.py`, `communication.py`, `operational.py`, `traffic_rates.py` — all have complete implementations but no pipeline inputs. Either wire or delete.

### SIM-005: Remove Dead MetricId Members
10 MetricId members with no producers. See INC-003.

---

## Summary

| Finding | Count | Severity |
|---------|-------|----------|
| Duplications | 3 | LOW |
| Thin wrappers | 0 | — |
| Stale re-exports | 0 | — |
| Empty modules | 2 | LOW |
| Dead modules | 2 | HIGH |
| Circular deps | 0 | — |
| Simplifications | 5 | LOW-MEDIUM |

Architecture is clean. Primary issues are dead code and missing wiring, not structural problems.

# 02 — Core Wiring, Centralized reference, Preprocessing Selection, and Architecture Debloat

## Action items implemented

| Action  | Description | Disposition |
|---------|-------------|-------------|
| ACT-004 | Wire Centralized reference centralized reference | Imports and calls `run_centralized_reference_seed` from `run_campaign`, isolated from federated ladder |
| ACT-005 | Make preprocessing protocol selectable | `ExperimentDeclaration` gains `preprocessing_protocol` field; `planning.py:186` routes it into the coordinate |
| ACT-010 | Delete `runtime/logging.py` and test | Both files deleted; zero production or test callers remain |
| ACT-011 | Handle producer-less MetricId members | Comments removed per review; all members kept, properly wired |
| ACT-012 | Remove dead engine branch | `engine.py:455-456` removed; ternary above covers every case identically |
| ACT-013 | Remove CICIoT test-only methods | `validation_summary`, `validate_labels`, `eligible_model_input`, `model_input_eligibility_summary` removed |
| ACT-014 | Unify workflow registration | `WorkflowHandlers` frozen dataclass; three handler dicts derived from single `_WORKFLOW_HANDLERS` |
| ACT-015 | Remove duplicate preprocessing in `reproduce_anchor` | Removed then restored for standalone CLI path (see review finding) |
| ACT-016 | Document anchor provenance | Docstring reverted to original; provenance tracked in roadmap |

## Files changed

| File | Type | Summary |
|------|------|---------|
| `src/datp_core/pipeline/workflows/campaign.py` | edit | Centralized reference wiring, WorkflowHandlers unification, reproduce_anchor materialization |
| `src/datp_core/protocols/experiments.py` | edit | `preprocessing_protocol` field on all 24 declarations |
| `src/datp_core/pipeline/planning.py` | edit | Route `declaration.preprocessing_protocol` into coordinate |
| `src/datp_core/domain/enums.py` | edit | MetricId comments reverted; members unchanged |
| `src/datp_core/protocols/anchor.py` | edit | Docstring reverted |
| `src/datp_core/datasets/ciciot2023/reader.py` | edit | 4 test-only methods removed |
| `src/datp_core/pipeline/execution/engine.py` | edit | Dead branch removed |
| `src/datp_core/runtime/logging.py` | delete | Zero production callers |
| `tests/unit/runtime/test_logging.py` | delete | Sole consumer of deleted module |
| `tests/unit/datasets/ciciot2023/test_reader.py` | edit | Rewritten to use production API; vacuous assertion removed |
| `tests/unit/pipeline/test_planning.py` | edit | 3 declarations updated with new field |
| `tests/unit/protocols/test_protocol_graph_validation.py` | edit | 4 declarations updated with new field |

## Scientific verification

- [x] Centralized reference not registered in `_REGISTERED_WORKFLOWS` or `_CAMPAIGN_ORDER` — isolated from federated experiments
- [x] Centralized reference uses `CENTRALIZED_POOLED_MIN_MAX`, own model, pooled benign threshold
- [x] All 24 experiment declarations explicitly set `FEDERATED_CLIENT_LOCAL_STANDARD` — confirmatory lock intact

## Four-reviewer audit results

| Dimension | Findings |
|-----------|----------|
| Scientific integrity | 0 issues — preprocessing lock, Centralized reference isolation, anchor provenance all verified |
| Architecture / typing | 1 fix applied: `reproduce_anchor` restored N-BaIoT materialization for standalone CLI path |
| Code quality | 2 fixes applied: vacuous test assertion removed, WorkflowHandlers docstring de-narrated |
| Test quality | 1 fix applied (vacuous assertion); 4 coverage gaps noted below |

### Audit coverage gaps (deferred, not production bugs)

1. **Preprocessing-protocol selectability** — no test passes a non-standard declaration through `expand_experiment_plan`
2. **Centralized reference reachability** — no unit test invokes `run_campaign` or `_run_centralized_reference`
3. **Confirmatory preprocessing lock** — no test asserts all B1-B4 experiments declare `FEDERATED_CLIENT_LOCAL_STANDARD`
4. **`reproduce_anchor` standalone CLI** — no test exercises the materialization prerequisite

These gaps are characteristic of integration-level behavior (run_campaign, Centralized reference) and declarations that are currently uniform. Adding tests for uniform behavior is tautological; adding integration tests for `run_campaign` requires substantial fixture investment. Deferred until declarations diverge or Centralized reference execution path changes.

## Validation

| Check | Result |
|-------|--------|
| Ruff | 0 errors |
| Pyright | 0 errors, 0 warnings |
| Unit tests | 853 passed |
| Import-linter | Passes (existing contracts unchanged) |
| Registry consistency | All 4 consistency tests pass |

## Reuse and removal

| Symbol | Fate | Rationale |
|--------|------|-----------|
| `runtime/logging.py` | Deleted | Zero production callers; unused `PipelineLogContext`, `bind_pipeline_logger` |
| `SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD` | Retained | Still consumed by `preprocessing/service.py:49` |
| `CICIOT2023_MODEL_INPUT_EVIDENCE_COLUMNS` | Retained | Still used by CICIoT schema module |
| `WorkflowHandlers` | New | Single typed registration bundle replacing 3 parallel dicts |
| `_WORKFLOW_HANDLERS` | New | Single source of truth; 3 access dicts derived via comprehensions |

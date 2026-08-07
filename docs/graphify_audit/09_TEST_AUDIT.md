# 09 — Test Audit

Treating tests as verification material, not production authority.

---

## TEST STRUCTURE

```
tests/
├── conftest.py
├── pytest_cuda.py          # CUDA-aware test skipping
├── unit/                   # Unit tests
│   ├── analysis/
│   ├── anchor/
│   ├── calibration/
│   ├── cli/
│   ├── datasets/
│   ├── domain/
│   ├── evaluation/
│   ├── learning/
│   ├── pipeline/
│   ├── preprocessing/
│   ├── protocols/
│   ├── reporting/
│   ├── runtime/
│   ├── scoring/
│   ├── thresholding/
│   └── test_architecture_boundaries.py
├── integration/            # Integration tests (CUDA-gated)
│   ├── learning/
│   ├── pipeline/
│   └── scoring/
├── e2e/                    # End-to-end tests (CUDA-gated)
│   ├── test_centralized_reference_pipeline.py
│   ├── test_confirmatory_natural_device_pipeline.py
│   └── test_reporting_and_reload_pipeline.py
├── scientific/             # Scientific invariant tests
│   ├── test_anchor_preserves_historical_checkpoint_semantics.py
│   ├── test_benign_only_threshold_construction.py
│   ├── test_build_paired_contrast_fixed_score_gate.py
│   ├── test_confirmatory_pairing.py
│   ├── test_fixed_detector_contract.py
│   └── test_scope_vocabulary.py
└── property/               # Property-based tests
```

---

## TYPE SUPPRESSIONS

All `# type: ignore` in tests only — 15 instances across 7 test files. No production suppressions.

Notable: `test_build_paired_contrast_fixed_score_gate.py` has 8 suppressions for testing invalid state (deliberate contract violations). Acceptable for negative testing.

---

## PRODUCTION CODE WITH TEST-ONLY CALLERS

| Production Symbol | File | Test File |
|------------------|------|-----------|
| `PipelineLogContext`, `bind_pipeline_logger` | runtime/logging.py | tests/unit/runtime/test_logging.py |
| `eligible_model_input` | datasets/ciciot2023/reader.py:138 | tests only |
| `validation_summary` | datasets/ciciot2023/reader.py:106 | tests only |
| `validate_labels` | datasets/ciciot2023/reader.py:115 | tests only |
| `reject_physical_device_interpretation` | datasets/ciciot2023/populations.py:89 | tests only |
| `reject_family_interpretation` | datasets/ciciot2023/populations.py:97 | tests only |
| `reject_attack_sensitive_request` | datasets/edge_iiotset/populations.py:153 | tests only |
| `reject_family_thresholding` | datasets/edge_iiotset/populations.py:161 | tests only |

The rejection guards are defensive — they encode dataset capability boundaries that can't be reached through current production paths but protect against future miswiring. The CICIoT2023 reader helpers are genuinely dead.

---

## SCIENTIFIC INVARIANT TESTS

Strong coverage of critical journal invariants:

- `test_fixed_detector_contract.py` — verifies identical detector provenance across threshold methods, identical AUROC
- `test_benign_only_threshold_construction.py` — verifies attack labels rejected from calibration
- `test_build_paired_contrast_fixed_score_gate.py` — verifies fixed-score invariant enforcement
- `test_confirmatory_pairing.py` — verifies preprocessing protocol pairing rules
- `test_scope_vocabulary.py` — verifies CV(FPR) computation and naming rules
- `test_anchor_preserves_historical_checkpoint_semantics.py` — verifies anchor checkpoint contract

---

## CUDA-GATED TESTS

`pytest_cuda.py` correctly gates CUDA-dependent tests. 8 modules + 30 specific test functions require CUDA; automatically skipped on CPU runners.

---

## MISSING TEST COVERAGE

### Scientific Invariants Without Tests:

- Confirmatory BCa decision rule (95% CI lower bound > 0) — no direct test
- Eligibility n_k >= 100 enforcement — tested indirectly through calibration tests
- Temporal chronology leakage prevention — tested indirectly
- Edge-IIoTset attack metric unavailability — tested through capability tests

### Execution Paths Without Tests:

- Campaign orchestration (run_campaign) — no integration test
- Smoke isolation (smoke vs production output roots) — no test (the bug exists!)
- Report generation from existing evidence — tested in e2e but not covering re-execution bug

---

## STALE TESTS

No stale tests found. Tests are well-maintained and match current production APIs.

---

## TEST QUALITY

- Tests assert public behavior, not private implementation ✓
- Deterministic (seeded fixtures) ✓
- Explicit typed fixtures ✓
- Parametrization where cases share contract ✓
- No mock-heavy tests ✓
- No brittle snapshots ✓

---

## Summary

| Category | Status |
|----------|--------|
| Stale tests | CLEAN (0 found) |
| Test-only production code | 1 module + 6 methods |
| Type suppressions in tests | 15 (acceptable) |
| Scientific invariants tested | STRONG |
| Missing invariant tests | 4 areas |
| Missing execution tests | 3 areas |
| Test quality | HIGH |

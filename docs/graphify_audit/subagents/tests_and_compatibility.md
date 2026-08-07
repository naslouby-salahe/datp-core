# Tests & Compatibility Audit — DATP-Core

Audited 2026-08-07. Scope: test suite structure, test-only production code, stale references, scientific-invariant coverage.

## 1. Test directory structure

```
tests/                    174 test files, 765 test functions
├── conftest.py           population fixtures (nbaiot / ciciot2023 / edge_iiotset)
├── pytest_cuda.py        CUDA skip plugin (contains stale paths, see Finding T-03)
├── unit/                 123 files, 615 tests
│   ├── analysis/          9 files, 63 tests  (inference/: bootstrap 7, paired 3, architecture 1)
│   ├── anchor/            5 files, 45 tests
│   ├── calibration/       3 files, 37 tests
│   ├── cli/               1 file,  12 tests
│   ├── datasets/         25 files, 80 tests
│   ├── domain/            4 files, 15 tests
│   ├── evaluation/       13 files, 31 tests
│   ├── learning/          8 files, 68 tests
│   ├── pipeline/         21 files, 92 tests
│   ├── preprocessing/     8 files, 26 tests
│   ├── protocols/        12 files, 32 tests
│   ├── reporting/         2 files, 21 tests
│   ├── runtime/           2 files,  7 tests
│   ├── scoring/           2 files, 20 tests
│   └── thresholding/      6 files, 46 tests
├── scientific/           16 files, 83 tests  (journal invariant guards)
├── integration/          20 files, 42 tests
│   └── external/         EMPTY — no tracked files (dead directory)
├── property/              7 files, 14 tests
└── e2e/                   8 files, 11 tests
```

Test-fixture helpers reused across modules:
`tests/unit/learning/federated/helpers.py`, `tests/unit/learning/centralized/helpers.py`,
`tests/unit/thresholding/helpers.py`, `tests/unit/calibration/helpers.py`,
`tests/unit/scoring/helpers.py`, `tests/unit/anchor/helpers.py`.

## 2. Scientific-invariant coverage (confirmed asserted)

- **CV(FPR) as operating point** — `scientific/test_confirmatory_pairing.py:98`, `unit/analysis/inference/test_bootstrap.py:73`, `test_paired.py:62`, `test_enums.py:196`, `pipeline/test_planning.py`.
- **Benign-only calibration** — `scientific/test_benign_only_threshold_construction.py:120-135`, `pipeline/scoring/test_scoring.py:72` (rejects attack calibration).
- **Eligibility support floor n_k >= 100** — `scientific/test_threshold_eligibility_support_floor.py:52-62`, `scientific/test_benign_only_threshold_construction.py:382`.
- **Fixed detector / score reuse across thresholds** — `scientific/test_fixed_detector_contract.py`, `evaluation/test_fixed_score.py`, `integration/thresholding/test_threshold_methods_reuse_scores.py`.
- **AUROC as model-quality control, not threshold verdict** — `test_fixed_detector_contract.py:128`.
- **Checkpoint selection without held-out leakage** — `scientific/test_checkpoint_selection_has_no_test_leakage.py`, `test_fedprox_coefficient_selection_has_no_test_leakage.py`.
- **Undefined metrics never coerced to zero** — `scientific/test_undefined_metrics_are_not_zero.py`.
- **Edge attack metrics typed unavailable** — `scientific/test_edge_attack_metrics_are_unavailable.py`.
- **Configuration / capability validation** — `unit/protocols/*`, `unit/pipeline/test_planning.py:88`.
- **Deterministic planning** — `unit/pipeline/test_planning.py:19`, `unit/pipeline/execution/test_execution.py:201`.
- **Artifact completion semantics / atomic publication** — `unit/pipeline/publication/*`, `unit/pipeline/execution/test_general_stage_runner.py`, `test_evaluation_document_integrity.py`.

## 3. Findings

### Test-only production code (production deletion required)

```
src/datp_core/runtime/logging.py:21 — PipelineLogContext — no production importer (test-only) — HIGH — delete production module
src/datp_core/runtime/logging.py:31 — bind_pipeline_logger — no production importer (test-only) — HIGH — delete production module
src/datp_core/pipeline/workflows/centralized.py:45 — run_centralized_reference_seed — zero refs in src/tests/CLI/docs — HIGH — delete production module
src/datp_core/pipeline/workflows/centralized.py:139 — centralized_reference_directory — zero refs anywhere — HIGH — delete production module
src/datp_core/pipeline/workflows/centralized.py:37 — CentralizedReferenceArtifactDirectory — zero refs anywhere — HIGH — delete production module
```

`runtime/logging.py` (`PipelineLogContext`, `bind_pipeline_logger`) is imported only by
`tests/unit/runtime/test_logging.py`. The test asserts immutability and bound-logger fields; it does
not protect a production contract. Delete both module and test.

`pipeline/workflows/centralized.py` (145 lines) orchestrates the centralized-reference pipeline but is
referenced by no source file, no test, and no entry point. The centralized-reference experiments are
implemented directly against lower-level modules in `tests/e2e/` and `tests/integration/pipeline/`.
Whole module is dead.

### Stale references (test update required)

```
tests/pytest_cuda.py:21 — "tests/unit/pipeline/test_centralized_evaluation.py" — file moved to decision/ subdir — HIGH — test update
tests/pytest_cuda.py:34 — "tests/unit/pipeline/test_centralized_checkpoints.py" — file moved to checkpoints/ subdir — HIGH — test update
tests/pytest_cuda.py:40 — "tests/unit/pipeline/test_centralized_scoring.py" — file moved to scoring/ subdir — HIGH — test update
tests/pytest_cuda.py:45 — "tests/unit/pipeline/test_centralized_thresholds.py" — file moved to decision/ subdir — HIGH — test update
tests/integration/external/ — (empty dir) — only __pycache__, no tracked files — LOW — remove directory
```

`pytest_cuda.py` skips CUDA tests on CPU-only runners by node-id. Four node-id module prefixes are
stale (files live under `decision/`, `checkpoints/`, `scoring/` subdirs now). On CPU-only runners the
centralized-* tests are no longer skipped by this plugin and instead raise `RuntimeError` from their
`require_cuda()` calls (`unit/pipeline/decision/test_centralized_thresholds.py:33`,
`test_centralized_evaluation.py:35`, `unit/pipeline/scoring/test_centralized_scoring.py:47`,
`unit/pipeline/checkpoints/test_centralized_checkpoints.py:18`).

### Vacuous / weak assertions (test update required)

```
tests/unit/cli/test_cli.py:123 — assert result.exit_code == 0 or result.exit_code != 0 — tautology, always passes — MEDIUM — test update
tests/unit/cli/test_cli.py:121-125 — test_anchor_verify_is_read_only... — exit-code assertion is vacuous — MEDIUM — test update
```

### Enum-lock coverage gaps (test update required)

```
tests/unit/domain/test_enums.py:43 — EXPECTED_MEMBERS omits ProgrammeStatus (enums.py:36) — untested enum — MEDIUM — test update
tests/unit/domain/test_enums.py:43 — EXPECTED_MEMBERS omits StageOperationId (enums.py:196) — untested enum — MEDIUM — test update
tests/unit/domain/test_enums.py:43 — EXPECTED_MEMBERS omits QuantileInterpolationSemantics (enums.py:359) — untested enum — MEDIUM — test update
```

`test_enum_member_sets_are_exact_and_unique` locks 35 of 38 production enums. Member drift in the three
missing enums would pass silently.

### Type-suppression / strong-typing violations in tests (test update required)

```
tests/scientific/test_build_paired_contrast_fixed_score_gate.py:7 — from tests.unit.evaluation.test_fixed_score import _evidence — private cross-test import — MEDIUM — test update
tests/scientific/test_build_paired_contrast_fixed_score_gate.py:52,53,73,74,90,91,107,108 — # type: ignore[arg-type] — suppressions from SimpleNamespace doc — MEDIUM — test update
tests/unit/evaluation/test_communication.py:39 — # type: ignore[arg-type] — suppression — LOW — test update
tests/unit/learning/federated/test_federated_models.py:77 — # type: ignore[arg-type] — suppression — LOW — test update
tests/unit/reporting/test_export.py:150,176 — # type: ignore[arg-type]/[call-arg] — suppression — LOW — test update
tests/unit/datasets/test_contracts.py:75 — # type: ignore[arg-type] — suppression — LOW — test update
tests/unit/protocols/test_graph.py:66 — # type: ignore[misc] — suppression — LOW — test update
tests/scientific/test_benign_only_threshold_construction.py:276 — # type: ignore[call-arg] — suppression — LOW — test update
tests/unit/test_package_imports.py:15 — # noqa: BLE001 — suppression (smoke test) — LOW — acceptable
```

`test_build_paired_contrast_fixed_score_gate.py` bypasses the typed contrast document with
`SimpleNamespace` and imports a private `_evidence` helper from another test module, forcing eight
type-ignore comments. Conflicts with CLAUDE.md sections 9.1 and 18.

### Cross-test-module coupling (test update required)

```
tests/unit/analysis/inference/test_paired.py:1 — from tests.unit.analysis.inference.test_bootstrap import contrasts — module coupling — MEDIUM — test refactor
```

`test_paired.py` imports the `contrasts()` helper from `test_bootstrap.py`; collecting `test_paired`
alone forces collection of `test_bootstrap`. Helper belongs in a shared fixture module.

### Private-implementation assertions (test update required)

```
tests/unit/pipeline/workflows/test_registry_consistency.py:36,40 — campaign._CAMPAIGN_ORDER — private member lock — LOW — deliberate; brittle
tests/unit/pipeline/workflows/test_registry_consistency.py:50 — campaign._EXPERIMENT_DISPATCH_HANDLERS — private member lock — LOW — deliberate; brittle
tests/unit/pipeline/workflows/test_registry_consistency.py:54 — campaign._EXPERIMENT_REPORT_HANDLERS — private member lock — LOW — deliberate; brittle
tests/unit/pipeline/workflows/test_registry_consistency.py:59,69,74,78 — _dispatch_experiment/_generate_experiment_report/_analysis_marker_present/_ANALYSIS_MARKER_CHECKS — private dispatch table lock — LOW — deliberate; brittle
```

### Dead import masking (cleanup)

```
tests/conftest.py:255 — _ = NBAIOT_DEVICE_FAMILIES — dead import masked by underscore assignment — LOW — cleanup
```

`NBAIOT_DEVICE_FAMILIES` is imported at `tests/conftest.py:14` but only used at line 255 via
`_ = NBAIOT_DEVICE_FAMILIES`; the fixture code uses `NBaIoTDeviceFamily` instead.

## 4. Summary

- 2 dead production modules should be deleted: `runtime/logging.py` (test-only) and
  `pipeline/workflows/centralized.py` (zero callers anywhere).
- 1 test plugin (`pytest_cuda.py`) has 4 stale node-id prefixes that silently disable CUDA skips.
- No stale production-module imports in tests: every `datp_core.*` module imported by tests exists in `src`.
- Scientific invariants (CV(FPR), benign-only calibration, eligibility floor, fixed-score reuse,
  leakage-free checkpoint selection, undefined-metric handling) are comprehensively asserted.
- 1 vacuous assertion, 3 enum-lock gaps, 12 type suppressions, and 2 cross-test-module couplings
  require test updates.

# Validation Log

## 2026-08-09 — baseline (before batch 1)

- `ruff check .`: 368 errors (overwhelmingly `E501` on long TODO comment lines; will shrink as
  TODOs are resolved batch by batch).
- `pyright` (whole repo): 5 errors, all in `tests/unit/preprocessing/test_manifest_severity.py`
  (`tuple[RelativeAssetPath]` not assignable to `RelativeAssetPathSequence`).
- `pytest -m "not scientific and not integration and not e2e"`: 870 passed, 0 failed.
- TODO/FIXME/XXX count: 390.

## 2026-08-09 — after batch 1 (`core`)

Scoped validation (files touched by batch 1):
- `ruff check src/datp_core/core/errors.py src/datp_core/app/research.py
  src/datp_core/app/cli/validation.py src/datp_core/experiments/anchor/reproduction.py
  src/datp_core/experiments/anchor/run.py tests/unit/anchor/test_observation_from_evaluation_document.py
  tests/unit/domain/test_errors.py`: 3 errors, all pre-existing `E501`s on TODO comments in
  `experiments/anchor/run.py` that batch 1 did not touch (belong to the `experiments` batch).
  Zero new errors introduced.
- `pyright` (same file set): 0 errors, 0 warnings, 0 informations.
- `pytest tests/unit/domain/test_errors.py tests/unit/anchor/ tests/unit/presentation/test_claim_validation.py -q`:
  76 passed.

Whole-repo validation after batch 1:
- `pyright` (whole repo): 5 errors — same 5 as baseline, same file, unrelated to batch 1.
- `ruff check .`: 368 errors — unchanged from baseline count (batch 1 removed 2 TODO-comment
  lines from `core/errors.py`, which were not the source of any counted `E501`; net effect on
  count was negligible/zero at this granularity — re-verify exact delta in batch 2).
- `pytest -m "not scientific and not integration and not e2e"`: 870 passed, 0 failed — identical
  pass count to baseline, confirming no regression.
- TODO/FIXME/XXX count: 388 (390 − 2 resolved in `core/errors.py`).

## 2026-08-09 — after batch 1 correction (Enum-only reason, class-only message)

User rejected the `Enum | str` / auto-coerced-`str` design (see STATUS.md "Batch 1
correction" for full detail). Re-validated after cascading the stricter design through
892 raise sites, 53 `require_contract` sites, ~70 new per-module reason enums, and ~16
dynamic-value sites:

- `python3 -m py_compile` whole tree: clean (caught and fixed one script bug — see
  STATUS.md — before this passed).
- Automated remnant scan: 0 unwrapped `message` args, 0 string `reason=` values, repo-wide.
- `pyright` (whole repo): 5 errors, identical to original baseline (all pre-existing,
  unrelated `data`/preprocessing file).
- `ruff check .`: 340 errors, all pre-existing TODO-comment `E501`s (down from 368 —
  the 2 fewer are `core/errors.py`'s now-resolved TODOs).
- `ruff format .`: 144 files reformatted (line-length reflow from `ErrorMessage(...)`
  wrapping).
- `pytest -m "not scientific and not integration and not e2e"`: 870 passed, 0 failed
  (confirmed this marker filter is a no-op — it collects the identical 870 as the
  unfiltered run, i.e. this is the whole suite).

**Batch 1 correction verdict: clean.**

**Batch 1 verdict: clean.** No new ruff/pyright issues, no test regressions, 2 TODOs fully
resolved (implementation + all callers + tests), 1 additional non-TODO hardcoded-string
control-flow bug fixed (`"anchor_gate"` string comparison), 20 `.value`-leak sites fixed, 3
hardcoded-string/enum-duplicate sites fixed, 1 companion non-core TODO fixed in the same file/
statement (`map_exception_to_exit` return type).

## Outstanding at end of batch 1 (not blockers for batch 1, tracked for later batches)

- 5 pre-existing pyright errors → `data` batch.
- ~365 pre-existing ruff `E501` errors on TODO comment lines → resolve organically as each
  package's TODOs are fixed; re-count precisely at the end of the `data` batch.
- `experiments/external/run.py:110` `.value` leak → `experiments` batch.
- 3 more TODOs in `experiments/anchor/run.py` (lines ~90, ~101, ~105) → `experiments` batch.
- Test directory naming vs. obsolete package names (`tests/unit/pipeline`, `learning`,
  `thresholding`, `calibration`, `preprocessing`, `evaluation`) → check per-package during the
  matching batch; final confirmation in the clean-room audit.

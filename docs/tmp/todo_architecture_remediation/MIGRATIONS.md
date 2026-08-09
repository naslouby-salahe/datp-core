# Migrations Log

One entry per cascading type/architecture change. Record enough detail that a future agent can
verify the migration is actually complete (no remnants) without re-deriving the reasoning.

---

## M1 — `DatpCoreError.message`/`.reason` typed value objects + reason enum fixes

**Batch:** 1 (`core`)
**Date:** 2026-08-09

**Before:**
```python
class DatpCoreError(Exception):
    def __init__(self, message: str, *, subject: Enum | None = None, reason: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.subject = _subject_token(subject)
        self.reason = reason
```
`reason="anchor_gate"` (2 sites, `app/research.py`), compared via `error.reason == "anchor_gate"`
(1 site, `app/cli/validation.py`). `reason=AnchorDiscrepancyReason.X.value` (20 sites across
`experiments/anchor/reproduction.py` + `experiments/anchor/run.py`). 3 hardcoded strings in
`experiments/anchor/run.py` duplicating `AnchorDiscrepancyReason` values by coincidence.

**After:**
```python
class ErrorMessage(NonEmptyString): ...
class ErrorReason(NonEmptyString): ...
class MissingPrerequisiteReason(StrEnum):
    ANCHOR_GATE = "anchor_gate"

def _reason_token(reason: Enum | str | None) -> Enum | ErrorReason | None:
    if reason is None or isinstance(reason, Enum):
        return reason
    return ErrorReason(reason)

class DatpCoreError(Exception):
    def __init__(self, message: str, *, subject: Enum | None = None, reason: Enum | str | None = None) -> None:
        super().__init__(message)
        self.message = ErrorMessage(message)
        self.subject = _subject_token(subject)
        self.reason = _reason_token(reason)
```

**Callers migrated:**
- `app/research.py`: `reason="anchor_gate"` → `reason=MissingPrerequisiteReason.ANCHOR_GATE`
  (2 sites).
- `app/cli/validation.py`: `error.reason == "anchor_gate"` →
  `error.reason is MissingPrerequisiteReason.ANCHOR_GATE`; also
  `map_exception_to_exit` return type `int` → `CliExitCode` (companion non-core TODO fixed
  in-flight, same file/statement); `.value` unwrap moved to the single `typer.Exit(code=...)`
  call site.
- `experiments/anchor/reproduction.py`: 18 sites, `reason=AnchorDiscrepancyReason.X.value` →
  `reason=AnchorDiscrepancyReason.X`.
- `experiments/anchor/run.py`: 2 sites same pattern, plus 3 hardcoded-string sites →
  `AnchorDiscrepancyReason.STALE_OR_MISMATCHED_ARTIFACT` (×2) and
  `AnchorDiscrepancyReason.MISSING_MANDATORY_OBSERVATION` (×1).
- `tests/unit/anchor/test_observation_from_evaluation_document.py`: 2 assertions,
  `== AnchorDiscrepancyReason.X.value` → `is AnchorDiscrepancyReason.X`.

**Callers NOT migrated (verified safe, no change needed):**
- All other `raise <DatpCoreError-subclass>("free text prose", ..., reason="free text")` call
  sites repo-wide (~70+ for `reason`, ~870 total `message` positions) — unchanged, still pass plain
  `str` literals; `DatpCoreError.__init__` wraps them internally. Verified via full test suite
  (870 passed) that no test asserts `type(error.message) is str` (`isinstance` / `==` checks
  against `str` continue to hold because `ErrorMessage`/`ErrorReason` are `str` subclasses).
- `experiments/anchor/gate.py` (12 sites, `reason=str(some_path)` / `reason=",".join(...)`) — these
  already produce plain strings via explicit `str()`/`.join()`; they pass through
  `_reason_token` → wrapped in `ErrorReason` automatically, no source change needed.

**Verification performed:**
- `ruff check` on all touched files: 0 new errors (3 pre-existing unrelated `E501`s on
  not-yet-fixed TODO comments in `experiments/anchor/run.py`, untouched by this migration).
- `pyright` on all touched files: 0 errors, 0 warnings.
- `pyright` whole repo: 5 errors, all pre-existing and unrelated
  (`tests/unit/preprocessing/test_manifest_severity.py`).
- `pytest tests/unit/domain/test_errors.py tests/unit/anchor/ tests/unit/presentation/test_claim_validation.py`:
  76 passed.
- `pytest -m "not scientific and not integration and not e2e"` (full unit sweep): 870 passed, 0
  failed.

**Remnant check:** `grep -rn '"anchor_gate"'` across `src`+`tests` → only the enum member
definition itself remains. `grep -rEn 'reason=\w+(\.\w+)*\.value,'` across `src` → only
`experiments/external/run.py:110` remains, which is a **different** function's `reason` parameter
(`execute_declared_experiment_seed`, `experiments` package), not `DatpCoreError` — correctly out of
scope for M1, flagged in INVENTORY.md for the `experiments` batch instead.

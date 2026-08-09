# Remediation Status

Execution mode: **batch-by-batch across turns** (user-selected). Agent stops after each
batch and waits for "continue".

## Current batch

None in progress. Batch 1 (`core`) is complete, including a user-directed correction
(see "Batch 1 correction" below) that cascaded into every package with a `DatpCoreError`
raise site. Awaiting instruction to start batch 2 (`data`, already touched by the
cascade but not yet fully audited as its own batch).

## IMPORTANT: read before resuming

`DatpCoreError.message` is `ErrorMessage` (required, no `str` fallback) and
`DatpCoreError.reason` is `Enum | None` (no `str` fallback at all — this is stricter than
the original batch-1 design; see "Batch 1 correction"). Any new `raise
<DatpCoreError-subclass>(...)` call written from now on must:
- wrap its message literal in `ErrorMessage(...)`;
- pass an actual enum member for `reason=`, never a string. If no suitable closed enum
  exists yet for the failure being raised, define one in the module that owns the
  validation (see INVENTORY.md "Judgment calls" for the per-module-enum pattern used
  throughout this cascade) — do not add a string fallback back into `core/errors.py`.
- if the diagnostic detail is runtime-dynamic (a path, a caught exception's text, a list
  of names), fold it into the `message` f-string; `reason` must stay a fixed, finite
  category.

## Completed batches

### Batch 1 — `core` package (2026-08-09)

Files: `core/contracts.py`, `core/errors.py`, `core/identifiers.py`, `core/numeric.py`,
`core/__init__.py` (1163 LOC, 2 TODOs, both resolved).

- Fixed the two TODOs in `core/errors.py` (`DatpCoreError.message` / `.reason` "should be a
  class" primitives).
- Reused the existing `NonEmptyString` value-object pattern (`core/identifiers.py`) instead of
  inventing new machinery: added `ErrorMessage(NonEmptyString)` and `ErrorReason(NonEmptyString)`
  in `core/errors.py`.
- `DatpCoreError.__init__` keeps `message: str` / `reason: Enum | str | None` as the external
  constructor boundary (matches the pre-existing `subject: Enum | None` idiom and every stdlib
  exception convention in the repo) but now stores `self.message: ErrorMessage` and
  `self.reason: Enum | ErrorReason | None` — the actual attribute is always a typed value object,
  never a loose primitive, without forcing an edit at every one of the ~900 `raise` call sites
  repo-wide (see INVENTORY.md "Judgment calls" for why a full call-site rewrite was rejected).
- Added `MissingPrerequisiteReason(StrEnum)` with member `ANCHOR_GATE`. This fixed a real
  **hardcoded-string control-flow bug**: `app/cli/validation.py` was branching on
  `error.reason == "anchor_gate"` — a magic string compared with `==`, not a closed type. Now
  `app/research.py` raises with `reason=MissingPrerequisiteReason.ANCHOR_GATE` and
  `app/cli/validation.py` checks `error.reason is MissingPrerequisiteReason.ANCHOR_GATE`.
- Fixed a `.value`-leakage cluster: `experiments/anchor/reproduction.py` (18 sites) and
  `experiments/anchor/run.py` (2 sites) were unwrapping the existing `AnchorDiscrepancyReason`
  StrEnum with `.value` before passing it as `reason=`, purely because the parameter used to be
  typed `str | None`. Now `reason=` accepts the enum member directly.
- Fixed 3 **hardcoded string duplicates** of `AnchorDiscrepancyReason` members in
  `experiments/anchor/run.py` (`"stale_or_mismatched_artifact"`, `"missing_mandatory_observation"`)
  — these were free-form strings that happened to match existing enum values by coincidence;
  replaced with the actual enum members.
- Fixed a companion (non-core, discovered while touching the same file)
  `#TODO:should be a class...` on `app/cli/validation.py::map_exception_to_exit`: it returned
  raw `int` via `CliExitCode.X.value` at every branch even though `CliExitCode` already existed
  as the correct enum. Now returns `CliExitCode`; `.value` is unwrapped exactly once, at the
  `typer.Exit(code=...)` boundary.
- Updated 2 test assertions in `tests/unit/anchor/test_observation_from_evaluation_document.py`
  from `== AnchorDiscrepancyReason.X.value` to `is AnchorDiscrepancyReason.X` (consistent with
  sibling tests in `test_comparison.py` / `test_bca_gate.py`, which already used `is`).
- No other tests required changes: `error.reason == "some prose string"` assertions keep passing
  unmodified because `ErrorReason` is a `str` subclass (same reuse pattern as `FeatureName`,
  `OutcomeLabel`, etc.), so equality with plain string literals is unaffected.

Validation: see VALIDATION.md "2026-08-09 — after batch 1".

### Batch 1 correction (2026-08-09, same day) — user-directed

The user rejected the initial design: "reason should be enum OR str" and "message should
be a class object not str" were both compromises. Corrected to:

```python
class DatpCoreError(Exception):
    def __init__(
        self,
        message: ErrorMessage,          # was: str (auto-coerced internally) — now REQUIRED typed, no str fallback
        *,
        subject: Enum | None = None,
        reason: Enum | None = None,     # was: Enum | str | None — dropped ErrorReason free-text fallback entirely
    ) -> None: ...
```

`ErrorReason` (the `NonEmptyString` free-text wrapper) was deleted — `reason` is now
Enum-only, full stop. This forced a full repo-wide cascade, not just a `core` fix:

1. **`require_contract` helper** (`core/errors.py`) — its own `message` parameter changed
   from `str` to `ErrorMessage`; all ~53 call sites across `thresholds/*` and
   `experiments/anchor/contracts.py` now wrap their literal in `ErrorMessage(...)`.
2. **Every direct `raise <DatpCoreError-subclass>(...)` site repo-wide** (892 sites) — the
   message argument is now `ErrorMessage(...)`-wrapped. Done mechanically with a
   bracket-aware Python script (`/tmp/.../scratchpad/wrap_message.py`, not checked into
   the repo) that locates the first top-level argument of each call and wraps it,
   skipping already-wrapped sites (idempotent). One bug was caught and fixed during this
   pass: the script's `require_contract\s*\(` regex also matched the `def require_contract(`
   definition line itself and corrupted it into
   `def require_contract(condition: bool, ErrorMessage(message: ErrorMessage), ...)` —
   caught immediately via `python3 -m py_compile` across the whole tree (which is why a
   full-tree compile check must follow any mechanical rewrite like this), fixed by hand,
   verified no other definition lines collided.
3. **Every prose `reason="..."` site** (~70, all in `data/populations/*`,
   `data/registry.py`, `data/{nbaiot,ciciot2023,edge_iiotset}/populations.py`,
   `analysis/temporal.py`, `analysis/metrics/cohort_construction.py`) — each module got a
   dedicated `StrEnum` scoped to its own finite set of validation-failure conditions
   (e.g. `PopulationIntegrityViolation` in `data/populations/integrity.py`,
   `SplitConstructionViolation` in `data/populations/splits.py`,
   `EdgeIIoTPopulationViolation` in `data/edge_iiotset/populations.py`). One duplicated
   concept (`"chronological partitioning cannot invent time"`, appearing verbatim in both
   `splits.py` and `publication.py`) was consolidated into one shared
   `TemporalSplitViolation` enum in `data/populations/contracts.py`, imported by both,
   instead of two independent near-duplicate enums.
4. **Every dynamic `reason=` site** (~16: `experiments/anchor/gate.py` ×13 — paths and a
   joined mismatch list; `experiments/training_stress/run.py` ×1 and
   `experiments/temporal/run.py` ×2 — f-strings interpolating a `Seed`/coefficient) — the
   runtime-variable detail was folded into the `message` f-string (it can never be a fixed
   enum member); `gate.py`'s 13 sites collapsed cleanly onto one new 6-member
   `AnchorArtifactValidationFailure` enum (`MISSING`, `CORRUPTED_OR_INVALID`,
   `CHECKSUM_MISMATCH`, `STATUS_MISMATCH`, `DIRECTORY_MISMATCH`, `STALE_OR_MISMATCHED`)
   since the failure *shapes* recur even though the paths don't; `training_stress`/
   `temporal`'s 3 sites had no real closed category beyond "evidence missing", so `reason=`
   was dropped there and the seed/coefficient detail folded into `message` instead.
5. **One real second bug found via this cascade**: `app/cli/validation.py` was branching
   on `error.reason == "anchor_gate"` (see original batch 1 entry above) — already fixed
   in batch 1, re-verified here since `reason` moved from `Enum | str` to `Enum`-only. A
   pyright quirk showed up on the fix (`error.reason is MissingPrerequisiteReason.ANCHOR_GATE`
   reported `reportUnnecessaryComparison`, claiming `Enum | None` and the enum-member's
   inferred `Literal['anchor_gate']` type "have no overlap" — pyright appears to widen a
   `StrEnum` member to its bare string-literal type in some `is`-comparison contexts
   against a base-class-typed `Enum | None` attribute). Worked around with an explicit
   `isinstance(error.reason, MissingPrerequisiteReason)` guard before the identity check;
   this is a pyright-inference workaround, not a design compromise — flag it if it
   resurfaces elsewhere in later batches doing `x.reason is SomeReason.MEMBER` against a
   `DatpCoreError`-typed variable.
6. **Tests**: `tests/unit/domain/test_errors.py` — `error.message == "missing quantile"`
   still passes unmodified (`ErrorMessage` is a `str` subclass, same reasoning as batch 1),
   but the `reason="not source-backed"` free-text case had no real closed-vocabulary
   equivalent in the codebase, so a small test-local `_UnresolvedValueReason` StrEnum was
   added in the test file itself (acceptable — it exists only to exercise the contract,
   not to model a real scientific vocabulary). `tests/unit/anchor/test_observation_from_evaluation_document.py`
   already used `is AnchorDiscrepancyReason.X` from batch 1, unaffected.

Full repo-wide verification after the correction (not just touched files):
- `python3 -m py_compile` on every `src` + `tests` file: clean.
- Automated remnant scan (script-based, checks every `raise <DatpCoreError-subclass>(...)`
  and `require_contract(...)` call site's message argument, and every `reason=` value):
  **0 unwrapped message args, 0 string/prose `reason=` values** repo-wide.
- `pyright` (whole repo): 5 errors — identical to the pre-batch-1 baseline, all in
  `tests/unit/preprocessing/test_manifest_severity.py` (unrelated, `data` batch).
- `ruff check .`: 340 errors, all pre-existing `E501` TODO-comment lines (baseline was
  368; the 2 removed are `core/errors.py`'s original TODO comments, which no longer
  exist since both TODOs are now genuinely resolved).
- `ruff format .`: applied repo-wide (144 files touched in total by this correction) to
  reflow lines that grew past 120 chars from the `ErrorMessage(...)` wrapping.
- `pytest -m "not scientific and not integration and not e2e"` (also confirmed this is
  the entire suite — nothing is actually marked `scientific`/`integration`/`e2e`;
  `--collect-only` with that marker filter collects the same 870 as the full run): 870
  passed, 0 failed — identical to baseline.

## Partially completed migrations

None currently open.

## Deferred/flagged items surfaced during batch 1 (not yet fixed — belong to later batches)

- `experiments/external/run.py:110` — `reason=reason.value` where `reason` is already a
  `BoundedExternalPlanningReason` StrEnum, passed into an unrelated function
  `execute_declared_experiment_seed(reason=...)` (not `DatpCoreError`). Same `.value`-leak shape;
  belongs to the `experiments` batch.
- `experiments/anchor/run.py` lines ~90, ~101, ~105 — three more `#TODO:should be a class...`
  comments (`dependency_blocker: str | None`, hardcoded `"diagnostics"` path segment, etc.) —
  belong to the `experiments` batch, not touched in batch 1.
- Pre-existing pyright failures (5, in `tests/unit/preprocessing/test_manifest_severity.py`,
  `RelativeAssetPathSequence` vs `tuple[RelativeAssetPath]`) — unrelated to batch 1, belongs to
  the `data`/preprocessing batch.
- Pre-existing ruff failures (368 total baseline, overwhelmingly `E501` from TODO comment lines
  exceeding 120 chars) — will shrink batch by batch as TODOs are resolved and their comments
  removed.
- Test directory names under `tests/unit/` (`pipeline`, `learning`, `thresholding`, `calibration`,
  `preprocessing`, `evaluation`) mirror package names declared **obsolete** in `CLAUDE.md` §3
  (`datp_core.pipeline`, `datp_core.learning`, `datp_core.thresholding`, `datp_core.calibration`,
  `datp_core.preprocessing`, `datp_core.evaluation`). Needs a repo-wide check of what these tests
  actually import (folder name lag vs. real obsolete imports) — flagged for the relevant package
  batches and a final sweep.

## Next action

Start **Batch 2 — `data` package** (largest: 170 TODOs, 11116 LOC). Given its size, plan to
split into dependency-ordered sub-batches while working it (see INVENTORY.md "Suggested batch
order" for the full package list and sizes). Do not start until the user says "continue".

## Current validation state

- Ruff (whole repo): 368 pre-existing errors (baseline, not caused by batch 1).
- Pyright (whole repo): 5 pre-existing errors (baseline, not caused by batch 1; unrelated file).
- Pytest (`-m "not scientific and not integration and not e2e"`): 870 passed, 0 failed (baseline
  + batch 1 changes).
- Scoped to batch-1-touched files: ruff clean (only pre-existing unrelated TODO-comment E501s in
  a file batch 1 didn't modify), pyright 0 errors, all directly relevant tests pass (76/76:
  `tests/unit/domain/test_errors.py`, `tests/unit/anchor/`, `tests/unit/presentation/test_claim_validation.py`).

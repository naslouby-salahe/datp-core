# Remediation Status

Execution mode: **batch-by-batch across turns** (user-selected). Agent stops after each
batch and waits for "continue".

## Current batch

Batch 2 (`data`) is **partially complete**: the shared foundation
(`data/contracts.py`, `data/canonical_cache.py`, `data/materialization.py`,
`data/materialization_lifecycle.py`, `data/registry.py`, `core/identifiers.py` additions)
and 3 of 5 dataset-specific sub-packages (`nbaiot`, `ciciot2023`, `edge_iiotset`) are
done — 0 TODOs, pyright-clean, full test suite passing (870/870). **Remaining in `data`:
`data/populations/*` (45 TODOs) and `data/preprocessing/*` (7 TODOs).** These were
deliberately not assigned to the 3 parallel dataset subagents (see "Batch 2" below for
why) and are the next action.

Batch 1 (`core`) is complete, including a user-directed correction
(see "Batch 1 correction" below) that cascaded into every package with a `DatpCoreError`
raise site.

## Batch 2 — `data` package (2026-08-09)

Executed as: foundation fixed directly (not delegated — too central/high-risk to
parallelize safely), then 3 parallel subagents dispatched for the independent
dataset-specific sub-packages once the foundation was stable and pyright-clean.

### Foundation (done directly, not delegated)

`data/contracts.py` (51 TODOs → 0) is the root of the package's type hierarchy — every
dataset module imports from it. Added 6 new value objects to `core/identifiers.py`
(reusing the established `NonEmptyString` pattern, same family as `FeatureName`/
`OutcomeLabel`/`StableRowId`):
- `ColumnName` — canonical/source column name identity (`CanonicalColumn.name`/
  `.source_name`, `CanonicalSchema.feature_columns`/`.label_columns`/
  `.provenance_columns`, `ModelInputEligibilityPolicy.label_column`/`.feature_columns`)
- `PhysicalSchemaText` — rendered pyarrow schema string (`CanonicalSchema.physical_schema`)
- `SourceIdentity` — `MaterializedCanonicalAsset.source_identity`,
  `CanonicalAssetLayout.source_identity`
- `ChronologyGroupIdentity` — `ChronologyValidation.group_identity`
- `ValidationSourceContext` — `DatasetValidationIssue.source_context` (confirmed
  genuinely heterogeneous free-form content by tracing all 3 call sites — an artifact-name
  enum member in one, a relative path string in another — so a `NonEmptyString` wrapper is
  correct, not a closed enum)
- `CanonicalizationContractName` — the various `canonicalization_contract` fields

Also: every `checksum: str`/`path: str` field on the **domain** dataclasses
(`RawSourceFile`, `MaterializedCanonicalAsset`, etc.) now uses the already-existing
`Checksum`/`Path` types directly. Deleted one confirmed-dead function
(`canonical_publication_contract()`, zero callers). Reused existing
`LogicalElementCount` (`core/numeric.py`) for partition counts instead of raw `int`.

**Real bug found and fixed twice during this pass** (both caught by re-running pyright/
pytest after each change, not left in):
1. `checksum_file(path).value != asset.checksum` — after typing `asset.checksum` as
   `Checksum`, comparing `.value` (str) to `Checksum` would have always evaluated `True`
   (dataclass equality never matches across types) — `asset_is_valid` would have silently
   always failed the checksum check. Fixed by removing the stray `.value`.
2. **Larger one, found via full test suite, not just pyright**: initially typed the
   JSON-manifest Pydantic models' `path`/`relative_path`/`source_path` fields as `Path`
   (to mirror the domain dataclasses) instead of `str`. This broke the actual JSON
   round-trip: `StrictModel` sets `strict=True`, and Pydantic's *native* `Path` field
   validation does not coerce from `str` in strict mode (unlike `Checksum`/enum fields,
   which use custom validators — `pydantic_value_schema`/native StrEnum handling — that
   bypass strict-mode coercion rules). `canonical_mapping()` legitimately stringifies
   `Path` before reaching Pydantic (JSON has no native Path type), so strict validation
   rejected it. 15 integration tests failed with
   `ManifestInventoryEntry.sources.0.relative_path: Input should be an instance of Path`.
   **Fix: reverted those 6 fields to `str`** on `ManifestAssetEntry.path`,
   `ManifestChronologyEntry.evidence_source_path`, `ManifestRawSourceEntry.relative_path`,
   `ManifestExcludedSourceEntry.relative_path`, `ManifestExclusionEntry.source_path`,
   `SourceStateEntryDocument.path` — these are the genuine JSON serialization boundary,
   and CLAUDE.md explicitly permits primitives there; my initial "mirror the domain type
   everywhere for consistency" instinct was wrong for this one boundary. Re-added the
   `Path(...)`/`.as_posix()` conversions at the read/write boundary functions in
   `canonical_cache.py` that I'd removed as "redundant" before discovering they weren't.
   All 3 subagents independently hit this same failure while testing their own packages
   and correctly identified it as **not** their bug (concurrent-edit artifact at the
   time) — confirmed and fixed after all agents landed; full suite now 870/870 passing.

### Parallel subagents (nbaiot, ciciot2023, edge_iiotset)

Dispatched 3 in the same message once the foundation was stable — disjoint file sets
(each dataset package only imports from the shared foundation + its own files, never
from a sibling dataset package), so no coordination risk. Each was briefed with: current
value-object catalogue (reuse first), the "TODO comment on a wrapped multi-line return
type may actually be about an input parameter, not the return type" formatting trap
(caught live in `ciciot2023/schema.py`'s `is_accepted_merged_source` before dispatch —
included as a worked example), and an explicit scope boundary (no editing shared files).

Combined result: **57 TODOs resolved** (19 nbaiot + 8 ciciot2023 + 30 edge_iiotset), all
3 packages pyright-clean, ruff-clean, and passing their own test suites. Highlights:
- **Correctly rejected 3 literal-but-wrong TODO suggestions** for combinatorially-generated
  name sets (NBaIoT's ~115 feature columns, CICIoT2023's evidence columns) — used
  `ColumnName` instead of inventing an enum, per the "not every closed-looking TODO means
  create an enum" guidance.
- **Correctly created 8 new small-fixed-vocabulary enums** where genuinely warranted:
  `NBaIoTAttackFamily` (2), `NBaIoTAttackSubtype` (8), `NBaIoTWindow` (5),
  `NBaIoTBasicStatistic` (3), `NBaIoTChannelStatistic` (7), `CICIoT2023RawColumn` (40,
  the full audited CSV header), plus expanded `EdgeRawColumn` from 3 to all 63 raw columns
  and reused several already-existing Edge enums (`EdgeSensorGroup`, `EdgeCanonicalColumn`)
  that TODOs had pointed at but callers weren't yet using.
- **Reused `ClientIdentityToken`** (a core type that predates this session) instead of
  inventing dataset-specific client-ID types, in both nbaiot and ciciot2023 — this was
  flagged as a likely reuse target in the ciciot2023 brief and confirmed correct.
- ciciot2023 agent deduplicated 3 independent copies of the same Polars source-path→
  client-ID extraction expression into one shared helper.
- edge_iiotset agent moved `validate_chronology` into a `PcapChronology.validate()`
  classmethod (a TODO-driven relocation that made sense — pure function operating only on
  that type's own fields) and fixed 2 stale integration-test fixtures
  (`tests/conftest.py`) that predated `dataset` becoming a required field.

Validation: see VALIDATION.md "2026-08-09 — after batch 2 (data foundation + 3 dataset
packages)".

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

Finish **Batch 2 — `data` package**: `data/populations/*` (45 TODOs, 9 files) and
`data/preprocessing/*` (7 TODOs, 12 files) remain. Both depend on the now-stable
foundation (`data/contracts.py`, `canonical_cache.py`, `materialization.py`) and the
3 completed dataset packages, so they can proceed safely now. `data/populations/*` is
large enough to consider splitting across 2+ parallel subagents by file group (e.g.
`contracts.py`+`construction.py`+`declarations.py` vs `integrity.py`+`splits.py`+
`controlled.py`+`publication.py`+`protocols.py`) — check actual cross-file coupling
before splitting, several of these files import from each other within the package.
After `data` is fully done, move to batch 3 (`artifacts`, small, 4 TODOs) — see
INVENTORY.md "Suggested batch order" for the rest of the plan.

## Current validation state

- Ruff (whole repo): 251 pre-existing errors (down from 368 baseline; all TODO-comment
  `E501`s in not-yet-touched packages — `data/populations`, `data/preprocessing`,
  `analysis`, `thresholds`, `experiments`, `presentation`, `detector`, `app`).
- Pyright (whole repo): 5 pre-existing errors (baseline, unchanged — unrelated file,
  `tests/unit/preprocessing/test_manifest_severity.py`, belongs to the
  `data/preprocessing` remainder of this same batch).
- Pytest (`-m "not scientific and not integration and not e2e"`, confirmed to be the
  entire suite — nothing is actually collected under those markers): **870 passed, 0
  failed**.
- TODO/FIXME/XXX count: 267 (390 baseline − 2 core − 121 data-foundation/nbaiot/
  ciciot2023/edge_iiotset).

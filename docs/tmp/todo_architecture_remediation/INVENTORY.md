# Inventory

Snapshot taken 2026-08-09, before batch 1. Re-run the counts below (same grep) before resuming a
batch — this file is a snapshot, not a live view; re-verify against current repo state per the
resumability rules in the parent instructions.

## Repository size

- `src/datp_core`: 48555 LOC total.
- 390 `TODO`/`FIXME`/`XXX` markers at snapshot time (388 after batch 1 resolved core's 2).
- `tests/`: 0 TODO markers.

## TODO/FIXME/XXX by package (snapshot, before batch 1)

```
170 data
 86 analysis
 50 experiments
 39 presentation
 24 detector
  8 thresholds
  4 artifacts
  4 app        (was 5; map_exception_to_exit TODO fixed in batch 1, non-core but fixed in-flight)
  2 core       (fixed in batch 1 — now 0)
  2 runtime
  0 artifacts sub-lifecycle (folded into artifacts count above)
```

Package LOC (for batch-sizing):
```
core          1163  (batch 1, DONE)
data         11116
detector      7597
thresholds    3572
analysis      8560
experiments  11387
artifacts     1000
presentation  1345
app           2592
runtime        220
```

## Dominant TODO phrasing patterns (repo-wide grep, informs how to triage each batch)

- `#TODO:should be a class. Check what already exists. Do not use primitives for this, use
  something else...` — 281 occurrences. This is the single dominant pattern. Per batch 1's
  finding, **do not treat this as "always wrap in a new class."** First determine: (a) is there
  already an established value object/enum for this exact concept (reuse), (b) is it a genuine
  closed vocabulary worth a `StrEnum`, (c) is it actually free-form human/diagnostic text that's
  fine as a `str`-subclass boundary type or even a plain primitive at a real boundary. See
  "Judgment calls" below for the worked example from batch 1.
- `#TODO: should be tuple[X] and adapt all callers and usage` (X = ClientId, EdgeSensorGroup,
  NBaIoTFeatureColumn, EdgeRawColumn, EdgeCanonicalColumn, CanonicalProvenanceColumn, ...) — ~25
  occurrences, concentrated in `data`. These are genuine tuple-shaped-pseudo-object fixes:
  currently likely `list[str]` or bare `tuple` where a named, validated sequence type is wanted.
  Check `core/identifiers.py` for the `FeatureNameSequence` / `OutcomeLabelSequence` /
  `StableRowIdSequence` pattern (uses `sequence_pydantic_schema`) before inventing a new one —
  this is the established repo idiom for "validated homogeneous tuple of a value object."
- `#TODO: should probably be an existing class. Check if already exists...` — 11 occurrences.
  Explicitly says an existing type is likely the fix; search before creating.
- `#TODO: no hardcoded values. Should use what already exists...` — 3+ occurrences (one instance
  seen at `experiments/anchor/run.py` for a hardcoded `"diagnostics"` path segment and
  `IndependentAnchorAssetName.ROOT.value`).
- `#TODO: i believe this is duplicated and probably should be either i...` — 3 occurrences,
  explicit duplication flags, high priority (violates §11 "bias toward deletion").
- A handful of one-off narrative TODOs (`what's this for?`, `doesn't even seem used`, `should be
  handled better than so much nested code`) — these need individual reading, not pattern-matching.

## Existing type catalogue (core package, fully read in batch 1 — reuse these before creating new ones)

`core/contracts.py`: `StrictModel` (frozen/strict/extra-forbid Pydantic base), Pydantic core-schema
helpers (`pydantic_value_schema`, `str_subclass_schema`, `str_enum_schema`,
`sequence_pydantic_schema`), `validate_non_empty_tuple`, `validate_unique`, generic
`ClientOwned[ClientT, ValueT]` / `ClientCollection[ClientT, ValueT]` (one-value-per-client
container with `.require(client)`, `.clients()`, `.values()`).

`core/identifiers.py`: ~40 `StrEnum`s covering the full closed vocabulary of the programme
(`DatasetId`, `PopulationId`, `ExperimentId`, `FederatedThresholdMethod`, `MetricId`,
`ContractSubject`, `PartitionRole`, `SplitProtocolId`, `PreprocessingProtocolId`,
`StageOperationId`, `CheckpointStatus`, etc. — read the file directly, it is the closed-vocabulary
source of truth). Also: `NonEmptyString(str)` base class with `validation_name: ClassVar[str]`
override hook and `str_subclass_schema` Pydantic integration — the established pattern for "a
validated, non-empty, string-shaped identity" (subclasses: `FeatureName`, `OutcomeLabel`,
`StableRowId`, `CaptureTimestampColumn`, `SafeTensorFilename`, `CudaDeviceName`, and now
`ErrorMessage`/`ErrorReason` from batch 1). Plus non-string value objects `ClientPathToken`,
`ClientIdentityToken`, `FamilyIdentity` (frozen dataclasses with `__post_init__` validation +
`pydantic_value_schema`), and validated sequence wrappers `FeatureNameSequence`,
`OutcomeLabelSequence`, `StableRowIdSequence` (frozen dataclasses over a tuple of a value object,
with `sequence_pydantic_schema`, `__len__`, `__iter__`).

`core/numeric.py`: numeric value-object family — `PositiveIntegerValue`, `NonNegativeIntegerValue`,
`FiniteFloatValue` (+ `PositiveFiniteFloatValue`, `NonNegativeFiniteFloatValue`,
`OpenUnitIntervalValue`, `ClosedUnitIntervalValue` variants), each with `validation_name: ClassVar`
and dozens of named subclasses (`Seed`, `ClientCount`, `RoundNumber`, `BatchSize`, `Ratio`,
`Quantile`, `ThresholdValue`, `ScoreValue`, `MetricValue`, ...). **This is the pattern to reuse for
every "should be RowCount instead of int" / "should be X instead of primitive" TODO** — check
whether the exact semantic already has a subclass here before adding one.

`core/errors.py` (after batch 1 correction): `DatpCoreError` hierarchy
(`ScientificContractError`, `CapabilityError`, `InfeasibleExperimentError`,
`DataIntegrityError`, `LeakageError`, `AnchorReproductionError`, `ProtocolValidationError`,
`SerializationSafetyError`, `ArtifactIntegrityError`, `ExecutionStateError`,
`UnknownIdentifierError`, `MissingPrerequisiteError`, `ReportEvidenceError`,
`UnresolvedScientificValueError`), `CliExitCode` enum. `__init__(message: ErrorMessage, *,
subject: Enum | None = None, reason: Enum | None = None)` — both `message` and `reason`
require real typed values from every caller; there is no `str` fallback for either.
`ErrorMessage` (`NonEmptyString` subclass) is the only free-text-shaped type left; there is
no `ErrorReason` — it was deleted in the correction. `MissingPrerequisiteReason`
(`StrEnum`, currently one member `ANCHOR_GATE` — add more members here if future
`MissingPrerequisiteError` call sites need another closed discriminant instead of prose).

## Judgment calls (read before pattern-matching future "should be a class" TODOs)

**UPDATE (same day, batch 1 correction):** the design described immediately below (auto
Enum-or-str coercion inside `DatpCoreError.__init__`) was explicitly rejected by the user
and replaced with a **strict** version: `message: ErrorMessage` (required, no `str`
fallback — every caller must construct `ErrorMessage(...)` explicitly) and `reason: Enum
| None` (no string fallback at all — every non-`None` reason must be a real enum member).
The reasoning below about *why* `message`/`reason` needed real types is still correct and
worth reading; only the "auto-coerce at the boundary so callers don't have to change"
conclusion was overridden. The standing precedent for all future batches is now: **when a
validation function raises with a `reason=`, and no existing enum fits, define a small
`StrEnum` scoped to that module** (named `<Module>Violation`/`<Module>Failure`, one member
per distinct failure condition currently expressed as prose) rather than leaving it as a
string or inventing a free-text wrapper class. See STATUS.md "Batch 1 correction" for the
full list of ~15 new per-module enums this produced, and reuse that list before creating
another one for the same concept in a later batch.

**`core/errors.py` `message`/`reason` (batch 1).** The TODO said "should be a class... do not use
primitives." A literal reading would mean wrapping the string literal at every one of the ~900
`raise <DatpCoreError-subclass>(...)` call sites repo-wide in `ErrorMessage(...)`. Investigation
showed:
- `message` is always free-form human-readable prose, used exactly like every stdlib exception's
  message argument (compare: hundreds of unmarked `raise ValueError(f"...")` elsewhere in the same
  files, never flagged). Forcing explicit construction at every call site would be pure churn with
  no scientific or safety benefit, and contradicts CLAUDE.md §"primitive audit": "primitives are
  acceptable at genuine external boundaries... final presentation output" and "do not create
  unnecessary wrappers."
- `reason` turned out to be **three different concepts wearing one parameter**: (1) free-form
  prose explanation (majority, ~70 sites) — same boundary argument as `message`; (2) an *already
  existing* closed enum (`AnchorDiscrepancyReason`) being needlessly unwrapped with `.value` before
  being handed to a `str | None` parameter (18+2 sites) — a genuine `.value`-leak bug; (3) a
  single ad hoc string `"anchor_gate"` that was actually being **compared with `==` in control
  flow** (`app/cli/validation.py`) — i.e. a real closed discriminant hiding as a hardcoded string,
  which is exactly the kind of primitive leak CLAUDE.md's audit section targets.

  Resolution applied: reuse `NonEmptyString` (already exists) for the free-text cases via new
  `ErrorMessage`/`ErrorReason` subclasses; widen `reason`'s type to `Enum | str | None` (mirroring
  the pre-existing `subject: Enum | None` idiom in the same file) so category (2) can pass the
  enum member directly with no `.value`; add a genuine new closed enum
  (`MissingPrerequisiteReason.ANCHOR_GATE`) for category (3). The `message`/free-text-`reason`
  wrapping happens **inside `DatpCoreError.__init__`**, not at each call site — the constructor
  argument stays `str`-shaped (a real external boundary, same as any stdlib exception), and the
  *stored attribute* (`self.message`, `self.reason`) is always the typed value object. This is the
  same "convert immediately at the boundary" principle CLAUDE.md prescribes for external-library
  dicts, applied to exception construction instead of full call-site rewrite.

  Apply the same triage to every future "should be a class" TODO: (a) grep for existing
  enum/value-object candidates first (`core/identifiers.py`, `core/numeric.py`, and the owning
  package's own `contracts.py`), (b) check whether the value is ever compared/branched on
  programmatically (→ needs a real enum) vs. only ever displayed/logged (→ a `NonEmptyString`-style
  wrapper or an internal-boundary conversion is enough — do not force call-site churn), (c) grep
  for `.value` near the site — an unwrap-before-a-loosely-typed-parameter is a strong signal the
  fix is "stop typing the parameter as `str`," not "invent a new type."

## Suggested batch order (dependency-aware; adjust if actual imports disagree)

1. **core** — DONE (batch 1).
2. **data** — 170 TODOs, 11116 LOC, largest. Owns dataset capability/schema/reader/materialization,
   population construction/splitting, preprocessing. Everything else depends on it. Likely needs
   internal sub-batches while working it, e.g.: `data/contracts.py` + `data/materialization*.py`
   first (shared contracts), then per-dataset modules (`data/nbaiot`, `data/ciciot2023`,
   `data/edge_iiotset`), then `data/populations/*`. Record sub-batch progress in this file's
   "Completed batches" section as they land, same as core.
3. **artifacts** — 4 TODOs, 1000 LOC, small; owns generic layout/checksum/publication primitives
   that `data`/`detector`/`thresholds` persistence delegates to. Do before detector/thresholds if
   their TODOs touch persistence.
4. **detector** — 24 TODOs, 7597 LOC. Depends on core + data + artifacts.
5. **thresholds** — 8 TODOs, 3572 LOC. Depends on core + data + detector (fixed scores).
6. **analysis** — 86 TODOs, 8560 LOC. Depends on core + thresholds + detector outputs.
7. **experiments** — 50 TODOs, 11387 LOC (+ the 3 flagged-but-deferred anchor TODOs from batch 1).
   Orchestrates data/detector/thresholds/analysis; do after all of them.
8. **presentation** — 39 TODOs, 1345 LOC. Consumes analysis output.
9. **app** — remaining ~4 TODOs (one already fixed in batch 1), 2592 LOC. CLI/planning layer, do
   last among src packages since it depends on everything.
10. **runtime** — 2 TODOs, 220 LOC. Low-level, could be pulled earlier if a data/detector batch
    needs a runtime fix as a dependency; otherwise fine last.
11. **Final clean-room audit** — full second pass without the TODO list, per the top-level
    instructions, only after all 10 packages above are done.

## Non-TODO issues already observed (repo-wide, not yet fixed)

- Test directory names under `tests/unit/` include `pipeline/`, `learning/`, `thresholding/`,
  `calibration/`, `preprocessing/`, `evaluation/` — these match package names CLAUDE.md §3 declares
  **obsolete** (`datp_core.pipeline`, `datp_core.learning`, `datp_core.thresholding`,
  `datp_core.calibration`, `datp_core.preprocessing`, `datp_core.evaluation`). Not yet determined
  whether this is only stale folder naming (imports already point at the correct canonical
  packages) or an actual leftover architecture problem. **Action for whichever batch touches these
  tests**: check actual imports in each such test file; if they import current canonical packages,
  just rename the directory to match; if they still reference obsolete modules, that's a real
  broken-import defect to fix as part of that package's batch.
- Baseline pyright (whole repo, before batch 1): 5 errors, all in
  `tests/unit/preprocessing/test_manifest_severity.py` — `tuple[RelativeAssetPath]` not assignable
  to `RelativeAssetPathSequence` parameter. Belongs to the `data` batch (preprocessing manifest).
- Baseline ruff (whole repo, before batch 1): 368 errors, overwhelmingly `E501` (TODO comment
  lines exceeding 120 chars — will shrink automatically as TODOs are resolved and comments
  removed). Re-run `ruff check .` after each batch to see the real remaining count once TODO-noise
  is gone.
- `experiments/external/run.py:110`: `reason=reason.value` where `reason:
  BoundedExternalPlanningReason` (existing StrEnum) is unwrapped before being passed to
  `execute_declared_experiment_seed(reason=...)`. Same `.value`-leak shape as the batch-1 anchor
  fix; check whether that function's `reason` parameter can just accept the enum directly.

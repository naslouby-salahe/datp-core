# Skill: typed-immutable-domain

## Trigger

Adding or editing protocol state, a specification/result/value/identity type, or an artifact/reuse path
in `domain`, `application`, or `analysis`.

## Checks

- **Typed protocol state.** Protocol state that crosses a module boundary or controls scientific
  behavior uses `StrEnum` (UPPER_SNAKE members, snake_case values), `Literal`, value objects, or frozen
  dataclasses — never a raw string, `dict[str, Any]`, object-shaped dict, or positional tuple.
- **Correct construct.** Closed value set → `StrEnum`; bounded/validated quantity → value object (no
  primitive obsession); related fields with identity → frozen dataclass; discriminated variant →
  tagged union / `match` with `assert_never`, never a boolean or optional-field combination.
- **Immutable by construction.** Domain/application/analysis identity and configuration objects are
  frozen, slotted, keyword-only; constructed once, never mutated. A changed input yields a new identity.
- **No hidden behavior.** No hidden default, mutable default, unexplained broad default, unjustified
  `Any`/`cast`/`type: ignore` (a narrow, explained third-party gap is acceptable).
- **Deterministic identity.** An `ArtifactId`/`StageFingerprint` is a pure function of its logical
  inputs (`hash(stage_kind, own_inputs, upstream_identity)`); a downstream identity changes only when
  its own or an upstream input changes. Random ids are for operational concepts only.
- **Lineage-correct reuse.** A `REUSE`/`RECOMPUTE` decision compares stage fingerprints, never file
  path, filename, or list position, and belongs on a final (not draft) stage. An identical logical id
  with mismatched content bytes is rejected as an integrity conflict, never silently reissued.
- **Atomic persistence.** A bundle becomes readable only after every member and its commit marker are
  verified; single-file commits are atomic; lock leases support heartbeat, release, and stale-owner
  recovery. Scientific checkpoints live under `checkpoints/`; ephemeral recovery state under `.runtime/`.

## Fail conditions

Protocol meaning rides on ad hoc strings/dicts, a specification/result is mutated after construction,
an identity is non-deterministic, or a reuse decision skips a fingerprint comparison.

## Output

State which types changed, that immutability/typing held, and any remaining identity risk.

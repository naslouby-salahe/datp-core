# Lineage and Provenance Hook

## Trigger
After any edit touching an artifact identity, stage fingerprint, reuse decision, or provenance record.

## Purpose
Keep artifact identity stage-scoped, lineage-compatible, and immutable.

## Blocking status
Blocks completion.

## Required checks
- Every stage identity is a distinct frozen structure wrapping `hash(stage_kind, own_scientific_inputs, upstream_identity)`; a downstream identity changes only when its own inputs or an upstream identity changes.
- A reuse decision is based on lineage-compatibility comparison of stage fingerprints, never on file path, filename similarity, or list position.
- A scientific specification, once constructed, is never mutated; a changed input produces a new identity, never an in-place edit of an existing one.
- An identical logical identity with mismatched content bytes is rejected as an integrity conflict, never silently reissued.

## Failure behavior
Stop the edit and report the exact lineage violation; never approve a reuse decision based on convenience rather than a verified fingerprint comparison.

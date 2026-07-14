# Lineage and Identity Design Check

## Purpose
Keep artifact and stage identity deterministic and lineage-compatible.

## When to apply
Apply whenever an `ArtifactId`, `StageFingerprint`, or reuse decision is introduced or changed.

## Blocking rules
Block a non-deterministic identity construction, an identical logical id issued with different content bytes, and a reuse decision that crosses an incompatible lineage boundary without being classified `RECOMPUTE`.

## Pass criteria
An identity is a pure function of its logical inputs, a content mismatch under the same id is rejected as an integrity conflict, and a reuse decision states its lineage-compatibility reasoning explicitly.

## Fail criteria
Two runs with identical logical inputs produce different ids, or a lineage-incompatible artifact is silently reused.

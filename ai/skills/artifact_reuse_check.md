# Artifact Reuse Check

## Purpose
Keep artifact reuse decisions lineage-correct.

## When to apply
Apply whenever the planner's reuse gate or a `ScoreReuseGate`-style decision is added or changed.

## Blocking rules
Block a reuse decision made without comparing the candidate artifact's stage fingerprint against the required lineage, and a `DraftPlannedStage` carrying a reuse decision (reuse is decided only once a stage becomes final).

## Pass criteria
Every `FinalPlannedStage` carries an explicit, classified reuse decision (`REUSE` or `RECOMPUTE`) backed by a fingerprint comparison, and the planner never queries the artifact store directly.

## Fail criteria
A stage reuses an artifact without a fingerprint comparison, or a draft stage is treated as if its reuse decision were final.

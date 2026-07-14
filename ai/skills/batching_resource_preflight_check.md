# Batching and Resource Preflight Check

## Purpose
Keep batch/chunk profiles fixed and resource pressure handled without silent mutation.

## When to apply
Apply whenever a `TrainingBatchSpec`, `ScoringBatchSpec`, `PreprocessingChunkSpec`, or resource-pressure path is added or changed.

## Blocking rules
Block an automatic batch-size or chunk-size reduction under memory pressure, a gradient-accumulation or effective-batch-size change after stage start, and a resource-pressure pause that mutates the profile instead of only pausing or failing the stage.

## Pass criteria
Preflight validates the exact configured batch/chunk combination before the stage starts, and resource pressure can only pause or fail a stage, never change its profile.

## Fail criteria
A batch or chunk size changes automatically in response to memory or disk pressure, or a manually changed profile is applied without creating a new affected identity.

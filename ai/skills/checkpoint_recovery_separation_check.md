# Checkpoint and Recovery Separation Check

## Purpose
Keep scientific checkpoints and runtime recovery state separately owned.

## When to apply
Apply whenever a checkpoint schedule, recovery policy, or `.runtime/`-rooted state path is added or changed.

## Blocking rules
Block a recovery checkpoint reused under a changed execution profile, scientific checkpoint state written into `.runtime/`, and runtime recovery state written into `checkpoints/`.

## Pass criteria
Scientific checkpoints live only under the recoverable `checkpoints/` root, ephemeral runtime/recovery state lives only under `.runtime/`, and a recovery attempt verifies profile compatibility before reuse.

## Fail criteria
A recovery checkpoint is reused after a batch/chunk profile change, or scientific and ephemeral state share a root.

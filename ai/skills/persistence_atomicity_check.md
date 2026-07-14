# Persistence Atomicity Check

## Purpose
Keep artifact and bundle commits atomic and lock-safe.

## When to apply
Apply whenever an `ArtifactStore`, `CheckpointStore`, `ManifestStore`, or `ArtifactLockProvider` path is added or changed.

## Blocking rules
Block a partial bundle commit reaching a readable state, a single-file write that is not atomic on the same filesystem, and a lock lease acquired without a heartbeat or stale-owner recovery path.

## Pass criteria
A bundle becomes readable only after every member and its commit marker are verified, single-file commits are atomic, and lock leases support heartbeat, release, and stale-owner recovery.

## Fail criteria
A reader observes a partially committed bundle, a crash mid-write leaves a corrupt file, or a stale lock blocks recovery indefinitely.

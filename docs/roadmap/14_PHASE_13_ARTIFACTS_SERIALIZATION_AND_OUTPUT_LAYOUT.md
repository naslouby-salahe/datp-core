# Phase 13 — Artifacts, Safe Serialization, and Output Layout

## Authority and ownership

`docs/Journal_Extension_Master_Roadmap.md` is the scientific authority.

Final experiment-output ownership is consolidated under:

- `src/datp_core/pipeline/publication/` for records, deterministic layout, manifests, canonical serialization, atomic publication, checksums, completion, reuse, and reload validation;
- `src/datp_core/pipeline/checkpoints/` for checkpoint records, service, and safe persistence;
- `src/datp_core/pipeline/scoring/` for score records, frame contracts, and score persistence.

Capability packages construct typed scientific results. Pipeline publication services persist them. CLI and Dagster do not implement persistence.

## Deterministic identity

Output paths derive only from active typed scientific coordinates. They contain no timestamp, run ID, job ID, resume ID, random suffix, or generic parameter bag. Inactive coordinates are omitted. Two distinct complete scientific coordinates must never collide.

Reusable canonical and processed data remain under `data/`. Experiment-specific training, checkpoints, scores, calibration, thresholds, evaluation, analysis, anchor evidence, and reports remain under `outputs/`. Outputs refer to reusable assets by typed identity, path, schema, and checksum; they do not copy them.

## Canonical publication lifecycle

Every publication follows one lifecycle:

1. derive the deterministic target coordinate;
2. acquire the coordinate lock;
3. remove stale sibling staging directories;
4. validate any existing publication before reuse;
5. write all artifacts into a temporary sibling directory;
6. reload and semantically validate every expected artifact;
7. calculate actual byte counts and BLAKE2 checksums from persisted bytes;
8. create the typed inventory and manifest;
9. write the completion record last;
10. atomically replace the target directory.

An output without a valid completion record is incomplete. A complete marker with missing, corrupt, schema-invalid, or coordinate-mismatched artifacts is invalid. Neither state is reusable.

## Approved formats

- SafeTensors for model and checkpoint tensor state;
- skops only for validated preprocessing estimators with explicit trusted types;
- Parquet/PyArrow for tabular artifacts;
- canonical Pydantic JSON for protocols, manifests, summaries, decisions, warnings, inventories, unavailable outcomes, and completion records;
- explicit JSON or Arrow schemas for feature and table contracts.

Pickle, joblib pickle, cloudpickle, dill, arbitrary object serialization, executable codecs, and serialized optimizer objects are prohibited.

## Manifest and reload requirements

Typed manifests bind:

- all active scientific coordinates;
- protocol and declaration digests;
- canonical and processed data references;
- preprocessing, model, checkpoint, score, calibration, threshold, evaluation, analysis, and report identities;
- schema identifiers;
- expected artifacts;
- availability, suppression, anchor, publication, and completion states.

Reload validation checks actual file checksums and sizes, artifact membership and ordering, coordinate identity, schema identity, tensor names/shapes/dtypes/model architecture, checkpoint round, estimator type and feature order, table schemas and semantic columns, typed unavailable outcomes, and inventory completeness.

A file that can be parsed but fails semantic reload is invalid.

## Reuse and cleanup

Path existence is insufficient for reuse. Complete scientific identity, manifest, checksum, schema, and reload validation must all match. Reuse across centralized/federated identity, dataset, population, seeds, split, preprocessing, training, coefficient, checkpoint, score, calibration, threshold, evidence role, or temporal state mismatch is prohibited.

Incomplete experiment outputs are deleted before restart. Explicit overwrite deletes the full experiment coordinate. Completed valid outputs are reused unless overwrite is requested.

## Verification

Tests cover deterministic path construction and collision rejection, absence of run/timestamp identity, atomic replacement, stale staging cleanup, actual checksum corruption, missing completed artifacts, wrong-coordinate reload, model/checkpoint round trips, preprocessing round trips, Parquet schema round trips, completion-last integrity, unsafe serializer prohibition, and data/output separation.

## Completion record

Phase 13 is complete only when every persisted experiment artifact uses the canonical lifecycle, every reusable artifact passes strict semantic reload, completion evidence is trustworthy, unsafe serialization and bypass paths are absent, and relevant unit, integration, architecture, and scientific tests pass.

Formatting, Ruff, Pyright, Pylint, SonarQube, CodeScene, GitHub Actions, hosted CI, and external quality gates are outside this pull request's completion procedure.

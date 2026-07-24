"""Resolution of the authored artifact-identity contract into its domain record."""

from __future__ import annotations

from datp_core.artifacts.manifest import ArtifactFingerprintsRecord, ArtifactIdentityRecord
from datp_core.config.authored.protocols.artifacts import ArtifactIdentityConfig


def resolve_artifact_identity(cfg: ArtifactIdentityConfig) -> ArtifactIdentityRecord:
    fp = cfg.fingerprints
    return ArtifactIdentityRecord(
        hash_function=cfg.hash_function,
        digest_bytes=cfg.digest_bytes,
        canonical_serialization=cfg.canonical_serialization,
        absolute_paths_excluded_from_identity=cfg.absolute_paths_excluded_from_identity,
        fingerprints=ArtifactFingerprintsRecord(
            source=tuple(fp.source),
            schema_stage=tuple(fp.schema_stage),
            materialization=tuple(fp.materialization),
            client_assignment=tuple(fp.client_assignment),
            model_stage=tuple(fp.model_stage),
            training=tuple(fp.training),
            checkpoint=tuple(fp.checkpoint),
            score=tuple(fp.score),
            threshold=tuple(fp.threshold),
            metric=tuple(fp.metric),
            analysis=tuple(fp.analysis),
        ),
        lineage_validation_before_reuse=tuple(cfg.lineage_validation_before_reuse),
        reuse_rejected_when_any_changes=tuple(cfg.reuse_rejected_when_any_changes),
    )

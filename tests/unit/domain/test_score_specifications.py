from dataclasses import fields

import pytest

from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.lineage import (
    CentralizedCalibrationScoringIdentity,
    CentralizedCheckpointIdentity,
    CheckpointIdentity,
    TrainingIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.data.splitting import SplitIdentity
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import (
    CentralizedClientCalibrationScoreArtifact,
    ClientCalibrationScoreArtifact,
    ClientTemporalScoreArtifact,
    ClientTestScoreArtifact,
    ScoreGenerationSpec,
    ScoreSampleCount,
    ScoringBatchSpec,
    SplitScopedScoreBundle,
)
from datp_core.domain.runtime.admissibility import BatchSize


def test_calibration_score_artifact_has_no_attack_surface() -> None:
    field_names = {entry.name for entry in fields(ClientCalibrationScoreArtifact)}

    assert all("attack" not in name for name in field_names)


def test_test_score_artifact_exposes_one_citable_aggregate_identity() -> None:
    field_names = {entry.name for entry in fields(ClientTestScoreArtifact)}

    assert "aggregate_manifest_hash" in field_names
    assert "benign_scores_identity" not in field_names
    assert "attack_scores_identity" not in field_names
    assert {"benign_scores_ref", "attack_scores_ref"} <= field_names


def test_scoring_ownership_and_role_types_are_structurally_distinct() -> None:
    assert {entry.name for entry in fields(ScoreGenerationSpec)} == {
        "scoring_batch",
        "precision",
        "numeric_equivalence_policy",
    }
    assert {entry.name for entry in fields(ScoringBatchSpec)} == {
        "calibration_batch_size",
        "test_batch_size",
        "temporal_batch_size",
    }
    assert ClientCalibrationScoreArtifact is not ClientTestScoreArtifact
    assert ClientTestScoreArtifact is not ClientTemporalScoreArtifact
    assert {entry.name for entry in fields(SplitScopedScoreBundle)} == {"calibration", "test", "temporal"}


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def _b0_artifact_ref() -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value="artifact-" + "a" * 64),
        artifact_type=ArtifactType.CALIBRATION_SCORE_SET,
        content_hash="a" * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.JSON,
    )


def test_centralized_calibration_score_artifact_rejects_a_fedavg_checkpoint_identity() -> None:
    client_id = ClientId(value="client-a")
    split_identity = SplitIdentity(value=_fingerprint("b"))
    scoring_identity = CentralizedCalibrationScoringIdentity(value=_fingerprint("e"))
    fedavg_checkpoint_identity = TrainingIdentity(value=_fingerprint("f"))
    sample_count = ScoreSampleCount(value=10)
    schema_version = ArtifactSchemaVersion(value="v1")
    artifact_ref = _b0_artifact_ref()

    with pytest.raises(DomainValidationError):
        CentralizedClientCalibrationScoreArtifact(
            client_id=client_id,
            calibration_split_identity=split_identity,
            split_manifest_hash="c" * 64,
            scoring_identity=scoring_identity,
            centralized_checkpoint_identity=fedavg_checkpoint_identity,  # type: ignore[arg-type]
            centralized_checkpoint_content_hash="d" * 64,
            scoring_batch_size=BatchSize(value=4),
            sample_count=sample_count,
            schema_version=schema_version,
            content_hash="a" * 64,
            row_order_checksum="order",
            artifact_ref=artifact_ref,
        )


def test_centralized_calibration_score_artifact_accepts_only_centralized_identity_types() -> None:
    artifact = CentralizedClientCalibrationScoreArtifact(
        client_id=ClientId(value="client-a"),
        calibration_split_identity=SplitIdentity(value=_fingerprint("b")),
        split_manifest_hash="c" * 64,
        scoring_identity=CentralizedCalibrationScoringIdentity(value=_fingerprint("e")),
        centralized_checkpoint_identity=CentralizedCheckpointIdentity(value=_fingerprint("f")),
        centralized_checkpoint_content_hash="d" * 64,
        scoring_batch_size=BatchSize(value=4),
        sample_count=ScoreSampleCount(value=10),
        schema_version=ArtifactSchemaVersion(value="v1"),
        content_hash="a" * 64,
        row_order_checksum="order",
        artifact_ref=_b0_artifact_ref(),
    )

    assert type(artifact.centralized_checkpoint_identity) is CentralizedCheckpointIdentity
    assert CentralizedCheckpointIdentity is not CheckpointIdentity

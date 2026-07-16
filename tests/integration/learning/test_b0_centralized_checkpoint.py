import pytest
import torch

from datp_core.application.ports.learning import CentralizedTrainingRunResult, TrainCentralizedModelRequest
from datp_core.application.stages.select_checkpoint import select_centralized_checkpoint
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.lineage import (
    CentralizedCalibrationScoringIdentity,
    CentralizedCheckpointIdentity,
    CentralizedEvaluationIdentity,
    CentralizedModelIdentity,
    CentralizedTestScoringIdentity,
    CentralizedThresholdIdentity,
    DatasetSourceIdentity,
    FittedPreprocessorIdentity,
    TrainingIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.data.preprocessing import ProcessedSplitResult
from datp_core.domain.data.splitting import SplitIdentity
from datp_core.domain.errors import CheckpointSelectionError, DomainValidationError
from datp_core.domain.experiments.specifications import CentralizedModelComparatorSpec
from datp_core.infrastructure.learning.centralized.nbaiot_b0_checkpoint import (
    B0CentralizedCheckpointStager,
)


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def _comparator() -> CentralizedModelComparatorSpec:
    return CentralizedModelComparatorSpec(
        model_identity=CentralizedModelIdentity(value=_fingerprint("1")),
        checkpoint_identity=CentralizedCheckpointIdentity(value=_fingerprint("2")),
        calibration_score_identity=CentralizedCalibrationScoringIdentity(value=_fingerprint("3")),
        test_score_identity=CentralizedTestScoringIdentity(value=_fingerprint("4")),
        threshold_identity=CentralizedThresholdIdentity(value=_fingerprint("5")),
        evaluation_identity=CentralizedEvaluationIdentity(value=_fingerprint("6")),
    )


def _request(*, comparator: object) -> TrainCentralizedModelRequest:
    processed_splits = ProcessedSplitResult(
        artifacts=(
            ArtifactRef(
                artifact_id=ArtifactId(value="artifact-" + "7" * 64),
                artifact_type=ArtifactType.PROCESSED_SPLIT,
                content_hash="7" * 64,
                schema_version=ArtifactSchemaVersion(value="v1"),
                serialization_format=SerializationFormat.PARQUET,
            ),
        ),
        split_manifest_identity=SplitIdentity(value=_fingerprint("8")),
        preprocessor_identity=FittedPreprocessorIdentity(value=_fingerprint("9")),
        source_row_lineage=(DatasetSourceIdentity(value=_fingerprint("0")),),
    )
    return TrainCentralizedModelRequest(processed_splits=processed_splits, comparator=comparator)  # type: ignore[arg-type]


def test_stager_rejects_a_fedavg_identity_in_place_of_a_centralized_comparator() -> None:
    stager = B0CentralizedCheckpointStager(parameters=(torch.rand(4, 4),))
    request = _request(comparator=TrainingIdentity(value=_fingerprint("a")))

    with pytest.raises(DomainValidationError):
        stager.stage(request)


def test_stager_rejects_empty_parameters() -> None:
    stager = B0CentralizedCheckpointStager(parameters=())
    request = _request(comparator=_comparator())

    with pytest.raises(DomainValidationError):
        stager.stage(request)


def test_stager_produces_a_deterministic_scientific_checkpoint_artifact() -> None:
    parameters = (torch.arange(6, dtype=torch.float32).reshape(2, 3),)
    request = _request(comparator=_comparator())

    first = B0CentralizedCheckpointStager(parameters=parameters).stage(request)
    second = B0CentralizedCheckpointStager(parameters=parameters).stage(request)

    assert first == second
    assert first.artifact_type is ArtifactType.SCIENTIFIC_CHECKPOINT
    assert first.serialization_format is SerializationFormat.TORCH_STATE


def _checkpoint_result(*, artifact_type: ArtifactType) -> CentralizedTrainingRunResult:
    return CentralizedTrainingRunResult(
        checkpoint_identity=CentralizedCheckpointIdentity(value=_fingerprint("b")),
        checkpoint_artifact=ArtifactRef(
            artifact_id=ArtifactId(value="artifact-" + "c" * 64),
            artifact_type=artifact_type,
            content_hash="c" * 64,
            schema_version=ArtifactSchemaVersion(value="v1"),
            serialization_format=SerializationFormat.TORCH_STATE,
        ),
    )


def test_select_centralized_checkpoint_accepts_a_scientific_checkpoint() -> None:
    result = _checkpoint_result(artifact_type=ArtifactType.SCIENTIFIC_CHECKPOINT)

    selected = select_centralized_checkpoint(result)

    assert selected is result


def test_select_centralized_checkpoint_rejects_a_non_scientific_artifact_type() -> None:
    result = _checkpoint_result(artifact_type=ArtifactType.RECOVERY_CHECKPOINT)

    with pytest.raises(CheckpointSelectionError):
        select_centralized_checkpoint(result)

import pytest
import torch
from torch import Tensor, nn

from datp_core.application.ports.learning import CentralizedTrainingRunResult
from datp_core.application.ports.scoring import (
    GenerateCentralizedCalibrationScoresRequest,
    GenerateCentralizedTestScoresRequest,
)
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.lineage import (
    CentralizedCheckpointIdentity,
    DatasetSourceIdentity,
    FittedPreprocessorIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.data.preprocessing import ProcessedSplitResult
from datp_core.domain.data.splitting import SplitIdentity
from datp_core.domain.errors import ScoringError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import B0ScoringBatchSpec
from datp_core.domain.runtime.admissibility import BatchSize
from datp_core.infrastructure.learning.centralized.nbaiot_b0_scoring import (
    B0CalibrationScoreGenerationWorkflow,
    B0TestScoreGenerationWorkflow,
)


class _IdentityModel(nn.Module):
    def forward(self, values: Tensor) -> Tensor:
        return values.clone()


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def _checkpoint_identity() -> CentralizedCheckpointIdentity:
    return CentralizedCheckpointIdentity(value=_fingerprint("1"))


def _checkpoint() -> CentralizedTrainingRunResult:
    return CentralizedTrainingRunResult(
        checkpoint_identity=_checkpoint_identity(),
        checkpoint_artifact=ArtifactRef(
            artifact_id=ArtifactId(value="artifact-" + "2" * 64),
            artifact_type=ArtifactType.SCIENTIFIC_CHECKPOINT,
            content_hash="2" * 64,
            schema_version=ArtifactSchemaVersion(value="v1"),
            serialization_format=SerializationFormat.TORCH_STATE,
        ),
    )


def _processed_splits(*, split_character: str) -> ProcessedSplitResult:
    return ProcessedSplitResult(
        artifacts=(
            ArtifactRef(
                artifact_id=ArtifactId(value="artifact-" + "5" * 64),
                artifact_type=ArtifactType.PROCESSED_SPLIT,
                content_hash="5" * 64,
                schema_version=ArtifactSchemaVersion(value="v1"),
                serialization_format=SerializationFormat.PARQUET,
            ),
        ),
        split_manifest_identity=SplitIdentity(value=_fingerprint(split_character)),
        preprocessor_identity=FittedPreprocessorIdentity(value=_fingerprint("6")),
        source_row_lineage=(DatasetSourceIdentity(value=_fingerprint("7")),),
    )


def _scoring(*, batch_size: int = 4) -> B0ScoringBatchSpec:
    return B0ScoringBatchSpec(
        calibration_batch_size=BatchSize(value=batch_size), test_batch_size=BatchSize(value=batch_size)
    )


def _calibration_workflow(*, batches: dict[ClientId, Tensor]) -> B0CalibrationScoreGenerationWorkflow:
    return B0CalibrationScoreGenerationWorkflow(
        model=_IdentityModel(), device=torch.device("cpu"), calibration_batches=batches
    )


def test_calibration_workflow_rejects_empty_client_batches() -> None:
    workflow = _calibration_workflow(batches={})
    request = GenerateCentralizedCalibrationScoresRequest(
        processed_splits=_processed_splits(split_character="3"), checkpoint=_checkpoint(), scoring=_scoring()
    )

    with pytest.raises(ScoringError):
        workflow.generate_calibration_scores(request)


def test_calibration_workflow_produces_one_artifact_per_client_in_canonical_order() -> None:
    client_a = ClientId(value="client-a")
    client_b = ClientId(value="client-b")
    batches = {
        client_b: torch.rand(4, 3, dtype=torch.float32),
        client_a: torch.rand(6, 3, dtype=torch.float32),
    }
    workflow = _calibration_workflow(batches=batches)
    request = GenerateCentralizedCalibrationScoresRequest(
        processed_splits=_processed_splits(split_character="3"), checkpoint=_checkpoint(), scoring=_scoring()
    )

    result = workflow.generate_calibration_scores(request)

    assert tuple(artifact.client_id for artifact in result.scores) == (client_a, client_b)
    for artifact in result.scores:
        assert artifact.sample_count.value == batches[artifact.client_id].shape[0]
        assert artifact.centralized_checkpoint_identity == _checkpoint_identity()


def _test_workflow(*, benign: dict[ClientId, Tensor], attack: dict[ClientId, Tensor]) -> B0TestScoreGenerationWorkflow:
    return B0TestScoreGenerationWorkflow(
        model=_IdentityModel(), device=torch.device("cpu"), benign_batches=benign, attack_batches=attack
    )


def test_test_workflow_rejects_a_mismatched_benign_attack_roster() -> None:
    client_a = ClientId(value="client-a")
    client_b = ClientId(value="client-b")
    benign = {client_a: torch.rand(4, 3)}
    attack = {client_b: torch.rand(2, 3)}

    with pytest.raises(ScoringError):
        _test_workflow(benign=benign, attack=attack)


def test_test_workflow_produces_a_benign_attack_pair_per_client() -> None:
    client_a = ClientId(value="client-a")
    benign = {client_a: torch.rand(6, 3, dtype=torch.float32)}
    attack = {client_a: torch.rand(4, 3, dtype=torch.float32)}
    workflow = _test_workflow(benign=benign, attack=attack)
    request = GenerateCentralizedTestScoresRequest(
        processed_splits=_processed_splits(split_character="4"), checkpoint=_checkpoint(), scoring=_scoring()
    )

    result = workflow.generate_test_scores(request)

    assert len(result.scores) == 1
    artifact = result.scores[0]
    assert artifact.benign_sample_count.value == 6
    assert artifact.attack_sample_count.value == 4
    assert artifact.centralized_checkpoint_identity == _checkpoint_identity()

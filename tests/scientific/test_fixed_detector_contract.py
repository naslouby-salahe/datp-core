import dataclasses
from pathlib import Path

from datp_core.core.identifiers import (
    ClientIdentityToken,
    FederatedThresholdMethod,
    PartitionRole,
    PopulationId,
    PopulationIdentityKind,
    PreprocessingProtocolId,
    SerializationFormat,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.core.numeric import FeatureCount, RowCount, Seed
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.scoring.contracts import ScoreArtifactManifest, ScoreRecord
from datp_core.detector.training.models import FederatedTrainingCoordinate, FederatedTrainingResult


def _coordinate() -> FederatedTrainingCoordinate:
    return FederatedTrainingCoordinate(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_seed=Seed(1),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        model=TrainingModelId.FEDAVG_AUTOENCODER,
        model_coefficient=None,
    )


def _manifest() -> ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]:
    coordinate = _coordinate()
    client = ClientIdentity(
        PopulationId.NBAIOT_NATURAL_DEVICES,
        ClientIdentityToken("client"),
        PopulationIdentityKind.PHYSICAL_DEVICES,
    )
    return ScoreArtifactManifest(
        coordinate=coordinate,
        scored_split_protocol=coordinate.split_protocol,
        calibration_records=(
            ScoreRecord(
                coordinate=coordinate,
                partition_role=PartitionRole.CALIBRATION,
                path=Path("calibration.parquet"),
                row_count=RowCount(8),
                feature_count=FeatureCount(4),
                serialization_format=SerializationFormat.PARQUET,
                scored_client=client,
            ),
        ),
        evaluation_records=(
            ScoreRecord(
                coordinate=coordinate,
                partition_role=PartitionRole.EVALUATION,
                path=Path("evaluation.parquet"),
                row_count=RowCount(8),
                feature_count=FeatureCount(4),
                serialization_format=SerializationFormat.PARQUET,
                scored_client=client,
            ),
        ),
    )


def test_terminal_training_has_no_checkpoint_selection_contract() -> None:
    fields = frozenset(field.name for field in dataclasses.fields(FederatedTrainingResult))
    assert "terminal_model_state" in fields
    assert "candidate" not in " ".join(fields)
    assert "selection" not in " ".join(fields)


def test_threshold_methods_share_the_same_score_manifest_object() -> None:
    manifest = _manifest()
    manifests = {
        FederatedThresholdMethod.SHARED_THRESHOLD: manifest,
        FederatedThresholdMethod.LOCAL_THRESHOLD: manifest,
    }
    assert manifests[FederatedThresholdMethod.SHARED_THRESHOLD] is manifests[FederatedThresholdMethod.LOCAL_THRESHOLD]

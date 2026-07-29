from pathlib import Path

import pytest

from datp_core.centralized_reference.checkpointing import FederatedCheckpointMarker, reject_federated_checkpoint
from datp_core.centralized_reference.preprocessing import reject_federated_state_for_pooled
from datp_core.centralized_reference.thresholding import (
    FederatedScoreMarker,
    reject_federated_scores_for_centralized_threshold,
    reject_local_quantile_mean_as_centralized,
)
from datp_core.centralized_reference.training import reject_federated_preprocessing_for_training
from datp_core.domain.enums import (
    FederatedThresholdMethod,
    PartitionRole,
    PreprocessingFitScope,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    SerializationFormat,
    TrustedEstimatorClassName,
    TrustedEstimatorModule,
)
from datp_core.domain.errors import LeakageError
from datp_core.domain.values import Checksum, ClientIdentity
from datp_core.preprocessing.models import (
    FittedPreprocessingState,
    PreprocessingProtocol,
    TransformedFeature,
    TransformedSchema,
)
from datp_core.protocols.anchor import FIXED_SCORE_ABSOLUTE_TOLERANCE


def _federated_state(path: Path) -> FittedPreprocessingState:
    protocol = PreprocessingProtocol(
        identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        input_feature_names=("f0",),
        transformed_schema=TransformedSchema(features=(TransformedFeature(name="f0", position=0),)),
        serialization_format=SerializationFormat.SKOPS,
        estimator_module=TrustedEstimatorModule.SKLEARN_PREPROCESSING,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=FIXED_SCORE_ABSOLUTE_TOLERANCE.value,
    )
    path.write_bytes(b"x")
    return FittedPreprocessingState(
        protocol=protocol,
        branch=ProcessedDataBranch.FEDERATED,
        client_identity=ClientIdentity("device_a"),
        estimator_path=path,
        estimator_checksum=Checksum("1" * 64),
        transformed_schema=protocol.transformed_schema,
        fit_row_count=3,
        fit_partition=PartitionRole.TRAIN,
    )


def test_centralized_pipeline_rejects_all_federated_artifacts(tmp_path: Path) -> None:
    state = _federated_state(tmp_path / "state.skops")
    with pytest.raises(LeakageError):
        reject_federated_state_for_pooled(state)
    with pytest.raises(LeakageError):
        reject_federated_preprocessing_for_training(state)
    with pytest.raises(LeakageError):
        reject_federated_checkpoint(FederatedCheckpointMarker("fedavg", tmp_path / "m.pt"))
    with pytest.raises(LeakageError):
        reject_federated_checkpoint(FederatedCheckpointMarker("fedavg", tmp_path / "m.pt"))
    with pytest.raises(LeakageError):
        reject_federated_scores_for_centralized_threshold(
            FederatedScoreMarker("scores", FederatedThresholdMethod.LOCAL_THRESHOLD)
        )
    with pytest.raises(LeakageError):
        reject_local_quantile_mean_as_centralized((1.0, 2.0))

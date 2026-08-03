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
    PreprocessingFitScope,
    PreprocessingProtocolId,
    SerializationFormat,
    TrustedEstimatorClassName,
)
from datp_core.domain.errors import LeakageError
from datp_core.domain.values import (
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    Checksum,
    ClientPathToken,
    FeatureName,
    FeatureNameSequence,
    RowCount,
)
from datp_core.preprocessing.models import (
    FederatedFittedPreprocessingState,
    PreprocessingProtocol,
)


def _federated_state(path: Path) -> FederatedFittedPreprocessingState:
    protocol = PreprocessingProtocol(
        identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        input_feature_names=FeatureNameSequence((FeatureName("f0"),)),
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    )
    path.write_bytes(b"x")
    return FederatedFittedPreprocessingState(
        protocol=protocol,
        client_identity=ClientPathToken("device_a"),
        estimator_path=path,
        estimator_checksum=Checksum("1" * 64),
        fit_row_count=RowCount(3),
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

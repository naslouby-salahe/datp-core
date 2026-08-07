from pathlib import Path

import pytest

from datp_core.domain.enums import (
    PreprocessingProtocolId,
    SerializationFormat,
    TrainingModelId,
)
from datp_core.domain.errors import LeakageError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import RowCount
from datp_core.domain.values.identifiers import FeatureName, FeatureNameSequence
from datp_core.domain.values.paths import ClientPathToken
from datp_core.domain.values.ratios import NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE
from datp_core.learning.centralized.training import reject_federated_preprocessing_for_training
from datp_core.pipeline.checkpoints.service import reject_federated_checkpoint
from datp_core.preprocessing.centralized import reject_federated_state_for_pooled
from datp_core.preprocessing.contracts import PreprocessingFitScope, TrustedEstimatorClassName
from datp_core.preprocessing.models import FederatedFittedPreprocessingState, PreprocessingProtocol


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
        reject_federated_checkpoint(TrainingModelId.FEDAVG_AUTOENCODER)

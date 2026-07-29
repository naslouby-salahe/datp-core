from pathlib import Path

import numpy as np
import pytest

from datp_core.artifacts.serialization import construct_trusted_estimator
from datp_core.domain.enums import (
    PartitionRole,
    PreprocessingFitScope,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    SerializationFormat,
    TrustedEstimatorClassName,
    TrustedEstimatorModule,
)
from datp_core.domain.errors import LeakageError
from datp_core.domain.values import Checksum
from datp_core.preprocessing.federated import fit_client_preprocessing, reject_centralized_state_for_client
from datp_core.preprocessing.models import (
    FittedPreprocessingState,
    PreprocessingFitBatch,
    PreprocessingProtocol,
    TransformedFeature,
    TransformedSchema,
)


def _protocol() -> PreprocessingProtocol:
    return PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        input_feature_names=("f0", "f1"),
        transformed_schema=TransformedSchema(
            features=(TransformedFeature(name="f0", position=0), TransformedFeature(name="f1", position=1))
        ),
        serialization_format=SerializationFormat.SKOPS,
        estimator_module=TrustedEstimatorModule.SKLEARN_PREPROCESSING,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=1e-12,
    )


def test_fit_client_preprocessing_rejects_attack_labels() -> None:
    protocol = _protocol()
    matrix = np.asarray([[0.0, 1.0], [1.0, 2.0]], dtype=float)
    fitted = fit_client_preprocessing(
        protocol,
        construct_trusted_estimator(TrustedEstimatorClassName.STANDARD_SCALER),
        PreprocessingFitBatch(
            training_matrix=matrix,
            training_row_ids=("r0", "r1"),
            training_labels=("benign", "benign"),
            benign_label="benign",
        ),
    )
    assert fitted.get_params()["with_mean"] is True
    assert fitted.get_params()["with_std"] is True
    transformed = np.asarray(fitted.transform(matrix), dtype=float)
    assert transformed.shape == matrix.shape
    with pytest.raises(LeakageError):
        fit_client_preprocessing(
            protocol,
            construct_trusted_estimator(TrustedEstimatorClassName.STANDARD_SCALER),
            PreprocessingFitBatch(
                training_matrix=matrix,
                training_row_ids=("r0", "r1"),
                training_labels=("benign", "attack"),
                benign_label="benign",
            ),
        )


def test_centralized_state_rejected_for_client() -> None:
    protocol = _protocol()
    state = FittedPreprocessingState(
        protocol=protocol,
        branch=ProcessedDataBranch.CENTRALIZED_REFERENCE,
        client_identity=None,
        estimator_path=Path("state.skops"),
        estimator_checksum=Checksum("a" * 64),
        transformed_schema=protocol.transformed_schema,
        fit_row_count=2,
        fit_partition=PartitionRole.TRAIN,
    )
    with pytest.raises(LeakageError):
        reject_centralized_state_for_client(state)

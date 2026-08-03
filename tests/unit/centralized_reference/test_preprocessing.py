from pathlib import Path

import numpy as np
import pytest

from datp_core.artifacts.serialization import construct_trusted_estimator
from datp_core.centralized_reference.preprocessing import fit_pooled_preprocessing, reject_federated_state_for_pooled
from datp_core.domain.enums import (
    PartitionRole,
    PreprocessingFitScope,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    SerializationFormat,
    TrustedEstimatorClassName,
)
from datp_core.domain.errors import LeakageError
from datp_core.domain.values import (
    Checksum,
    ClientPathToken,
    FeatureNameSequence,
    OutcomeLabelSequence,
    RowCount,
    StableRowIdSequence,
)
from datp_core.preprocessing.models import (
    FittedPreprocessingState,
    PreprocessingFitBatch,
    PreprocessingProtocol,
    TransformedSchema,
)
from datp_core.protocols.anchor import FIXED_SCORE_ABSOLUTE_TOLERANCE


def _protocol() -> PreprocessingProtocol:
    return PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=PreprocessingFitScope.POOLED_TRAINING,
        input_feature_names=FeatureNameSequence(("f0", "f1")),
        transformed_schema=TransformedSchema(feature_names=FeatureNameSequence(("f0", "f1"))),
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=FIXED_SCORE_ABSOLUTE_TOLERANCE,
    )


def test_pooled_fit_is_independent_of_federated_state() -> None:
    protocol = _protocol()
    matrix = np.asarray([[0.0, 1.0], [2.0, 3.0]], dtype=float)
    fitted = fit_pooled_preprocessing(
        protocol,
        construct_trusted_estimator(TrustedEstimatorClassName.STANDARD_SCALER),
        PreprocessingFitBatch(
            training_matrix=matrix,
            training_row_ids=StableRowIdSequence(("a", "b")),
            training_labels=OutcomeLabelSequence(("benign", "benign")),
        ),
    )
    assert np.asarray(fitted.transform(matrix), dtype=float).shape == matrix.shape
    federated_state = FittedPreprocessingState(
        protocol=protocol,
        branch=ProcessedDataBranch.FEDERATED,
        client_identity=ClientPathToken("device_a"),
        estimator_path=Path("state.skops"),
        estimator_checksum=Checksum("b" * 64),
        fit_row_count=RowCount(2),
        fit_partition=PartitionRole.TRAIN,
    )
    with pytest.raises(LeakageError):
        reject_federated_state_for_pooled(federated_state)

from pathlib import Path

import numpy as np
import pytest

from datp_core.domain.enums import (
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
    OutcomeLabel,
    OutcomeLabelSequence,
    RowCount,
    StableRowId,
    StableRowIdSequence,
)
from datp_core.preprocessing.centralized import fit_pooled_preprocessing, reject_federated_state_for_pooled
from datp_core.preprocessing.models import (
    FederatedFittedPreprocessingState,
    PreprocessingFitBatch,
    PreprocessingProtocol,
)


def _protocol() -> PreprocessingProtocol:
    return PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=PreprocessingFitScope.POOLED_TRAINING,
        input_feature_names=FeatureNameSequence((FeatureName("f0"), FeatureName("f1"))),
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    )


def test_pooled_fit_is_independent_of_federated_state() -> None:
    protocol = _protocol()
    matrix = np.asarray([[0.0, 1.0], [2.0, 3.0]], dtype=float)
    fitted = fit_pooled_preprocessing(
        protocol,
        PreprocessingFitBatch(
            training_matrix=matrix,
            training_row_ids=StableRowIdSequence((StableRowId("a"), StableRowId("b"))),
            training_labels=OutcomeLabelSequence((OutcomeLabel("benign"), OutcomeLabel("benign"))),
        ),
    )
    assert np.asarray(fitted.transform(matrix), dtype=float).shape == matrix.shape
    federated_state = FederatedFittedPreprocessingState(
        protocol=protocol,
        client_identity=ClientPathToken("device_a"),
        estimator_path=Path("state.skops"),
        estimator_checksum=Checksum("b" * 64),
        fit_row_count=RowCount(2),
    )
    with pytest.raises(LeakageError):
        reject_federated_state_for_pooled(federated_state)

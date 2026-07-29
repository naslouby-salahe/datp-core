from pathlib import Path

import numpy as np
import pytest
from sklearn.decomposition import PCA

from datp_core.artifacts.reload_validation import reload_and_compare_transform
from datp_core.artifacts.serialization import (
    construct_trusted_estimator,
    load_estimator,
    serialize_estimator,
    trusted_estimator_type_names,
)
from datp_core.domain.enums import (
    PreprocessingFitScope,
    PreprocessingProtocolId,
    SerializationFormat,
    TrustedEstimatorClassName,
    TrustedEstimatorModule,
)
from datp_core.domain.errors import SerializationSafetyError
from datp_core.preprocessing.models import PreprocessingProtocol, TransformedFeature, TransformedSchema


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


def test_skops_round_trip_and_untrusted_rejection(tmp_path: Path) -> None:
    protocol = _protocol()
    matrix = np.asarray([[0.0, 1.0], [2.0, 3.0]], dtype=float)
    estimator = construct_trusted_estimator(TrustedEstimatorClassName.STANDARD_SCALER).fit(matrix)
    expected = np.asarray(estimator.transform(matrix), dtype=float)
    state_path = tmp_path / "state.skops"
    serialize_estimator(estimator, state_path)
    reloaded = load_estimator(state_path, protocol)
    assert trusted_estimator_type_names()
    reload_and_compare_transform(state_path, protocol, matrix, expected)
    assert np.allclose(reloaded.transform(matrix), expected)
    with pytest.raises(SerializationSafetyError):
        serialize_estimator(PCA(n_components=1).fit(matrix), tmp_path / "bad.skops")

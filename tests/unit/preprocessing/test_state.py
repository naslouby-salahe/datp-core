from pathlib import Path

import numpy as np
import pytest
from sklearn.decomposition import PCA

from datp_core.domain.errors import SerializationSafetyError
from datp_core.domain.values.ratios import AbsoluteTolerance
from datp_core.preprocessing.contracts import TrustedEstimatorClassName
from datp_core.preprocessing.state import (
    TransformReloadCheck,
    construct_trusted_estimator,
    load_estimator,
    reload_and_compare_transform,
    serialize_estimator,
    trusted_estimator_type_names,
)


def test_skops_round_trip_and_untrusted_rejection(tmp_path: Path) -> None:
    matrix = np.asarray([[0.0, 1.0], [2.0, 3.0]], dtype=float)
    estimator = construct_trusted_estimator(TrustedEstimatorClassName.STANDARD_SCALER).fit(matrix)
    expected = np.asarray(estimator.transform(matrix), dtype=float)
    state_path = tmp_path / "state.skops"
    serialize_estimator(estimator, state_path)
    reloaded = load_estimator(state_path, TrustedEstimatorClassName.STANDARD_SCALER)
    assert trusted_estimator_type_names()
    reload_and_compare_transform(
        TransformReloadCheck(
            state_path=state_path,
            class_name=TrustedEstimatorClassName.STANDARD_SCALER,
            absolute_tolerance=AbsoluteTolerance(1e-12),
            source_matrix=matrix,
            expected_transformed=expected,
        )
    )
    assert np.allclose(reloaded.transform(matrix), expected)
    with pytest.raises(SerializationSafetyError):
        serialize_estimator(PCA(n_components=1).fit(matrix), tmp_path / "bad.skops")

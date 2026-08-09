from pathlib import Path

import numpy as np
import pytest
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from datp_core.core.errors import SerializationSafetyError
from datp_core.core.numeric import AbsoluteTolerance
from datp_core.data.preprocessing.artifacts import TrustedEstimatorClassName
from datp_core.data.preprocessing.state import (
    TransformReloadCheck,
    load_estimator,
    reload_and_compare_transform,
    serialize_estimator,
)


def test_skops_round_trip_and_untrusted_rejection(tmp_path: Path) -> None:
    matrix = np.asarray([[0.0, 1.0], [2.0, 3.0]], dtype=float)
    estimator = StandardScaler().fit(matrix)
    expected = np.asarray(estimator.transform(matrix), dtype=float)
    state_path = tmp_path / "state.skops"
    serialize_estimator(estimator, state_path)
    reloaded = load_estimator(state_path, TrustedEstimatorClassName.STANDARD_SCALER)
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
    untrusted_estimator = PCA(n_components=1).fit(matrix)
    bad_state_path = tmp_path / "bad.skops"
    with pytest.raises(SerializationSafetyError):
        serialize_estimator(untrusted_estimator, bad_state_path)

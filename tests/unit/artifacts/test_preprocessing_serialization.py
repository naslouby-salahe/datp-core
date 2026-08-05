from pathlib import Path

import numpy as np
import pytest
from sklearn.decomposition import PCA

from datp_core.domain.enums import TrustedEstimatorClassName
from datp_core.domain.errors import SerializationSafetyError
from datp_core.domain.provenance import canonical_value
from datp_core.domain.values import AbsoluteTolerance, RowCount
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


def test_canonical_value_is_deterministic_finite_and_strict() -> None:
    document = canonical_value({"z": RowCount(2), "a": Path("data/value.json")})
    assert isinstance(document, dict)
    assert tuple(document) == ("a", "z")
    assert document == {"a": "data/value.json", "z": 2}
    assert canonical_value((RowCount(1), RowCount(2))) == (1, 2)
    with pytest.raises(ValueError, match="non-finite"):
        canonical_value(float("nan"))
    with pytest.raises(TypeError, match="keys must be strings"):
        canonical_value({1: "invalid"})

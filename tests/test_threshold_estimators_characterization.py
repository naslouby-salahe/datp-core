"""Unit and characterization tests for threshold policy estimators."""

from __future__ import annotations

from typing import Any

import pytest

from datp_core.application.threshold_construction import ConstructThresholdsUseCase
from datp_core.domain.identifiers import ClientId, ThresholdPolicyId
from datp_core.domain.thresholding import BenignCalibrationScores
from datp_core.domain.values import Probability


@pytest.fixture
def mock_calibration() -> tuple[BenignCalibrationScores, ...]:
    c1 = BenignCalibrationScores(client_id=ClientId("c1"), values=tuple(float(i) for i in range(1, 101)))
    c2 = BenignCalibrationScores(client_id=ClientId("c2"), values=tuple(float(i * 2) for i in range(1, 101)))
    c3 = BenignCalibrationScores(client_id=ClientId("c3"), values=tuple(float(i * 3) for i in range(1, 101)))
    return (c1, c2, c3)


def _to_float(val: Any) -> float:
    if hasattr(val, "value"):
        return float(val.value)
    return float(val)


def test_shared_mean_p95(mock_calibration: tuple[BenignCalibrationScores, ...]) -> None:
    use_case = ConstructThresholdsUseCase()
    t_set = use_case.execute(ThresholdPolicyId("shared_mean_p95"), mock_calibration, Probability(0.95))
    assert len(t_set.values) == 3
    vals = [_to_float(item.threshold) for item in t_set.values]
    assert vals[0] == vals[1] == vals[2]


def test_local_quantile_p95(mock_calibration: tuple[BenignCalibrationScores, ...]) -> None:
    use_case = ConstructThresholdsUseCase()
    t_set = use_case.execute(ThresholdPolicyId("local_quantile_p95"), mock_calibration, Probability(0.95))
    assert len(t_set.values) == 3
    vals = [_to_float(item.threshold) for item in t_set.values]
    assert vals[0] < vals[1] < vals[2]


def test_conformal_local_p95(mock_calibration: tuple[BenignCalibrationScores, ...]) -> None:
    use_case = ConstructThresholdsUseCase()
    t_set = use_case.execute(ThresholdPolicyId("conformal_local_p95"), mock_calibration, Probability(0.95))
    assert len(t_set.values) == 3
    vals = [_to_float(item.threshold) for item in t_set.values]
    assert vals[0] < vals[1] < vals[2]


def test_federated_fixed_k30(mock_calibration: tuple[BenignCalibrationScores, ...]) -> None:
    use_case = ConstructThresholdsUseCase()
    t_set = use_case.execute(
        ThresholdPolicyId("federated_fixed_k30"),
        mock_calibration,
        Probability(0.95),
        fixed_k=3.0,
    )
    assert len(t_set.values) == 3
    vals = [_to_float(item.threshold) for item in t_set.values]
    assert vals[0] < vals[1] < vals[2]


def test_federated_matched_exceedance_p95(mock_calibration: tuple[BenignCalibrationScores, ...]) -> None:
    use_case = ConstructThresholdsUseCase()
    t_set = use_case.execute(
        ThresholdPolicyId("federated_matched_exceedance_p95"),
        mock_calibration,
        Probability(0.95),
    )
    assert len(t_set.values) == 3
    vals = [_to_float(item.threshold) for item in t_set.values]
    assert all(v > 0.0 for v in vals)

"""Tests for semantic value-object validation and isolation."""

import pytest
from pydantic import BaseModel

from datp_core.domain.values import (
    CalibrationSize,
    ClientCount,
    GroupCount,
    MetricValue,
    Quantile,
    Ratio,
    RowCount,
    ScoreValue,
    Seed,
    SeedCount,
    ThresholdValue,
)
from datp_core.protocols.models import SeedCohort
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL


class _ValueDocument(BaseModel):
    threshold: ThresholdValue
    metric: MetricValue
    ratio: Ratio


def test_value_boundaries_and_immutability() -> None:
    assert Ratio(0).value == 0
    assert Ratio(1).value == 1
    assert MetricValue(2).value == 2
    with pytest.raises(ValueError):
        Quantile(1)
    with pytest.raises(ValueError):
        Seed(True)
    left = Ratio(0.5)
    right = Ratio(0.5)
    assert hash(left) == hash(right)


def test_seed_count_values_and_types_are_distinct() -> None:
    seed_count = SeedCount(10)
    client_count = ClientCount(10)
    assert seed_count == SeedCount(10)
    assert seed_count != client_count
    assert isinstance(seed_count, SeedCount)
    assert isinstance(client_count, ClientCount)
    assert CONFIRMATORY_SEED_COHORT.member_count == SeedCount(10)
    assert isinstance(CONFIRMATORY_SEED_COHORT.member_count, SeedCount)
    assert not isinstance(CONFIRMATORY_SEED_COHORT.member_count, ClientCount)
    assert CONFIRMATORY_INFERENCE_PROTOCOL.paired_seed_count == SeedCount(10)
    assert isinstance(CONFIRMATORY_INFERENCE_PROTOCOL.paired_seed_count, SeedCount)
    cohort = SeedCohort(values=(Seed(0), Seed(1)))
    assert cohort.member_count == SeedCount(2)


def test_unrelated_integer_value_objects_cannot_be_ordered() -> None:
    with pytest.raises(TypeError):
        _ = Seed(1) < RowCount(2)


def test_unrelated_integer_value_objects_cannot_be_added() -> None:
    with pytest.raises(TypeError):
        _ = Seed(1) + RowCount(2)


def test_same_integer_value_type_supports_arithmetic() -> None:
    assert RowCount(2) + RowCount(3) == RowCount(5)
    assert sum((RowCount(2), RowCount(3)), start=0) == RowCount(5)


def test_explicit_count_families_remain_comparable() -> None:
    assert RowCount(100) >= CalibrationSize(100)
    assert GroupCount(3) < ClientCount(9)


def test_anomaly_scores_remain_comparable_to_thresholds() -> None:
    assert ScoreValue(0.6) > ThresholdValue(0.5)
    assert ScoreValue(0.5) == ThresholdValue(0.5)


def test_unrelated_float_value_objects_are_not_equal() -> None:
    assert MetricValue(0.5) != ThresholdValue(0.5)
    assert Quantile(0.5) != Ratio(0.5)


def test_float_values_validate_and_serialize_through_pydantic() -> None:
    document = _ValueDocument.model_validate({"threshold": 0.5, "metric": 0.75, "ratio": 0.25})

    assert document.threshold == ThresholdValue(0.5)
    assert document.model_dump(mode="json") == {
        "threshold": 0.5,
        "metric": 0.75,
        "ratio": 0.25,
    }

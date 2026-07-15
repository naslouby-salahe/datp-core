from decimal import Decimal
from urllib.parse import quote

import pytest
from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.artifacts.keys import ByteCount, DiskCapacity, RelativeArtifactPath
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.alert_burden import (
    BootstrapResampleCount,
    CalibrationSampleCount,
    ConfusionCount,
    SampleCount,
    TrafficRate,
    TrafficRateUnit,
)
from datp_core.domain.runtime.admissibility import (
    BatchSize,
    ChunkRowCount,
    GpuIndex,
    GradientAccumulationSteps,
    NumericTolerance,
    RamBudgetBytes,
    VramFraction,
    WorkerCount,
)


@given(st.integers(min_value=1))
def test_positive_integer_value_objects_accept_generated_positive_values(value: int) -> None:
    for constructor in (BatchSize, GradientAccumulationSteps, ChunkRowCount, RamBudgetBytes, BootstrapResampleCount):
        assert constructor(value=value).value == value


@given(st.integers(max_value=0))
def test_positive_integer_value_objects_reject_generated_nonpositive_values(value: int) -> None:
    for constructor in (BatchSize, GradientAccumulationSteps, ChunkRowCount, RamBudgetBytes, BootstrapResampleCount):
        with pytest.raises(DomainValidationError):
            constructor(value=value)


@given(st.integers())
def test_nonnegative_integer_value_objects_enforce_generated_bounds(value: int) -> None:
    for constructor in (
        WorkerCount,
        GpuIndex,
        ByteCount,
        DiskCapacity,
        SampleCount,
        ConfusionCount,
        CalibrationSampleCount,
    ):
        if value >= 0:
            assert constructor(value=value).value == value
        else:
            with pytest.raises(DomainValidationError):
                constructor(value=value)


@given(st.floats(allow_nan=True, allow_infinity=True))
def test_float_resource_value_objects_enforce_finiteness_and_bounds(value: float) -> None:
    for constructor, valid in (
        (VramFraction, value == value and value not in (float("inf"), float("-inf")) and 0 < value <= 1),
        (NumericTolerance, value == value and value not in (float("inf"), float("-inf")) and value > 0),
    ):
        if valid:
            assert constructor(value=value).value == value
        else:
            with pytest.raises(DomainValidationError):
                constructor(value=value)


@given(st.decimals(allow_nan=True, allow_infinity=True, places=12))
def test_traffic_rate_enforces_generated_finiteness_and_positivity(value: Decimal) -> None:
    if value.is_finite() and value > 0:
        assert TrafficRate(value=value, unit=TrafficRateUnit.EVENTS_PER_SECOND).value > Decimal(0)
    else:
        with pytest.raises(DomainValidationError):
            TrafficRate(value=value, unit=TrafficRateUnit.EVENTS_PER_SECOND)


@given(st.sampled_from(("..", "../x", "..\\x", "/x", "C:\\x", "%2e%2e/x", quote("../x"), "has space")))
def test_relative_artifact_path_rejects_generated_adversarial_forms(value: str) -> None:
    with pytest.raises(DomainValidationError):
        RelativeArtifactPath(value=value)

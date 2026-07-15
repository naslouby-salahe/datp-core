from collections.abc import Callable
from dataclasses import MISSING, fields
from decimal import Decimal

import pytest

from datp_core.domain.artifacts.keys import ByteCount, DiskCapacity, RelativeArtifactPath
from datp_core.domain.artifacts.references import CalibrationScoreArtifactId
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.alert_burden import (
    BootstrapResampleCount,
    CalibrationSampleCount,
    CalibrationSampleCountRef,
    ConfusionCount,
    SampleCount,
    TrafficRate,
    TrafficRateUnit,
)
from datp_core.domain.experiments.identities import ClientId
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


def test_resource_and_count_value_objects_accept_boundary_values() -> None:
    assert BatchSize(value=1).value == 1
    assert GradientAccumulationSteps(value=1).value == 1
    assert WorkerCount(value=0).value == 0
    assert ChunkRowCount(value=1).value == 1
    assert RamBudgetBytes(value=1).value == 1
    assert VramFraction(value=1).value == 1.0
    assert GpuIndex(value=0).value == 0
    assert NumericTolerance(value=0.5).value == 0.5
    assert ByteCount(value=0).value == 0
    assert DiskCapacity(value=0).value == 0
    assert BootstrapResampleCount(value=1).value == 1
    assert SampleCount(value=0).value == 0
    assert ConfusionCount(value=0).value == 0
    assert CalibrationSampleCount(value=0).value == 0


@pytest.mark.parametrize(
    ("constructor", "invalid_value"),
    [
        (BatchSize, 0),
        (GradientAccumulationSteps, 0),
        (WorkerCount, -1),
        (ChunkRowCount, 0),
        (RamBudgetBytes, 0),
        (VramFraction, 0.0),
        (VramFraction, 1.1),
        (GpuIndex, -1),
        (NumericTolerance, 0.0),
        (ByteCount, -1),
        (DiskCapacity, -1),
        (BootstrapResampleCount, 0),
        (SampleCount, -1),
        (ConfusionCount, -1),
        (CalibrationSampleCount, -1),
    ],
)
def test_resource_and_count_value_objects_reject_invalid_ranges(
    constructor: Callable[..., object],
    invalid_value: float | int,
) -> None:
    with pytest.raises(DomainValidationError):
        constructor(value=invalid_value)


@pytest.mark.parametrize("invalid_value", [float("nan"), float("inf"), float("-inf")])
def test_float_resource_value_objects_reject_nonfinite_values(invalid_value: float) -> None:
    for constructor in (VramFraction, NumericTolerance):
        with pytest.raises(DomainValidationError):
            constructor(value=invalid_value)


def test_bootstrap_resample_count_requires_an_explicit_keyword_value() -> None:
    assert fields(BootstrapResampleCount)[0].default is MISSING
    with pytest.raises(TypeError):
        type.__call__(BootstrapResampleCount)


@pytest.mark.parametrize("value", ["../x", "/abs/x", "C:\\x", "x y", "%2e%2e/x", "..\\x", "safe/%20x"])
def test_relative_artifact_path_rejects_explicit_unsafe_forms(value: str) -> None:
    with pytest.raises(DomainValidationError):
        RelativeArtifactPath(value=value)


def test_relative_artifact_path_accepts_a_safe_posix_relative_path() -> None:
    assert RelativeArtifactPath(value="scores/client-01.parquet").value == "scores/client-01.parquet"


def test_traffic_rate_requires_a_positive_decimal_with_a_supported_unit() -> None:
    assert TrafficRate(value=Decimal("120.5"), unit=TrafficRateUnit.EVENTS_PER_MINUTE).value == Decimal(
        "120.500000000000"
    )
    for invalid_value in (Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")):
        with pytest.raises(DomainValidationError):
            TrafficRate(value=invalid_value, unit=TrafficRateUnit.EVENTS_PER_DAY)


def test_calibration_sample_count_reference_keeps_artifact_client_and_count_typed() -> None:
    reference = CalibrationSampleCountRef(
        calibration_artifact_id=CalibrationScoreArtifactId(value=f"artifact-{'a' * 64}"),
        client_id=ClientId(value="client-01"),
        recorded_count=CalibrationSampleCount(value=100),
    )

    assert reference.recorded_count.value == 100

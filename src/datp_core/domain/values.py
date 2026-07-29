"""Validated scalar scientific values."""

from dataclasses import dataclass
from hashlib import file_digest, sha256
from math import isfinite
from pathlib import Path
from typing import ClassVar


def _integer(value: object, name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")
    return value


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


@dataclass(frozen=True, slots=True)
class PositiveIntegerValue:
    value: int
    validation_name: ClassVar[str] = "value"

    def __post_init__(self) -> None:
        _integer(self.value, self.validation_name, 1)


@dataclass(frozen=True, slots=True)
class NonNegativeIntegerValue:
    value: int
    validation_name: ClassVar[str] = "value"

    def __post_init__(self) -> None:
        _integer(self.value, self.validation_name, 0)


@dataclass(frozen=True, slots=True)
class PositiveFiniteFloatValue:
    value: float
    validation_name: ClassVar[str] = "value"

    def __post_init__(self) -> None:
        if _number(self.value, self.validation_name) <= 0:
            raise ValueError(f"{self.validation_name} must be positive")


@dataclass(frozen=True, slots=True)
class NonNegativeFiniteFloatValue:
    value: float
    validation_name: ClassVar[str] = "value"

    def __post_init__(self) -> None:
        if _number(self.value, self.validation_name) < 0:
            raise ValueError(f"{self.validation_name} must be non-negative")


@dataclass(frozen=True, slots=True)
class OpenUnitIntervalValue:
    value: float
    validation_name: ClassVar[str] = "value"

    def __post_init__(self) -> None:
        value = _number(self.value, self.validation_name)
        if not 0 < value < 1:
            raise ValueError(f"{self.validation_name} must be in (0, 1)")


@dataclass(frozen=True, slots=True)
class ClosedUnitIntervalValue:
    value: float
    validation_name: ClassVar[str] = "value"

    def __post_init__(self) -> None:
        value = _number(self.value, self.validation_name)
        if not 0 <= value <= 1:
            raise ValueError(f"{self.validation_name} must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class Seed(NonNegativeIntegerValue):
    validation_name = "seed"


@dataclass(frozen=True, slots=True)
class Ratio(ClosedUnitIntervalValue):
    validation_name = "ratio"


@dataclass(frozen=True, slots=True)
class Quantile(OpenUnitIntervalValue):
    validation_name = "quantile"


@dataclass(frozen=True, slots=True)
class CoverageTarget(OpenUnitIntervalValue):
    validation_name = "coverage target"


@dataclass(frozen=True, slots=True)
class CalibrationSize(PositiveIntegerValue):
    validation_name = "calibration size"


@dataclass(frozen=True, slots=True)
class ClientCount(PositiveIntegerValue):
    validation_name = "client count"


@dataclass(frozen=True, slots=True)
class SeedCount(PositiveIntegerValue):
    validation_name = "seed count"


@dataclass(frozen=True, slots=True)
class RoundNumber(PositiveIntegerValue):
    validation_name = "round number"


@dataclass(frozen=True, slots=True)
class LocalEpochCount(PositiveIntegerValue):
    validation_name = "local epoch count"


@dataclass(frozen=True, slots=True)
class BatchSize(PositiveIntegerValue):
    validation_name = "batch size"


@dataclass(frozen=True, slots=True)
class BootstrapReplicateCount(PositiveIntegerValue):
    validation_name = "bootstrap replicate count"


@dataclass(frozen=True, slots=True)
class SubsampleReplicateCount(PositiveIntegerValue):
    validation_name = "subsample replicate count"


@dataclass(frozen=True, slots=True)
class GroupCount(PositiveIntegerValue):
    validation_name = "group count"


@dataclass(frozen=True, slots=True)
class KMeansInitializationCount(PositiveIntegerValue):
    validation_name = "k-means initialization count"


@dataclass(frozen=True, slots=True)
class KMeansMaximumIterationCount(PositiveIntegerValue):
    validation_name = "k-means maximum iteration count"


@dataclass(frozen=True, slots=True)
class ByteCount(NonNegativeIntegerValue):
    validation_name = "byte count"


@dataclass(frozen=True, slots=True)
class LearningRate(PositiveFiniteFloatValue):
    validation_name = "learning rate"


@dataclass(frozen=True, slots=True)
class DirichletConcentration(PositiveFiniteFloatValue):
    validation_name = "Dirichlet concentration"


@dataclass(frozen=True, slots=True)
class ProximalCoefficient(PositiveFiniteFloatValue):
    validation_name = "proximal coefficient"


@dataclass(frozen=True, slots=True)
class DittoRegularization(NonNegativeFiniteFloatValue):
    validation_name = "Ditto regularization"


@dataclass(frozen=True, slots=True)
class ShrinkageWeight(ClosedUnitIntervalValue):
    validation_name = "shrinkage weight"


@dataclass(frozen=True, slots=True)
class SummaryCoefficient(PositiveFiniteFloatValue):
    validation_name = "summary coefficient"


@dataclass(frozen=True, slots=True)
class ConfidenceLevel(OpenUnitIntervalValue):
    validation_name = "confidence level"


@dataclass(frozen=True, slots=True)
class ThresholdValue:
    value: float

    def __post_init__(self) -> None:
        _number(self.value, "threshold")


@dataclass(frozen=True, slots=True)
class ScoreValue:
    value: float

    def __post_init__(self) -> None:
        _number(self.value, "score")


@dataclass(frozen=True, slots=True)
class MetricValue:
    value: float

    def __post_init__(self) -> None:
        _number(self.value, "metric")


@dataclass(frozen=True, slots=True)
class TrafficRatePerDay(NonNegativeFiniteFloatValue):
    validation_name = "traffic rate"


@dataclass(frozen=True, slots=True)
class Checksum:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("checksum must be non-empty")
        object.__setattr__(self, "value", self.value.strip().lower())


@dataclass(frozen=True, slots=True)
class ClientIdentity:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("client identity must be non-empty")
        if self.value in {".", ".."} or any(token in self.value for token in ("=", "/", "\\")):
            raise ValueError("client identity must be a single non-relative path segment without key=value syntax")


def checksum_text(payload: str) -> Checksum:
    return Checksum(sha256(payload.encode()).hexdigest())


def checksum_file(path: Path) -> Checksum:
    with path.open("rb") as source:
        return Checksum(file_digest(source, "sha256").hexdigest())

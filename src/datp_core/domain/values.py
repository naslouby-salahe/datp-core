"""Validated scalar scientific values."""

from dataclasses import dataclass
from hashlib import file_digest, sha256
from math import isclose, isfinite
from pathlib import Path
from typing import ClassVar

# Shared math.isclose controls for absolute-only floating comparisons.
NUMERIC_ZERO: float = 0.0
NO_RELATIVE_TOLERANCE: float = 0.0


def floats_absolutely_close(left: float, right: float, absolute_tolerance: float) -> bool:
    """Compare floats with an explicit absolute tolerance and zero relative tolerance."""
    if absolute_tolerance < NUMERIC_ZERO:
        raise ValueError("absolute tolerance must be non-negative")
    return isclose(left, right, rel_tol=NO_RELATIVE_TOLERANCE, abs_tol=absolute_tolerance)


def floats_exactly_equal(left: float, right: float) -> bool:
    """Full-precision equality with no absolute or relative tolerance band."""
    return isclose(left, right, rel_tol=NO_RELATIVE_TOLERANCE, abs_tol=NUMERIC_ZERO)


def is_numeric_zero(value: float) -> bool:
    return floats_exactly_equal(value, NUMERIC_ZERO)


def _integer(value: int, name: str, minimum: int) -> int:
    # bool is a subclass of int; reject it explicitly.
    if isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")
    return value


def _number(value: int | float, name: str) -> float:
    # bool is a subclass of int; reject it explicitly.
    if isinstance(value, bool) or not isfinite(float(value)):
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
    validation_name: ClassVar[str] = "seed"


@dataclass(frozen=True, slots=True)
class Ratio(ClosedUnitIntervalValue):
    validation_name: ClassVar[str] = "ratio"


@dataclass(frozen=True, slots=True)
class Quantile(OpenUnitIntervalValue):
    validation_name: ClassVar[str] = "quantile"


@dataclass(frozen=True, slots=True)
class CoverageTarget(OpenUnitIntervalValue):
    validation_name: ClassVar[str] = "coverage target"


@dataclass(frozen=True, slots=True)
class CalibrationSize(PositiveIntegerValue):
    validation_name: ClassVar[str] = "calibration size"


@dataclass(frozen=True, slots=True)
class ClientCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "client count"


@dataclass(frozen=True, slots=True)
class SeedCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "seed count"


@dataclass(frozen=True, slots=True)
class RoundNumber(PositiveIntegerValue):
    validation_name: ClassVar[str] = "round number"


@dataclass(frozen=True, slots=True)
class LocalEpochCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "local epoch count"


@dataclass(frozen=True, slots=True)
class BatchSize(PositiveIntegerValue):
    validation_name: ClassVar[str] = "batch size"


@dataclass(frozen=True, slots=True)
class BootstrapReplicateCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "bootstrap replicate count"


@dataclass(frozen=True, slots=True)
class SubsampleReplicateCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "subsample replicate count"


@dataclass(frozen=True, slots=True)
class GroupCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "group count"


@dataclass(frozen=True, slots=True)
class ReplicateIndex(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "replicate index"


@dataclass(frozen=True, slots=True)
class ClusterIndex(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "cluster index"


@dataclass(frozen=True, slots=True)
class KMeansInitializationCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "k-means initialization count"


@dataclass(frozen=True, slots=True)
class KMeansMaximumIterationCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "k-means maximum iteration count"


@dataclass(frozen=True, slots=True)
class ByteCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "byte count"


@dataclass(frozen=True, slots=True)
class LearningRate(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "learning rate"


@dataclass(frozen=True, slots=True)
class WeightDecay(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "weight decay"


@dataclass(frozen=True, slots=True)
class DataLoaderWorkerCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "data loader worker count"


@dataclass(frozen=True, slots=True)
class WorkerCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "worker count"


@dataclass(frozen=True, slots=True)
class FeatureCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "feature count"


@dataclass(frozen=True, slots=True)
class RowCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "row count"


@dataclass(frozen=True, slots=True)
class FeatureNameSequence:
    names: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.names, tuple) or not self.names:
            raise ValueError("feature name sequence requires a non-empty tuple")
        if any(not isinstance(name, str) or not name for name in self.names):
            raise ValueError("feature names must be non-empty strings")
        if len(frozenset(self.names)) != len(self.names):
            raise ValueError("feature names must be unique")

    def __len__(self) -> int:
        return len(self.names)

    def __iter__(self):
        return iter(self.names)

    def as_list(self) -> list[str]:
        return list(self.names)


@dataclass(frozen=True, slots=True)
class OutcomeLabelSequence:
    labels: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.labels, tuple):
            raise TypeError("outcome labels must be an immutable tuple")
        if any(not isinstance(label, str) or not label for label in self.labels):
            raise ValueError("outcome labels must be non-empty strings")

    def __len__(self) -> int:
        return len(self.labels)

    def __iter__(self):
        return iter(self.labels)


@dataclass(frozen=True, slots=True)
class DirichletConcentration(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "Dirichlet concentration"


@dataclass(frozen=True, slots=True)
class ProximalCoefficient(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "proximal coefficient"


@dataclass(frozen=True, slots=True)
class DittoRegularization(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "Ditto regularization"


@dataclass(frozen=True, slots=True)
class ShrinkageWeight(ClosedUnitIntervalValue):
    validation_name: ClassVar[str] = "shrinkage weight"


@dataclass(frozen=True, slots=True)
class SummaryCoefficient(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "summary coefficient"


@dataclass(frozen=True, slots=True)
class ConfidenceLevel(OpenUnitIntervalValue):
    validation_name: ClassVar[str] = "confidence level"


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
    validation_name: ClassVar[str] = "traffic rate"


@dataclass(frozen=True, slots=True)
class Checksum:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("checksum must be non-empty")
        object.__setattr__(self, "value", self.value.strip().lower())


@dataclass(frozen=True, slots=True)
class ClientPathToken:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("client path token must be non-empty")
        if self.value in {".", ".."} or any(token in self.value for token in ("=", "/", "\\")):
            raise ValueError("client path token must be a single non-relative path segment without key=value syntax")


@dataclass(frozen=True, slots=True)
class FamilyIdentity:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("family identity must be non-empty")


def checksum_text(payload: str) -> Checksum:
    return Checksum(sha256(payload.encode()).hexdigest())


def checksum_file(path: Path) -> Checksum:
    with path.open("rb") as source:
        return Checksum(file_digest(source, "sha256").hexdigest())

"""Validated scalar scientific values."""

from dataclasses import dataclass
from math import isfinite


def _integer(value: object, name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")
    return value


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


@dataclass(frozen=True, slots=True)
class Seed:
    value: int

    def __post_init__(self) -> None:
        _integer(self.value, "seed", 0)


@dataclass(frozen=True, slots=True)
class Ratio:
    value: float

    def __post_init__(self) -> None:
        if not 0 <= _number(self.value, "ratio") <= 1:
            raise ValueError("ratio must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class Quantile:
    value: float

    def __post_init__(self) -> None:
        if not 0 < _number(self.value, "quantile") < 1:
            raise ValueError("quantile must be in (0, 1)")


@dataclass(frozen=True, slots=True)
class CoverageTarget:
    value: float

    def __post_init__(self) -> None:
        if not 0 < _number(self.value, "coverage target") < 1:
            raise ValueError("coverage target must be in (0, 1)")


@dataclass(frozen=True, slots=True)
class CalibrationSize:
    value: int

    def __post_init__(self) -> None:
        _integer(self.value, "calibration size", 1)


@dataclass(frozen=True, slots=True)
class ClientCount:
    value: int

    def __post_init__(self) -> None:
        _integer(self.value, "client count", 1)


@dataclass(frozen=True, slots=True)
class RoundNumber:
    value: int

    def __post_init__(self) -> None:
        _integer(self.value, "round number", 1)


@dataclass(frozen=True, slots=True)
class LocalEpochCount:
    value: int

    def __post_init__(self) -> None:
        _integer(self.value, "local epoch count", 1)


@dataclass(frozen=True, slots=True)
class BatchSize:
    value: int

    def __post_init__(self) -> None:
        _integer(self.value, "batch size", 1)


@dataclass(frozen=True, slots=True)
class BootstrapReplicateCount:
    value: int

    def __post_init__(self) -> None:
        _integer(self.value, "bootstrap replicate count", 1)


@dataclass(frozen=True, slots=True)
class SubsampleReplicateCount:
    value: int

    def __post_init__(self) -> None:
        _integer(self.value, "subsample replicate count", 1)


@dataclass(frozen=True, slots=True)
class GroupCount:
    value: int

    def __post_init__(self) -> None:
        _integer(self.value, "group count", 1)


@dataclass(frozen=True, slots=True)
class ByteCount:
    value: int

    def __post_init__(self) -> None:
        _integer(self.value, "byte count", 0)


@dataclass(frozen=True, slots=True)
class LearningRate:
    value: float

    def __post_init__(self) -> None:
        if _number(self.value, "learning rate") <= 0:
            raise ValueError("learning rate must be positive")


@dataclass(frozen=True, slots=True)
class DirichletConcentration:
    value: float

    def __post_init__(self) -> None:
        if _number(self.value, "Dirichlet concentration") <= 0:
            raise ValueError("Dirichlet concentration must be positive")


@dataclass(frozen=True, slots=True)
class ProximalCoefficient:
    value: float

    def __post_init__(self) -> None:
        if _number(self.value, "proximal coefficient") <= 0:
            raise ValueError("proximal coefficient must be positive")


@dataclass(frozen=True, slots=True)
class DittoRegularization:
    value: float

    def __post_init__(self) -> None:
        if _number(self.value, "Ditto regularization") < 0:
            raise ValueError("Ditto regularization must be non-negative")


@dataclass(frozen=True, slots=True)
class ShrinkageWeight:
    value: float

    def __post_init__(self) -> None:
        if not 0 <= _number(self.value, "shrinkage weight") <= 1:
            raise ValueError("shrinkage weight must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class SummaryCoefficient:
    value: float

    def __post_init__(self) -> None:
        if _number(self.value, "summary coefficient") <= 0:
            raise ValueError("summary coefficient must be positive")


@dataclass(frozen=True, slots=True)
class ConfidenceLevel:
    value: float

    def __post_init__(self) -> None:
        if not 0 < _number(self.value, "confidence level") < 1:
            raise ValueError("confidence level must be in (0, 1)")


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
class TrafficRatePerDay:
    value: float

    def __post_init__(self) -> None:
        if _number(self.value, "traffic rate") < 0:
            raise ValueError("traffic rate must be non-negative")


@dataclass(frozen=True, slots=True)
class Checksum:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("checksum must be non-empty")
        object.__setattr__(self, "value", self.value.strip().lower())

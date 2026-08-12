from dataclasses import dataclass
from functools import total_ordering
from math import isclose, isfinite
from types import NotImplementedType
from typing import ClassVar, Self

from datp_core.core.contracts import pydantic_value_schema, sequence_pydantic_schema, validate_non_empty_tuple

NUMERIC_ZERO: float = 0.0
NO_RELATIVE_TOLERANCE: float = 0.0


def floats_absolutely_close(left: float, right: float, absolute_tolerance: float) -> bool:
    if absolute_tolerance < NUMERIC_ZERO:
        raise ValueError("absolute tolerance must be non-negative")
    return isclose(left, right, rel_tol=NO_RELATIVE_TOLERANCE, abs_tol=absolute_tolerance)


def floats_exactly_equal(left: float, right: float) -> bool:
    return isclose(left, right, rel_tol=NO_RELATIVE_TOLERANCE, abs_tol=NUMERIC_ZERO)


def is_numeric_zero(value: float) -> bool:
    return floats_exactly_equal(value, NUMERIC_ZERO)


def _integer(value: int, name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")
    return value


def _number(value: int | float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


type NumericValue = int | float


def _numeric_value(instance: object) -> NumericValue:
    value = getattr(instance, "value", None)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{type(instance).__name__} does not expose a numeric value")
    return value


def _compatible_value(self: object, other: object) -> NumericValue | NotImplementedType:
    if type(other) is type(self):
        return _numeric_value(other)
    return NotImplemented


def _ordering_compare(self: object, other: object) -> bool | NotImplementedType:
    other_value = _compatible_value(self, other)
    if other_value is NotImplemented:
        return NotImplemented
    return _numeric_value(self) < other_value


def _typed_eq(self: object, other: object) -> bool | NotImplementedType:
    other_value = _compatible_value(self, other)
    if other_value is NotImplemented:
        return NotImplemented
    return _numeric_value(self) == other_value


@total_ordering
@dataclass(frozen=True, slots=True)
class PositiveIntegerValue:
    value: int
    validation_name: ClassVar[str] = "value"

    def __post_init__(self) -> None:
        _integer(self.value, self.validation_name, 1)

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    def __hash__(self) -> int:
        return hash(self.value)

    def plus(self, other: Self) -> Self:
        if type(other) is not type(self):
            raise TypeError(f"{type(self).__name__}.plus requires another {type(self).__name__}")
        return type(self)(self.value + other.value)

    __get_pydantic_core_schema__ = classmethod(pydantic_value_schema)


@total_ordering
@dataclass(frozen=True, slots=True)
class NonNegativeIntegerValue:
    value: int
    validation_name: ClassVar[str] = "value"

    def __post_init__(self) -> None:
        _integer(self.value, self.validation_name, 0)

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    def __hash__(self) -> int:
        return hash(self.value)

    def plus(self, other: Self) -> Self:
        if type(other) is not type(self):
            raise TypeError(f"{type(self).__name__}.plus requires another {type(self).__name__}")
        return type(self)(self.value + other.value)

    __get_pydantic_core_schema__ = classmethod(pydantic_value_schema)


@total_ordering
@dataclass(frozen=True, slots=True)
class FiniteFloatValue:
    value: float
    validation_name: ClassVar[str] = "value"

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _number(self.value, self.validation_name))

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    def __hash__(self) -> int:
        return hash(self.value)

    def __float__(self) -> float:
        return self.value

    __get_pydantic_core_schema__ = classmethod(pydantic_value_schema)


class PositiveFiniteFloatValue(FiniteFloatValue):
    def __post_init__(self) -> None:
        super().__post_init__()
        if self.value <= 0:
            raise ValueError(f"{self.validation_name} must be positive")


class NonNegativeFiniteFloatValue(FiniteFloatValue):
    def __post_init__(self) -> None:
        super().__post_init__()
        if self.value < 0:
            raise ValueError(f"{self.validation_name} must be non-negative")


class OpenUnitIntervalValue(FiniteFloatValue):
    def __post_init__(self) -> None:
        super().__post_init__()
        if self.value <= NUMERIC_ZERO or self.value >= 1.0:
            raise ValueError(f"{self.validation_name} must be in (0, 1)")


class ClosedUnitIntervalValue(FiniteFloatValue):
    def __post_init__(self) -> None:
        super().__post_init__()
        if not 0 <= self.value <= 1:
            raise ValueError(f"{self.validation_name} must be in [0, 1]")


class Seed(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "seed"


class CalibrationSize(PositiveIntegerValue):
    validation_name: ClassVar[str] = "calibration size"

    def fits_within(self, count: "RowCount") -> bool:
        return self.value <= count.value


class OnboardingCalibrationSize(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "onboarding calibration size"


class ClientCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "client count"


class SeedCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "seed count"


class RoundNumber(PositiveIntegerValue):
    validation_name: ClassVar[str] = "round number"


class LocalEpochCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "local epoch count"


class BatchSize(PositiveIntegerValue):
    validation_name: ClassVar[str] = "batch size"


class BootstrapReplicateCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "bootstrap replicate count"


class SubsampleReplicateCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "subsample replicate count"


class GroupCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "group count"

    def fits_within(self, count: ClientCount) -> bool:
        return self.value < count.value


class KllSketchSize(PositiveIntegerValue):
    validation_name: ClassVar[str] = "KLL sketch size"


class KllReconstructionReplicateCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "KLL reconstruction replicate count"


class ReplicateIndex(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "replicate index"


class ConformalRankIndex(PositiveIntegerValue):
    validation_name: ClassVar[str] = "conformal rank index"


class ClusterIndex(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "cluster index"


class KMeansInitializationCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "k-means initialization count"


class KMeansMaximumIterationCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "k-means maximum iteration count"


class ByteCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "byte count"


class SourceFileCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "source file count"


class CanonicalColumnPosition(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "canonical column position"


class SourceRowIndex(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "source row index"


class MatrixRowIndex(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "matrix row index"


class NanosecondTimestamp(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "nanosecond timestamp"


class MicrosecondClock(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "microsecond clock"


class MicrosecondOffset(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "microsecond offset"


class ValidationIssueCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "validation issue count"


class PairedObservationCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "paired observation count"


class SeedObservationCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "seed observation count"


class SeedDerivationComponent(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "seed derivation component"


class PresentationDecimalCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "presentation decimal count"


class CampaignOrdinal(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "campaign ordinal"


class CampaignCoordinateCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "campaign coordinate count"


class ElapsedSeconds(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "elapsed seconds"


class LogicalElementCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "logical element count"


class CudaDeviceCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "CUDA device count"


class ClientPublicationCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "client publication count"


class DataLoaderWorkerCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "data loader worker count"


class ParallelEvaluationWorkerCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "parallel evaluation worker count"


class FeatureCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "feature count"


class RowCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "row count"


class ManifestSchemaVersion(PositiveIntegerValue):
    validation_name: ClassVar[str] = "manifest schema version"


class Ratio(ClosedUnitIntervalValue):
    validation_name: ClassVar[str] = "ratio"


class Quantile(OpenUnitIntervalValue):
    validation_name: ClassVar[str] = "quantile"


class CoverageTarget(OpenUnitIntervalValue):
    validation_name: ClassVar[str] = "coverage target"

    @property
    def significance(self) -> Ratio:
        return Ratio(1.0 - self.value)


class RankSum(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "rank sum"


class ThresholdVariance(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "threshold variance"


class AbsoluteThresholdError(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "absolute threshold error"


class RelativeThresholdError(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "relative threshold error"


class LearningRate(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "learning rate"


class WeightDecay(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "weight decay"


class AbsoluteTolerance(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "absolute tolerance"


NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE = AbsoluteTolerance(1e-12)


class DirichletConcentration(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "Dirichlet concentration"


class ProximalCoefficient(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "proximal coefficient"


class DittoRegularization(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "Ditto regularization"


class ModelCoefficientValue(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "model coefficient value"


class ShrinkageWeight(ClosedUnitIntervalValue):
    validation_name: ClassVar[str] = "shrinkage weight"


class NormalizedWeight(ClosedUnitIntervalValue):
    validation_name: ClassVar[str] = "normalized weight"


class SummaryCoefficient(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "summary coefficient"


class ConfidenceLevel(OpenUnitIntervalValue):
    validation_name: ClassVar[str] = "confidence level"


class ThresholdValue(FiniteFloatValue):
    validation_name: ClassVar[str] = "threshold"


class ScoreValue(FiniteFloatValue):
    validation_name: ClassVar[str] = "score"

    def exceeds(self, threshold: ThresholdValue) -> bool:
        return self.value > threshold.value


class MetricValue(FiniteFloatValue):
    validation_name: ClassVar[str] = "metric"


class MetricDelta(FiniteFloatValue):
    validation_name: ClassVar[str] = "metric delta"


class TrafficRatePerDay(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "traffic rate"


class ScoreMoment(FiniteFloatValue):
    validation_name: ClassVar[str] = "score moment"


class ScoreVariance(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "score variance"


class DistributionSkewness(FiniteFloatValue):
    validation_name: ClassVar[str] = "distribution skewness"


@dataclass(frozen=True, slots=True)
class CalibrationSampleWeights:
    weights: tuple[RowCount, ...]

    def __post_init__(self) -> None:
        validate_non_empty_tuple(self.weights, "calibration sample weights")

    @property
    def total(self) -> RowCount:
        return RowCount(sum(weight.value for weight in self.weights))

    @property
    def normalized(self) -> tuple[NormalizedWeight, ...]:
        total = self.total
        if total.value == 0:
            raise ValueError("calibration sample weights require positive total support")
        return tuple(NormalizedWeight(weight.value / total.value) for weight in self.weights)

    def __len__(self) -> int:
        return len(self.weights)

    def __iter__(self):
        return iter(self.weights)

    __get_pydantic_core_schema__ = classmethod(sequence_pydantic_schema)

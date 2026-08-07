"""Validated ratios, quantiles, tolerances, and scientific numeric values."""

from dataclasses import dataclass
from typing import ClassVar

from datp_core.domain.values.base import (
    ClosedUnitIntervalValue,
    FiniteFloatValue,
    NonNegativeFiniteFloatValue,
    OpenUnitIntervalValue,
    PositiveFiniteFloatValue,
    sequence_pydantic_schema,
    validate_non_empty_tuple,
)
from datp_core.domain.values.counts import RowCount


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
    """Serialized form of a proximal or Ditto coefficient at manifest boundaries."""

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
        """The sole global operating rule: reconstruction error strictly exceeds threshold."""
        return self.value > threshold.value


class MetricValue(FiniteFloatValue):
    validation_name: ClassVar[str] = "metric"


class MetricDelta(FiniteFloatValue):
    validation_name: ClassVar[str] = "metric delta"


class TrafficRatePerDay(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "traffic rate"


class ScoreMoment(FiniteFloatValue):
    """Arithmetic mean of anomaly scores aggregated across a client or cohort."""

    validation_name: ClassVar[str] = "score moment"


class ScoreVariance(NonNegativeFiniteFloatValue):
    """Population or sample variance of anomaly scores."""

    validation_name: ClassVar[str] = "score variance"


class DistributionSkewness(FiniteFloatValue):
    """Skewness of a score distribution for cluster fingerprinting."""

    validation_name: ClassVar[str] = "distribution skewness"


@dataclass(frozen=True, slots=True)
class CalibrationSampleWeights:
    """Per-client calibration sample counts used as aggregation weights."""

    weights: tuple[RowCount, ...]

    def __post_init__(self) -> None:
        validate_non_empty_tuple(self.weights, "calibration sample weights")

    @property
    def as_floats(self) -> tuple[float, ...]:
        return tuple(float(w.value) for w in self.weights)

    @property
    def total(self) -> float:
        return float(sum(w.value for w in self.weights))

    @property
    def normalized(self) -> tuple[NormalizedWeight, ...]:
        t = self.total
        return tuple(NormalizedWeight(w.value / t) for w in self.weights)

    def __len__(self) -> int:
        return len(self.weights)

    def __iter__(self):
        return iter(self.weights)

    __get_pydantic_core_schema__ = classmethod(sequence_pydantic_schema)

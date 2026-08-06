"""Validated ratios, quantiles, tolerances, and scientific numeric values."""

from typing import ClassVar

from datp_core.domain.values.base import (
    ClosedUnitIntervalValue,
    FiniteFloatValue,
    NonNegativeFiniteFloatValue,
    OpenUnitIntervalValue,
    PositiveFiniteFloatValue,
)


class Ratio(ClosedUnitIntervalValue):
    validation_name: ClassVar[str] = "ratio"


class Quantile(OpenUnitIntervalValue):
    validation_name: ClassVar[str] = "quantile"


class CoverageTarget(OpenUnitIntervalValue):
    validation_name: ClassVar[str] = "coverage target"


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


class SummaryCoefficient(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "summary coefficient"


class ConfidenceLevel(OpenUnitIntervalValue):
    validation_name: ClassVar[str] = "confidence level"


class ThresholdValue(FiniteFloatValue):
    validation_name: ClassVar[str] = "threshold"
    comparison_family: ClassVar[str | None] = "anomaly_score"


class ScoreValue(FiniteFloatValue):
    validation_name: ClassVar[str] = "score"
    comparison_family: ClassVar[str | None] = "anomaly_score"


class MetricValue(FiniteFloatValue):
    validation_name: ClassVar[str] = "metric"


class TrafficRatePerDay(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "traffic rate"

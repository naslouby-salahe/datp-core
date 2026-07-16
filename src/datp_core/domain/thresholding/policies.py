from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from enum import StrEnum
from math import isfinite
from typing import TYPE_CHECKING

from datp_core.domain.artifacts.lineage import ThresholdIdentity
from datp_core.domain.artifacts.references import CalibrationScoreArtifactId, StageFingerprint
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.learning.scores import QuantileEstimatorType

if TYPE_CHECKING:
    from datp_core.domain.learning.scores import ThresholdAssignmentSet
    from datp_core.domain.thresholding.clustering import B4ClusteringSpec, ClusterThresholdAggregationSpec
    from datp_core.domain.thresholding.federated_statistics import (
        FedStatsBenignThresholdSpec,
        ThresholdComparatorRole,
    )
    from datp_core.domain.thresholding.variants import (
        CalibrationSizeFallbackThresholdSpec,
        ConformalThresholdSpec,
        RobustClusterMedianThresholdSpec,
        ShrinkageThresholdSpec,
        ThresholdVariant,
    )

type DecimalInput = Decimal | float | int | str

DECIMAL_QUANTUM = Decimal("0.000000000001")


def _finite_decimal(value: DecimalInput) -> Decimal:
    if isinstance(value, DecimalValue):
        raise DomainValidationError(
            detail="a probability-like value object cannot construct another probability-like type",
            value=repr(value),
            constraint="raw Decimal-compatible value",
        )
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise DomainValidationError(
            detail="value must be a finite Decimal-compatible value",
            value=repr(value),
            constraint="finite Decimal-compatible value",
        ) from error
    if not decimal_value.is_finite():
        raise DomainValidationError(
            detail="value must be finite",
            value=str(decimal_value),
            constraint="finite Decimal",
        )
    return decimal_value


def canonical_decimal(value: DecimalInput) -> Decimal:
    decimal_value = _finite_decimal(value)
    try:
        return decimal_value.quantize(DECIMAL_QUANTUM, rounding=ROUND_HALF_EVEN)
    except InvalidOperation as error:
        raise DomainValidationError(
            detail="value cannot be represented at the canonical Decimal precision",
            value=str(decimal_value),
            constraint="twelve fractional Decimal places",
        ) from error


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class DecimalValue:
    value: Decimal

    def __init__(self, *, value: DecimalInput) -> None:
        canonical_value = canonical_decimal(value)
        self._validate(canonical_value)
        object.__setattr__(self, "value", canonical_value)

    def _validate(self, value: Decimal) -> None:
        del value


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class FiniteFloatValue:
    value: float

    def __init__(self, *, value: float | int) -> None:
        if isinstance(value, FiniteFloatValue):
            raise DomainValidationError(
                detail="a float value object cannot construct another float value object",
                value=repr(value),
                constraint="raw finite float-compatible value",
            )
        try:
            float_value = float(value)
        except (TypeError, ValueError) as error:
            raise DomainValidationError(
                detail="value must be float-compatible",
                value=repr(value),
                constraint="float-compatible value",
            ) from error
        if not isfinite(float_value):
            raise DomainValidationError(
                detail="value must be finite",
                value=str(float_value),
                constraint="finite float",
            )
        self._validate(float_value)
        object.__setattr__(self, "value", float_value)

    def _validate(self, value: float) -> None:
        del value


class CoreThresholdPolicy(StrEnum):
    B1 = "b1"
    B2 = "b2"
    B3 = "b3"
    B4 = "b4"


class SharedThresholdConstruction(StrEnum):
    MEAN = "mean"
    POOLED = "pooled"
    WEIGHTED = "weighted"


class ThresholdConstructionKind(StrEnum):
    SHARED = "shared"
    LOCAL = "local"
    FAMILY = "family"
    CLUSTER = "cluster"
    ROBUST_CLUSTER_MEDIAN = "robust_cluster_median"
    SHRINKAGE = "shrinkage"
    CALIB_SIZE_FALLBACK = "calib_size_fallback"
    CONFORMAL = "conformal"
    FED_STATS_BENIGN = "fed_stats_benign"


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ThresholdPercentile(DecimalValue):
    def _validate(self, value: Decimal) -> None:
        if not Decimal(0) < value < Decimal(1):
            raise DomainValidationError(
                detail="threshold percentile must be strictly between zero and one",
                value=str(value),
                constraint="0 < threshold percentile < 1",
            )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class FprTarget(DecimalValue):
    def _validate(self, value: Decimal) -> None:
        if not Decimal(0) < value < Decimal(1):
            raise DomainValidationError(
                detail="FPR target must be strictly between zero and one",
                value=str(value),
                constraint="0 < FPR target < 1",
            )

    @classmethod
    def from_percentile(cls, *, percentile: ThresholdPercentile) -> FprTarget:
        return cls(value=Decimal(1) - percentile.value)


def validate_fpr_target(*, percentile: ThresholdPercentile, target: FprTarget) -> None:
    expected_target = Decimal(1) - percentile.value
    if target.value != expected_target:
        raise DomainValidationError(
            detail="FPR target must equal one minus the threshold percentile",
            value=str(target.value),
            constraint=f"FPR target == 1 - {percentile.value}",
        )


def validate_construction_kind(*, value: ThresholdConstructionKind, expected: ThresholdConstructionKind) -> None:
    if value is not expected:
        raise DomainValidationError(
            detail="threshold construction must carry its explicit matching kind",
            value=repr(value),
            constraint=expected.value,
        )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ThresholdValue(FiniteFloatValue):
    def _validate(self, value: float) -> None:
        if value < 0:
            raise DomainValidationError(
                detail="threshold value must be non-negative",
                value=str(value),
                constraint="threshold value >= 0",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SharedThresholdSpec:
    kind: ThresholdConstructionKind
    percentile: ThresholdPercentile
    construction: SharedThresholdConstruction
    estimator: QuantileEstimatorType

    def __post_init__(self) -> None:
        validate_construction_kind(value=self.kind, expected=ThresholdConstructionKind.SHARED)
        if type(self.estimator) is not QuantileEstimatorType:
            raise DomainValidationError(
                detail="shared threshold requires a closed exact estimator",
                value=repr(self.estimator),
                constraint="QuantileEstimatorType",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class LocalThresholdSpec:
    kind: ThresholdConstructionKind
    percentile: ThresholdPercentile
    estimator: QuantileEstimatorType

    def __post_init__(self) -> None:
        validate_construction_kind(value=self.kind, expected=ThresholdConstructionKind.LOCAL)
        if type(self.estimator) is not QuantileEstimatorType:
            raise DomainValidationError(
                detail="local threshold requires a closed exact estimator",
                value=repr(self.estimator),
                constraint="QuantileEstimatorType",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class FamilyThresholdSpec:
    kind: ThresholdConstructionKind
    percentile: ThresholdPercentile
    family_manifest_identity: StageFingerprint

    def __post_init__(self) -> None:
        validate_construction_kind(value=self.kind, expected=ThresholdConstructionKind.FAMILY)


@dataclass(frozen=True, slots=True, kw_only=True)
class ClusterThresholdSpec:
    kind: ThresholdConstructionKind
    percentile: ThresholdPercentile
    clustering: B4ClusteringSpec
    aggregation: ClusterThresholdAggregationSpec

    def __post_init__(self) -> None:
        validate_construction_kind(value=self.kind, expected=ThresholdConstructionKind.CLUSTER)
        from datp_core.domain.thresholding.clustering import B4ClusteringSpec, ClusterThresholdAggregationSpec

        if (
            type(self.clustering) is not B4ClusteringSpec
            or type(self.aggregation) is not ClusterThresholdAggregationSpec
        ):
            raise DomainValidationError(
                detail="cluster threshold requires canonical B4 clustering and typed aggregation specifications",
                value=repr(self),
                constraint="B4ClusteringSpec and ClusterThresholdAggregationSpec",
            )
        if self.percentile != self.aggregation.percentile:
            raise DomainValidationError(
                detail="cluster threshold percentile must match the aggregation percentile",
                value=repr((self.percentile, self.aggregation.percentile)),
                constraint="matching threshold percentiles",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class B0PooledThresholdSpec:
    percentile: ThresholdPercentile

    def __post_init__(self) -> None:
        if self.percentile.value != Decimal("0.95"):
            raise DomainValidationError(
                detail="B0's pooled threshold percentile is locked to the recovered p95 value",
                value=str(self.percentile.value),
                constraint="percentile == 0.95",
            )


def compute_b0_pooled_threshold(
    *, pooled_calibration_scores: tuple[float, ...], spec: B0PooledThresholdSpec
) -> ThresholdValue:
    from datp_core.domain.mathematics.quantiles import exact_quantile

    return ThresholdValue(value=exact_quantile(values=pooled_calibration_scores, percentile=spec.percentile))


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdSuiteSpec:
    constructions: tuple[ThresholdConstructionSpec, ...]

    def __post_init__(self) -> None:
        construction_types = _threshold_construction_types()
        if not self.constructions or any(
            type(construction) not in construction_types for construction in self.constructions
        ):
            raise DomainValidationError(
                detail="threshold suite requires closed typed constructions",
                value=repr(self.constructions),
                constraint="non-empty tuple[ThresholdConstructionSpec, ...]",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdAssignment:
    policy: CoreThresholdPolicy | ThresholdVariant | ThresholdComparatorRole
    per_client_tau: ThresholdAssignmentSet
    calibration_score_artifact_id: CalibrationScoreArtifactId
    threshold_identity: ThresholdIdentity
    eligible_client_set_identity: StageFingerprint
    fallback_fingerprint: StageFingerprint

    def __post_init__(self) -> None:
        from datp_core.domain.thresholding.federated_statistics import ThresholdComparatorRole
        from datp_core.domain.thresholding.variants import ThresholdVariant

        if type(self.policy) not in {CoreThresholdPolicy, ThresholdVariant, ThresholdComparatorRole}:
            raise DomainValidationError(
                detail="threshold assignment requires a core policy, declared variant, or comparator role",
                value=repr(self.policy),
                constraint="CoreThresholdPolicy, ThresholdVariant, or ThresholdComparatorRole",
            )


def unweighted_shared_threshold(*, local_thresholds: tuple[ThresholdValue, ...]) -> ThresholdValue:
    if not local_thresholds:
        raise DomainValidationError(
            detail="shared threshold requires eligible local thresholds",
            value=repr(local_thresholds),
            constraint="non-empty",
        )
    return ThresholdValue(value=sum(threshold.value for threshold in local_thresholds) / len(local_thresholds))


if TYPE_CHECKING:
    type ThresholdConstructionSpec = (
        SharedThresholdSpec
        | LocalThresholdSpec
        | FamilyThresholdSpec
        | ClusterThresholdSpec
        | RobustClusterMedianThresholdSpec
        | ShrinkageThresholdSpec
        | CalibrationSizeFallbackThresholdSpec
        | ConformalThresholdSpec
        | FedStatsBenignThresholdSpec
    )


def __getattr__(name: str) -> object:
    if name != "ThresholdConstructionSpec":
        raise AttributeError(name)
    from datp_core.domain.thresholding.federated_statistics import FedStatsBenignThresholdSpec
    from datp_core.domain.thresholding.variants import (
        CalibrationSizeFallbackThresholdSpec,
        ConformalThresholdSpec,
        RobustClusterMedianThresholdSpec,
        ShrinkageThresholdSpec,
    )

    return (
        SharedThresholdSpec
        | LocalThresholdSpec
        | FamilyThresholdSpec
        | ClusterThresholdSpec
        | RobustClusterMedianThresholdSpec
        | ShrinkageThresholdSpec
        | CalibrationSizeFallbackThresholdSpec
        | ConformalThresholdSpec
        | FedStatsBenignThresholdSpec
    )


def _threshold_construction_types() -> tuple[type[object], ...]:
    from datp_core.domain.thresholding.federated_statistics import FedStatsBenignThresholdSpec
    from datp_core.domain.thresholding.variants import (
        CalibrationSizeFallbackThresholdSpec,
        ConformalThresholdSpec,
        RobustClusterMedianThresholdSpec,
        ShrinkageThresholdSpec,
    )

    return (
        SharedThresholdSpec,
        LocalThresholdSpec,
        FamilyThresholdSpec,
        ClusterThresholdSpec,
        RobustClusterMedianThresholdSpec,
        ShrinkageThresholdSpec,
        CalibrationSizeFallbackThresholdSpec,
        ConformalThresholdSpec,
        FedStatsBenignThresholdSpec,
    )

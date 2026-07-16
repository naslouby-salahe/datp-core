from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.data.splitting import ConformalSplitSpec
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.alert_burden import CalibrationSampleCount
from datp_core.domain.thresholding.policies import (
    DecimalValue,
    FiniteFloatValue,
    ThresholdConstructionKind,
    ThresholdPercentile,
    validate_construction_kind,
)


class ThresholdVariant(StrEnum):
    SHRINKAGE_LGS = "shrinkage_lgs"
    CALIB_SIZE_FALLBACK = "calib_size_fallback"
    CONFORMAL_B2 = "conformal_b2"
    ROBUST_CLUSTER_MEDIAN_B4 = "robust_cluster_median_b4"


class ConformalMode(StrEnum):
    SPLIT = "split"
    FEDERATED = "federated"


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ShrinkageWeight(FiniteFloatValue):
    def _validate(self, value: float) -> None:
        if not 0 <= value <= 1:
            raise DomainValidationError(
                detail="shrinkage weight must be between zero and one",
                value=str(value),
                constraint="0 <= shrinkage weight <= 1",
            )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ConformalCoverage(DecimalValue):
    def _validate(self, value: Decimal) -> None:
        if not Decimal(0) <= value <= Decimal(1):
            raise DomainValidationError(
                detail="conformal coverage must be between zero and one",
                value=str(value),
                constraint="0 <= conformal coverage <= 1",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ShrinkageThresholdSpec:
    kind: ThresholdConstructionKind
    percentile: ThresholdPercentile
    shrinkage_weight: ShrinkageWeight

    def __post_init__(self) -> None:
        validate_construction_kind(value=self.kind, expected=ThresholdConstructionKind.SHRINKAGE)


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationSizeFallbackThresholdSpec:
    kind: ThresholdConstructionKind
    percentile: ThresholdPercentile
    fallback_rule_version: str
    calibration_sample_count: CalibrationSampleCount

    def __post_init__(self) -> None:
        validate_construction_kind(value=self.kind, expected=ThresholdConstructionKind.CALIB_SIZE_FALLBACK)
        if type(self.fallback_rule_version) is not str or not self.fallback_rule_version:
            raise DomainValidationError(
                detail="calibration-size fallback requires an explicit rule version",
                value=repr(self.fallback_rule_version),
                constraint="non-empty rule version",
            )
        if type(self.calibration_sample_count) is not CalibrationSampleCount:
            raise DomainValidationError(
                detail="calibration-size fallback requires a typed calibration sample count",
                value=repr(self.calibration_sample_count),
                constraint="CalibrationSampleCount",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ConformalThresholdSpec:
    kind: ThresholdConstructionKind
    conformal_split: ConformalSplitSpec
    mode: ConformalMode

    def __post_init__(self) -> None:
        validate_construction_kind(value=self.kind, expected=ThresholdConstructionKind.CONFORMAL)
        if type(self.conformal_split) is not ConformalSplitSpec or self.mode is not ConformalMode.SPLIT:
            raise DomainValidationError(
                detail="conformal threshold requires the closed split-conformal contract",
                value=repr(self),
                constraint="ConformalSplitSpec and SPLIT mode",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class RobustClusterMedianThresholdSpec:
    kind: ThresholdConstructionKind
    canonical_assignment_identity: StageFingerprint

    def __post_init__(self) -> None:
        validate_construction_kind(value=self.kind, expected=ThresholdConstructionKind.ROBUST_CLUSTER_MEDIAN)
        if type(self.canonical_assignment_identity) is not StageFingerprint:
            raise DomainValidationError(
                detail="robust cluster median requires a canonical B4 assignment identity",
                value=repr(self.canonical_assignment_identity),
                constraint="StageFingerprint",
            )

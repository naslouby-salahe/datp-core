from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar

from datp_core.domain.artifacts.lineage import PartitionIdentity, SplitIdentity, TemporalWindowIdentity
from datp_core.domain.artifacts.references import ArtifactRef
from datp_core.domain.data.datasets import TimestampEvidence
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.statistical_results import Probability
from datp_core.domain.mathematics.pooled_statistics import REGIME_D_TEMPORAL_HISTORICAL_FRACTION
from datp_core.domain.thresholding.policies import FprTarget, ThresholdPercentile, validate_fpr_target


class SplitRole(StrEnum):
    TRAIN = "train"
    CALIBRATION = "calibration"
    TEST = "test"
    TEMPORAL_EVALUATION = "temporal_evaluation"


class RecalibrationMode(StrEnum):
    FROZEN = "frozen"
    ONE_SHOT = "one_shot"


class TemporalOutcome(StrEnum):
    RECAL_HELPS = "recal_helps"
    RECAL_INSUFFICIENT = "recal_insufficient"
    NO_MEANINGFUL_DRIFT = "no_meaningful_drift"


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainingSplitSpec:
    split_identity: SplitIdentity
    partition_identity: PartitionIdentity
    role: SplitRole = field(default=SplitRole.TRAIN, init=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class BenignCalibrationSplitSpec:
    split_identity: SplitIdentity
    partition_identity: PartitionIdentity
    role: SplitRole = field(default=SplitRole.CALIBRATION, init=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class TestSplitSpec:
    __test__: ClassVar[bool] = False
    split_identity: SplitIdentity
    partition_identity: PartitionIdentity
    role: SplitRole = field(default=SplitRole.TEST, init=False)


type SplitSpec = TrainingSplitSpec | BenignCalibrationSplitSpec | TestSplitSpec


@dataclass(frozen=True, slots=True, kw_only=True)
class SplitCollectionSpec:
    training: TrainingSplitSpec
    calibration: BenignCalibrationSplitSpec
    test: TestSplitSpec

    def __post_init__(self) -> None:
        split_ids = (self.training.split_identity, self.calibration.split_identity, self.test.split_identity)
        if len(set(split_ids)) != len(split_ids):
            raise DomainValidationError(
                detail="split collection requires distinct training, calibration, and test identities",
                value=repr(split_ids),
                constraint="one distinct split identity for every static role",
            )
        partition_ids = (
            self.training.partition_identity,
            self.calibration.partition_identity,
            self.test.partition_identity,
        )
        if len(set(partition_ids)) != 1:
            raise DomainValidationError(
                detail="split collection roles must share one partition identity",
                value=repr(partition_ids),
                constraint="one shared partition identity",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SplitManifestResult:
    split_manifest: ArtifactRef
    split_identities: SplitCollectionSpec
    partition_identity: PartitionIdentity

    def __post_init__(self) -> None:
        if self.split_identities.training.partition_identity != self.partition_identity:
            raise DomainValidationError(
                detail="split manifest partition identity must match all split roles",
                value=repr(self.partition_identity),
                constraint="split collection partition identity",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalBoundary:
    historical_fraction: Probability
    timestamp_field: TimestampEvidence
    boundary_identity: TemporalWindowIdentity

    def __post_init__(self) -> None:
        if self.historical_fraction != REGIME_D_TEMPORAL_HISTORICAL_FRACTION:
            raise DomainValidationError(
                detail="temporal boundary must use the locked historical fraction",
                value=str(self.historical_fraction.value),
                constraint=str(REGIME_D_TEMPORAL_HISTORICAL_FRACTION.value),
            )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class TemporalWindowSpec:
    boundary: TemporalBoundary


@dataclass(frozen=True, slots=True, kw_only=True)
class HistoricalTemporalWindowSpec(TemporalWindowSpec):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalEvaluationWindowSpec(TemporalWindowSpec):
    role: SplitRole = field(default=SplitRole.TEMPORAL_EVALUATION, init=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class OneShotRecalibrationSpec:
    mode: RecalibrationMode
    calibration_split: BenignCalibrationSplitSpec

    def __post_init__(self) -> None:
        if self.mode is not RecalibrationMode.ONE_SHOT:
            raise DomainValidationError(
                detail="one-shot recalibration requires ONE_SHOT mode",
                value=self.mode.value,
                constraint="ONE_SHOT",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalProtocolSpec:
    historical: HistoricalTemporalWindowSpec
    evaluation: TemporalEvaluationWindowSpec
    one_shot_recalibration: OneShotRecalibrationSpec

    def __post_init__(self) -> None:
        if self.historical.boundary != self.evaluation.boundary:
            raise DomainValidationError(
                detail="temporal protocol windows must share one temporal boundary",
                value=repr((self.historical.boundary, self.evaluation.boundary)),
                constraint="shared temporal boundary",
            )


class ConformalQuantileIndexRule(StrEnum):
    CEILING_N_PLUS_ONE = "ceiling_n_plus_one"


@dataclass(frozen=True, slots=True, kw_only=True)
class ConformalSplitSpec:
    proper_fit_split: TrainingSplitSpec
    calibration_split: BenignCalibrationSplitSpec
    percentile: ThresholdPercentile
    alpha: FprTarget
    quantile_index_rule: ConformalQuantileIndexRule

    def __post_init__(self) -> None:
        if type(self.proper_fit_split) is not TrainingSplitSpec:
            raise DomainValidationError(
                detail="conformal proper-fit substrate must be the training split",
                value=type(self.proper_fit_split).__name__,
                constraint="TrainingSplitSpec",
            )
        if type(self.calibration_split) is not BenignCalibrationSplitSpec:
            raise DomainValidationError(
                detail="conformal calibration substrate must be the benign calibration split",
                value=type(self.calibration_split).__name__,
                constraint="BenignCalibrationSplitSpec",
            )
        validate_fpr_target(percentile=self.percentile, target=self.alpha)

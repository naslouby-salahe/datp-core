from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar

from datp_core.domain.artifacts.lineage import PartitionIdentity, SplitIdentity, TemporalWindowIdentity
from datp_core.domain.artifacts.references import ArtifactRef, StageFingerprint
from datp_core.domain.data.datasets import TimestampEvidence
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.statistical_results import Probability
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.mathematics.pooled_statistics import (
    REGIME_A_STATIC_SPLIT_CALIBRATION_FRACTION,
    REGIME_A_STATIC_SPLIT_GAP_FRACTION,
    REGIME_A_STATIC_SPLIT_TRAIN_FRACTION,
    REGIME_D_TEMPORAL_HISTORICAL_FRACTION,
    EligibilityClassification,
)
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


def _validated_split_row_count(value: int, *, name: str) -> None:
    if isinstance(value, bool) or value < 0:
        raise DomainValidationError(
            detail=f"{name} must be a non-negative integer", value=repr(value), constraint=f"{name} >= 0"
        )


def _validated_split_checksum(value: str, *, name: str) -> None:
    if not value:
        raise DomainValidationError(
            detail=f"{name} must be a non-empty row-order checksum", value=repr(value), constraint="non-empty"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientSplitMembership:
    client_id: ClientId
    train_row_count: int
    train_row_order_checksum: str
    calibration_row_count: int
    calibration_row_order_checksum: str
    test_row_count: int
    test_row_order_checksum: str
    eligibility: EligibilityClassification

    def __post_init__(self) -> None:
        _validated_split_row_count(self.train_row_count, name="train row count")
        _validated_split_checksum(self.train_row_order_checksum, name="train row-order checksum")
        _validated_split_row_count(self.calibration_row_count, name="calibration row count")
        _validated_split_checksum(self.calibration_row_order_checksum, name="calibration row-order checksum")
        _validated_split_row_count(self.test_row_count, name="test row count")
        _validated_split_checksum(self.test_row_order_checksum, name="test row-order checksum")


def _validated_unique_membership_client_ids(memberships: tuple[ClientSplitMembership, ...]) -> None:
    client_ids = tuple(membership.client_id.value for membership in memberships)
    if not client_ids or len(set(client_ids)) != len(client_ids):
        raise DomainValidationError(
            detail="split manifest requires at least one client with unique client ids",
            value=repr(client_ids),
            constraint="non-empty unique client ids",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class SplitManifest:
    partition_identity: PartitionIdentity
    split_identities: SplitCollectionSpec
    client_memberships: tuple[ClientSplitMembership, ...]
    eligible_client_set_identity: StageFingerprint

    def __post_init__(self) -> None:
        _validated_unique_membership_client_ids(self.client_memberships)


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


@dataclass(frozen=True, slots=True, kw_only=True)
class RegimeAStaticSplitBoundarySpec:
    train_fraction: Probability
    gap_fraction: Probability
    calibration_fraction: Probability

    def __post_init__(self) -> None:
        if (
            self.train_fraction != REGIME_A_STATIC_SPLIT_TRAIN_FRACTION
            or self.gap_fraction != REGIME_A_STATIC_SPLIT_GAP_FRACTION
            or self.calibration_fraction != REGIME_A_STATIC_SPLIT_CALIBRATION_FRACTION
        ):
            raise DomainValidationError(
                detail="Regime A static split boundary must use the locked recovered fractions",
                value=repr((self.train_fraction.value, self.gap_fraction.value, self.calibration_fraction.value)),
                constraint=repr(
                    (
                        REGIME_A_STATIC_SPLIT_TRAIN_FRACTION.value,
                        REGIME_A_STATIC_SPLIT_GAP_FRACTION.value,
                        REGIME_A_STATIC_SPLIT_CALIBRATION_FRACTION.value,
                    )
                ),
            )


LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY = RegimeAStaticSplitBoundarySpec(
    train_fraction=REGIME_A_STATIC_SPLIT_TRAIN_FRACTION,
    gap_fraction=REGIME_A_STATIC_SPLIT_GAP_FRACTION,
    calibration_fraction=REGIME_A_STATIC_SPLIT_CALIBRATION_FRACTION,
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

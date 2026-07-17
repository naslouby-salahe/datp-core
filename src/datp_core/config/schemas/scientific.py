from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from datp_core.domain.artifacts.references import CONTENT_HASH_PATTERN
from datp_core.domain.data.datasets import Regime, TimestampEvidenceKind
from datp_core.domain.data.partitioning import ClientDefinitionStrategy, DirichletAlphaSentinel
from datp_core.domain.data.preprocessing import FittedStatisticPolicy, NormalizationScope, NormalizationStrategy
from datp_core.domain.data.splitting import ConformalQuantileIndexRule
from datp_core.domain.evaluation.metrics import OperatingPointMetric
from datp_core.domain.evaluation.statistical_results import (
    CANONICAL_ANCHOR_REFERENCE_LOWER,
    CANONICAL_ANCHOR_REFERENCE_UPPER,
    CANONICAL_ANCHOR_TOLERANCE_MULTIPLIER,
)
from datp_core.domain.experiments.protocols import ProtocolTrack
from datp_core.domain.learning.scores import QuantileEstimatorType
from datp_core.domain.learning.training import AggregationStrategy, ParticipationStrategy
from datp_core.domain.mathematics.pooled_statistics import (
    REGIME_A_STATIC_SPLIT_CALIBRATION_FRACTION,
    REGIME_A_STATIC_SPLIT_GAP_FRACTION,
    REGIME_A_STATIC_SPLIT_TRAIN_FRACTION,
    REGIME_D_TEMPORAL_HISTORICAL_FRACTION,
)
from datp_core.domain.runtime.seeds import CONFIRMATORY_CONFIDENCE_LEVEL
from datp_core.domain.thresholding.federated_statistics import FED_STATS_SUPPLEMENTARY_K_VALUES
from datp_core.domain.thresholding.policies import SharedThresholdConstruction

type OpenUnitInterval = Annotated[Decimal, Field(gt=Decimal(0), lt=Decimal(1))]
type ClosedUnitInterval = Annotated[Decimal, Field(ge=Decimal(0), le=Decimal(1))]
type PositiveInteger = Annotated[int, Field(gt=0)]
type ConfirmatoryConfidence = Annotated[
    Decimal, Field(ge=CONFIRMATORY_CONFIDENCE_LEVEL, le=CONFIRMATORY_CONFIDENCE_LEVEL)
]
type CanonicalTemporalFraction = Annotated[
    Decimal,
    Field(ge=REGIME_D_TEMPORAL_HISTORICAL_FRACTION.value, le=REGIME_D_TEMPORAL_HISTORICAL_FRACTION.value),
]
type StageFingerprintText = Annotated[str, Field(pattern=f"^{CONTENT_HASH_PATTERN}$")]
type ConformalTargetAlpha = OpenUnitInterval
type AbsorptionStronglyUsefulFraction = ClosedUnitInterval
type AbsorptionPartialFraction = ClosedUnitInterval
type AbsorptionAlternativePathDistance = ClosedUnitInterval
type TemporalRecoveryFraction = ClosedUnitInterval
type FedStatsSupplementaryKValues = tuple[
    Annotated[
        Decimal,
        Field(ge=FED_STATS_SUPPLEMENTARY_K_VALUES[0], le=FED_STATS_SUPPLEMENTARY_K_VALUES[0]),
    ],
    Annotated[
        Decimal,
        Field(ge=FED_STATS_SUPPLEMENTARY_K_VALUES[1], le=FED_STATS_SUPPLEMENTARY_K_VALUES[1]),
    ],
    Annotated[
        Decimal,
        Field(ge=FED_STATS_SUPPLEMENTARY_K_VALUES[2], le=FED_STATS_SUPPLEMENTARY_K_VALUES[2]),
    ],
]


class ScientificSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SharedThresholdConfig(ScientificSchema):
    kind: Literal["shared"]
    percentile: OpenUnitInterval
    construction: SharedThresholdConstruction
    estimator: QuantileEstimatorType


class LocalThresholdConfig(ScientificSchema):
    kind: Literal["local"]
    percentile: OpenUnitInterval
    estimator: QuantileEstimatorType


class FamilyThresholdConfig(ScientificSchema):
    kind: Literal["family"]
    percentile: OpenUnitInterval
    family_taxonomy_id: str


class ClusterThresholdConfig(ScientificSchema):
    kind: Literal["cluster"]
    percentile: OpenUnitInterval


class RobustClusterMedianThresholdConfig(ScientificSchema):
    kind: Literal["robust_cluster_median"]


class ShrinkageThresholdConfig(ScientificSchema):
    kind: Literal["shrinkage"]
    percentile: OpenUnitInterval
    shrinkage_weight: ClosedUnitInterval


class CalibrationSizeFallbackThresholdConfig(ScientificSchema):
    kind: Literal["calib_size_fallback"]
    percentile: OpenUnitInterval
    fallback_rule_version: str
    calibration_sample_count: PositiveInteger


class ConformalThresholdConfig(ScientificSchema):
    kind: Literal["conformal"]
    mode: Literal["split"]
    alpha: ConformalTargetAlpha
    percentile: OpenUnitInterval
    quantile_index_rule: Literal[ConformalQuantileIndexRule.CEILING_N_PLUS_ONE]


class FedStatsBenignThresholdConfig(ScientificSchema):
    kind: Literal["fed_stats_benign"]


class QSensitivityGridConfig(ScientificSchema):
    values: tuple[OpenUnitInterval, ...]

    @field_validator("values")
    @classmethod
    def _values_are_unique_and_ordered(cls, values: tuple[Decimal, ...]) -> tuple[Decimal, ...]:
        if not values or tuple(sorted(set(values))) != tuple(values):
            raise ValueError("q-sensitivity grid values must be non-empty, unique, and strictly increasing")
        return values


type ThresholdConstructionConfig = Annotated[
    SharedThresholdConfig
    | LocalThresholdConfig
    | FamilyThresholdConfig
    | ClusterThresholdConfig
    | RobustClusterMedianThresholdConfig
    | ShrinkageThresholdConfig
    | CalibrationSizeFallbackThresholdConfig
    | ConformalThresholdConfig
    | FedStatsBenignThresholdConfig,
    Field(discriminator="kind"),
]


class EvaluationConfig(ScientificSchema):
    primary: Literal[OperatingPointMetric.CV_FPR]
    controls: tuple[OperatingPointMetric, ...]


class BcaBootstrapStatisticalConfig(ScientificSchema):
    method: Literal["bca_bootstrap"]
    confidence: ConfirmatoryConfidence
    paired_seed_count: Literal[10]
    resamples: PositiveInteger


class PercentileBootstrapStatisticalConfig(ScientificSchema):
    method: Literal["percentile_bootstrap"]
    confidence: OpenUnitInterval
    paired_seed_count: PositiveInteger
    resamples: PositiveInteger


class WilcoxonStatisticalConfig(ScientificSchema):
    method: Literal["wilcoxon_signed_rank"]
    confidence: OpenUnitInterval
    paired_seed_count: PositiveInteger
    resamples: PositiveInteger


class CliffsDeltaStatisticalConfig(ScientificSchema):
    method: Literal["cliffs_delta"]
    confidence: OpenUnitInterval
    paired_seed_count: PositiveInteger
    resamples: PositiveInteger


class SpearmanStatisticalConfig(ScientificSchema):
    method: Literal["spearman"]
    confidence: OpenUnitInterval
    paired_seed_count: PositiveInteger
    resamples: PositiveInteger


class LinearRegressionStatisticalConfig(ScientificSchema):
    method: Literal["linear_regression_r2"]
    confidence: OpenUnitInterval
    paired_seed_count: PositiveInteger
    resamples: PositiveInteger


type StatisticalConfig = Annotated[
    BcaBootstrapStatisticalConfig
    | PercentileBootstrapStatisticalConfig
    | WilcoxonStatisticalConfig
    | CliffsDeltaStatisticalConfig
    | SpearmanStatisticalConfig
    | LinearRegressionStatisticalConfig,
    Field(discriminator="method"),
]


class FedAvgFederationConfig(ScientificSchema):
    aggregation: Literal[AggregationStrategy.FEDAVG]
    local_epochs: Literal[1]
    participation: Literal[ParticipationStrategy.FULL]
    rounds_max: Literal[200]
    fedprox_mu: Literal[None]
    selection_source: Literal["not_applicable"]


class FedProxFederationConfig(ScientificSchema):
    aggregation: Literal[AggregationStrategy.FEDPROX]
    local_epochs: Literal[1]
    participation: Literal[ParticipationStrategy.FULL]
    rounds_max: Literal[200]
    fedprox_mu: Decimal
    selection_source: Literal["pre_registered_grid"]


type FederationConfig = Annotated[
    FedAvgFederationConfig | FedProxFederationConfig,
    Field(discriminator="aggregation"),
]


class AnchorCheckpointTerminationConfig(ScientificSchema):
    rounds_initial: Literal[40]
    rounds_max: Literal[150]


type AnchorReferenceLower = Annotated[
    float, Field(ge=CANONICAL_ANCHOR_REFERENCE_LOWER, le=CANONICAL_ANCHOR_REFERENCE_LOWER)
]
type AnchorReferenceUpper = Annotated[
    float, Field(ge=CANONICAL_ANCHOR_REFERENCE_UPPER, le=CANONICAL_ANCHOR_REFERENCE_UPPER)
]
type AnchorToleranceMultiplier = Annotated[
    float, Field(ge=CANONICAL_ANCHOR_TOLERANCE_MULTIPLIER, le=CANONICAL_ANCHOR_TOLERANCE_MULTIPLIER)
]


class AnchorReferenceIntervalConfig(ScientificSchema):
    lower: AnchorReferenceLower
    upper: AnchorReferenceUpper
    tolerance_multiplier: AnchorToleranceMultiplier


class B0PooledThresholdConfig(ScientificSchema):
    percentile: Literal[95]


class CanonicalTemporalConfig(ScientificSchema):
    historical_fraction: CanonicalTemporalFraction
    timestamp_evidence_kind: Literal[TimestampEvidenceKind.GENUINE_CAPTURE_TIME]
    capture_timestamp_field: str
    boundary_identity: StageFingerprintText


type RegimeAStaticTrainFraction = Annotated[
    Decimal,
    Field(ge=REGIME_A_STATIC_SPLIT_TRAIN_FRACTION.value, le=REGIME_A_STATIC_SPLIT_TRAIN_FRACTION.value),
]
type RegimeAStaticGapFraction = Annotated[
    Decimal,
    Field(ge=REGIME_A_STATIC_SPLIT_GAP_FRACTION.value, le=REGIME_A_STATIC_SPLIT_GAP_FRACTION.value),
]
type RegimeAStaticCalibrationFraction = Annotated[
    Decimal,
    Field(ge=REGIME_A_STATIC_SPLIT_CALIBRATION_FRACTION.value, le=REGIME_A_STATIC_SPLIT_CALIBRATION_FRACTION.value),
]


class RegimeAStaticSplitConfig(ScientificSchema):
    train_fraction: RegimeAStaticTrainFraction
    gap_fraction: RegimeAStaticGapFraction
    calibration_fraction: RegimeAStaticCalibrationFraction


class AbsorptionGateConfig(ScientificSchema):
    strongly_useful_fraction: AbsorptionStronglyUsefulFraction
    partial_absorption_fraction: AbsorptionPartialFraction
    alternative_path_distance: AbsorptionAlternativePathDistance

    @model_validator(mode="after")
    def _partial_is_below_strongly_useful(self) -> "AbsorptionGateConfig":
        if self.partial_absorption_fraction >= self.strongly_useful_fraction:
            raise ValueError("partial_absorption_fraction must be strictly below strongly_useful_fraction")
        return self


class TemporalRecoveryGateConfig(ScientificSchema):
    meaningful_recovery_fraction: TemporalRecoveryFraction


class FedStatsSupplementaryKConfig(ScientificSchema):
    values: FedStatsSupplementaryKValues


class NaturalDevicePartitionConfig(ScientificSchema):
    strategy: Literal[ClientDefinitionStrategy.NATURAL_DEVICE]
    regime: Regime


class FilePseudoClientPartitionConfig(ScientificSchema):
    strategy: Literal[ClientDefinitionStrategy.FILE_PSEUDO_CLIENT]
    regime: Regime


class DeviceClientPartitionConfig(ScientificSchema):
    strategy: Literal[ClientDefinitionStrategy.DEVICE_CLIENT]
    regime: Regime


class GroupClientPartitionConfig(ScientificSchema):
    strategy: Literal[ClientDefinitionStrategy.GROUP_CLIENT]
    regime: Regime


class DirichletPartitionConfig(ScientificSchema):
    strategy: Literal[ClientDefinitionStrategy.DIRICHLET_SYNTHETIC]
    regime: Regime
    alpha: float | DirichletAlphaSentinel


type PartitioningConfig = Annotated[
    NaturalDevicePartitionConfig
    | FilePseudoClientPartitionConfig
    | DeviceClientPartitionConfig
    | GroupClientPartitionConfig
    | DirichletPartitionConfig,
    Field(discriminator="strategy"),
]


class RegimeAPreprocessingConfig(ScientificSchema):
    strategy: Literal[NormalizationStrategy.STANDARD]
    scope: Literal[NormalizationScope.PER_CLIENT_TRAIN]
    fitted_stat_policy: Literal[FittedStatisticPolicy.EXACT_TWO_PASS]


class CentralizedComparatorConfig(ScientificSchema):
    model_identity: StageFingerprintText
    checkpoint_identity: StageFingerprintText
    calibration_score_identity: StageFingerprintText
    test_score_identity: StageFingerprintText
    threshold_identity: StageFingerprintText
    evaluation_identity: StageFingerprintText


class DirichletAlphaGridConfig(ScientificSchema):
    values: tuple[float | DirichletAlphaSentinel, ...]

    @field_validator("values")
    @classmethod
    def _values_are_unique_positive(
        cls, values: tuple[float | DirichletAlphaSentinel, ...]
    ) -> tuple[float | DirichletAlphaSentinel, ...]:
        numeric = [value for value in values if value is not DirichletAlphaSentinel.IID]
        if not _has_unique_values(values) or not _has_positive_values(numeric):
            raise ValueError("Dirichlet alpha grid values must be non-empty, unique, and strictly positive")
        return values


class CalibrationSizeGridConfig(ScientificSchema):
    values: tuple[PositiveInteger, ...]

    @field_validator("values")
    @classmethod
    def _values_are_unique_and_ordered(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        if not values or tuple(sorted(set(values))) != tuple(values):
            raise ValueError("calibration-size grid values must be non-empty, unique, and strictly increasing")
        return values


class ShrinkageWeightGridConfig(ScientificSchema):
    values: tuple[ClosedUnitInterval, ...]

    @field_validator("values")
    @classmethod
    def _values_span_zero_to_one(cls, values: tuple[Decimal, ...]) -> tuple[Decimal, ...]:
        if not _is_complete_shrinkage_weight_grid(values):
            raise ValueError("shrinkage-weight grid must be unique, strictly increasing, and span 0 to 1")
        return values


def _has_unique_values[Value](values: tuple[Value, ...]) -> bool:
    return bool(values) and len(set(values)) == len(values)


def _has_positive_values(values: list[float]) -> bool:
    return all(value > 0 for value in values)


def _is_complete_shrinkage_weight_grid(values: tuple[Decimal, ...]) -> bool:
    if not values or tuple(sorted(set(values))) != values:
        return False
    return values[0] == Decimal("0") and values[-1] == Decimal("1")


class ConformalAlphaConfig(ScientificSchema):
    alpha: OpenUnitInterval


class ScientificConfig(ScientificSchema):
    protocol_track: ProtocolTrack
    partitioning: PartitioningConfig
    threshold_constructions: tuple[ThresholdConstructionConfig, ...]
    evaluation: EvaluationConfig
    statistics: StatisticalConfig
    federation: FederationConfig
    canonical_temporal: CanonicalTemporalConfig | None

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from datp_core.domain.artifacts.references import CONTENT_HASH_PATTERN
from datp_core.domain.data.datasets import TimestampEvidenceKind
from datp_core.domain.data.preprocessing import FittedStatisticPolicy, NormalizationScope, NormalizationStrategy
from datp_core.domain.evaluation.metrics import OperatingPointMetric
from datp_core.domain.experiments.protocols import ProtocolTrack
from datp_core.domain.learning.scores import QuantileEstimatorType
from datp_core.domain.learning.training import AggregationStrategy, ParticipationStrategy
from datp_core.domain.thresholding.policies import SharedThresholdConstruction

type OpenUnitInterval = Annotated[Decimal, Field(gt=Decimal(0), lt=Decimal(1))]
type ClosedUnitInterval = Annotated[Decimal, Field(ge=Decimal(0), le=Decimal(1))]
type PositiveInteger = Annotated[int, Field(gt=0)]
type ConfirmatoryConfidence = Annotated[Decimal, Field(ge=Decimal("0.95"), le=Decimal("0.95"))]
type CanonicalTemporalFraction = Annotated[Decimal, Field(ge=Decimal("0.70"), le=Decimal("0.70"))]
type StageFingerprintText = Annotated[str, Field(pattern=f"^{CONTENT_HASH_PATTERN}$")]


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


class ConformalThresholdConfig(ScientificSchema):
    kind: Literal["conformal"]
    mode: Literal["split"]


class FedStatsBenignThresholdConfig(ScientificSchema):
    kind: Literal["fed_stats_benign"]


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


class CanonicalTemporalConfig(ScientificSchema):
    historical_fraction: CanonicalTemporalFraction
    timestamp_evidence_kind: Literal[TimestampEvidenceKind.GENUINE_CAPTURE_TIME]
    capture_timestamp_field: str
    boundary_identity: StageFingerprintText


type RegimeAStaticTrainFraction = Annotated[Decimal, Field(ge=Decimal("0.60"), le=Decimal("0.60"))]
type RegimeAStaticGapFraction = Annotated[Decimal, Field(ge=Decimal("0.01"), le=Decimal("0.01"))]
type RegimeAStaticCalibrationFraction = Annotated[Decimal, Field(ge=Decimal("0.20"), le=Decimal("0.20"))]


class RegimeAStaticSplitConfig(ScientificSchema):
    train_fraction: RegimeAStaticTrainFraction
    gap_fraction: RegimeAStaticGapFraction
    calibration_fraction: RegimeAStaticCalibrationFraction


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


class ScientificConfig(ScientificSchema):
    protocol_track: ProtocolTrack
    threshold_constructions: tuple[ThresholdConstructionConfig, ...]
    evaluation: EvaluationConfig
    statistics: StatisticalConfig
    federation: FederationConfig
    canonical_temporal: CanonicalTemporalConfig | None

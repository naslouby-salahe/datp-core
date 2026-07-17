from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from datp_core.domain.data.datasets import Dataset, Regime, TimestampEvidenceKind
from datp_core.domain.data.partitioning import ClientDefinitionStrategy, DirichletAlphaSentinel
from datp_core.domain.evaluation.metrics import DetectionQualityMetric, OperatingPointMetric
from datp_core.domain.experiments.claims import ClaimTier, ExperimentRole
from datp_core.domain.experiments.protocols import ProtocolTrack
from datp_core.domain.learning.training import ParticipationStrategy
from datp_core.domain.runtime.policies import ExecutionMode
from datp_core.domain.thresholding.clustering import (
    B4ClusteringAlgorithm,
    B4FingerprintField,
    B4FingerprintFitScope,
    B4FingerprintScalerSpec,
)

type OpenUnitInterval = Annotated[Decimal, Field(gt=Decimal("0"), lt=Decimal("1"))]
type ClosedUnitInterval = Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("1"))]
type PositiveInteger = Annotated[int, Field(gt=0)]
type NonNegativeInteger = Annotated[int, Field(ge=0)]


class CatalogSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ConfirmatoryProtocolConfig(CatalogSchema):
    track: Literal[ProtocolTrack.JOURNAL_EXTENSION]
    metric: Literal[OperatingPointMetric.CV_FPR]
    direction: Literal["b1_minus_b2"]
    statistical_method: Literal["bca_bootstrap"]
    confidence: OpenUnitInterval
    paired_seed_count: PositiveInteger

    @model_validator(mode="after")
    def _confirmatory_contract(self) -> "ConfirmatoryProtocolConfig":
        if self.confidence != Decimal("0.95") or self.paired_seed_count != 10:
            raise ValueError("confirmatory protocol must use the configured 95% BCa ten-paired-seed contract")
        return self


class ProtocolCatalogConfig(CatalogSchema):
    confirmatory: ConfirmatoryProtocolConfig


class DatasetProfileConfig(CatalogSchema):
    dataset: Dataset
    feature_schema_id: str
    input_dimension: PositiveInteger | Literal["unverified"]
    timestamp_evidence: Literal["unavailable"] | TimestampEvidenceKind
    allowed_regimes: Annotated[tuple[Regime, ...], Field(min_length=1)]

    @field_validator("allowed_regimes")
    @classmethod
    def _non_empty_regimes(cls, values: tuple[Regime, ...]) -> tuple[Regime, ...]:
        if len(set(values)) != len(values):
            raise ValueError("dataset allowed regimes must be non-empty and unique")
        return values


class DatasetCatalogConfig(CatalogSchema):
    profiles: Annotated[tuple[DatasetProfileConfig, ...], Field(min_length=1)]

    @field_validator("profiles")
    @classmethod
    def _unique_datasets(cls, values: tuple[DatasetProfileConfig, ...]) -> tuple[DatasetProfileConfig, ...]:
        if len({value.dataset for value in values}) != len(values):
            raise ValueError("dataset catalogue must contain unique dataset profiles")
        return values


class StaticSplitConfig(CatalogSchema):
    train_fraction: OpenUnitInterval
    gap_fraction: OpenUnitInterval
    calibration_fraction: OpenUnitInterval
    test_fraction_kind: Literal["derived_remainder"]

    @model_validator(mode="after")
    def _complete_split(self) -> "StaticSplitConfig":
        if self.train_fraction + self.calibration_fraction + (self.gap_fraction * 2) >= Decimal("1"):
            raise ValueError("static split fractions and two gaps must leave a positive derived test remainder")
        return self


class StaticSplitDisabledConfig(CatalogSchema):
    kind: Literal["disabled"]


class StaticSplitConfiguredConfig(StaticSplitConfig):
    kind: Literal["configured"]


type RegimeStaticSplitConfig = Annotated[
    StaticSplitDisabledConfig | StaticSplitConfiguredConfig,
    Field(discriminator="kind"),
]


class TemporalBehaviorDisabledConfig(CatalogSchema):
    kind: Literal["disabled"]


class TemporalBehaviorChronologicalConfig(CatalogSchema):
    kind: Literal["chronological"]
    historical_fraction: OpenUnitInterval
    timestamp_evidence: Literal[TimestampEvidenceKind.GENUINE_CAPTURE_TIME]


type TemporalBehaviorConfig = Annotated[
    TemporalBehaviorDisabledConfig | TemporalBehaviorChronologicalConfig,
    Field(discriminator="kind"),
]


class EligibilityCoverageDisabledConfig(CatalogSchema):
    kind: Literal["disabled"]


class EligibilityCoverageRequiredConfig(CatalogSchema):
    kind: Literal["required"]
    minimum_fraction: ClosedUnitInterval


type EligibilityCoverageConfig = Annotated[
    EligibilityCoverageDisabledConfig | EligibilityCoverageRequiredConfig,
    Field(discriminator="kind"),
]


class RegimeProfileConfig(CatalogSchema):
    regime: Regime
    dataset: Dataset
    client_strategy: ClientDefinitionStrategy
    client_count: PositiveInteger | Literal["derived"]
    static_split: RegimeStaticSplitConfig
    eligibility_coverage: EligibilityCoverageConfig
    temporal: TemporalBehaviorConfig


class RegimeCatalogConfig(CatalogSchema):
    profiles: Annotated[tuple[RegimeProfileConfig, ...], Field(min_length=1)]

    @field_validator("profiles")
    @classmethod
    def _unique_regimes(cls, values: tuple[RegimeProfileConfig, ...]) -> tuple[RegimeProfileConfig, ...]:
        if len({value.regime for value in values}) != len(values):
            raise ValueError("regime catalogue must contain unique regime profiles")
        return values


class ModelProfileConfig(CatalogSchema):
    profile_id: str
    hidden_dimensions: tuple[PositiveInteger, ...]
    bottleneck_dimension: PositiveInteger
    activation: Literal["relu"]
    optimizer: Literal["adam"]
    learning_rate: Annotated[Decimal, Field(gt=Decimal("0"))]
    weight_decay: Annotated[Decimal, Field(ge=Decimal("0"))]
    micro_batch_size: PositiveInteger
    local_epochs: PositiveInteger
    participation: ParticipationStrategy
    maximum_rounds: PositiveInteger
    checkpoint_rounds: Annotated[tuple[PositiveInteger, ...], Field(min_length=1)]

    @field_validator("checkpoint_rounds")
    @classmethod
    def _checkpoint_rounds(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        if tuple(sorted(set(values))) != values:
            raise ValueError("checkpoint rounds must be non-empty, unique, and strictly increasing")
        return values


class ModelCatalogConfig(CatalogSchema):
    profiles: tuple[ModelProfileConfig, ...]


class B4ClusteringProfileConfig(CatalogSchema):
    profile_id: str
    cluster_count: PositiveInteger
    fingerprint_fields: tuple[B4FingerprintField, ...]
    scaler: B4FingerprintScalerSpec
    scaler_fit_scope: B4FingerprintFitScope
    algorithm: B4ClusteringAlgorithm
    n_init: PositiveInteger
    max_iter: PositiveInteger
    fixed_percentile: OpenUnitInterval
    is_canonical: bool


class ThresholdCatalogConfig(CatalogSchema):
    quantile_grid: Annotated[tuple[OpenUnitInterval, ...], Field(min_length=1)]
    conformal_percentile: OpenUnitInterval
    dirichlet_alpha_grid: tuple[float | DirichletAlphaSentinel, ...]
    calibration_size_grid: Annotated[tuple[PositiveInteger, ...], Field(min_length=1)]
    shrinkage_weight_grid: Annotated[tuple[ClosedUnitInterval, ...], Field(min_length=1)]
    conformal_derivation: Literal["one_minus_percentile"]
    fed_stats_supplementary_k: tuple[Annotated[Decimal, Field(gt=Decimal("0"))], ...]
    b4_profiles: tuple[B4ClusteringProfileConfig, ...]

    @field_validator("quantile_grid", "calibration_size_grid", "shrinkage_weight_grid")
    @classmethod
    def _increasing_unique(cls, values: tuple[Decimal | int, ...]) -> tuple[Decimal | int, ...]:
        if tuple(sorted(set(values))) != values:
            raise ValueError("grid values must be non-empty, unique, and strictly increasing")
        return values

    @model_validator(mode="after")
    def _threshold_profiles(self) -> "ThresholdCatalogConfig":
        canonical_profiles = tuple(profile for profile in self.b4_profiles if profile.is_canonical)
        if len(canonical_profiles) != 1:
            raise ValueError("threshold catalogue must have exactly one canonical B4 profile")
        if canonical_profiles[0].fixed_percentile not in self.quantile_grid:
            raise ValueError("canonical B4 fixed percentile must be a configured quantile-grid member")
        if self.conformal_percentile not in self.quantile_grid:
            raise ValueError("conformal percentile must be a configured quantile-grid member")
        return self


class EvaluationCatalogConfig(CatalogSchema):
    minimum_eligible_calibration_samples: PositiveInteger
    primary_metric: Literal[OperatingPointMetric.CV_FPR]
    controls: tuple[OperatingPointMetric | DetectionQualityMetric, ...]
    absorption_strongly_useful_fraction: ClosedUnitInterval
    absorption_partial_fraction: ClosedUnitInterval
    alternative_path_distance: ClosedUnitInterval
    temporal_recovery_fraction: ClosedUnitInterval

    @model_validator(mode="after")
    def _evaluation_bands(self) -> "EvaluationCatalogConfig":
        if self.absorption_partial_fraction >= self.absorption_strongly_useful_fraction:
            raise ValueError("partial absorption must be below strongly useful absorption")
        return self


class ExperimentProfileReferenceConfig(CatalogSchema):
    experiment_id: str
    protocol_track: ProtocolTrack
    dataset: Dataset
    regime: Regime
    model_profile_id: str
    threshold_profile_id: str
    execution_profile_id: str
    artifact_policy_id: str
    reporting_policy_id: str
    evidence_role: ExperimentRole
    claim_tier: ClaimTier


class ExperimentCatalogConfig(CatalogSchema):
    profiles: tuple[ExperimentProfileReferenceConfig, ...]


class ExecutionProfileReferenceConfig(CatalogSchema):
    profile_id: str
    mode: ExecutionMode


class TestProfileReferenceConfig(CatalogSchema):
    profile_id: str
    data_scale: Literal["tiny", "small", "full"]
    execution_profile_id: str
    scientific_fixture: Literal["canonical_anchor", "synthetic"]


class TestCatalogConfig(CatalogSchema):
    profiles: tuple[TestProfileReferenceConfig, ...]

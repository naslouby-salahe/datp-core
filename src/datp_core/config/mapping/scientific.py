from dataclasses import dataclass
from decimal import Decimal
from typing import assert_never

from datp_core.config.mapping.artifacts import map_artifact_config
from datp_core.config.mapping.execution import map_execution_config
from datp_core.config.mapping.reporting import map_reporting_config
from datp_core.config.schemas.artifacts import ArtifactConfig
from datp_core.config.schemas.execution import ExecutionConfig
from datp_core.config.schemas.reporting import ReportingConfig
from datp_core.config.schemas.scientific import (
    AbsorptionGateConfig,
    AnchorCheckpointTerminationConfig,
    AnchorReferenceIntervalConfig,
    B0PooledThresholdConfig,
    BcaBootstrapStatisticalConfig,
    CalibrationSizeFallbackThresholdConfig,
    CalibrationSizeGridConfig,
    CanonicalTemporalConfig,
    CentralizedComparatorConfig,
    CliffsDeltaStatisticalConfig,
    ClusterThresholdConfig,
    ConformalAlphaConfig,
    ConformalThresholdConfig,
    DeviceClientPartitionConfig,
    DirichletAlphaGridConfig,
    DirichletPartitionConfig,
    EvaluationConfig,
    FamilyThresholdConfig,
    FedAvgFederationConfig,
    FederationConfig,
    FedProxFederationConfig,
    FedStatsBenignThresholdConfig,
    FedStatsSupplementaryKConfig,
    FilePseudoClientPartitionConfig,
    GroupClientPartitionConfig,
    LinearRegressionStatisticalConfig,
    LocalThresholdConfig,
    NaturalDevicePartitionConfig,
    PartitioningConfig,
    PercentileBootstrapStatisticalConfig,
    QSensitivityGridConfig,
    RegimeAPreprocessingConfig,
    RegimeAStaticSplitConfig,
    RobustClusterMedianThresholdConfig,
    ScientificConfig,
    SharedThresholdConfig,
    ShrinkageThresholdConfig,
    ShrinkageWeightGridConfig,
    SpearmanStatisticalConfig,
    StatisticalConfig,
    TemporalRecoveryGateConfig,
    ThresholdConstructionConfig,
    WilcoxonStatisticalConfig,
)
from datp_core.domain.artifacts.lineage import (
    CentralizedCalibrationScoringIdentity,
    CentralizedCheckpointIdentity,
    CentralizedEvaluationIdentity,
    CentralizedModelIdentity,
    CentralizedTestScoringIdentity,
    CentralizedThresholdIdentity,
    TemporalWindowIdentity,
)
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.data.datasets import TimestampEvidence
from datp_core.domain.data.partitioning import (
    ClientPartitionSpec,
    DeviceClientPartitionSpec,
    DirichletAlpha,
    DirichletPartitionSpec,
    FilePseudoClientPartitionSpec,
    GroupClientPartitionSpec,
    NaturalDevicePartitionSpec,
)
from datp_core.domain.data.preprocessing import PreprocessingChunkSpec, PreprocessingSpec
from datp_core.domain.data.splitting import RegimeAStaticSplitBoundarySpec, TemporalBoundary
from datp_core.domain.errors import ConfigurationError, DomainValidationError
from datp_core.domain.evaluation.alert_burden import BootstrapResampleCount, CalibrationSampleCount
from datp_core.domain.evaluation.metrics import METRIC_SPECS, OperatingPointMetric
from datp_core.domain.evaluation.operating_points import EvaluationSuiteSpec
from datp_core.domain.evaluation.statistical_results import (
    AnchorReferenceInterval,
    ConfidenceLevel,
    Probability,
    StatisticalAnalysisSpec,
    StatisticalMethod,
)
from datp_core.domain.experiments.identities import ExperimentId
from datp_core.domain.experiments.protocols import ScientificProtocolSpec
from datp_core.domain.experiments.specifications import (
    AbsorptionGateSpec,
    CentralizedModelComparatorProfileSpec,
    CentralizedModelComparatorSpec,
    ConfirmatoryExperimentProfileSpec,
    ExperimentProfileSpec,
    ExperimentSpec,
    ProfileCatalogueSpec,
    TemporalRecoveryGateSpec,
)
from datp_core.domain.learning.checkpoints import AnchorCheckpointTerminationPolicy
from datp_core.domain.learning.training import FEDPROX_MU_GRID, FederationSpec
from datp_core.domain.mathematics.pooled_statistics import REGIME_D_TEMPORAL_HISTORICAL_FRACTION
from datp_core.domain.runtime.seeds import RoundNumber
from datp_core.domain.thresholding.federated_statistics import (
    FED_STATS_SUPPLEMENTARY_K_VALUES,
    FedStatsBenignThresholdSpec,
)
from datp_core.domain.thresholding.policies import (
    B0PooledThresholdSpec,
    ClusterThresholdSpec,
    FamilyThresholdSpec,
    FprTarget,
    LocalThresholdSpec,
    SharedThresholdSpec,
    ThresholdPercentile,
    ThresholdSuiteSpec,
)
from datp_core.domain.thresholding.variants import (
    CalibrationSizeFallbackThresholdSpec,
    ConformalThresholdSpec,
    RobustClusterMedianThresholdSpec,
    ShrinkageThresholdSpec,
    ShrinkageWeight,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolveExperimentProfileRequest:
    experiment_id: ExperimentId
    profiles: tuple[ExperimentProfileSpec, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentConfigSchema:
    profile_request: ResolveExperimentProfileRequest
    scientific: ScientificConfig
    execution: ExecutionConfig
    artifacts: ArtifactConfig
    reporting: ReportingConfig


def resolve_experiment_profile(request: ResolveExperimentProfileRequest) -> ExperimentProfileSpec:
    matches = tuple(
        profile
        for profile in request.profiles
        if type(profile) in {ExperimentProfileSpec, ConfirmatoryExperimentProfileSpec}
        and profile.claim.identity.experiment_id == request.experiment_id
    )
    if len(matches) != 1:
        raise ConfigurationError(
            detail="a named experiment must resolve to exactly one closed profile",
            section="profile",
            field="experiment_id",
            mode="resolution",
        )
    return matches[0]


def map_experiment_schema(schema: ExperimentConfigSchema, *, catalogue: ProfileCatalogueSpec) -> ExperimentSpec:
    profile = resolve_experiment_profile(schema.profile_request)
    protocol = _resolve_authorized_protocol(schema.scientific, profile, catalogue=catalogue)
    return ExperimentSpec(
        claim=profile.claim,
        profile=profile,
        scientific_protocol=protocol,
        execution_policy=map_execution_config(schema.execution),
        artifact_policy=map_artifact_config(schema.artifacts),
        reporting_policy=map_reporting_config(schema.reporting),
    )


def map_centralized_comparator_config(
    schema: CentralizedComparatorConfig,
    profile: CentralizedModelComparatorProfileSpec,
) -> CentralizedModelComparatorSpec:
    candidate = CentralizedModelComparatorSpec(
        model_identity=CentralizedModelIdentity(value=StageFingerprint(value=schema.model_identity)),
        checkpoint_identity=CentralizedCheckpointIdentity(value=StageFingerprint(value=schema.checkpoint_identity)),
        calibration_score_identity=CentralizedCalibrationScoringIdentity(
            value=StageFingerprint(value=schema.calibration_score_identity)
        ),
        test_score_identity=CentralizedTestScoringIdentity(value=StageFingerprint(value=schema.test_score_identity)),
        threshold_identity=CentralizedThresholdIdentity(value=StageFingerprint(value=schema.threshold_identity)),
        evaluation_identity=CentralizedEvaluationIdentity(value=StageFingerprint(value=schema.evaluation_identity)),
    )
    if candidate != profile.comparator:
        raise ConfigurationError(
            detail="B0 configuration must match the resolved centralized comparator profile",
            section="scientific",
            field="centralized_comparator",
            mode="mapping",
        )
    return candidate


def map_federation_config(schema: FederationConfig) -> FederationSpec:
    match schema:
        case FedAvgFederationConfig():
            return FederationSpec(
                aggregation=schema.aggregation,
                local_epochs=schema.local_epochs,
                participation=schema.participation,
                rounds_max=schema.rounds_max,
                fedprox_mu=None,
            )
        case FedProxFederationConfig():
            if schema.selection_source != "pre_registered_grid" or float(schema.fedprox_mu) not in FEDPROX_MU_GRID:
                raise ConfigurationError(
                    detail="FedProx coefficients must be strictly positive frozen grid members",
                    section="scientific",
                    field="fedprox_mu",
                    mode="mapping",
                )
            return FederationSpec(
                aggregation=schema.aggregation,
                local_epochs=schema.local_epochs,
                participation=schema.participation,
                rounds_max=schema.rounds_max,
                fedprox_mu=float(schema.fedprox_mu),
            )
        case _:
            assert_never(schema)


def map_canonical_temporal_config(schema: CanonicalTemporalConfig) -> TemporalBoundary:
    try:
        return TemporalBoundary(
            historical_fraction=Probability(value=schema.historical_fraction),
            timestamp_field=TimestampEvidence(
                kind=schema.timestamp_evidence_kind,
                capture_timestamp_field=schema.capture_timestamp_field,
            ),
            boundary_identity=TemporalWindowIdentity(value=StageFingerprint(value=schema.boundary_identity)),
        )
    except DomainValidationError as error:
        raise ConfigurationError(
            detail="canonical D-temporal mapping requires a genuine capture-time 70/30 boundary",
            section="scientific",
            field="canonical_temporal",
            mode="mapping",
        ) from error


def map_regime_a_static_split_config(schema: RegimeAStaticSplitConfig) -> RegimeAStaticSplitBoundarySpec:
    try:
        return RegimeAStaticSplitBoundarySpec(
            train_fraction=Probability(value=schema.train_fraction),
            gap_fraction=Probability(value=schema.gap_fraction),
            calibration_fraction=Probability(value=schema.calibration_fraction),
        )
    except DomainValidationError as error:
        raise ConfigurationError(
            detail="Regime A static split mapping requires the locked recovered 0.60/0.01/0.20 boundary fractions",
            section="scientific",
            field="regime_a_static_split",
            mode="mapping",
        ) from error


def map_anchor_checkpoint_termination_config(
    schema: AnchorCheckpointTerminationConfig,
) -> AnchorCheckpointTerminationPolicy:
    try:
        return AnchorCheckpointTerminationPolicy(
            rounds_initial=RoundNumber(value=schema.rounds_initial),
            rounds_max=RoundNumber(value=schema.rounds_max),
        )
    except DomainValidationError as error:
        raise ConfigurationError(
            detail="anchor checkpoint termination mapping requires the locked recovered 40/150 round boundary",
            section="scientific",
            field="anchor_checkpoint_termination",
            mode="mapping",
        ) from error


def map_anchor_reference_interval_config(schema: AnchorReferenceIntervalConfig) -> AnchorReferenceInterval:
    try:
        return AnchorReferenceInterval(
            lower=schema.lower,
            upper=schema.upper,
            tolerance_multiplier=schema.tolerance_multiplier,
        )
    except DomainValidationError as error:
        raise ConfigurationError(
            detail=(
                "anchor reference interval mapping requires the locked recovered 5-seed bounds and ~20%-wider tolerance"
            ),
            section="scientific",
            field="anchor_reference_interval",
            mode="mapping",
        ) from error


def map_b0_pooled_threshold_config(schema: B0PooledThresholdConfig) -> B0PooledThresholdSpec:
    try:
        return B0PooledThresholdSpec(percentile=ThresholdPercentile(value=Decimal(schema.percentile) / Decimal(100)))
    except DomainValidationError as error:
        raise ConfigurationError(
            detail="B0 pooled threshold mapping requires the locked p95 percentile",
            section="scientific",
            field="b0_pooled_threshold",
            mode="mapping",
        ) from error


def map_absorption_gate_config(schema: AbsorptionGateConfig) -> AbsorptionGateSpec:
    try:
        return AbsorptionGateSpec(
            strongly_useful_fraction=Probability(value=schema.strongly_useful_fraction),
            partial_absorption_fraction=Probability(value=schema.partial_absorption_fraction),
            alternative_path_distance=Probability(value=schema.alternative_path_distance),
        )
    except DomainValidationError as error:
        raise ConfigurationError(
            detail=(
                "absorption gate mapping requires the partial-absorption band strictly below the strongly-useful band"
            ),
            section="scientific",
            field="absorption_gates",
            mode="mapping",
        ) from error


def map_temporal_recovery_gate_config(schema: TemporalRecoveryGateConfig) -> TemporalRecoveryGateSpec:
    return TemporalRecoveryGateSpec(meaningful_recovery_fraction=Probability(value=schema.meaningful_recovery_fraction))


def map_fed_stats_supplementary_k_config(schema: FedStatsSupplementaryKConfig) -> tuple[Decimal, ...]:
    if schema.values != FED_STATS_SUPPLEMENTARY_K_VALUES:
        raise ConfigurationError(
            detail="FedStats supplementary k configuration must match the locked 2.0/2.5/3.0 roadmap grid",
            section="scientific",
            field="fed_stats_supplementary_k",
            mode="mapping",
        )
    return schema.values


def map_partitioning_config(schema: PartitioningConfig, *, catalogue: ProfileCatalogueSpec) -> ClientPartitionSpec:
    match schema:
        case NaturalDevicePartitionConfig():
            return NaturalDevicePartitionSpec(strategy=schema.strategy, regime=schema.regime)
        case FilePseudoClientPartitionConfig():
            return FilePseudoClientPartitionSpec(strategy=schema.strategy, regime=schema.regime)
        case DeviceClientPartitionConfig():
            return DeviceClientPartitionSpec(strategy=schema.strategy, regime=schema.regime)
        case GroupClientPartitionConfig():
            return GroupClientPartitionSpec(strategy=schema.strategy, regime=schema.regime)
        case DirichletPartitionConfig():
            if DirichletAlpha(value=schema.alpha) not in catalogue.dirichlet_alpha_grid:
                raise ConfigurationError(
                    detail="Dirichlet alpha must be a frozen pre-registered profile grid member",
                    section="scientific",
                    field="partitioning",
                    mode="mapping",
                )
            return DirichletPartitionSpec(
                strategy=schema.strategy,
                regime=schema.regime,
                alpha=DirichletAlpha(value=schema.alpha),
            )
        case _:
            assert_never(schema)


def map_q_sensitivity_grid_config(schema: QSensitivityGridConfig) -> tuple[ThresholdPercentile, ...]:
    return tuple(ThresholdPercentile(value=value) for value in schema.values)


def map_regime_a_preprocessing_config(
    schema: RegimeAPreprocessingConfig, *, chunking: PreprocessingChunkSpec
) -> PreprocessingSpec:
    return PreprocessingSpec(
        strategy=schema.strategy,
        scope=schema.scope,
        fitted_stat_policy=schema.fitted_stat_policy,
        chunking=chunking,
    )


def map_dirichlet_alpha_grid_config(schema: DirichletAlphaGridConfig) -> tuple[DirichletAlpha, ...]:
    return tuple(DirichletAlpha(value=value) for value in schema.values)


def map_calibration_size_grid_config(schema: CalibrationSizeGridConfig) -> tuple[CalibrationSampleCount, ...]:
    return tuple(CalibrationSampleCount(value=value) for value in schema.values)


def map_shrinkage_weight_grid_config(schema: ShrinkageWeightGridConfig) -> tuple[ShrinkageWeight, ...]:
    return tuple(ShrinkageWeight(value=float(value)) for value in schema.values)


def map_conformal_alpha_config(schema: ConformalAlphaConfig) -> FprTarget:
    return FprTarget(value=float(schema.alpha))


def map_statistical_config(schema: StatisticalConfig) -> StatisticalAnalysisSpec:
    method = _statistical_method(schema)
    return StatisticalAnalysisSpec(
        method=method,
        confidence=ConfidenceLevel(value=schema.confidence),
        resamples=BootstrapResampleCount(value=_resample_count(schema)),
        paired_seed_count=schema.paired_seed_count,
    )


def _statistical_method(schema: StatisticalConfig) -> StatisticalMethod:
    match schema:
        case BcaBootstrapStatisticalConfig():
            return StatisticalMethod.BCA_BOOTSTRAP
        case PercentileBootstrapStatisticalConfig():
            return StatisticalMethod.PERCENTILE_BOOTSTRAP
        case WilcoxonStatisticalConfig():
            return StatisticalMethod.WILCOXON_SIGNED_RANK
        case CliffsDeltaStatisticalConfig():
            return StatisticalMethod.CLIFFS_DELTA
        case SpearmanStatisticalConfig():
            return StatisticalMethod.SPEARMAN
        case LinearRegressionStatisticalConfig():
            return StatisticalMethod.LINEAR_REGRESSION_R2
        case _:
            assert_never(schema)


def _resample_count(schema: StatisticalConfig) -> int:
    return schema.resamples


def _resolve_authorized_protocol(
    schema: ScientificConfig, profile: ExperimentProfileSpec, *, catalogue: ProfileCatalogueSpec
) -> ScientificProtocolSpec:
    candidates = tuple(
        protocol
        for protocol in profile.authorized_protocols
        if _matches_scientific_config(schema, protocol, catalogue=catalogue)
    )
    if len(candidates) != 1:
        raise ConfigurationError(
            detail="scientific configuration must select exactly one protocol authorized by its resolved profile",
            section="scientific",
            field="protocol",
            mode="mapping",
        )
    return candidates[0]


def _matches_scientific_config(
    schema: ScientificConfig, protocol: ScientificProtocolSpec, *, catalogue: ProfileCatalogueSpec
) -> bool:
    return all(
        (
            schema.protocol_track is protocol.track,
            map_partitioning_config(schema.partitioning, catalogue=catalogue) == protocol.regime_data.partitioning,
            _matches_threshold_suite(
                schema.threshold_constructions, protocol.evaluation_arm.thresholds, catalogue=catalogue
            ),
            _matches_evaluation(schema.evaluation, protocol.evaluation_arm.evaluation),
            map_statistical_config(schema.statistics) == protocol.statistics,
            map_federation_config(schema.federation) == protocol.detector_branch.training.federation,
            _matches_canonical_temporal(schema.canonical_temporal, protocol),
        )
    )


def _matches_threshold_suite(
    configurations: tuple[ThresholdConstructionConfig, ...],
    suite: ThresholdSuiteSpec,
    *,
    catalogue: ProfileCatalogueSpec,
) -> bool:
    return len(configurations) == len(suite.constructions) and all(
        _matches_threshold_configuration(configuration, construction, catalogue=catalogue)
        for configuration, construction in zip(configurations, suite.constructions, strict=True)
    )


def _matches_threshold_configuration(
    configuration: ThresholdConstructionConfig, construction: object, *, catalogue: ProfileCatalogueSpec
) -> bool:
    match configuration, construction:
        case SharedThresholdConfig(), SharedThresholdSpec():
            return (
                _is_authorized_percentile(configuration.percentile, catalogue=catalogue)
                and construction.percentile.value == configuration.percentile
                and construction.construction is configuration.construction
                and construction.estimator is configuration.estimator
            )
        case LocalThresholdConfig(), LocalThresholdSpec():
            return (
                _is_authorized_percentile(configuration.percentile, catalogue=catalogue)
                and construction.percentile.value == configuration.percentile
                and construction.estimator is configuration.estimator
            )
        case FamilyThresholdConfig(), FamilyThresholdSpec():
            return (
                _is_authorized_percentile(configuration.percentile, catalogue=catalogue)
                and construction.percentile.value == configuration.percentile
                and construction.family_manifest_identity.value == configuration.family_taxonomy_id
            )
        case ClusterThresholdConfig(), ClusterThresholdSpec():
            return (
                _is_authorized_percentile(configuration.percentile, catalogue=catalogue)
                and construction.percentile.value == configuration.percentile
            )
        case RobustClusterMedianThresholdConfig(), RobustClusterMedianThresholdSpec():
            return True
        case ShrinkageThresholdConfig(), ShrinkageThresholdSpec():
            return (
                _is_authorized_percentile(configuration.percentile, catalogue=catalogue)
                and _is_authorized_shrinkage_weight(configuration.shrinkage_weight, catalogue=catalogue)
                and construction.percentile.value == configuration.percentile
                and construction.shrinkage_weight.value == float(configuration.shrinkage_weight)
            )
        case CalibrationSizeFallbackThresholdConfig(), CalibrationSizeFallbackThresholdSpec():
            return (
                _is_authorized_percentile(configuration.percentile, catalogue=catalogue)
                and _is_authorized_calibration_sample_count(configuration.calibration_sample_count, catalogue=catalogue)
                and construction.percentile.value == configuration.percentile
                and construction.fallback_rule_version == configuration.fallback_rule_version
                and construction.calibration_sample_count.value == configuration.calibration_sample_count
            )
        case ConformalThresholdConfig(), ConformalThresholdSpec():
            return (
                _is_authorized_percentile(configuration.percentile, catalogue=catalogue)
                and construction.mode.value == configuration.mode
                and construction.conformal_split.alpha.value == configuration.alpha
                and construction.conformal_split.percentile.value == configuration.percentile
                and construction.conformal_split.quantile_index_rule == configuration.quantile_index_rule
            )
        case FedStatsBenignThresholdConfig(), FedStatsBenignThresholdSpec():
            return True
        case _:
            return False


def _is_authorized_percentile(value: Decimal, *, catalogue: ProfileCatalogueSpec) -> bool:
    return ThresholdPercentile(value=value) in catalogue.quantile_grid


def _is_authorized_shrinkage_weight(value: Decimal, *, catalogue: ProfileCatalogueSpec) -> bool:
    return ShrinkageWeight(value=float(value)) in catalogue.shrinkage_weight_grid


def _is_authorized_calibration_sample_count(value: int, *, catalogue: ProfileCatalogueSpec) -> bool:
    return CalibrationSampleCount(value=value) in catalogue.calibration_size_grid


def _matches_evaluation(configuration: EvaluationConfig, evaluation: EvaluationSuiteSpec) -> bool:
    metrics = tuple(metric.metric for metric in evaluation.metrics)
    return (
        evaluation.primary_metric is configuration.primary
        and metrics == (configuration.primary, *configuration.controls)
        and all(_is_control_metric(metric) for metric in configuration.controls)
    )


def _is_control_metric(metric: OperatingPointMetric) -> bool:
    return any(specification.metric is metric and specification.is_control for specification in METRIC_SPECS)


def _matches_canonical_temporal(
    configuration: CanonicalTemporalConfig | None,
    protocol: ScientificProtocolSpec,
) -> bool:
    if configuration is None:
        return True
    mapped_boundary = map_canonical_temporal_config(configuration)
    return (
        protocol.regime_data.partitioning.regime.value == "d_temporal"
        and mapped_boundary.historical_fraction == REGIME_D_TEMPORAL_HISTORICAL_FRACTION
    )

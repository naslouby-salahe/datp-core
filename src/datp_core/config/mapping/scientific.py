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
    AnchorCheckpointTerminationConfig,
    B0PooledThresholdConfig,
    BcaBootstrapStatisticalConfig,
    CalibrationSizeFallbackThresholdConfig,
    CanonicalTemporalConfig,
    CentralizedComparatorConfig,
    CliffsDeltaStatisticalConfig,
    ClusterThresholdConfig,
    ConformalThresholdConfig,
    EvaluationConfig,
    FamilyThresholdConfig,
    FedAvgFederationConfig,
    FederationConfig,
    FedProxFederationConfig,
    FedStatsBenignThresholdConfig,
    LinearRegressionStatisticalConfig,
    LocalThresholdConfig,
    PercentileBootstrapStatisticalConfig,
    RegimeAPreprocessingConfig,
    RegimeAStaticSplitConfig,
    RobustClusterMedianThresholdConfig,
    ScientificConfig,
    SharedThresholdConfig,
    ShrinkageThresholdConfig,
    SpearmanStatisticalConfig,
    StatisticalConfig,
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
from datp_core.domain.data.preprocessing import PreprocessingChunkSpec, PreprocessingSpec
from datp_core.domain.data.splitting import RegimeAStaticSplitBoundarySpec, TemporalBoundary
from datp_core.domain.errors import ConfigurationError, DomainValidationError
from datp_core.domain.evaluation.alert_burden import BootstrapResampleCount
from datp_core.domain.evaluation.metrics import METRIC_SPECS, OperatingPointMetric
from datp_core.domain.evaluation.operating_points import EvaluationSuiteSpec
from datp_core.domain.evaluation.statistical_results import (
    ConfidenceLevel,
    Probability,
    StatisticalAnalysisSpec,
    StatisticalMethod,
)
from datp_core.domain.experiments.identities import ExperimentId
from datp_core.domain.experiments.protocols import ScientificProtocolSpec
from datp_core.domain.experiments.specifications import (
    CentralizedModelComparatorProfileSpec,
    CentralizedModelComparatorSpec,
    ConfirmatoryExperimentProfileSpec,
    ExperimentProfileSpec,
    ExperimentSpec,
)
from datp_core.domain.learning.checkpoints import AnchorCheckpointTerminationPolicy
from datp_core.domain.learning.training import FEDPROX_MU_GRID, FederationSpec
from datp_core.domain.runtime.seeds import RoundNumber
from datp_core.domain.thresholding.federated_statistics import FedStatsBenignThresholdSpec
from datp_core.domain.thresholding.policies import (
    B0PooledThresholdSpec,
    ClusterThresholdSpec,
    FamilyThresholdSpec,
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
        and profile.identity.experiment_id == request.experiment_id
    )
    if len(matches) != 1:
        raise ConfigurationError(
            detail="a named experiment must resolve to exactly one closed profile",
            section="profile",
            field="experiment_id",
            mode="resolution",
        )
    return matches[0]


def map_experiment_schema(schema: ExperimentConfigSchema) -> ExperimentSpec:
    profile = resolve_experiment_profile(schema.profile_request)
    protocol = _resolve_authorized_protocol(schema.scientific, profile)
    return ExperimentSpec(
        identity=profile.identity,
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


def map_regime_a_preprocessing_config(
    schema: RegimeAPreprocessingConfig, *, chunking: PreprocessingChunkSpec
) -> PreprocessingSpec:
    return PreprocessingSpec(
        strategy=schema.strategy,
        scope=schema.scope,
        fitted_stat_policy=schema.fitted_stat_policy,
        chunking=chunking,
    )


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


def _resolve_authorized_protocol(schema: ScientificConfig, profile: ExperimentProfileSpec) -> ScientificProtocolSpec:
    candidates = tuple(
        protocol for protocol in profile.authorized_protocols if _matches_scientific_config(schema, protocol)
    )
    if len(candidates) != 1:
        raise ConfigurationError(
            detail="scientific configuration must select exactly one protocol authorized by its resolved profile",
            section="scientific",
            field="protocol",
            mode="mapping",
        )
    return candidates[0]


def _matches_scientific_config(schema: ScientificConfig, protocol: ScientificProtocolSpec) -> bool:
    return all(
        (
            schema.protocol_track is protocol.track,
            _matches_threshold_suite(schema.threshold_constructions, protocol.thresholds),
            _matches_evaluation(schema.evaluation, protocol.evaluation),
            map_statistical_config(schema.statistics) == protocol.statistics,
            map_federation_config(schema.federation) == protocol.training.federation,
            _matches_canonical_temporal(schema.canonical_temporal, protocol),
        )
    )


def _matches_threshold_suite(
    configurations: tuple[ThresholdConstructionConfig, ...],
    suite: ThresholdSuiteSpec,
) -> bool:
    return len(configurations) == len(suite.constructions) and all(
        _matches_threshold_configuration(configuration, construction)
        for configuration, construction in zip(configurations, suite.constructions, strict=True)
    )


def _matches_threshold_configuration(configuration: ThresholdConstructionConfig, construction: object) -> bool:
    match configuration, construction:
        case SharedThresholdConfig(), SharedThresholdSpec():
            return (
                construction.percentile.value == configuration.percentile
                and construction.construction is configuration.construction
                and construction.estimator is configuration.estimator
            )
        case LocalThresholdConfig(), LocalThresholdSpec():
            return (
                construction.percentile.value == configuration.percentile
                and construction.estimator is configuration.estimator
            )
        case FamilyThresholdConfig(), FamilyThresholdSpec():
            return (
                construction.percentile.value == configuration.percentile
                and construction.family_manifest_identity.value == configuration.family_taxonomy_id
            )
        case ClusterThresholdConfig(), ClusterThresholdSpec():
            return construction.percentile.value == configuration.percentile
        case RobustClusterMedianThresholdConfig(), RobustClusterMedianThresholdSpec():
            return True
        case ShrinkageThresholdConfig(), ShrinkageThresholdSpec():
            return (
                construction.percentile.value == configuration.percentile
                and construction.shrinkage_weight.value == float(configuration.shrinkage_weight)
            )
        case CalibrationSizeFallbackThresholdConfig(), CalibrationSizeFallbackThresholdSpec():
            return (
                construction.percentile.value == configuration.percentile
                and construction.fallback_rule_version == configuration.fallback_rule_version
            )
        case ConformalThresholdConfig(), ConformalThresholdSpec():
            return construction.mode.value == configuration.mode
        case FedStatsBenignThresholdConfig(), FedStatsBenignThresholdSpec():
            return True
        case _:
            return False


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
    return protocol.partitioning.regime.value == "d_temporal" and mapped_boundary.historical_fraction == Probability(
        value=Decimal("0.70")
    )

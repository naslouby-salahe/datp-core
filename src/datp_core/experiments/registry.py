from pydantic import model_validator

from datp_core.analysis.metrics.protocols import (
    CONFIRMATORY_METRICS,
    OPERATING_POINT_METRICS,
    OPTIONAL_EQUITY_INDEX_METRICS,
)
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ErrorMessage, UnknownIdentifierError
from datp_core.core.identifiers import (
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    TrainingModelId,
)


class ExperimentDeclaration(StrictModel):
    id: ExperimentId
    role: EvidenceRole
    population: PopulationId
    training_model: TrainingModelId
    preprocessing_protocol: PreprocessingProtocolId
    supplementary_preprocessing_protocols: tuple[PreprocessingProtocolId, ...] = ()
    federated_thresholds: tuple[FederatedThresholdMethod, ...]
    metrics: tuple[MetricId, ...]
    readiness: ExperimentReadiness

    @model_validator(mode="after")
    def validate_contents(self) -> "ExperimentDeclaration":
        if not self.federated_thresholds or not self.metrics:
            raise ValueError("experiments require threshold methods and metrics")
        if len(set(self.federated_thresholds)) != len(self.federated_thresholds):
            raise ValueError("experiment threshold methods must be unique")
        if len(set(self.metrics)) != len(self.metrics):
            raise ValueError("experiment metrics must be unique")
        if self.preprocessing_protocol in self.supplementary_preprocessing_protocols:
            raise ValueError("supplementary preprocessing protocols must exclude the primary protocol")
        if len(set(self.supplementary_preprocessing_protocols)) != len(self.supplementary_preprocessing_protocols):
            raise ValueError("supplementary preprocessing protocols must be unique")
        if self.readiness is ExperimentReadiness.EXECUTABLE and self.role is EvidenceRole.OPERATIONAL_TRANSLATION:
            raise ValueError("operational translation experiments cannot be marked executable without rate evidence")
        return self

    @property
    def preprocessing_protocols(self) -> tuple[PreprocessingProtocolId, ...]:
        return (self.preprocessing_protocol, *self.supplementary_preprocessing_protocols)


_SHARED_AND_LOCAL_METHODS = (
    FederatedThresholdMethod.SHARED_THRESHOLD,
    FederatedThresholdMethod.LOCAL_THRESHOLD,
)
_HISTORICAL_ANCHOR_METRICS = (MetricId.FPR_COEFFICIENT_OF_VARIATION,)
_SHARED_LOCAL_AND_GROUPED_METHODS = (
    FederatedThresholdMethod.SHARED_THRESHOLD,
    FederatedThresholdMethod.CLUSTER_THRESHOLD,
    FederatedThresholdMethod.LOCAL_THRESHOLD,
)
_FULL_THRESHOLD_LADDER = (
    FederatedThresholdMethod.SHARED_THRESHOLD,
    FederatedThresholdMethod.FAMILY_THRESHOLD,
    FederatedThresholdMethod.CLUSTER_THRESHOLD,
    FederatedThresholdMethod.LOCAL_THRESHOLD,
)
_SHARED_THRESHOLD_CONSTRUCTIONS = (
    FederatedThresholdMethod.SHARED_THRESHOLD,
    FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
    FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
    FederatedThresholdMethod.LOCAL_THRESHOLD,
)
_FEDERATED_STATISTICS_COMPARISON_METHODS = _SHARED_THRESHOLD_CONSTRUCTIONS + (
    FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS,
)
_FEDERATED_QUANTILE_COMPARISON_METHODS = _FEDERATED_STATISTICS_COMPARISON_METHODS + (
    FederatedThresholdMethod.FEDERATED_KLL_SHARED_THRESHOLD,
)
_EDGE_BENIGN_EQUITY_METHODS = _FEDERATED_STATISTICS_COMPARISON_METHODS + (FederatedThresholdMethod.CLUSTER_THRESHOLD,)
_CALIBRATION_SIZE_METHODS = _SHARED_LOCAL_AND_GROUPED_METHODS + (
    FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,
    FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,
    FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD,
)
_ONBOARDING_CALIBRATION_METHODS = (
    FederatedThresholdMethod.SHARED_THRESHOLD,
    FederatedThresholdMethod.LOCAL_THRESHOLD,
    FederatedThresholdMethod.FAMILY_THRESHOLD,
    FederatedThresholdMethod.CLUSTER_THRESHOLD,
)
_TEMPORAL_METHODS = _SHARED_LOCAL_AND_GROUPED_METHODS + (FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,)


def _declared_readiness(
    experiment_id: ExperimentId,
    role: EvidenceRole,
) -> ExperimentReadiness:
    if experiment_id is ExperimentId.ALERT_BURDEN_TRANSLATION:
        return ExperimentReadiness.SUPPRESSED
    if role is EvidenceRole.OPERATIONAL_TRANSLATION:
        return ExperimentReadiness.SUPPRESSED
    return ExperimentReadiness.DECLARED


def _declare(
    experiment_id: ExperimentId,
    role: EvidenceRole,
    population: PopulationId,
    training_model: TrainingModelId,
    preprocessing_protocol: PreprocessingProtocolId,
    thresholds: tuple[FederatedThresholdMethod, ...],
    metrics: tuple[MetricId, ...],
    supplementary_preprocessing_protocols: tuple[PreprocessingProtocolId, ...] = (),
) -> ExperimentDeclaration:
    return ExperimentDeclaration(
        id=experiment_id,
        role=role,
        population=population,
        training_model=training_model,
        preprocessing_protocol=preprocessing_protocol,
        supplementary_preprocessing_protocols=supplementary_preprocessing_protocols,
        federated_thresholds=thresholds,
        metrics=metrics,
        readiness=_declared_readiness(experiment_id, role),
    )


EXPERIMENTS = (
    _declare(
        ExperimentId.HISTORICAL_DATP_REPRODUCTION,
        EvidenceRole.ANCHOR_REPRODUCTION,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS,
        _HISTORICAL_ANCHOR_METRICS,
    ),
    _declare(
        ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        EvidenceRole.CONFIRMATORY,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY,
        EvidenceRole.SUPPORTIVE,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_THRESHOLD_CONSTRUCTIONS,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.QUANTILE_SENSITIVITY,
        EvidenceRole.SUPPORTIVE,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_LOCAL_AND_GROUPED_METHODS,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.THRESHOLD_ESTIMATOR_SCOPE_SENSITIVITY,
        EvidenceRole.SUPPORTIVE,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS,
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
        EvidenceRole.MECHANISM,
        PopulationId.NBAIOT_DIRICHLET_CLIENTS,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_LOCAL_AND_GROUPED_METHODS,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.FAMILY_AND_GROUPED_GRANULARITY,
        EvidenceRole.MECHANISM,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _FULL_THRESHOLD_LADDER,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.PER_CLIENT_SCORE_GEOMETRY,
        EvidenceRole.MECHANISM,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_LOCAL_AND_GROUPED_METHODS,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
        EvidenceRole.MECHANISM,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS,
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF,
        EvidenceRole.MECHANISM,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.CALIBRATION_SIZE_ABLATION,
        EvidenceRole.SUPPORTIVE,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _CALIBRATION_SIZE_METHODS,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.CALIBRATION_COLD_START_ONBOARDING,
        EvidenceRole.SUPPORTIVE,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _ONBOARDING_CALIBRATION_METHODS,
        CONFIRMATORY_METRICS + (MetricId.AVERAGE_PRECISION,),
    ),
    _declare(
        ExperimentId.FIXED_SHRINKAGE_CURVE,
        EvidenceRole.SUPPORTIVE,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS + (FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,),
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.SIZE_AWARE_SHRINKAGE,
        EvidenceRole.SUPPORTIVE,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS + (FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,),
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.PREPROCESSING_GEOMETRY_SENSITIVITY,
        EvidenceRole.SUPPORTIVE,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS,
        CONFIRMATORY_METRICS + (MetricId.AVERAGE_PRECISION,),
        supplementary_preprocessing_protocols=(PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,),
    ),
    _declare(
        ExperimentId.LOCAL_CONFORMAL_COVERAGE,
        EvidenceRole.SUPPORTIVE,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS + (FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD,),
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON,
        EvidenceRole.THRESHOLD_VARIANT,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _FEDERATED_STATISTICS_COMPARISON_METHODS,
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.FEDERATED_QUANTILE_ESTIMATION,
        EvidenceRole.THRESHOLD_VARIANT,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _FEDERATED_QUANTILE_COMPARISON_METHODS,
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY,
        EvidenceRole.THRESHOLD_VARIANT,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS + (FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS,),
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        EvidenceRole.EXTERNAL_VALIDATION,
        PopulationId.EDGE_SENSOR_GROUPS,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _EDGE_BENIGN_EQUITY_METHODS,
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
        EvidenceRole.APPLICABILITY_BOUNDARY,
        PopulationId.CICIOT_FILE_CLIENTS,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_LOCAL_AND_GROUPED_METHODS,
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        EvidenceRole.TRAINING_STRESS_TEST,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDPROX_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _FULL_THRESHOLD_LADDER,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.FEDAVG_LOCAL_FINE_TUNING,
        EvidenceRole.TRAINING_STRESS_TEST,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_LOCAL_FINE_TUNING,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        EvidenceRole.TRAINING_STRESS_TEST,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        EvidenceRole.TEMPORAL_BOUNDARY,
        PopulationId.EDGE_TEMPORAL_GROUPS,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _TEMPORAL_METHODS,
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.ALERT_BURDEN_TRANSLATION,
        EvidenceRole.OPERATIONAL_TRANSLATION,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS,
        (MetricId.ALERTS_PER_DAY,),
    ),
    _declare(
        ExperimentId.GROUP_MEDIAN_SUPPLEMENT,
        EvidenceRole.EXPLORATORY,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        (FederatedThresholdMethod.CLUSTER_THRESHOLD,),
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.OPTIONAL_EQUITY_INDICES,
        EvidenceRole.EXPLORATORY,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_LOCAL_AND_GROUPED_METHODS,
        OPERATING_POINT_METRICS + OPTIONAL_EQUITY_INDEX_METRICS,
    ),
)


def require_experiment_declaration(experiment_id: ExperimentId) -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is experiment_id)
    if len(matches) != 1:
        raise UnknownIdentifierError(
            ErrorMessage(f"experiment must be declared exactly once: {experiment_id.value}"),
            subject=experiment_id,
        )
    return matches[0]

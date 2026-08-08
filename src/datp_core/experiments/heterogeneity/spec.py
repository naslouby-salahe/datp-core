"""Controlled heterogeneity and threshold-mechanism experiment specifications."""

from datp_core.protocols.metrics import ATTACK_QUALITY_CONTROL_METRICS, OPERATING_POINT_METRICS
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
from datp_core.experiments.common.coordinates import ExperimentSpec

_MECHANISM_METRICS = OPERATING_POINT_METRICS + ATTACK_QUALITY_CONTROL_METRICS

CONTROLLED_HETEROGENEITY_SWEEP = ExperimentSpec(
    id=ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
    role=EvidenceRole.MECHANISM,
    population=PopulationId.NBAIOT_DIRICHLET_CLIENTS,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD),
    metrics=_MECHANISM_METRICS,
    readiness=ExperimentReadiness.DECLARED,
)
FAMILY_AND_GROUPED_GRANULARITY = ExperimentSpec(
    id=ExperimentId.FAMILY_AND_GROUPED_GRANULARITY,
    role=EvidenceRole.MECHANISM,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.FAMILY_THRESHOLD,
        FederatedThresholdMethod.CLUSTER_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    ),
    metrics=_MECHANISM_METRICS,
    readiness=ExperimentReadiness.DECLARED,
)
PER_CLIENT_SCORE_GEOMETRY = ExperimentSpec(
    id=ExperimentId.PER_CLIENT_SCORE_GEOMETRY,
    role=EvidenceRole.MECHANISM,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD),
    metrics=(MetricId.RECONSTRUCTION_ERROR, MetricId.EMPIRICAL_CUMULATIVE_PROBABILITY),
    readiness=ExperimentReadiness.DECLARED,
)
HETEROGENEITY_BENEFIT_ASSOCIATION = ExperimentSpec(
    id=ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
    role=EvidenceRole.MECHANISM,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD),
    metrics=(MetricId.FALSE_POSITIVE_RATE, MetricId.BINARY_MACRO_F1),
    readiness=ExperimentReadiness.DECLARED,
)
THRESHOLD_MOVEMENT_TRADEOFF = ExperimentSpec(
    id=ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF,
    role=EvidenceRole.MECHANISM,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD),
    metrics=(MetricId.FALSE_POSITIVE_RATE, MetricId.TRUE_POSITIVE_RATE, MetricId.BINARY_MACRO_F1),
    readiness=ExperimentReadiness.DECLARED,
)
OPTIONAL_EQUITY_INDICES = ExperimentSpec(
    id=ExperimentId.OPTIONAL_EQUITY_INDICES,
    role=EvidenceRole.EXPLORATORY,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD),
    metrics=(MetricId.JAIN_FAIRNESS_INDEX, MetricId.GINI_COEFFICIENT),
    readiness=ExperimentReadiness.DECLARED,
)

HETEROGENEITY_EXPERIMENTS = (
    CONTROLLED_HETEROGENEITY_SWEEP,
    FAMILY_AND_GROUPED_GRANULARITY,
    PER_CLIENT_SCORE_GEOMETRY,
    HETEROGENEITY_BENEFIT_ASSOCIATION,
    THRESHOLD_MOVEMENT_TRADEOFF,
    OPTIONAL_EQUITY_INDICES,
)

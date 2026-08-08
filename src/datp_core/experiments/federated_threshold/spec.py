"""Benign-only federated threshold-comparator experiment specifications."""

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

FEDERATED_BENIGN_STATISTICS_COMPARISON = ExperimentSpec(
    id=ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON,
    role=EvidenceRole.SUPPORTIVE,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS,
    ),
    metrics=OPERATING_POINT_METRICS + ATTACK_QUALITY_CONTROL_METRICS,
    readiness=ExperimentReadiness.DECLARED,
)
FEDERATED_QUANTILE_ESTIMATION = ExperimentSpec(
    id=ExperimentId.FEDERATED_QUANTILE_ESTIMATION,
    role=EvidenceRole.MECHANISM,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS,),
    metrics=(
        MetricId.ABSOLUTE_THRESHOLD_ERROR,
        MetricId.RELATIVE_THRESHOLD_ERROR,
        MetricId.SIGNED_ATTAINMENT_ERROR,
        MetricId.ABSOLUTE_ATTAINMENT_ERROR,
        MetricId.COMMUNICATION_BYTES,
    ),
    readiness=ExperimentReadiness.DECLARED,
)
FIXED_COEFFICIENT_STATISTICS_SENSITIVITY = ExperimentSpec(
    id=ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY,
    role=EvidenceRole.EXPLORATORY,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS,),
    metrics=(MetricId.ABSOLUTE_THRESHOLD_ERROR, MetricId.ABSOLUTE_ATTAINMENT_ERROR),
    readiness=ExperimentReadiness.DECLARED,
)

FEDERATED_THRESHOLD_EXPERIMENTS = (
    FEDERATED_BENIGN_STATISTICS_COMPARISON,
    FEDERATED_QUANTILE_ESTIMATION,
    FIXED_COEFFICIENT_STATISTICS_SENSITIVITY,
)

"""FedProx training-side absorption stress-test specification."""

from datp_core.analysis.metrics.contracts import ATTACK_QUALITY_CONTROL_METRICS, OPERATING_POINT_METRICS
from datp_core.core.identifiers import (
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    PopulationId,
    PreprocessingProtocolId,
    TrainingModelId,
)
from datp_core.experiments.common.coordinates import ExperimentSpec

FEDPROX_ABSORPTION_STRESS_TEST = ExperimentSpec(
    id=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
    role=EvidenceRole.TRAINING_STRESS_TEST,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDPROX_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD),
    metrics=OPERATING_POINT_METRICS + ATTACK_QUALITY_CONTROL_METRICS,
    readiness=ExperimentReadiness.DECLARED,
)

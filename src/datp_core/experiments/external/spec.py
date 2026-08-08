"""Edge-IIoTset benign-equity external-validation specification."""

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
from datp_core.protocols.metrics import OPERATING_POINT_METRICS

EDGE_BENIGN_EQUITY_VALIDATION = ExperimentSpec(
    id=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
    role=EvidenceRole.EXTERNAL_VALIDATION,
    population=PopulationId.EDGE_SENSOR_GROUPS,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        FederatedThresholdMethod.CLUSTER_THRESHOLD,
    ),
    metrics=OPERATING_POINT_METRICS,
    readiness=ExperimentReadiness.DECLARED,
)

EXTERNAL_EXPERIMENTS = (EDGE_BENIGN_EQUITY_VALIDATION,)

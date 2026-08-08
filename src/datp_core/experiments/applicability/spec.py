"""CICIoT2023 file-defined pseudo-client applicability-boundary specification."""

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

CICIOT_FILE_CLIENT_BOUNDARY = ExperimentSpec(
    id=ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
    role=EvidenceRole.APPLICABILITY_BOUNDARY,
    population=PopulationId.CICIOT_FILE_CLIENTS,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD),
    metrics=OPERATING_POINT_METRICS,
    readiness=ExperimentReadiness.DECLARED,
)

APPLICABILITY_EXPERIMENTS = (CICIOT_FILE_CLIENT_BOUNDARY,)

from datp_core.domain.enums import EvidenceRole, ExperimentId, FederatedThresholdMethod, MetricId, PopulationId
from datp_core.experiments.feasibility import (
    ExternalTemporalFeasibilityRequest,
    FeasibilityReason,
    assess_external_temporal_feasibility,
)


def test_external_evidence_cannot_be_promoted_to_confirmatory() -> None:
    result = assess_external_temporal_feasibility(
        ExternalTemporalFeasibilityRequest(
            ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
            PopulationId.EDGE_SENSOR_GROUPS,
            EvidenceRole.CONFIRMATORY,
            FederatedThresholdMethod.SHARED_THRESHOLD,
            (MetricId.FALSE_POSITIVE_RATE,),
            False,
            False,
            True,
            False,
        )
    )
    assert result.reason is FeasibilityReason.EXTERNAL_PROMOTED_TO_CONFIRMATORY

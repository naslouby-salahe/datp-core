from datp_core.domain.enums import (
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    TemporalState,
)
from datp_core.experiments.feasibility import (
    ExternalTemporalFeasibilityRequest,
    FeasibilityReason,
    assess_external_temporal_feasibility,
)


def test_cic_file_client_boundary_rejects_chronology() -> None:
    result = assess_external_temporal_feasibility(
        ExternalTemporalFeasibilityRequest(
            ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
            PopulationId.CICIOT_FILE_CLIENTS,
            EvidenceRole.APPLICABILITY_BOUNDARY,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
            (MetricId.FALSE_POSITIVE_RATE,),
            False,
            False,
            True,
            False,
            temporal_state=TemporalState.FROZEN_FUTURE,
        )
    )
    assert result.reason is FeasibilityReason.CIC_TEMPORAL_UNAVAILABLE

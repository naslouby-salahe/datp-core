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


def test_future_leakage_is_a_pre_execution_failure() -> None:
    result = assess_external_temporal_feasibility(
        ExternalTemporalFeasibilityRequest(
            ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
            PopulationId.EDGE_TEMPORAL_GROUPS,
            EvidenceRole.TEMPORAL_BOUNDARY,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
            (MetricId.FALSE_POSITIVE_RATE,),
            False,
            False,
            True,
            False,
            temporal_state=TemporalState.FROZEN_FUTURE,
            future_leakage_detected=True,
        )
    )
    assert result.reason is FeasibilityReason.FUTURE_LEAKAGE

from datp_core.domain.enums import FederatedThresholdMethod, MetricId, TemporalState
from datp_core.pipeline.feasibility import (
    EdgeTemporalFeasibilityRequest,
    FeasibilityReason,
    TemporalExecutionMode,
    assess_external_temporal_feasibility,
)


def test_future_leakage_is_a_pre_execution_failure() -> None:
    result = assess_external_temporal_feasibility(
        EdgeTemporalFeasibilityRequest(
            threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            requested_metrics=(MetricId.FALSE_POSITIVE_RATE,),
            routed_through_confirmatory_command=False,
            grouped_assignment_available=False,
            required_artifacts_available=True,
            attack_assignment_claimed_available=False,
            chronology_valid=True,
            includes_modbus=False,
            materiality_protocol_available=True,
            temporal_client_sets_match=True,
            future_leakage_detected=True,
            temporal_state=TemporalState.FROZEN_FUTURE,
            temporal_execution_mode=TemporalExecutionMode.ONE_SHOT,
            recovery_ratio_requested=False,
        )
    )
    assert result.reason is FeasibilityReason.FUTURE_LEAKAGE

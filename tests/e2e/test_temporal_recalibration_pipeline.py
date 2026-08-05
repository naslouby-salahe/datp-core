from datp_core.domain.enums import AvailabilityStatus, FederatedThresholdMethod, MetricId, TemporalState
from datp_core.pipeline.planning import (
    EdgeTemporalFeasibilityRequest,
    FeasibilityReason,
    TemporalExecutionMode,
    assess_external_temporal_feasibility,
)


def _request(*, future_leakage: bool, mode: TemporalExecutionMode) -> EdgeTemporalFeasibilityRequest:
    return EdgeTemporalFeasibilityRequest(
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
        future_leakage_detected=future_leakage,
        temporal_state=TemporalState.FROZEN_FUTURE,
        temporal_execution_mode=mode,
        recovery_ratio_requested=False,
    )


def test_temporal_pipeline_is_one_shot_and_rejects_future_leakage() -> None:
    valid = assess_external_temporal_feasibility(_request(future_leakage=False, mode=TemporalExecutionMode.ONE_SHOT))
    leaking = assess_external_temporal_feasibility(_request(future_leakage=True, mode=TemporalExecutionMode.ONE_SHOT))
    streaming = assess_external_temporal_feasibility(
        _request(future_leakage=False, mode=TemporalExecutionMode.STREAMING)
    )

    assert valid.feasible
    assert leaking.availability is AvailabilityStatus.INFEASIBLE
    assert leaking.reason is FeasibilityReason.FUTURE_LEAKAGE
    assert streaming.reason is FeasibilityReason.UNSUPPORTED_TEMPORAL_EXECUTION_MODE

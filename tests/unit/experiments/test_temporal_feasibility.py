from dataclasses import replace

from datp_core.domain.enums import FederatedThresholdMethod, MetricId, TemporalState
from datp_core.experiments.feasibility import (
    EdgeTemporalFeasibilityRequest,
    FeasibilityReason,
    TemporalExecutionMode,
    assess_external_temporal_feasibility,
)


def _request() -> EdgeTemporalFeasibilityRequest:
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
        future_leakage_detected=False,
        temporal_state=TemporalState.FROZEN_FUTURE,
        temporal_execution_mode=TemporalExecutionMode.ONE_SHOT,
        recovery_ratio_requested=False,
    )


def test_valid_temporal_request_is_feasible() -> None:
    assert assess_external_temporal_feasibility(_request()).feasible


def test_chronology_modbus_leakage_and_streaming_proxy_are_rejected() -> None:
    assert (
        assess_external_temporal_feasibility(replace(_request(), chronology_valid=False)).reason
        is FeasibilityReason.INVALID_TEMPORAL_CHRONOLOGY
    )
    assert (
        assess_external_temporal_feasibility(replace(_request(), includes_modbus=True)).reason
        is FeasibilityReason.MODBUS_TEMPORAL_UNAVAILABLE
    )
    assert (
        assess_external_temporal_feasibility(replace(_request(), future_leakage_detected=True)).reason
        is FeasibilityReason.FUTURE_LEAKAGE
    )
    assert (
        assess_external_temporal_feasibility(
            replace(_request(), temporal_execution_mode=TemporalExecutionMode.STREAMING)
        ).reason
        is FeasibilityReason.UNSUPPORTED_TEMPORAL_EXECUTION_MODE
    )

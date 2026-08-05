from datp_core.domain.enums import AvailabilityStatus, FederatedThresholdMethod, MetricId, TemporalState
from datp_core.pipeline.planning import (
    CiciotBoundaryFeasibilityRequest,
    EdgeExternalFeasibilityRequest,
    EdgeTemporalFeasibilityRequest,
    FeasibilityReason,
    TemporalExecutionMode,
    assess_external_temporal_feasibility,
)


def test_edge_rejects_attack_sensitive_metric() -> None:
    decision = assess_external_temporal_feasibility(
        EdgeExternalFeasibilityRequest(
            threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
            requested_metrics=(MetricId.TRUE_POSITIVE_RATE,),
            routed_through_confirmatory_command=False,
            grouped_assignment_available=False,
            required_artifacts_available=True,
            attack_assignment_claimed_available=False,
        )
    )
    assert decision.availability is AvailabilityStatus.INFEASIBLE
    assert decision.reason is FeasibilityReason.ATTACK_SENSITIVE_EDGE_METRIC


def test_ciciot_unresolved_divergence_is_blocked() -> None:
    decision = assess_external_temporal_feasibility(
        CiciotBoundaryFeasibilityRequest(
            threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            requested_metrics=(MetricId.FALSE_POSITIVE_RATE,),
            routed_through_confirmatory_command=False,
            grouped_assignment_available=False,
            required_artifacts_available=True,
            attack_assignment_claimed_available=False,
            divergence_required=True,
            divergence_semantics_resolved=False,
        )
    )
    assert decision.availability is AvailabilityStatus.UNAVAILABLE
    assert decision.reason is FeasibilityReason.DIVERGENCE_SEMANTICS_UNRESOLVED


def test_temporal_execution_is_one_shot_only() -> None:
    decision = assess_external_temporal_feasibility(
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
            future_leakage_detected=False,
            temporal_state=TemporalState.FROZEN_FUTURE,
            temporal_execution_mode=TemporalExecutionMode.STREAMING,
            recovery_ratio_requested=False,
        )
    )
    assert decision.reason is FeasibilityReason.UNSUPPORTED_TEMPORAL_EXECUTION_MODE

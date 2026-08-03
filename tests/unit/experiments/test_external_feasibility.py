from dataclasses import replace

from datp_core.domain.enums import FederatedThresholdMethod, MetricId
from datp_core.experiments.feasibility import (
    EdgeExternalFeasibilityRequest,
    FeasibilityReason,
    assess_external_temporal_feasibility,
)


def _edge_request() -> EdgeExternalFeasibilityRequest:
    return EdgeExternalFeasibilityRequest(
        threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        requested_metrics=(MetricId.FALSE_POSITIVE_RATE,),
        routed_through_confirmatory_command=False,
        grouped_assignment_available=False,
        required_artifacts_available=True,
        attack_assignment_claimed_available=False,
    )


def test_edge_benign_equity_is_feasible() -> None:
    assert assess_external_temporal_feasibility(_edge_request()).feasible


def test_edge_attack_metric_and_family_threshold_are_rejected() -> None:
    attack = assess_external_temporal_feasibility(
        replace(_edge_request(), requested_metrics=(MetricId.TRUE_POSITIVE_RATE,))
    )
    family = assess_external_temporal_feasibility(
        replace(_edge_request(), threshold_method=FederatedThresholdMethod.FAMILY_THRESHOLD)
    )
    assert attack.reason is FeasibilityReason.ATTACK_SENSITIVE_EDGE_METRIC
    assert family.reason is FeasibilityReason.FAMILY_THRESHOLD_UNAVAILABLE


def test_grouped_assignment_and_confirmatory_route_are_rejected() -> None:
    grouped = assess_external_temporal_feasibility(
        replace(_edge_request(), threshold_method=FederatedThresholdMethod.CLUSTER_THRESHOLD)
    )
    routed = assess_external_temporal_feasibility(
        replace(_edge_request(), routed_through_confirmatory_command=True)
    )
    assert grouped.reason is FeasibilityReason.GROUP_ASSIGNMENT_UNAVAILABLE
    assert routed.reason is FeasibilityReason.CONFIRMATORY_ROUTE_PROHIBITED

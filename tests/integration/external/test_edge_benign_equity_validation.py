from datp_core.domain.enums import FederatedThresholdMethod, MetricId
from datp_core.pipeline.feasibility import EdgeExternalFeasibilityRequest, assess_external_temporal_feasibility


def test_edge_validation_keeps_attack_assignment_unavailable() -> None:
    result = assess_external_temporal_feasibility(
        EdgeExternalFeasibilityRequest(
            threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
            requested_metrics=(MetricId.FALSE_POSITIVE_RATE,),
            routed_through_confirmatory_command=False,
            grouped_assignment_available=False,
            required_artifacts_available=True,
            attack_assignment_claimed_available=False,
        )
    )
    assert result.feasible

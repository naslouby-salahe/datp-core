from datp_core.domain.enums import AvailabilityStatus, FederatedThresholdMethod, MetricId
from datp_core.pipeline.planning import (
    EdgeExternalFeasibilityRequest,
    FeasibilityReason,
    assess_external_temporal_feasibility,
)


def test_edge_external_pipeline_exposes_only_benign_operating_point_evidence() -> None:
    benign = assess_external_temporal_feasibility(
        EdgeExternalFeasibilityRequest(
            threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
            requested_metrics=(MetricId.FALSE_POSITIVE_RATE,),
            routed_through_confirmatory_command=False,
            grouped_assignment_available=False,
            required_artifacts_available=True,
            attack_assignment_claimed_available=False,
        )
    )
    attack_sensitive = assess_external_temporal_feasibility(
        EdgeExternalFeasibilityRequest(
            threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
            requested_metrics=(MetricId.TRUE_POSITIVE_RATE,),
            routed_through_confirmatory_command=False,
            grouped_assignment_available=False,
            required_artifacts_available=True,
            attack_assignment_claimed_available=False,
        )
    )

    assert benign.feasible
    assert attack_sensitive.availability is AvailabilityStatus.INFEASIBLE
    assert attack_sensitive.reason is FeasibilityReason.ATTACK_SENSITIVE_EDGE_METRIC

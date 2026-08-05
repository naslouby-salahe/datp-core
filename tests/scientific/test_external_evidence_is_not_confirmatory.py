from datp_core.domain.enums import FederatedThresholdMethod, MetricId
from datp_core.pipeline.planning import (
    EdgeExternalFeasibilityRequest,
    FeasibilityReason,
    assess_external_temporal_feasibility,
)


def test_external_evidence_cannot_use_the_confirmatory_route() -> None:
    result = assess_external_temporal_feasibility(
        EdgeExternalFeasibilityRequest(
            threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
            requested_metrics=(MetricId.FALSE_POSITIVE_RATE,),
            routed_through_confirmatory_command=True,
            grouped_assignment_available=False,
            required_artifacts_available=True,
            attack_assignment_claimed_available=False,
        )
    )
    assert result.reason is FeasibilityReason.CONFIRMATORY_ROUTE_PROHIBITED

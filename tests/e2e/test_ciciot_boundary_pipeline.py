from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
)
from datp_core.pipeline.planning import (
    CiciotBoundaryFeasibilityRequest,
    FeasibilityReason,
    assess_external_temporal_feasibility,
)
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity


def test_ciciot_pipeline_remains_a_file_client_applicability_boundary() -> None:
    identity = ExternalTemporalExecutionIdentity(
        experiment=ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
        population=PopulationId.CICIOT_FILE_CLIENTS,
        evidence_role=EvidenceRole.APPLICABILITY_BOUNDARY,
        temporal_state=None,
    )
    feasible = assess_external_temporal_feasibility(
        CiciotBoundaryFeasibilityRequest(
            threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            requested_metrics=(MetricId.FALSE_POSITIVE_RATE,),
            routed_through_confirmatory_command=False,
            grouped_assignment_available=False,
            required_artifacts_available=True,
            attack_assignment_claimed_available=False,
            divergence_required=False,
            divergence_semantics_resolved=True,
        )
    )
    unresolved = assess_external_temporal_feasibility(
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

    assert identity.evidence_role is EvidenceRole.APPLICABILITY_BOUNDARY
    assert feasible.feasible
    assert unresolved.availability is AvailabilityStatus.UNAVAILABLE
    assert unresolved.reason is FeasibilityReason.DIVERGENCE_SEMANTICS_UNRESOLVED

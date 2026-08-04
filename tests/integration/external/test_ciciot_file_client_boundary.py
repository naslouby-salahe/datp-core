from dataclasses import fields

from datp_core.domain.enums import FederatedThresholdMethod, MetricId
from datp_core.experiments.feasibility import (
    CiciotBoundaryFeasibilityRequest,
    assess_external_temporal_feasibility,
)


def _request() -> CiciotBoundaryFeasibilityRequest:
    return CiciotBoundaryFeasibilityRequest(
        threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        requested_metrics=(MetricId.FALSE_POSITIVE_RATE,),
        routed_through_confirmatory_command=False,
        grouped_assignment_available=False,
        required_artifacts_available=True,
        attack_assignment_claimed_available=False,
        divergence_required=False,
        divergence_semantics_resolved=True,
    )


def test_cic_file_client_boundary_is_feasible_without_temporal_state() -> None:
    assert assess_external_temporal_feasibility(_request()).feasible


def test_cic_file_client_boundary_cannot_represent_chronology() -> None:
    field_names = {field.name for field in fields(CiciotBoundaryFeasibilityRequest)}
    assert "temporal_state" not in field_names

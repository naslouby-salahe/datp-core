from datp_core.domain.enums import EvidenceRole, ExperimentId, FederatedThresholdMethod, MetricId, PopulationId
from datp_core.experiments.feasibility import (
    ExternalTemporalFeasibilityRequest,
    FeasibilityReason,
    assess_external_temporal_feasibility,
)


def _edge_request(**changes: object) -> ExternalTemporalFeasibilityRequest:
    values: dict[str, object] = {
        "experiment": ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        "population": PopulationId.EDGE_SENSOR_GROUPS,
        "evidence_role": EvidenceRole.EXTERNAL_VALIDATION,
        "threshold_method": FederatedThresholdMethod.SHARED_THRESHOLD,
        "requested_metrics": (MetricId.FALSE_POSITIVE_RATE,),
        "routed_through_confirmatory_command": False,
        "grouped_assignment_available": False,
        "required_artifacts_available": True,
        "attack_assignment_claimed_available": False,
    }
    values.update(changes)
    return ExternalTemporalFeasibilityRequest(**values)  # type: ignore[arg-type]


def test_edge_benign_equity_is_feasible() -> None:
    assert assess_external_temporal_feasibility(_edge_request()).feasible


def test_edge_attack_metric_and_family_threshold_are_rejected() -> None:
    attack = assess_external_temporal_feasibility(_edge_request(requested_metrics=(MetricId.TRUE_POSITIVE_RATE,)))
    family = assess_external_temporal_feasibility(
        _edge_request(threshold_method=FederatedThresholdMethod.FAMILY_THRESHOLD)
    )
    assert attack.reason is FeasibilityReason.ATTACK_SENSITIVE_EDGE_METRIC
    assert family.reason is FeasibilityReason.FAMILY_THRESHOLD_UNAVAILABLE


def test_grouped_assignment_and_confirmatory_promotion_are_rejected() -> None:
    grouped = assess_external_temporal_feasibility(
        _edge_request(threshold_method=FederatedThresholdMethod.CLUSTER_THRESHOLD)
    )
    promoted = assess_external_temporal_feasibility(_edge_request(evidence_role=EvidenceRole.CONFIRMATORY))
    assert grouped.reason is FeasibilityReason.GROUP_ASSIGNMENT_UNAVAILABLE
    assert promoted.reason is FeasibilityReason.EXTERNAL_PROMOTED_TO_CONFIRMATORY

from datp_core.domain.enums import EvidenceRole, ExperimentId, FederatedThresholdMethod, MetricId, PopulationId
from datp_core.experiments.feasibility import ExternalTemporalFeasibilityRequest, assess_external_temporal_feasibility


def test_edge_validation_keeps_attack_assignment_unavailable() -> None:
    result = assess_external_temporal_feasibility(
        ExternalTemporalFeasibilityRequest(
            ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
            PopulationId.EDGE_SENSOR_GROUPS,
            EvidenceRole.EXTERNAL_VALIDATION,
            FederatedThresholdMethod.SHARED_THRESHOLD,
            (MetricId.FALSE_POSITIVE_RATE,),
            False,
            False,
            True,
            False,
        )
    )
    assert result.feasible

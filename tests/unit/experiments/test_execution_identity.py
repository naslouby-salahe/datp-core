import pytest

from datp_core.domain.enums import EvidenceRole, ExperimentId, PopulationId, TemporalState
from datp_core.domain.errors import ScientificContractError
from datp_core.experiments.models import ExternalTemporalExecutionIdentity, require_execution_identity


def test_temporal_identity_requires_its_declared_state() -> None:
    identity = ExternalTemporalExecutionIdentity(
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        population=PopulationId.EDGE_TEMPORAL_GROUPS,
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        temporal_state=TemporalState.FROZEN_FUTURE,
    )

    assert require_execution_identity(identity, PopulationId.EDGE_TEMPORAL_GROUPS) is identity


def test_identity_rejects_cross_population_evidence_promotion() -> None:
    with pytest.raises(ScientificContractError, match="must be declared"):
        ExternalTemporalExecutionIdentity(
            experiment=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
            population=PopulationId.EDGE_SENSOR_GROUPS,
            evidence_role=EvidenceRole.CONFIRMATORY,
            temporal_state=None,
        )


def test_external_population_cannot_execute_without_identity() -> None:
    with pytest.raises(ScientificContractError, match="requires an execution identity"):
        require_execution_identity(None, PopulationId.CICIOT_FILE_CLIENTS)

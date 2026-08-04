import pytest

from datp_core.artifacts.serialization import canonical_json_text
from datp_core.domain.enums import (
    EvidenceRole,
    ExperimentId,
    PopulationId,
    TemporalState,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.protocols.experiments import (
    EXECUTION_IDENTITY_DECLARATIONS,
    ExternalTemporalExecutionIdentity,
    require_execution_identity,
)


def test_temporal_identity_requires_its_declared_state() -> None:
    identity = ExternalTemporalExecutionIdentity(
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        population=PopulationId.EDGE_TEMPORAL_GROUPS,
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        temporal_state=TemporalState.FROZEN_FUTURE,
    )

    assert (
        require_execution_identity(
            identity,
            PopulationId.EDGE_TEMPORAL_GROUPS,
        )
        is identity
    )


def test_identity_rejects_cross_population_evidence_promotion() -> None:
    with pytest.raises(ScientificContractError, match="must be declared"):
        ExternalTemporalExecutionIdentity(
            experiment=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
            population=PopulationId.EDGE_SENSOR_GROUPS,
            evidence_role=EvidenceRole.CONFIRMATORY,
            temporal_state=None,
        )


def test_external_population_cannot_execute_without_identity() -> None:
    with pytest.raises(
        ScientificContractError,
        match="requires an execution identity",
    ):
        require_execution_identity(None, PopulationId.CICIOT_FILE_CLIENTS)


def test_execution_identity_round_trips_through_canonical_json() -> None:
    identity = ExternalTemporalExecutionIdentity(
        experiment=ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
        population=PopulationId.CICIOT_FILE_CLIENTS,
        evidence_role=EvidenceRole.APPLICABILITY_BOUNDARY,
        temporal_state=None,
    )
    persisted = ExternalTemporalExecutionIdentity.model_validate_json(
        canonical_json_text(identity)
    )
    assert persisted == identity


def test_execution_identity_registry_coordinates_are_unique() -> None:
    coordinates = tuple(
        (
            declaration.experiment,
            declaration.population,
            declaration.evidence_role,
            temporal_state,
        )
        for declaration in EXECUTION_IDENTITY_DECLARATIONS
        for temporal_state in declaration.temporal_states
    )
    assert len(coordinates) == len(frozenset(coordinates))

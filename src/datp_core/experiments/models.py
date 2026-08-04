"""Immutable execution identities for capability-constrained evidence."""

from pydantic import model_validator

from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import EvidenceRole, ExperimentId, PopulationId, TemporalState
from datp_core.domain.errors import ScientificContractError

BOUNDED_EVIDENCE_POPULATIONS = frozenset(
    {
        PopulationId.EDGE_SENSOR_GROUPS,
        PopulationId.CICIOT_FILE_CLIENTS,
        PopulationId.EDGE_TEMPORAL_GROUPS,
    }
)


class ExternalTemporalExecutionIdentity(StrictModel):
    experiment: ExperimentId
    population: PopulationId
    evidence_role: EvidenceRole
    temporal_state: TemporalState | None

    @model_validator(mode="after")
    def validate_declared_identity(self) -> "ExternalTemporalExecutionIdentity":
        if not _is_declared_identity(self):
            raise ScientificContractError("execution identity must be declared", subject=self.experiment)
        return self

    def require_population(self, population: PopulationId) -> None:
        if self.population is not population:
            raise ScientificContractError("execution identity population must match", subject=population)

    def require_evidence_role(self, evidence_role: EvidenceRole) -> None:
        if self.evidence_role is not evidence_role:
            raise ScientificContractError("execution identity evidence role must match", subject=evidence_role)


def require_execution_identity(
    identity: ExternalTemporalExecutionIdentity | None,
    population: PopulationId,
) -> ExternalTemporalExecutionIdentity | None:
    if population not in BOUNDED_EVIDENCE_POPULATIONS:
        if identity is not None:
            raise ScientificContractError("execution identity is reserved for bounded evidence", subject=population)
        return None
    if identity is None:
        raise ScientificContractError("bounded evidence requires an execution identity", subject=population)
    identity.require_population(population)
    return identity


def _is_declared_identity(identity: ExternalTemporalExecutionIdentity) -> bool:
    match identity.population, identity.experiment, identity.evidence_role, identity.temporal_state:
        case (
            PopulationId.EDGE_SENSOR_GROUPS,
            ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
            EvidenceRole.EXTERNAL_VALIDATION,
            None,
        ):
            return True
        case (
            PopulationId.CICIOT_FILE_CLIENTS,
            ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
            EvidenceRole.APPLICABILITY_BOUNDARY,
            None,
        ):
            return True
        case (
            PopulationId.EDGE_TEMPORAL_GROUPS,
            ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
            EvidenceRole.TEMPORAL_BOUNDARY,
            TemporalState.STATIC_REFERENCE | TemporalState.FROZEN_FUTURE | TemporalState.RECALIBRATED_FUTURE,
        ):
            return True
        case _:
            return False

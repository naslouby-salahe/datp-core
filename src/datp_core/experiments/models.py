"""Immutable execution identities for capability-constrained evidence."""

from dataclasses import dataclass

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


@dataclass(frozen=True, slots=True)
class ExternalTemporalExecutionIdentity:
    experiment: ExperimentId
    population: PopulationId
    evidence_role: EvidenceRole
    temporal_state: TemporalState | None

    def __post_init__(self) -> None:
        if not _is_declared_identity(self):
            raise ScientificContractError("execution identity must be declared", subject=self.experiment)

    def require_population(self, population: PopulationId) -> None:
        if self.population is not population:
            raise ScientificContractError("execution identity population must match", subject=population)

    def require_evidence_role(self, evidence_role: EvidenceRole) -> None:
        if self.evidence_role is not evidence_role:
            raise ScientificContractError("execution identity evidence role must match", subject=evidence_role)


class ExternalTemporalExecutionIdentityDocument(StrictModel):
    experiment: ExperimentId
    population: PopulationId
    evidence_role: EvidenceRole
    temporal_state: TemporalState | None

    @classmethod
    def from_identity(
        cls,
        identity: ExternalTemporalExecutionIdentity,
    ) -> "ExternalTemporalExecutionIdentityDocument":
        return cls(
            experiment=identity.experiment,
            population=identity.population,
            evidence_role=identity.evidence_role,
            temporal_state=identity.temporal_state,
        )

    def to_identity(self) -> ExternalTemporalExecutionIdentity:
        return ExternalTemporalExecutionIdentity(
            experiment=self.experiment,
            population=self.population,
            evidence_role=self.evidence_role,
            temporal_state=self.temporal_state,
        )


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

"""Immutable execution identities for capability-constrained evidence."""

from dataclasses import dataclass

from pydantic import model_validator

from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import EvidenceRole, ExperimentId, PopulationId, TemporalState
from datp_core.domain.errors import ScientificContractError


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionIdentityDeclaration:
    experiment: ExperimentId
    population: PopulationId
    evidence_role: EvidenceRole
    temporal_states: tuple[TemporalState | None, ...]

    def __post_init__(self) -> None:
        if not self.temporal_states:
            raise ValueError("execution identity declarations require at least one temporal state")
        if len(frozenset(self.temporal_states)) != len(self.temporal_states):
            raise ValueError("execution identity declaration temporal states must be unique")

    def matches(self, identity: "ExternalTemporalExecutionIdentity") -> bool:
        return (
            identity.experiment is self.experiment
            and identity.population is self.population
            and identity.evidence_role is self.evidence_role
            and identity.temporal_state in self.temporal_states
        )


EXECUTION_IDENTITY_DECLARATIONS = (
    ExecutionIdentityDeclaration(
        experiment=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        population=PopulationId.EDGE_SENSOR_GROUPS,
        evidence_role=EvidenceRole.EXTERNAL_VALIDATION,
        temporal_states=(None,),
    ),
    ExecutionIdentityDeclaration(
        experiment=ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
        population=PopulationId.CICIOT_FILE_CLIENTS,
        evidence_role=EvidenceRole.APPLICABILITY_BOUNDARY,
        temporal_states=(None,),
    ),
    ExecutionIdentityDeclaration(
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        population=PopulationId.EDGE_TEMPORAL_GROUPS,
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        temporal_states=(
            TemporalState.STATIC_REFERENCE,
            TemporalState.FROZEN_FUTURE,
            TemporalState.RECALIBRATED_FUTURE,
        ),
    ),
)
BOUNDED_EVIDENCE_POPULATIONS = frozenset(
    declaration.population for declaration in EXECUTION_IDENTITY_DECLARATIONS
)


class ExternalTemporalExecutionIdentity(StrictModel):
    experiment: ExperimentId
    population: PopulationId
    evidence_role: EvidenceRole
    temporal_state: TemporalState | None

    @model_validator(mode="after")
    def validate_declared_identity(self) -> "ExternalTemporalExecutionIdentity":
        matches = tuple(
            declaration
            for declaration in EXECUTION_IDENTITY_DECLARATIONS
            if declaration.matches(self)
        )
        if len(matches) != 1:
            raise ScientificContractError("execution identity must resolve exactly once", subject=self.experiment)
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

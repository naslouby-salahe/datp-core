"""Generic scientific decision result contracts."""

from enum import StrEnum

from pydantic import model_validator

from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import AvailabilityStatus, EvidenceRole
from datp_core.core.numeric import MetricValue


class ScientificDecision(StrEnum):
    SUPPORTED = "supported"
    DIRECTIONAL_INCONCLUSIVE = "directional_inconclusive"
    NO_OBSERVED_ADVANTAGE = "no_observed_advantage"
    OPPOSITE_DIRECTION = "opposite_direction"
    PARTIAL_ABSORPTION = "partial_absorption"
    FULL_ABSORPTION = "full_absorption"
    BOUNDARY_RESULT = "boundary_result"
    INFEASIBLE = "infeasible"
    BLOCKED = "blocked"


class ScientificDecisionResult(StrictModel):
    evidence_role: EvidenceRole
    decision: ScientificDecision
    point_estimate: MetricValue | None
    interval: BootstrapInterval | None
    rationale: str

    @model_validator(mode="after")
    def validate_decision(self) -> "ScientificDecisionResult":
        if not self.rationale.strip():
            raise ValueError("scientific decisions require a rationale")
        if self.interval is not None and self.point_estimate != self.interval.point_estimate:
            raise ValueError("decision estimate must match its interval estimate")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        return (
            AvailabilityStatus.UNAVAILABLE
            if self.decision is ScientificDecision.BLOCKED
            else AvailabilityStatus.AVAILABLE
        )


def blocked_decision(
    *,
    evidence_role: EvidenceRole,
    rationale: str,
    interval: BootstrapInterval | None = None,
) -> ScientificDecisionResult:
    return ScientificDecisionResult(
        evidence_role=evidence_role,
        decision=ScientificDecision.BLOCKED,
        point_estimate=None if interval is None else interval.point_estimate,
        interval=interval,
        rationale=rationale,
    )

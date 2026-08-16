from enum import StrEnum

from pydantic import model_validator

from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import AvailabilityStatus, DecisionRationale, EvidenceRole
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
    NOT_ESTABLISHED = "not_established"
    CONFIRMATORY_INFERENCE_UNAVAILABLE = "confirmatory_inference_unavailable"


class ScientificDecisionResult(StrictModel):
    evidence_role: EvidenceRole
    decision: ScientificDecision
    point_estimate: MetricValue | None
    interval: BootstrapInterval | None
    rationale: DecisionRationale

    @model_validator(mode="after")
    def validate_decision(self) -> "ScientificDecisionResult":
        if self.interval is not None and self.point_estimate != self.interval.point_estimate:
            raise ValueError("decision estimate must match its interval estimate")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        return (
            AvailabilityStatus.UNAVAILABLE if self.decision in _UNAVAILABLE_DECISIONS else AvailabilityStatus.AVAILABLE
        )


_UNAVAILABLE_DECISIONS = frozenset(
    {
        ScientificDecision.BLOCKED,
        ScientificDecision.NOT_ESTABLISHED,
        ScientificDecision.CONFIRMATORY_INFERENCE_UNAVAILABLE,
    }
)


def decide_confirmatory(interval: BootstrapInterval) -> ScientificDecisionResult:
    if (
        interval.availability is not AvailabilityStatus.AVAILABLE
        or interval.point_estimate is None
        or interval.lower_bound is None
        or interval.upper_bound is None
    ):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.CONFIRMATORY,
            decision=ScientificDecision.CONFIRMATORY_INFERENCE_UNAVAILABLE,
            point_estimate=interval.point_estimate,
            interval=interval,
            rationale=DecisionRationale("confirmatory BCa interval is unavailable or degenerate"),
        )
    if interval.lower_bound.value > 0.0:
        decision = ScientificDecision.SUPPORTED
        rationale = DecisionRationale("the paired BCa interval supports lower CV(FPR) under local thresholds")
    elif interval.upper_bound.value < 0.0:
        decision = ScientificDecision.OPPOSITE_DIRECTION
        rationale = DecisionRationale("the paired BCa interval supports the opposite direction")
    elif interval.point_estimate.value > 0.0:
        decision = ScientificDecision.DIRECTIONAL_INCONCLUSIVE
        rationale = DecisionRationale("the point estimate is directional but the paired BCa interval crosses zero")
    else:
        decision = ScientificDecision.NO_OBSERVED_ADVANTAGE
        rationale = DecisionRationale("the paired BCa interval crosses zero without a positive point estimate")
    return ScientificDecisionResult(
        evidence_role=EvidenceRole.CONFIRMATORY,
        decision=decision,
        point_estimate=interval.point_estimate,
        interval=interval,
        rationale=rationale,
    )

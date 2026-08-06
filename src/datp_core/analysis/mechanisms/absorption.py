"""Model-personalization absorption decisions."""

from datp_core.analysis.scientific_decision import ScientificDecision, ScientificDecisionResult
from datp_core.domain.enums import EvidenceRole
from datp_core.domain.values.ratios import MetricValue
from datp_core.protocols.training import ModelAbsorptionDecisionProtocol


def decide_model_absorption(
    reference_effect: MetricValue | None,
    personalized_effect: MetricValue | None,
    protocol: ModelAbsorptionDecisionProtocol,
) -> ScientificDecisionResult:
    if reference_effect is None or personalized_effect is None or reference_effect.value <= 0.0:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.SUPPORTIVE,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="model absorption requires a valid positive reference effect",
        )
    retention = MetricValue(personalized_effect.value / reference_effect.value)
    if retention.value >= protocol.full_retention_minimum.value:
        decision = ScientificDecision.SUPPORTED
        rationale = "the personalized-model effect is retained"
    elif retention.value >= protocol.partial_retention_minimum.value:
        decision = ScientificDecision.PARTIAL_ABSORPTION
        rationale = "the personalized-model effect is partially absorbed"
    else:
        decision = ScientificDecision.FULL_ABSORPTION
        rationale = "the personalized-model effect is largely absorbed"
    return ScientificDecisionResult(
        evidence_role=EvidenceRole.SUPPORTIVE,
        decision=decision,
        point_estimate=retention,
        interval=None,
        rationale=rationale,
    )

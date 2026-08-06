"""Model-personalization and FedProx absorption decisions from paired seed evidence."""

from pydantic import model_validator

from datp_core.analysis.scientific_decision import ScientificDecision, ScientificDecisionResult
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import EvidenceRole, ExperimentId, TrainingModelId
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import MetricValue
from datp_core.protocols.training import ModelAbsorptionDecisionProtocol


class AbsorptionSeedObservation(StrictModel):
    seed: Seed
    experiment: ExperimentId
    reference_model: TrainingModelId
    personalized_model: TrainingModelId
    reference_effect: MetricValue
    personalized_effect: MetricValue

    @model_validator(mode="after")
    def validate_observation(self) -> "AbsorptionSeedObservation":
        if self.reference_model is self.personalized_model:
            raise ValueError("absorption observation requires distinct reference and personalized models")
        return self

    @property
    def retention_ratio(self) -> MetricValue | None:
        if self.reference_effect.value <= 0.0:
            return None
        return MetricValue(self.personalized_effect.value / self.reference_effect.value)


class AbsorptionCohortResult(StrictModel):
    observations: tuple[AbsorptionSeedObservation, ...]
    decision: ScientificDecisionResult
    mean_retention: MetricValue | None
    retention_lower: MetricValue | None
    retention_upper: MetricValue | None

    @model_validator(mode="after")
    def validate_result(self) -> "AbsorptionCohortResult":
        if self.decision.evidence_role is not EvidenceRole.SUPPORTIVE:
            raise ValueError("absorption cohort decisions must remain supportive evidence")
        return self


def decide_model_absorption(
    reference_effect: MetricValue | None,
    personalized_effect: MetricValue | None,
    protocol: ModelAbsorptionDecisionProtocol,
) -> ScientificDecisionResult:
    """Point-estimate absorption rule retained for single-seed diagnostics."""
    if reference_effect is None or personalized_effect is None or reference_effect.value <= 0.0:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.SUPPORTIVE,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="model absorption requires a valid positive reference effect",
        )
    retention = MetricValue(personalized_effect.value / reference_effect.value)
    if personalized_effect.value < 0.0 < reference_effect.value:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.SUPPORTIVE,
            decision=ScientificDecision.OPPOSITE_DIRECTION,
            point_estimate=retention,
            interval=None,
            rationale="the personalized-model effect reversed the reference threshold-scope direction",
        )
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


def decide_absorption_cohort(
    observations: tuple[AbsorptionSeedObservation, ...],
    protocol: ModelAbsorptionDecisionProtocol,
) -> AbsorptionCohortResult:
    """Cohort-level absorption using paired seed-level retention ratios and uncertainty."""
    if not observations:
        decision = ScientificDecisionResult(
            evidence_role=EvidenceRole.SUPPORTIVE,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="absorption cohort requires at least one paired seed observation",
        )
        return AbsorptionCohortResult(
            observations=(),
            decision=decision,
            mean_retention=None,
            retention_lower=None,
            retention_upper=None,
        )
    ratios = tuple(item.retention_ratio for item in observations)
    if any(ratio is None for ratio in ratios):
        decision = ScientificDecisionResult(
            evidence_role=EvidenceRole.SUPPORTIVE,
            decision=ScientificDecision.INFEASIBLE,
            point_estimate=None,
            interval=None,
            rationale="absorption cohort contains a non-positive reference effect",
        )
        return AbsorptionCohortResult(
            observations=observations,
            decision=decision,
            mean_retention=None,
            retention_lower=None,
            retention_upper=None,
        )
    values = tuple(ratio.value for ratio in ratios if ratio is not None)
    mean_retention = MetricValue(sum(values) / len(values))
    lower = MetricValue(min(values))
    upper = MetricValue(max(values))
    opposite = sum(item.personalized_effect.value < 0.0 for item in observations)
    if opposite == len(observations):
        decision = ScientificDecisionResult(
            evidence_role=EvidenceRole.SUPPORTIVE,
            decision=ScientificDecision.OPPOSITE_DIRECTION,
            point_estimate=mean_retention,
            interval=None,
            rationale="every seed reversed the reference threshold-scope direction under personalization",
        )
    elif lower.value >= protocol.full_retention_minimum.value:
        decision = ScientificDecisionResult(
            evidence_role=EvidenceRole.SUPPORTIVE,
            decision=ScientificDecision.SUPPORTED,
            point_estimate=mean_retention,
            interval=None,
            rationale=(
                "paired seed-level retention remains at or above the full-retention threshold "
                f"(mean={mean_retention.value:.4g}, range=[{lower.value:.4g}, {upper.value:.4g}])"
            ),
        )
    elif upper.value < protocol.partial_retention_minimum.value:
        decision = ScientificDecisionResult(
            evidence_role=EvidenceRole.SUPPORTIVE,
            decision=ScientificDecision.FULL_ABSORPTION,
            point_estimate=mean_retention,
            interval=None,
            rationale=(
                "paired seed-level retention lies entirely below the partial-retention threshold "
                f"(mean={mean_retention.value:.4g}, range=[{lower.value:.4g}, {upper.value:.4g}])"
            ),
        )
    elif mean_retention.value >= protocol.partial_retention_minimum.value:
        decision = ScientificDecisionResult(
            evidence_role=EvidenceRole.SUPPORTIVE,
            decision=ScientificDecision.PARTIAL_ABSORPTION,
            point_estimate=mean_retention,
            interval=None,
            rationale=(
                "paired seed-level retention is partially absorbed with residual effect "
                f"(mean={mean_retention.value:.4g}, range=[{lower.value:.4g}, {upper.value:.4g}])"
            ),
        )
    else:
        decision = ScientificDecisionResult(
            evidence_role=EvidenceRole.SUPPORTIVE,
            decision=ScientificDecision.FULL_ABSORPTION,
            point_estimate=mean_retention,
            interval=None,
            rationale=(
                "paired seed-level mean retention falls below the partial-retention threshold "
                f"(mean={mean_retention.value:.4g}, range=[{lower.value:.4g}, {upper.value:.4g}])"
            ),
        )
    return AbsorptionCohortResult(
        observations=observations,
        decision=decision,
        mean_retention=mean_retention,
        retention_lower=lower,
        retention_upper=upper,
    )

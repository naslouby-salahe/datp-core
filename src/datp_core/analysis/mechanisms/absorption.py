"""Model-personalization absorption decisions from paired seed CV(FPR) evidence."""

from pydantic import model_validator

from datp_core.analysis.scientific_decision import ScientificDecision, ScientificDecisionResult
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import EvidenceRole, ExperimentId, TrainingModelId
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import MetricValue
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.protocols.training import ModelAbsorptionDecisionProtocol


class AbsorptionSeedObservation(StrictModel):
    """One seed of paired threshold-scope effects under reference vs personalized training."""

    seed: Seed
    experiment: ExperimentId
    reference_model: TrainingModelId
    personalized_model: TrainingModelId
    reference_effect: MetricValue
    personalized_effect: MetricValue
    reference_shared_cv: MetricValue | None = None
    reference_local_cv: MetricValue | None = None
    personalized_shared_cv: MetricValue | None = None
    personalized_local_cv: MetricValue | None = None

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

    @property
    def is_opposite_direction(self) -> bool:
        return self.personalized_effect.value < 0.0 < self.reference_effect.value


class AbsorptionCohortResult(StrictModel):
    observations: tuple[AbsorptionSeedObservation, ...]
    decision: ScientificDecisionResult
    mean_retention: MetricValue | None
    retention_range_lower: MetricValue | None
    retention_range_upper: MetricValue | None
    alternative_route_seed_count: int = 0

    @model_validator(mode="after")
    def validate_result(self) -> "AbsorptionCohortResult":
        if self.decision.evidence_role is not EvidenceRole.TRAINING_STRESS_TEST:
            raise ValueError("absorption cohort decisions must remain training-stress-test evidence")
        if self.alternative_route_seed_count < 0:
            raise ValueError("alternative-route seed count cannot be negative")
        return self


def decide_model_absorption(
    reference_effect: MetricValue | None,
    personalized_effect: MetricValue | None,
    protocol: ModelAbsorptionDecisionProtocol,
) -> ScientificDecisionResult:
    """Point-estimate absorption rule for single-seed diagnostics only."""
    if reference_effect is None or personalized_effect is None or reference_effect.value <= 0.0:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="model absorption requires a valid positive reference CV(FPR) effect",
        )
    retention = MetricValue(personalized_effect.value / reference_effect.value)
    if personalized_effect.value < 0.0:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.OPPOSITE_DIRECTION,
            point_estimate=retention,
            interval=None,
            rationale="the personalized-model CV(FPR) effect reversed the reference threshold-scope direction",
        )
    if retention.value >= protocol.full_retention_minimum.value:
        decision = ScientificDecision.SUPPORTED
        rationale = "the personalized-model CV(FPR) threshold-scope effect is retained"
    elif retention.value >= protocol.partial_retention_minimum.value:
        decision = ScientificDecision.PARTIAL_ABSORPTION
        rationale = "the personalized-model CV(FPR) threshold-scope effect is partially absorbed"
    else:
        decision = ScientificDecision.FULL_ABSORPTION
        rationale = "the personalized-model CV(FPR) threshold-scope effect is largely absorbed"
    return ScientificDecisionResult(
        evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
        decision=decision,
        point_estimate=retention,
        interval=None,
        rationale=rationale,
    )


def decide_absorption_cohort(
    observations: tuple[AbsorptionSeedObservation, ...],
    protocol: ModelAbsorptionDecisionProtocol,
    *,
    required_seed_cohort: SeedCohort = CONFIRMATORY_SEED_COHORT,
    alternative_route_seed_count: int = 0,
) -> AbsorptionCohortResult:
    """Cohort-level absorption using paired seed-level CV(FPR) retention ratios."""
    blocked = _blocked_cohort(observations, required_seed_cohort)
    if blocked is not None:
        return AbsorptionCohortResult(
            observations=observations,
            decision=blocked,
            mean_retention=None,
            retention_range_lower=None,
            retention_range_upper=None,
            alternative_route_seed_count=alternative_route_seed_count,
        )
    ratios = tuple(item.retention_ratio for item in observations)
    if any(ratio is None for ratio in ratios):
        decision = ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.INFEASIBLE,
            point_estimate=None,
            interval=None,
            rationale="absorption cohort contains a non-positive reference CV(FPR) effect",
        )
        return AbsorptionCohortResult(
            observations=observations,
            decision=decision,
            mean_retention=None,
            retention_range_lower=None,
            retention_range_upper=None,
            alternative_route_seed_count=alternative_route_seed_count,
        )
    values = tuple(ratio.value for ratio in ratios if ratio is not None)
    mean_retention = MetricValue(sum(values) / len(values))
    lower = MetricValue(min(values))
    upper = MetricValue(max(values))
    opposite_count = sum(1 for item in observations if item.is_opposite_direction)
    decision = _classify_cohort(
        observations=observations,
        protocol=protocol,
        mean_retention=mean_retention,
        lower=lower,
        upper=upper,
        opposite_count=opposite_count,
    )
    return AbsorptionCohortResult(
        observations=observations,
        decision=decision,
        mean_retention=mean_retention,
        retention_range_lower=lower,
        retention_range_upper=upper,
        alternative_route_seed_count=alternative_route_seed_count,
    )


def _blocked_cohort(
    observations: tuple[AbsorptionSeedObservation, ...],
    required_seed_cohort: SeedCohort,
) -> ScientificDecisionResult | None:
    if not observations:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="absorption cohort requires the complete declared seed cohort",
        )
    seeds = tuple(item.seed for item in observations)
    if len(seeds) != len(frozenset(seeds)):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="absorption cohort records must be unique by seed",
        )
    if frozenset(seeds) != frozenset(required_seed_cohort.values):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="absorption cohort must equal the complete declared seed set",
        )
    if len({item.experiment for item in observations}) != 1:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="absorption cohort records must share one experiment identity",
        )
    if len({(item.reference_model, item.personalized_model) for item in observations}) != 1:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="absorption cohort records must share one model pair",
        )
    return None


def _classify_cohort(
    *,
    observations: tuple[AbsorptionSeedObservation, ...],
    protocol: ModelAbsorptionDecisionProtocol,
    mean_retention: MetricValue,
    lower: MetricValue,
    upper: MetricValue,
    opposite_count: int,
) -> ScientificDecisionResult:
    total = len(observations)
    range_text = (
        f"(mean={mean_retention.value:.4g}, range=[{lower.value:.4g}, {upper.value:.4g}], "
        f"opposite_seeds={opposite_count}/{total})"
    )
    if opposite_count == total:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.OPPOSITE_DIRECTION,
            point_estimate=mean_retention,
            interval=None,
            rationale="every seed reversed the reference CV(FPR) threshold-scope direction under personalization",
        )
    if opposite_count > 0:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.OPPOSITE_DIRECTION,
            point_estimate=mean_retention,
            interval=None,
            rationale=(
                "absorption cohort contains opposite-direction CV(FPR) effects and cannot be classified "
                f"as retained or absorbed {range_text}"
            ),
        )
    if lower.value >= protocol.full_retention_minimum.value:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.SUPPORTED,
            point_estimate=mean_retention,
            interval=None,
            rationale=(
                f"paired seed-level CV(FPR) retention remains at or above the full-retention threshold {range_text}"
            ),
        )
    if upper.value < protocol.partial_retention_minimum.value:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.FULL_ABSORPTION,
            point_estimate=mean_retention,
            interval=None,
            rationale=(
                f"paired seed-level CV(FPR) retention lies entirely below the partial-retention threshold {range_text}"
            ),
        )
    if mean_retention.value >= protocol.partial_retention_minimum.value:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.PARTIAL_ABSORPTION,
            point_estimate=mean_retention,
            interval=None,
            rationale=(f"paired seed-level CV(FPR) retention is partially absorbed with residual effect {range_text}"),
        )
    return ScientificDecisionResult(
        evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
        decision=ScientificDecision.FULL_ABSORPTION,
        point_estimate=mean_retention,
        interval=None,
        rationale=(
            f"paired seed-level mean CV(FPR) retention falls below the partial-retention threshold {range_text}"
        ),
    )

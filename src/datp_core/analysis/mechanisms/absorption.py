"""Model-personalization absorption decisions from paired seed CV(FPR) evidence."""

from pydantic import model_validator

from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
from datp_core.analysis.inference.bootstrap.estimation import seed_level_bca_interval
from datp_core.analysis.scientific_decision import ScientificDecision, ScientificDecisionResult
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import EvidenceRole, ExperimentId, TrainingModelId
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE, MetricValue
from datp_core.protocols.seeds import CONFIRMATORY_ANALYSIS_SEED, CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL, PairedInferenceProtocol
from datp_core.protocols.training import ModelAbsorptionDecisionProtocol


class AbsorptionSeedObservation(StrictModel):
    """One seed of paired threshold-scope effects under reference vs personalized training.

    Four-corner estimand:
    Δ_ref = CV(FPR)_SHARED_ref − CV(FPR)_LOCAL_ref
    Δ_pers = CV(FPR)_SHARED_pers − CV(FPR)_LOCAL_pers
    """

    seed: Seed
    experiment: ExperimentId
    reference_model: TrainingModelId
    personalized_model: TrainingModelId
    reference_effect: MetricValue
    personalized_effect: MetricValue
    reference_shared_cv: MetricValue
    reference_local_cv: MetricValue
    personalized_shared_cv: MetricValue
    personalized_local_cv: MetricValue

    @model_validator(mode="after")
    def validate_observation(self) -> "AbsorptionSeedObservation":
        if self.reference_model is self.personalized_model:
            raise ValueError("absorption observation requires distinct reference and personalized models")
        ref_delta = self.reference_shared_cv.value - self.reference_local_cv.value
        pers_delta = self.personalized_shared_cv.value - self.personalized_local_cv.value
        tol = NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE.value
        if abs(ref_delta - self.reference_effect.value) > tol:
            raise ValueError("reference_effect must equal reference shared CV(FPR) − local CV(FPR)")
        if abs(pers_delta - self.personalized_effect.value) > tol:
            raise ValueError("personalized_effect must equal personalized shared CV(FPR) − local CV(FPR)")
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
    retention_interval: BootstrapInterval | None = None
    reference_effect_interval: BootstrapInterval | None = None
    personalized_effect_interval: BootstrapInterval | None = None
    paired_absorption_change_interval: BootstrapInterval | None = None
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
    inference_protocol: PairedInferenceProtocol | None = None,
    analysis_seed: Seed = CONFIRMATORY_ANALYSIS_SEED,
) -> AbsorptionCohortResult:
    """Cohort-level absorption using paired seed-level CV(FPR) retention ratios."""
    if alternative_route_seed_count < 0:
        raise ValueError("alternative-route seed count cannot be negative")
    route_count = alternative_route_seed_count
    blocked = _blocked_cohort(observations, required_seed_cohort)
    if blocked is not None:
        return AbsorptionCohortResult(
            observations=observations,
            decision=blocked,
            mean_retention=None,
            alternative_route_seed_count=route_count,
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
            alternative_route_seed_count=route_count,
        )
    defined_ratios = tuple(ratio for ratio in ratios if ratio is not None)
    mean_retention = MetricValue(sum(item.value for item in defined_ratios) / len(defined_ratios))
    opposite_count = sum(1 for item in observations if item.is_opposite_direction)
    stats_protocol = inference_protocol or CONFIRMATORY_INFERENCE_PROTOCOL
    retention_interval = seed_level_bca_interval(
        defined_ratios,
        protocol=stats_protocol,
        analysis_seed=analysis_seed,
        require_full_cohort=True,
    )
    reference_interval = seed_level_bca_interval(
        tuple(item.reference_effect for item in observations),
        protocol=stats_protocol,
        analysis_seed=analysis_seed,
        require_full_cohort=True,
    )
    personalized_interval = seed_level_bca_interval(
        tuple(item.personalized_effect for item in observations),
        protocol=stats_protocol,
        analysis_seed=analysis_seed,
        require_full_cohort=True,
    )
    absorption_change = tuple(
        MetricValue(item.reference_effect.value - item.personalized_effect.value) for item in observations
    )
    change_interval = seed_level_bca_interval(
        absorption_change,
        protocol=stats_protocol,
        analysis_seed=analysis_seed,
        require_full_cohort=True,
    )
    decision = _classify_cohort(
        observations=observations,
        protocol=protocol,
        mean_retention=mean_retention,
        opposite_count=opposite_count,
        retention_interval=retention_interval,
    )
    return AbsorptionCohortResult(
        observations=observations,
        decision=decision,
        mean_retention=mean_retention,
        retention_interval=retention_interval,
        reference_effect_interval=reference_interval,
        personalized_effect_interval=personalized_interval,
        paired_absorption_change_interval=change_interval,
        alternative_route_seed_count=route_count,
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
    opposite_count: int,
    retention_interval: BootstrapInterval | None,
) -> ScientificDecisionResult:
    total = len(observations)
    interval = retention_interval
    interval_text = (
        f"BCa=[{interval.lower_bound.value:.4g}, {interval.upper_bound.value:.4g}]"
        if interval is not None and interval.lower_bound is not None and interval.upper_bound is not None
        else "BCa=unavailable"
    )
    range_text = f"(mean={mean_retention.value:.4g}, {interval_text}, opposite_seeds={opposite_count}/{total})"
    if opposite_count == total:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.OPPOSITE_DIRECTION,
            point_estimate=mean_retention,
            interval=interval,
            rationale="every seed reversed the reference CV(FPR) threshold-scope direction under personalization",
        )
    if opposite_count > 0:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.OPPOSITE_DIRECTION,
            point_estimate=mean_retention,
            interval=interval,
            rationale=(
                "absorption cohort contains opposite-direction CV(FPR) effects and cannot be classified "
                f"as retained or absorbed {range_text}"
            ),
        )
    if mean_retention.value >= protocol.full_retention_minimum.value and (
        interval is None
        or interval.lower_bound is None
        or interval.lower_bound.value >= protocol.partial_retention_minimum.value
    ):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.SUPPORTED,
            point_estimate=mean_retention,
            interval=interval,
            rationale=(
                f"paired seed-level CV(FPR) retention remains at or above the full-retention threshold {range_text}"
            ),
        )
    if mean_retention.value < protocol.partial_retention_minimum.value and (
        interval is None
        or interval.upper_bound is None
        or interval.upper_bound.value < protocol.partial_retention_minimum.value
    ):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.FULL_ABSORPTION,
            point_estimate=mean_retention,
            interval=interval,
            rationale=(f"paired seed-level CV(FPR) retention lies below the partial-retention threshold {range_text}"),
        )
    if mean_retention.value >= protocol.partial_retention_minimum.value:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.PARTIAL_ABSORPTION,
            point_estimate=mean_retention,
            interval=interval,
            rationale=(f"paired seed-level CV(FPR) retention is partially absorbed with residual effect {range_text}"),
        )
    return ScientificDecisionResult(
        evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
        decision=ScientificDecision.FULL_ABSORPTION,
        point_estimate=mean_retention,
        interval=interval,
        rationale=(
            f"paired seed-level mean CV(FPR) retention falls below the partial-retention threshold {range_text}"
        ),
    )

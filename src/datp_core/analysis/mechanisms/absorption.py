"""Model-personalization absorption decisions from paired seed CV(FPR) evidence."""

from enum import StrEnum

from pydantic import model_validator

from datp_core.analysis.inference.bootstrap.contracts import BcaOutcome, BootstrapInterval
from datp_core.analysis.inference.bootstrap.estimation import seed_level_bca_interval
from datp_core.analysis.inference.contracts import PairedInferenceProtocol
from datp_core.analysis.metrics.protocols import ABSORPTION_REFERENCE_EFFECT_MATERIALITY_CUTOFF
from datp_core.analysis.scientific_decision import ScientificDecision, ScientificDecisionResult
from datp_core.artifacts.provenance import Checksum
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import (
    DecisionRationale,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    IntervalDescriptionText,
    PopulationId,
    TrainingModelId,
)
from datp_core.core.numeric import (
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    MetricValue,
    ModelCoefficientValue,
    ProximalCoefficient,
    Seed,
    SeedObservationCount,
)
from datp_core.detector.training.contracts import ModelAbsorptionDecisionProtocol
from datp_core.experiments.common.seeds import CONFIRMATORY_ANALYSIS_SEED, CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.experiments.confirmatory.spec import CONFIRMATORY_INFERENCE_PROTOCOL

_ZERO_ALTERNATIVE_ROUTE_SEED_COUNT = SeedObservationCount(0)


class AbsorptionRatioUnavailableReason(StrEnum):
    REFERENCE_EFFECT_NON_POSITIVE = "reference CV(FPR) effect is non-positive"
    REFERENCE_EFFECT_BELOW_MATERIALITY = (
        "reference CV(FPR) effect is below the declared absorption denominator materiality cutoff"
    )


class AbsorptionCornerEvidence(StrictModel):
    """One artifact-bound corner of the four-corner absorption estimand."""

    seed: Seed
    experiment: ExperimentId
    population: PopulationId
    model: TrainingModelId
    threshold_method: FederatedThresholdMethod
    coefficient: ModelCoefficientValue | None
    checkpoint_checksum: Checksum
    preprocessing_checksum: Checksum
    split_checksum: Checksum
    calibration_score_checksum: Checksum
    evaluation_score_checksum: Checksum
    evaluation_checksum: Checksum
    client_inventory_checksum: Checksum
    eligibility_checksum: Checksum
    population_cv_fpr: MetricValue

    @model_validator(mode="after")
    def validate_corner(self) -> "AbsorptionCornerEvidence":
        if self.threshold_method not in {
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
        }:
            raise ValueError("absorption corners must use SHARED_THRESHOLD or LOCAL_THRESHOLD")
        return self


class AbsorptionFourCornerEvidence(StrictModel):
    """Typed four-corner evidence for one seed under reference vs personalized training."""

    seed: Seed
    experiment: ExperimentId
    reference_model: TrainingModelId
    personalized_model: TrainingModelId
    reference_shared: AbsorptionCornerEvidence
    reference_local: AbsorptionCornerEvidence
    personalized_shared: AbsorptionCornerEvidence
    personalized_local: AbsorptionCornerEvidence

    @model_validator(mode="after")
    def validate_corners(self) -> "AbsorptionFourCornerEvidence":
        corners = (
            self.reference_shared,
            self.reference_local,
            self.personalized_shared,
            self.personalized_local,
        )
        if any(item.seed != self.seed for item in corners):
            raise ValueError("absorption corners must share the observation seed")
        if any(item.experiment is not self.experiment for item in corners):
            raise ValueError("absorption corners must share the observation experiment")
        if (
            self.reference_shared.model is not self.reference_model
            or self.reference_local.model is not self.reference_model
        ):
            raise ValueError("reference corners must use the reference model")
        if (
            self.personalized_shared.model is not self.personalized_model
            or self.personalized_local.model is not self.personalized_model
        ):
            raise ValueError("personalized corners must use the personalized model")
        if self.reference_shared.threshold_method is not FederatedThresholdMethod.SHARED_THRESHOLD:
            raise ValueError("reference shared corner must use SHARED_THRESHOLD")
        if self.reference_local.threshold_method is not FederatedThresholdMethod.LOCAL_THRESHOLD:
            raise ValueError("reference local corner must use LOCAL_THRESHOLD")
        if self.personalized_shared.threshold_method is not FederatedThresholdMethod.SHARED_THRESHOLD:
            raise ValueError("personalized shared corner must use SHARED_THRESHOLD")
        if self.personalized_local.threshold_method is not FederatedThresholdMethod.LOCAL_THRESHOLD:
            raise ValueError("personalized local corner must use LOCAL_THRESHOLD")
        identities = tuple(
            (
                item.checkpoint_checksum,
                item.preprocessing_checksum,
                item.split_checksum,
                item.calibration_score_checksum,
                item.evaluation_score_checksum,
                item.evaluation_checksum,
            )
            for item in corners
        )
        if len(frozenset(identities)) != 4:
            raise ValueError("absorption corners must not clone identical artifact identities")
        return self

    @property
    def reference_effect(self) -> MetricValue:
        return MetricValue(self.reference_shared.population_cv_fpr.value - self.reference_local.population_cv_fpr.value)

    @property
    def personalized_effect(self) -> MetricValue:
        return MetricValue(
            self.personalized_shared.population_cv_fpr.value - self.personalized_local.population_cv_fpr.value
        )


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
    corners: AbsorptionFourCornerEvidence | None = None
    model_coefficient: ProximalCoefficient | ModelCoefficientValue | None = None
    ratio_unavailable_reason: AbsorptionRatioUnavailableReason | None = None

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
        if self.corners is not None:
            if self.corners.seed != self.seed or self.corners.experiment is not self.experiment:
                raise ValueError("absorption corner evidence must match the observation identity")
            if abs(self.corners.reference_effect.value - self.reference_effect.value) > tol:
                raise ValueError("absorption corners must produce the declared reference effect")
            if abs(self.corners.personalized_effect.value - self.personalized_effect.value) > tol:
                raise ValueError("absorption corners must produce the declared personalized effect")
        return self

    @classmethod
    def from_corners(cls, corners: AbsorptionFourCornerEvidence) -> "AbsorptionSeedObservation":
        reference_effect = corners.reference_effect
        personalized_effect = corners.personalized_effect
        ratio_reason: AbsorptionRatioUnavailableReason | None = None
        if reference_effect.value <= 0.0:
            ratio_reason = AbsorptionRatioUnavailableReason.REFERENCE_EFFECT_NON_POSITIVE
        elif reference_effect.value < ABSORPTION_REFERENCE_EFFECT_MATERIALITY_CUTOFF.value:
            ratio_reason = AbsorptionRatioUnavailableReason.REFERENCE_EFFECT_BELOW_MATERIALITY
        coefficient = corners.personalized_shared.coefficient
        return cls(
            seed=corners.seed,
            experiment=corners.experiment,
            reference_model=corners.reference_model,
            personalized_model=corners.personalized_model,
            reference_effect=reference_effect,
            personalized_effect=personalized_effect,
            reference_shared_cv=corners.reference_shared.population_cv_fpr,
            reference_local_cv=corners.reference_local.population_cv_fpr,
            personalized_shared_cv=corners.personalized_shared.population_cv_fpr,
            personalized_local_cv=corners.personalized_local.population_cv_fpr,
            corners=corners,
            model_coefficient=coefficient,
            ratio_unavailable_reason=ratio_reason,
        )

    @property
    def retention_ratio(self) -> MetricValue | None:
        if self.ratio_unavailable_reason is not None:
            return None
        if self.reference_effect.value <= 0.0:
            return None
        if self.reference_effect.value < ABSORPTION_REFERENCE_EFFECT_MATERIALITY_CUTOFF.value:
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
    alternative_route_seed_count: SeedObservationCount = SeedObservationCount(0)

    @model_validator(mode="after")
    def validate_result(self) -> "AbsorptionCohortResult":
        if self.decision.evidence_role is not EvidenceRole.TRAINING_STRESS_TEST:
            raise ValueError("absorption cohort decisions must remain training-stress-test evidence")
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
            rationale=DecisionRationale("model absorption requires a valid positive reference CV(FPR) effect"),
        )
    retention = MetricValue(personalized_effect.value / reference_effect.value)
    if personalized_effect.value < 0.0:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.OPPOSITE_DIRECTION,
            point_estimate=retention,
            interval=None,
            rationale=DecisionRationale(
                "the personalized-model CV(FPR) effect reversed the reference threshold-scope direction"
            ),
        )
    if retention.value >= protocol.full_retention_minimum.value:
        decision = ScientificDecision.SUPPORTED
        rationale = DecisionRationale("the personalized-model CV(FPR) threshold-scope effect is retained")
    elif retention.value >= protocol.partial_retention_minimum.value:
        decision = ScientificDecision.PARTIAL_ABSORPTION
        rationale = DecisionRationale("the personalized-model CV(FPR) threshold-scope effect is partially absorbed")
    else:
        decision = ScientificDecision.FULL_ABSORPTION
        rationale = DecisionRationale("the personalized-model CV(FPR) threshold-scope effect is largely absorbed")
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
    alternative_route_seed_count: SeedObservationCount = _ZERO_ALTERNATIVE_ROUTE_SEED_COUNT,
    inference_protocol: PairedInferenceProtocol | None = None,
    analysis_seed: Seed = CONFIRMATORY_ANALYSIS_SEED,
) -> AbsorptionCohortResult:
    """Cohort-level absorption using paired seed-level CV(FPR) retention ratios."""
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
        reasons = sorted(
            {
                item.ratio_unavailable_reason
                or AbsorptionRatioUnavailableReason.REFERENCE_EFFECT_NON_POSITIVE
                for item in observations
                if item.retention_ratio is None
            }
        )
        decision = ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.INFEASIBLE,
            point_estimate=None,
            interval=None,
            rationale=DecisionRationale(
                "absorption cohort ratio interpretation is unavailable: "
                + "; ".join(reason.value for reason in reasons)
                + "; paired difference estimands remain available"
            ),
        )
        return AbsorptionCohortResult(
            observations=observations,
            decision=decision,
            mean_retention=None,
            alternative_route_seed_count=route_count,
        )
    defined_ratios = tuple(ratio for ratio in ratios if ratio is not None)
    mean_retention = MetricValue(sum(item.value for item in defined_ratios) / len(defined_ratios))
    opposite_count = SeedObservationCount(sum(1 for item in observations if item.is_opposite_direction))
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
            rationale=DecisionRationale("absorption cohort requires the complete declared seed cohort"),
        )
    seeds = tuple(item.seed for item in observations)
    if len(seeds) != len(frozenset(seeds)):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale=DecisionRationale("absorption cohort records must be unique by seed"),
        )
    if frozenset(seeds) != frozenset(required_seed_cohort.values):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale=DecisionRationale("absorption cohort must equal the complete declared seed set"),
        )
    if len({item.experiment for item in observations}) != 1:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale=DecisionRationale("absorption cohort records must share one experiment identity"),
        )
    if len({(item.reference_model, item.personalized_model) for item in observations}) != 1:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale=DecisionRationale("absorption cohort records must share one model pair"),
        )
    coefficients = tuple(item.model_coefficient for item in observations if item.model_coefficient is not None)
    if coefficients and len(coefficients) != len(observations):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale=DecisionRationale(
                "absorption cohort coefficients must be present for every seed when any seed declares one"
            ),
        )
    if coefficients and len({item.value for item in coefficients}) != 1:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale=DecisionRationale("absorption cohort records must share one model coefficient"),
        )
    return None


def _cohort_interval_text(interval: BootstrapInterval | None) -> IntervalDescriptionText:
    if (
        interval is not None
        and interval.outcome is BcaOutcome.AVAILABLE
        and interval.lower_bound is not None
        and interval.upper_bound is not None
    ):
        return IntervalDescriptionText(
            f"BCa=[{interval.lower_bound.value:.4g}, {interval.upper_bound.value:.4g}]"
        )
    return IntervalDescriptionText("BCa=unavailable")


def _stress_decision_result(
    *,
    decision: ScientificDecision,
    mean_retention: MetricValue,
    interval: BootstrapInterval | None,
    rationale: DecisionRationale,
) -> ScientificDecisionResult:
    return ScientificDecisionResult(
        evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
        decision=decision,
        point_estimate=mean_retention,
        interval=interval,
        rationale=rationale,
    )


def _classify_cohort(
    *,
    observations: tuple[AbsorptionSeedObservation, ...],
    protocol: ModelAbsorptionDecisionProtocol,
    mean_retention: MetricValue,
    opposite_count: SeedObservationCount,
    retention_interval: BootstrapInterval | None,
) -> ScientificDecisionResult:
    total = len(observations)
    interval = retention_interval
    if (
        interval is not None
        and interval.outcome is BcaOutcome.AVAILABLE
        and interval.lower_bound is not None
        and interval.upper_bound is not None
    ):
        bounded_interval = interval
    else:
        bounded_interval = None
    range_text = (
        f"(mean={mean_retention.value:.4g}, {_cohort_interval_text(interval)}, "
        f"opposite_seeds={opposite_count.value}/{total})"
    )
    if opposite_count.value == total:
        return _stress_decision_result(
            decision=ScientificDecision.OPPOSITE_DIRECTION,
            mean_retention=mean_retention,
            interval=interval,
            rationale=DecisionRationale(
                "every seed reversed the reference CV(FPR) threshold-scope direction under personalization"
            ),
        )
    if opposite_count.value > 0:
        return _stress_decision_result(
            decision=ScientificDecision.OPPOSITE_DIRECTION,
            mean_retention=mean_retention,
            interval=interval,
            rationale=DecisionRationale(
                "absorption cohort contains opposite-direction CV(FPR) effects and cannot be classified "
                f"as retained or absorbed {range_text}"
            ),
        )
    if (
        bounded_interval is None
        or bounded_interval.lower_bound is None
        or bounded_interval.upper_bound is None
    ):
        return _stress_decision_result(
            decision=ScientificDecision.DIRECTIONAL_INCONCLUSIVE,
            mean_retention=mean_retention,
            interval=interval,
            rationale=DecisionRationale(
                "absorption retention classification requires an available BCa interval with finite bounds "
                f"{range_text}"
            ),
        )
    lower = bounded_interval.lower_bound.value
    upper = bounded_interval.upper_bound.value
    if mean_retention.value >= protocol.full_retention_minimum.value and lower >= protocol.full_retention_minimum.value:
        return _stress_decision_result(
            decision=ScientificDecision.SUPPORTED,
            mean_retention=mean_retention,
            interval=interval,
            rationale=DecisionRationale(
                f"paired seed-level CV(FPR) retention remains at or above the full-retention threshold {range_text}"
            ),
        )
    if (
        mean_retention.value < protocol.partial_retention_minimum.value
        and upper < protocol.partial_retention_minimum.value
    ):
        return _stress_decision_result(
            decision=ScientificDecision.FULL_ABSORPTION,
            mean_retention=mean_retention,
            interval=interval,
            rationale=DecisionRationale(
                f"paired seed-level CV(FPR) retention lies below the partial-retention threshold {range_text}"
            ),
        )
    if (
        mean_retention.value >= protocol.partial_retention_minimum.value
        and lower >= protocol.partial_retention_minimum.value
        and upper < protocol.full_retention_minimum.value
    ):
        return _stress_decision_result(
            decision=ScientificDecision.PARTIAL_ABSORPTION,
            mean_retention=mean_retention,
            interval=interval,
            rationale=DecisionRationale(
                f"paired seed-level CV(FPR) retention is partially absorbed with residual effect {range_text}"
            ),
        )
    return _stress_decision_result(
        decision=ScientificDecision.DIRECTIONAL_INCONCLUSIVE,
        mean_retention=mean_retention,
        interval=interval,
        rationale=DecisionRationale(
            "absorption retention interval straddles declared retention boundaries and cannot support "
            f"a unique classification {range_text}"
        ),
    )

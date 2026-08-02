"""BCa paired bootstrap intervals, validation, and confirmatory decisions."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

import numpy as np
from scipy import stats

from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    FederatedThresholdMethod,
    IntervalMethod,
    MetricId,
    PopulationId,
    ScientificDecision,
)
from datp_core.domain.values import BootstrapReplicateCount, ConfidenceLevel, MetricValue, Seed
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.models import StatisticalInferenceProtocol
from datp_core.protocols.statistics import BOOTSTRAP_REPLICATE_COUNT
from datp_core.protocols.validation import CANONICAL_PROTOCOL_GRAPH


class BcaOutcome(StrEnum):
    AVAILABLE = "available"
    BLOCKED = "blocked"
    DEGENERATE = "degenerate"

    @property
    def availability_status(self) -> AvailabilityStatus:
        match self:
            case BcaOutcome.AVAILABLE:
                return AvailabilityStatus.AVAILABLE
            case BcaOutcome.BLOCKED:
                return AvailabilityStatus.UNAVAILABLE
            case BcaOutcome.DEGENERATE:
                return AvailabilityStatus.UNDEFINED

    @property
    def requires_point_estimate(self) -> bool:
        return self is not BcaOutcome.BLOCKED

    @property
    def supports_confirmatory_decision(self) -> bool:
        return self is BcaOutcome.AVAILABLE


class BcaReason(StrEnum):
    NONE = ""
    CANONICAL_PROTOCOL_MISMATCH = "canonical_protocol_mismatch"
    BOOTSTRAP_REPLICATE_COUNT_MISMATCH = "bootstrap_replicate_count_mismatch"
    DUPLICATE_SEED = "duplicate_seed"
    SEED_COHORT_MISMATCH = "seed_cohort_mismatch"
    CONFIRMATORY_ENDPOINT_MISMATCH = "confirmatory_endpoint_mismatch"
    FIXED_COORDINATE_MISMATCH = "fixed_coordinate_mismatch"
    IDENTICAL_PAIRED_DELTAS = "identical_paired_deltas"
    DEGENERATE_BOOTSTRAP_DISTRIBUTION = "degenerate_bootstrap_distribution"
    INFINITE_BIAS_CORRECTION = "infinite_bias_correction"
    UNDEFINED_ACCELERATION = "undefined_acceleration"
    INVALID_ADJUSTED_QUANTILES = "invalid_adjusted_quantiles"
    EXTERNAL_ANALYSIS_PLAN_MISMATCH = "external_analysis_plan_mismatch"
    EXTERNAL_SEED_COHORT_MISMATCH = "external_seed_cohort_mismatch"


class _ConfirmatoryContractError(ValueError):
    def __init__(self, reason: BcaReason) -> None:
        super().__init__(reason.value)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class _BootstrapDistribution: # TODO: move this to /home/naslouby/Projects/datp-core/src/datp_core/analysis/models.py and make public not private
    estimate: MetricValue
    paired_deltas: np.ndarray
    values: np.ndarray | None
    degeneracy_reason: BcaReason | None


@dataclass(frozen=True, slots=True)
class PairedContrast: # TODO: move this to /home/naslouby/Projects/datp-core/src/datp_core/analysis/models.py
    coordinate: FederatedTrainingCoordinate
    evidence_role: EvidenceRole
    seed: Seed
    metric: MetricId
    shared_method: FederatedThresholdMethod
    local_method: FederatedThresholdMethod
    shared_value: MetricValue
    local_value: MetricValue
    delta: MetricValue

    def __post_init__(self) -> None:
        if self.evidence_role is not EvidenceRole.CONFIRMATORY:
            raise ValueError("paired confirmatory contrasts require confirmatory evidence")
        if self.seed != self.coordinate.training_seed:
            raise ValueError("paired contrast seed must equal its coordinate seed")
        if self.shared_method is not FederatedThresholdMethod.SHARED_THRESHOLD:
            raise ValueError("paired contrast requires the shared-threshold method")
        if self.local_method is not FederatedThresholdMethod.LOCAL_THRESHOLD:
            raise ValueError("paired contrast requires the local-threshold method")
        if self.delta.value != self.shared_value.value - self.local_value.value:
            raise ValueError("paired contrast must preserve the exact shared-minus-local difference")


@dataclass(frozen=True, slots=True)
class ExternalPairedAnalysisPlan: # TODO: move this to /home/naslouby/Projects/datp-core/src/datp_core/analysis/models.py
    """Predeclared supplementary interval plan, intentionally separate from the endpoint."""

    population: PopulationId
    evidence_role: EvidenceRole
    metric: MetricId
    left_method: FederatedThresholdMethod
    right_method: FederatedThresholdMethod
    seed_cohort: tuple[Seed, ...]
    confidence_level: ConfidenceLevel

    def __post_init__(self) -> None:
        if self.evidence_role not in {
            EvidenceRole.EXTERNAL_VALIDATION,
            EvidenceRole.APPLICABILITY_BOUNDARY,
            EvidenceRole.TEMPORAL_BOUNDARY,
        }:
            raise ValueError("supplementary paired analysis requires external, applicability, or temporal evidence")
        if not self.seed_cohort or len(set(self.seed_cohort)) != len(self.seed_cohort):
            raise ValueError("external paired analysis requires a unique predeclared seed cohort")
        if self.left_method is self.right_method:
            raise ValueError("external paired analysis requires two distinct threshold methods")


@dataclass(frozen=True, slots=True)
class ExternalPairedContrast: # TODO: move this to /home/naslouby/Projects/datp-core/src/datp_core/analysis/models.py
    """A seed-level contrast that may inform supplementary external evidence only."""

    coordinate: FederatedTrainingCoordinate
    evidence_role: EvidenceRole
    seed: Seed
    metric: MetricId
    left_method: FederatedThresholdMethod
    right_method: FederatedThresholdMethod
    left_value: MetricValue
    right_value: MetricValue
    delta: MetricValue

    def __post_init__(self) -> None:
        if self.evidence_role not in {
            EvidenceRole.EXTERNAL_VALIDATION,
            EvidenceRole.APPLICABILITY_BOUNDARY,
            EvidenceRole.TEMPORAL_BOUNDARY,
        }:
            raise ValueError("external paired contrasts cannot carry confirmatory evidence")
        if self.seed != self.coordinate.training_seed:
            raise ValueError("external paired contrast seed must equal its coordinate seed")
        if self.delta.value != self.left_value.value - self.right_value.value:
            raise ValueError("external paired contrast must preserve the exact left-minus-right difference")


@dataclass(frozen=True, slots=True)
class BootstrapInterval: # TODO: move this to /home/naslouby/Projects/datp-core/src/datp_core/analysis/models.py
    method: IntervalMethod
    confidence_level: ConfidenceLevel
    replicate_count: BootstrapReplicateCount
    analysis_seed: Seed
    point_estimate: MetricValue | None
    lower_bound: MetricValue | None
    upper_bound: MetricValue | None
    bias_correction: float | None
    acceleration: float | None # TODO: make this a dataclass for acceleration in the codebase and see if it can be replaced with a more specific type
    availability: AvailabilityStatus
    outcome: BcaOutcome
    reason: BcaReason

    def __post_init__(self) -> None:
        bounds = self.lower_bound is not None and self.upper_bound is not None
        if (self.lower_bound is None) != (self.upper_bound is None):
            raise ValueError("bootstrap interval bounds must occur together")
        if self.outcome is BcaOutcome.AVAILABLE and (
            self.availability is not self.outcome.availability_status
            or self.point_estimate is None
            or not bounds
            or self.reason is not BcaReason.NONE
        ):
            raise ValueError("available BCa intervals require bounds and no reason")
        if self.outcome is BcaOutcome.BLOCKED and (
            self.availability is not self.outcome.availability_status or bounds or self.reason is BcaReason.NONE
        ):
            raise ValueError("blocked BCa intervals require a typed blocked reason and no bounds")
        if self.outcome is BcaOutcome.DEGENERATE and not self._is_degenerate(bounds):
            raise ValueError("degenerate BCa intervals require an estimate and typed reason")

    def _is_degenerate(self, bounds: bool) -> bool:
        return (
            self.availability is AvailabilityStatus.UNDEFINED
            and self.point_estimate is not None
            and not bounds
            and self.reason is not BcaReason.NONE
        )


@dataclass(frozen=True, slots=True)
class ScientificDecisionResult:
    evidence_role: EvidenceRole
    decision: ScientificDecision
    point_estimate: MetricValue | None
    interval: BootstrapInterval | None
    availability: AvailabilityStatus
    rationale: str


def validate_confirmatory_contrasts(
    contrasts: tuple[PairedContrast, ...], protocol: StatisticalInferenceProtocol
) -> tuple[PairedContrast, ...]:
    canonical = CANONICAL_PROTOCOL_GRAPH
    if protocol != canonical.confirmatory_inference:
        raise _ConfirmatoryContractError(BcaReason.CANONICAL_PROTOCOL_MISMATCH)
    endpoint = canonical.confirmatory_endpoint
    expected = endpoint.seed_cohort.values
    observed = tuple(item.seed for item in contrasts)
    if len(observed) != len(set(observed)):
        raise _ConfirmatoryContractError(BcaReason.DUPLICATE_SEED)
    if frozenset(observed) != frozenset(expected) or len(contrasts) != endpoint.seed_cohort.member_count.value:
        raise _ConfirmatoryContractError(BcaReason.SEED_COHORT_MISMATCH)
    baseline = contrasts[0].coordinate
    for item in contrasts:
        if (
            item.coordinate.population is not endpoint.population
            or item.coordinate.model is not endpoint.training_model
            or item.metric is not endpoint.metric
            or item.shared_method is not endpoint.shared_threshold
            or item.local_method is not endpoint.local_threshold
        ):
            raise _ConfirmatoryContractError(BcaReason.CONFIRMATORY_ENDPOINT_MISMATCH)
    for item in contrasts[1:]:
        coordinate = item.coordinate
        if (
            coordinate.population != baseline.population
            or coordinate.split_protocol != baseline.split_protocol
            or coordinate.preprocessing_identity != baseline.preprocessing_identity
            or coordinate.model != baseline.model
            or coordinate.model_coefficient != baseline.model_coefficient
        ):
            raise _ConfirmatoryContractError(BcaReason.FIXED_COORDINATE_MISMATCH)
    return tuple(sorted(contrasts, key=lambda item: item.seed.value))


def paired_bca_interval(
    contrasts: tuple[PairedContrast, ...],
    *,
    protocol: StatisticalInferenceProtocol,
    replicate_count: BootstrapReplicateCount,
    analysis_seed: Seed,
) -> BootstrapInterval:
    """Resample paired seed deltas only; no diagnostic interval can replace this result."""
    confidence_level = CANONICAL_PROTOCOL_GRAPH.confirmatory_inference.confidence_level
    if replicate_count != BOOTSTRAP_REPLICATE_COUNT:
        return _blocked_interval(
            _point_estimate_or_none(contrasts),
            confidence_level,
            replicate_count,
            analysis_seed,
            BcaReason.BOOTSTRAP_REPLICATE_COUNT_MISMATCH,
        )
    try:
        validated = validate_confirmatory_contrasts(contrasts, protocol)
    except _ConfirmatoryContractError as error:
        return _blocked_interval(
            _point_estimate_or_none(contrasts), confidence_level, replicate_count, analysis_seed, error.reason
        )
    return _construct_bca_interval(validated, confidence_level, replicate_count, analysis_seed)


def external_paired_bca_interval(
    contrasts: tuple[ExternalPairedContrast, ...],
    *,
    plan: ExternalPairedAnalysisPlan,
    replicate_count: BootstrapReplicateCount,
    analysis_seed: Seed,
) -> BootstrapInterval:
    """Supplementary paired BCa interval without a confirmatory decision pathway."""
    if replicate_count != BOOTSTRAP_REPLICATE_COUNT:
        return _blocked_interval(
            _point_estimate_or_none(contrasts),
            plan.confidence_level,
            replicate_count,
            analysis_seed,
            BcaReason.BOOTSTRAP_REPLICATE_COUNT_MISMATCH,
        )
    try:
        validated = validate_external_contrasts(contrasts, plan)
    except _ConfirmatoryContractError as error:
        return _blocked_interval(
            _point_estimate_or_none(contrasts),
            plan.confidence_level,
            replicate_count,
            analysis_seed,
            error.reason,
        )
    return _construct_bca_interval(validated, plan.confidence_level, replicate_count, analysis_seed)


def validate_external_contrasts(
    contrasts: tuple[ExternalPairedContrast, ...], plan: ExternalPairedAnalysisPlan
) -> tuple[ExternalPairedContrast, ...]:
    _require_external_seed_cohort(contrasts, plan)
    _require_external_plan_matches(contrasts, plan)
    _require_external_fixed_coordinate(contrasts)
    return tuple(sorted(contrasts, key=lambda item: item.seed.value))


def decide_confirmatory(interval: BootstrapInterval) -> ScientificDecisionResult:
    if (
        interval.availability is not AvailabilityStatus.AVAILABLE
        or interval.point_estimate is None
        or interval.lower_bound is None
        or interval.upper_bound is None
    ):
        return ScientificDecisionResult(
            EvidenceRole.CONFIRMATORY,
            ScientificDecision.BLOCKED,
            interval.point_estimate,
            interval,
            AvailabilityStatus.UNAVAILABLE,
            "confirmatory BCa interval is unavailable or degenerate",
        )
    if interval.lower_bound > 0:
        decision = ScientificDecision.SUPPORTED
        rationale = "the paired BCa interval supports lower CV(FPR) under local thresholds"
    elif interval.upper_bound < 0:
        decision = ScientificDecision.OPPOSITE_DIRECTION
        rationale = "the paired BCa interval supports the opposite direction"
    elif interval.point_estimate > 0:
        decision = ScientificDecision.DIRECTIONAL_INCONCLUSIVE
        rationale = "the point estimate is directional but the paired BCa interval crosses zero"
    else:
        decision = ScientificDecision.NO_OBSERVED_ADVANTAGE
        rationale = "the paired BCa interval crosses zero without a positive point estimate"
    return ScientificDecisionResult(
        EvidenceRole.CONFIRMATORY, decision, interval.point_estimate, interval, AvailabilityStatus.AVAILABLE, rationale
    )


def _require_external_seed_cohort(
    contrasts: tuple[ExternalPairedContrast, ...],
    plan: ExternalPairedAnalysisPlan,
) -> None:
    observed = tuple(item.seed for item in contrasts)
    if len(observed) != len(set(observed)):
        raise _ConfirmatoryContractError(BcaReason.DUPLICATE_SEED)
    if frozenset(observed) != frozenset(plan.seed_cohort) or len(contrasts) != len(plan.seed_cohort):
        raise _ConfirmatoryContractError(BcaReason.EXTERNAL_SEED_COHORT_MISMATCH)


def _require_external_plan_matches(
    contrasts: tuple[ExternalPairedContrast, ...],
    plan: ExternalPairedAnalysisPlan,
) -> None:
    for item in contrasts:
        if (
            item.coordinate.population is not plan.population
            or item.evidence_role is not plan.evidence_role
            or item.metric is not plan.metric
            or item.left_method is not plan.left_method
            or item.right_method is not plan.right_method
        ):
            raise _ConfirmatoryContractError(BcaReason.EXTERNAL_ANALYSIS_PLAN_MISMATCH)


def _require_external_fixed_coordinate(contrasts: tuple[ExternalPairedContrast, ...]) -> None:
    baseline = contrasts[0].coordinate
    for item in contrasts[1:]:
        coordinate = item.coordinate
        if (
            coordinate.population != baseline.population
            or coordinate.split_protocol != baseline.split_protocol
            or coordinate.preprocessing_identity != baseline.preprocessing_identity
            or coordinate.model != baseline.model
            or coordinate.model_coefficient != baseline.model_coefficient
        ):
            raise _ConfirmatoryContractError(BcaReason.FIXED_COORDINATE_MISMATCH)


def _construct_bca_interval(
    contrasts: tuple[PairedContrast, ...] | tuple[ExternalPairedContrast, ...],
    confidence_level: ConfidenceLevel,
    replicate_count: BootstrapReplicateCount,
    analysis_seed: Seed,
) -> BootstrapInterval:
    bootstrap = _bootstrap_distribution(contrasts, replicate_count, analysis_seed)
    if bootstrap.degeneracy_reason is not None:
        return _degenerate_interval(
            bootstrap.estimate, confidence_level, replicate_count, analysis_seed, bootstrap.degeneracy_reason
        )
    if bootstrap.values is None:
        raise RuntimeError("a non-degenerate bootstrap distribution must be present")
    interval = _bca_interval_from_distribution(
        bootstrap.estimate,
        bootstrap.paired_deltas,
        bootstrap.values,
        confidence_level,
    )
    if isinstance(interval, BcaReason):
        return _degenerate_interval(bootstrap.estimate, confidence_level, replicate_count, analysis_seed, interval)
    lower_bound, upper_bound, bias_correction, acceleration = interval
    return BootstrapInterval(
        IntervalMethod.BCA_PAIRED_ARITHMETIC_MEAN,
        confidence_level,
        replicate_count,
        analysis_seed,
        bootstrap.estimate,
        lower_bound,
        upper_bound,
        bias_correction,
        acceleration,
        AvailabilityStatus.AVAILABLE,
        BcaOutcome.AVAILABLE,
        BcaReason.NONE,
    )


def _bootstrap_distribution(
    contrasts: tuple[PairedContrast, ...] | tuple[ExternalPairedContrast, ...],
    replicate_count: BootstrapReplicateCount,
    analysis_seed: Seed,
) -> _BootstrapDistribution:
    deltas = _deltas(contrasts)
    estimate = MetricValue(float(np.mean(deltas)))
    if np.all(deltas == deltas[0]):
        return _BootstrapDistribution(estimate, deltas, None, BcaReason.IDENTICAL_PAIRED_DELTAS)
    generator = np.random.Generator(np.random.PCG64(analysis_seed.value))
    indexes = generator.integers(0, deltas.size, size=(replicate_count.value, deltas.size), endpoint=False)
    values = np.mean(deltas[indexes], axis=1)
    if np.all(values == values[0]):
        return _BootstrapDistribution(estimate, deltas, None, BcaReason.DEGENERATE_BOOTSTRAP_DISTRIBUTION)
    return _BootstrapDistribution(estimate, deltas, values, None)


def _bca_interval_from_distribution(
    estimate: MetricValue,
    deltas: np.ndarray,
    distribution: np.ndarray,
    confidence_level: ConfidenceLevel,
) -> tuple[MetricValue, MetricValue, float, float] | BcaReason:
    proportion_less = float(np.mean(distribution < estimate.value))
    if proportion_less <= 0 or proportion_less >= 1:
        return BcaReason.INFINITE_BIAS_CORRECTION
    bias_correction = float(stats.norm.ppf(proportion_less))
    acceleration = _jackknife_acceleration(deltas)
    if acceleration is None:
        return BcaReason.UNDEFINED_ACCELERATION
    alpha = (1 - confidence_level.value) / 2
    standard = np.asarray((stats.norm.ppf(alpha), stats.norm.ppf(1 - alpha)), dtype=np.float64)
    adjusted = stats.norm.cdf(
        bias_correction + (bias_correction + standard) / (1 - acceleration * (bias_correction + standard))
    )
    if np.any(~np.isfinite(adjusted)) or np.any((adjusted < 0) | (adjusted > 1)):
        return BcaReason.INVALID_ADJUSTED_QUANTILES
    bounds = np.quantile(distribution, adjusted, method="linear")
    return MetricValue(float(bounds[0])), MetricValue(float(bounds[1])), bias_correction, acceleration


def _jackknife_acceleration(deltas: np.ndarray) -> float | None:
    jackknife = np.asarray([float(np.mean(np.delete(deltas, index))) for index in range(deltas.size)], dtype=np.float64)
    centered = float(np.mean(jackknife)) - jackknife
    denominator = 6.0 * float(np.sum(centered**2) ** 1.5)
    if denominator == 0:
        return None
    return float(np.sum(centered**3) / denominator)


def _deltas(
    contrasts: tuple[PairedContrast, ...] | tuple[ExternalPairedContrast, ...],
) -> np.ndarray:
    values = tuple(item.delta.value for item in contrasts)
    if any(not isfinite(value) for value in values):
        raise ValueError("paired contrasts must be finite")
    return np.asarray(values, dtype=np.float64)


def _blocked_interval(
    point_estimate: MetricValue | None,
    confidence_level: ConfidenceLevel,
    replicate_count: BootstrapReplicateCount,
    analysis_seed: Seed,
    reason: BcaReason,
) -> BootstrapInterval:
    return BootstrapInterval(
        IntervalMethod.BCA_PAIRED_ARITHMETIC_MEAN,
        confidence_level,
        replicate_count,
        analysis_seed,
        point_estimate,
        None,
        None,
        None,
        None,
        AvailabilityStatus.UNAVAILABLE,
        BcaOutcome.BLOCKED,
        reason,
    )


def _degenerate_interval(
    point_estimate: MetricValue,
    confidence_level: ConfidenceLevel,
    replicate_count: BootstrapReplicateCount,
    analysis_seed: Seed,
    reason: BcaReason,
) -> BootstrapInterval:
    return BootstrapInterval(
        IntervalMethod.BCA_PAIRED_ARITHMETIC_MEAN,
        confidence_level,
        replicate_count,
        analysis_seed,
        point_estimate,
        None,
        None,
        None,
        None,
        AvailabilityStatus.UNDEFINED,
        BcaOutcome.DEGENERATE,
        reason,
    )


def _point_estimate_or_none(
    contrasts: tuple[PairedContrast, ...] | tuple[ExternalPairedContrast, ...],
) -> MetricValue | None:
    if not contrasts:
        return None
    return MetricValue(float(np.mean(_deltas(contrasts))))

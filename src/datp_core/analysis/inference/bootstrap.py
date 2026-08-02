from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import stats

from datp_core.analysis.models import (
    BcaAdjustment,
    BcaReason,
    BootstrapInterval,
    ExternalPairedAnalysisPlan,
    PairedContrasts,
    ScientificDecisionResult,
)
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    FederatedThresholdMethod,
    IntervalMethod,
    ScientificDecision,
)
from datp_core.domain.values import (
    BootstrapReplicateCount,
    ConfidenceLevel,
    MetricValue,
    Seed,
)
from datp_core.protocols.models import StatisticalInferenceProtocol
from datp_core.protocols.statistics import BOOTSTRAP_REPLICATE_COUNT
from datp_core.protocols.validation import CANONICAL_PROTOCOL_GRAPH

_INTERVAL_METHOD = IntervalMethod.BCA_PAIRED_ARITHMETIC_MEAN


class _ConfirmatoryContractError(ValueError):
    def __init__(self, reason: BcaReason) -> None:
        super().__init__(reason.value)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class _BootstrapDistribution:
    estimate: MetricValue
    paired_deltas: NDArray[np.float64]
    values: NDArray[np.float64] | None
    degeneracy_reason: BcaReason | None


def validate_confirmatory_contrasts(
    contrasts: PairedContrasts,
    protocol: StatisticalInferenceProtocol,
) -> PairedContrasts:
    canonical = CANONICAL_PROTOCOL_GRAPH
    if protocol != canonical.confirmatory_inference:
        raise _ConfirmatoryContractError(BcaReason.CANONICAL_PROTOCOL_MISMATCH)

    endpoint = canonical.confirmatory_endpoint
    observed_seeds = {c.seed for c in contrasts}

    if len(observed_seeds) != len(contrasts):
        raise _ConfirmatoryContractError(BcaReason.DUPLICATE_SEED)

    if tuple(sorted(c.seed.value for c in contrasts)) != tuple(
        sorted(s.value for s in endpoint.seed_cohort.values)
    ):
        raise _ConfirmatoryContractError(BcaReason.SEED_COHORT_MISMATCH)

    for c in contrasts:
        if (
            c.evidence_role is not EvidenceRole.CONFIRMATORY
            or c.coordinate.population is not endpoint.population
            or c.coordinate.model is not endpoint.training_model
            or c.metric is not endpoint.metric
            or c.left_method is not endpoint.shared_threshold
            or c.right_method is not endpoint.local_threshold
            or c.left_method is not FederatedThresholdMethod.SHARED_THRESHOLD
            or c.right_method is not FederatedThresholdMethod.LOCAL_THRESHOLD
        ):
            raise _ConfirmatoryContractError(BcaReason.CONFIRMATORY_ENDPOINT_MISMATCH)

    _require_fixed_coordinate(contrasts)
    return tuple(sorted(contrasts, key=lambda c: c.seed.value))


def validate_external_contrasts(
    contrasts: PairedContrasts,
    plan: ExternalPairedAnalysisPlan,
) -> PairedContrasts:
    observed_seeds = {c.seed for c in contrasts}

    if len(observed_seeds) != len(contrasts):
        raise _ConfirmatoryContractError(BcaReason.DUPLICATE_SEED)

    if tuple(sorted(c.seed.value for c in contrasts)) != tuple(sorted(s.value for s in plan.seed_cohort)):
        raise _ConfirmatoryContractError(BcaReason.EXTERNAL_SEED_COHORT_MISMATCH)

    for c in contrasts:
        if (
            c.coordinate.population is not plan.population
            or c.evidence_role is not plan.evidence_role
            or c.metric is not plan.metric
            or c.left_method is not plan.left_method
            or c.right_method is not plan.right_method
        ):
            raise _ConfirmatoryContractError(BcaReason.EXTERNAL_ANALYSIS_PLAN_MISMATCH)

    _require_fixed_coordinate(contrasts)
    return tuple(sorted(contrasts, key=lambda c: c.seed.value))


def paired_bca_interval(
    contrasts: PairedContrasts,
    *,
    protocol: StatisticalInferenceProtocol,
    replicate_count: BootstrapReplicateCount,
    analysis_seed: Seed,
) -> BootstrapInterval:
    confidence_level = CANONICAL_PROTOCOL_GRAPH.confirmatory_inference.confidence_level
    if replicate_count != BOOTSTRAP_REPLICATE_COUNT:
        return _blocked_interval(
            contrasts=contrasts,
            confidence_level=confidence_level,
            replicate_count=replicate_count,
            analysis_seed=analysis_seed,
            reason=BcaReason.BOOTSTRAP_REPLICATE_COUNT_MISMATCH,
        )

    try:
        validated = validate_confirmatory_contrasts(contrasts, protocol)
    except _ConfirmatoryContractError as error:
        return _blocked_interval(
            contrasts=contrasts,
            confidence_level=confidence_level,
            replicate_count=replicate_count,
            analysis_seed=analysis_seed,
            reason=error.reason,
        )

    return _construct_bca_interval(validated, confidence_level, replicate_count, analysis_seed)


def external_paired_bca_interval(
    contrasts: PairedContrasts,
    *,
    plan: ExternalPairedAnalysisPlan,
    replicate_count: BootstrapReplicateCount,
    analysis_seed: Seed,
) -> BootstrapInterval:
    if replicate_count != BOOTSTRAP_REPLICATE_COUNT:
        return _blocked_interval(
            contrasts=contrasts,
            confidence_level=plan.confidence_level,
            replicate_count=replicate_count,
            analysis_seed=analysis_seed,
            reason=BcaReason.BOOTSTRAP_REPLICATE_COUNT_MISMATCH,
        )

    try:
        validated = validate_external_contrasts(contrasts, plan)
    except _ConfirmatoryContractError as error:
        return _blocked_interval(
            contrasts=contrasts,
            confidence_level=plan.confidence_level,
            replicate_count=replicate_count,
            analysis_seed=analysis_seed,
            reason=error.reason,
        )

    return _construct_bca_interval(validated, plan.confidence_level, replicate_count, analysis_seed)


def decide_confirmatory(interval: BootstrapInterval) -> ScientificDecisionResult:
    if (
        interval.availability is not AvailabilityStatus.AVAILABLE
        or interval.point_estimate is None
        or interval.lower_bound is None
        or interval.upper_bound is None
    ):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.CONFIRMATORY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=interval.point_estimate,
            interval=interval,
            rationale="confirmatory BCa interval is unavailable or degenerate",
        )

    if interval.lower_bound.value > 0.0:
        decision = ScientificDecision.SUPPORTED
        rationale = "the paired BCa interval supports lower CV(FPR) under local thresholds"
    elif interval.upper_bound.value < 0.0:
        decision = ScientificDecision.OPPOSITE_DIRECTION
        rationale = "the paired BCa interval supports the opposite direction"
    elif interval.point_estimate.value > 0.0:
        decision = ScientificDecision.DIRECTIONAL_INCONCLUSIVE
        rationale = "the point estimate is directional but the paired BCa interval crosses zero"
    else:
        decision = ScientificDecision.NO_OBSERVED_ADVANTAGE
        rationale = "the paired BCa interval crosses zero without a positive point estimate"

    return ScientificDecisionResult(
        evidence_role=EvidenceRole.CONFIRMATORY,
        decision=decision,
        point_estimate=interval.point_estimate,
        interval=interval,
        rationale=rationale,
    )


def contrast_deltas(contrasts: PairedContrasts) -> NDArray[np.float64]:
    values = np.array([c.delta.value for c in contrasts], dtype=np.float64)
    if np.any(~np.isfinite(values)):
        raise ValueError("paired contrasts must be finite")
    return values


def _require_fixed_coordinate(contrasts: PairedContrasts) -> None:
    if not contrasts:
        raise _ConfirmatoryContractError(BcaReason.SEED_COHORT_MISMATCH)

    baseline = contrasts[0].coordinate
    for c in contrasts[1:]:
        if (
            c.coordinate.population != baseline.population
            or c.coordinate.split_protocol != baseline.split_protocol
            or c.coordinate.preprocessing_identity != baseline.preprocessing_identity
            or c.coordinate.model != baseline.model
            or c.coordinate.model_coefficient != baseline.model_coefficient
        ):
            raise _ConfirmatoryContractError(BcaReason.FIXED_COORDINATE_MISMATCH)


def _construct_bca_interval(
    contrasts: PairedContrasts,
    confidence_level: ConfidenceLevel,
    replicate_count: BootstrapReplicateCount,
    analysis_seed: Seed,
) -> BootstrapInterval:
    bootstrap = _bootstrap_distribution(contrasts, replicate_count, analysis_seed)
    
    if bootstrap.degeneracy_reason is not None:
        return BootstrapInterval.degenerate(
            method=_INTERVAL_METHOD,
            confidence_level=confidence_level,
            replicate_count=replicate_count,
            analysis_seed=analysis_seed,
            point_estimate=bootstrap.estimate,
            reason=bootstrap.degeneracy_reason,
        )
        
    if bootstrap.values is None:
        raise RuntimeError("non-degenerate bootstrap distribution is missing")

    interval = _bca_interval_from_distribution(
        estimate=bootstrap.estimate,
        deltas=bootstrap.paired_deltas,
        distribution=bootstrap.values,
        confidence_level=confidence_level,
    )

    if isinstance(interval, BcaReason):
        return BootstrapInterval.degenerate(
            method=_INTERVAL_METHOD,
            confidence_level=confidence_level,
            replicate_count=replicate_count,
            analysis_seed=analysis_seed,
            point_estimate=bootstrap.estimate,
            reason=interval,
        )

    lower_bound, upper_bound, adjustment = interval
    return BootstrapInterval.available(
        method=_INTERVAL_METHOD,
        confidence_level=confidence_level,
        replicate_count=replicate_count,
        analysis_seed=analysis_seed,
        point_estimate=bootstrap.estimate,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        adjustment=adjustment,
    )


def _bootstrap_distribution(
    contrasts: PairedContrasts,
    replicate_count: BootstrapReplicateCount,
    analysis_seed: Seed,
) -> _BootstrapDistribution:
    deltas = contrast_deltas(contrasts)
    if not deltas.size:
        raise ValueError("bootstrap requires at least one paired contrast")

    estimate = MetricValue(float(np.mean(deltas)))
    if np.ptp(deltas) <= 0.0:
        return _BootstrapDistribution(
            estimate=estimate,
            paired_deltas=deltas,
            values=None,
            degeneracy_reason=BcaReason.IDENTICAL_PAIRED_DELTAS,
        )

    rng = np.random.default_rng(analysis_seed.value)
    indexes = rng.integers(0, deltas.size, size=(replicate_count.value, deltas.size))
    values = np.mean(deltas[indexes], axis=1)

    if np.ptp(values) <= 0.0:
        return _BootstrapDistribution(
            estimate=estimate,
            paired_deltas=deltas,
            values=None,
            degeneracy_reason=BcaReason.DEGENERATE_BOOTSTRAP_DISTRIBUTION,
        )

    return _BootstrapDistribution(
        estimate=estimate,
        paired_deltas=deltas,
        values=values,
        degeneracy_reason=None,
    )


def _bca_interval_from_distribution(
    *,
    estimate: MetricValue,
    deltas: NDArray[np.float64],
    distribution: NDArray[np.float64],
    confidence_level: ConfidenceLevel,
) -> tuple[MetricValue, MetricValue, BcaAdjustment] | BcaReason:
    proportion_less = float(np.mean(distribution < estimate.value))
    if not 0.0 < proportion_less < 1.0:
        return BcaReason.INFINITE_BIAS_CORRECTION

    bias_correction = float(stats.norm.ppf(proportion_less))
    acceleration = _jackknife_acceleration(deltas)

    if acceleration is None:
        return BcaReason.UNDEFINED_ACCELERATION

    alpha = (1.0 - confidence_level.value) / 2.0
    standard_quantiles = np.array([stats.norm.ppf(alpha), stats.norm.ppf(1.0 - alpha)], dtype=np.float64)
    shifted = bias_correction + standard_quantiles
    denominator = 1.0 - acceleration * shifted

    if np.any(np.abs(denominator) <= np.finfo(np.float64).eps):
        return BcaReason.INVALID_ADJUSTED_QUANTILES

    adjusted_quantiles = stats.norm.cdf(bias_correction + shifted / denominator)
    if np.any(~np.isfinite(adjusted_quantiles)) or np.any((adjusted_quantiles < 0.0) | (adjusted_quantiles > 1.0)):
        return BcaReason.INVALID_ADJUSTED_QUANTILES

    bounds = np.quantile(distribution, adjusted_quantiles, method="linear")
    
    return (
        MetricValue(float(bounds[0])),
        MetricValue(float(bounds[1])),
        BcaAdjustment(bias_correction=bias_correction, acceleration=acceleration),
    )


def _jackknife_acceleration(deltas: NDArray[np.float64]) -> float | None:
    if deltas.size < 2:
        return None

    jackknife = (float(np.sum(deltas)) - deltas) / (deltas.size - 1)
    centered = float(np.mean(jackknife)) - jackknife
    squared_sum = float(np.sum(centered**2))
    
    if squared_sum <= 0.0:
        return None

    acceleration = float(np.sum(centered**3) / (6.0 * squared_sum**1.5))
    return acceleration if np.isfinite(acceleration) else None


def _blocked_interval(
    *,
    contrasts: PairedContrasts,
    confidence_level: ConfidenceLevel,
    replicate_count: BootstrapReplicateCount,
    analysis_seed: Seed,
    reason: BcaReason,
) -> BootstrapInterval:
    return BootstrapInterval.blocked(
        method=_INTERVAL_METHOD,
        confidence_level=confidence_level,
        replicate_count=replicate_count,
        analysis_seed=analysis_seed,
        point_estimate=_point_estimate_or_none(contrasts),
        reason=reason,
    )


def _point_estimate_or_none(contrasts: PairedContrasts) -> MetricValue | None:
    deltas = contrast_deltas(contrasts)
    return MetricValue(float(np.mean(deltas))) if deltas.size else None
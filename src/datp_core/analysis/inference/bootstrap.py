"""Paired BCa interval estimation under typed inference protocols."""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import stats

from datp_core.analysis.inference.paired import paired_deltas
from datp_core.analysis.models import (
    BcaAdjustment,
    BcaReason,
    BootstrapInterval,
    PairedContrasts,
    ScientificDecisionResult,
    SupplementaryPairedAnalysisPlan,
)
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole, FederatedThresholdMethod, ScientificDecision
from datp_core.domain.values import MetricValue, Seed
from datp_core.protocols.statistics import PairedInferenceProtocol
from datp_core.protocols.validation import CANONICAL_PROTOCOL_GRAPH


class _PairedAnalysisContractError(ValueError):
    def __init__(self, reason: BcaReason) -> None:
        super().__init__(reason.value)
        self.reason = reason


@dataclass(frozen=True, slots=True, eq=False)
class _BootstrapDistribution:
    estimate: MetricValue
    paired_deltas: NDArray[np.float64]
    values: NDArray[np.float64] | None
    degeneracy_reason: BcaReason | None


def validate_confirmatory_contrasts(
    contrasts: PairedContrasts,
    protocol: PairedInferenceProtocol,
) -> PairedContrasts:
    canonical = CANONICAL_PROTOCOL_GRAPH
    if protocol != canonical.confirmatory_inference:
        raise _PairedAnalysisContractError(BcaReason.CANONICAL_PROTOCOL_MISMATCH)
    endpoint = canonical.confirmatory_endpoint
    observed_seeds = {contrast.seed for contrast in contrasts}
    if len(observed_seeds) != len(contrasts):
        raise _PairedAnalysisContractError(BcaReason.DUPLICATE_SEED)
    if observed_seeds != set(endpoint.seed_cohort.values):
        raise _PairedAnalysisContractError(BcaReason.SEED_COHORT_MISMATCH)
    for contrast in contrasts:
        if (
            contrast.evidence_role is not EvidenceRole.CONFIRMATORY
            or contrast.coordinate.population is not endpoint.population
            or contrast.coordinate.model is not endpoint.training_model
            or contrast.metric is not endpoint.metric
            or contrast.left_method is not endpoint.shared_threshold
            or contrast.right_method is not endpoint.local_threshold
            or contrast.left_method is not FederatedThresholdMethod.SHARED_THRESHOLD
            or contrast.right_method is not FederatedThresholdMethod.LOCAL_THRESHOLD
        ):
            raise _PairedAnalysisContractError(BcaReason.CONFIRMATORY_ENDPOINT_MISMATCH)
    _require_fixed_design(contrasts)
    return tuple(sorted(contrasts, key=lambda contrast: contrast.seed.value))


def validate_supplementary_contrasts(
    contrasts: PairedContrasts,
    plan: SupplementaryPairedAnalysisPlan,
) -> PairedContrasts:
    observed_seeds = {contrast.seed for contrast in contrasts}
    if len(observed_seeds) != len(contrasts):
        raise _PairedAnalysisContractError(BcaReason.DUPLICATE_SEED)
    if observed_seeds != set(plan.seed_cohort.values):
        raise _PairedAnalysisContractError(BcaReason.SUPPLEMENTARY_SEED_COHORT_MISMATCH)
    for contrast in contrasts:
        if (
            contrast.coordinate.population is not plan.population
            or contrast.evidence_role is not plan.evidence_role
            or contrast.metric is not plan.metric
            or contrast.left_method is not plan.left_method
            or contrast.right_method is not plan.right_method
        ):
            raise _PairedAnalysisContractError(BcaReason.SUPPLEMENTARY_ANALYSIS_PLAN_MISMATCH)
    _require_fixed_design(contrasts)
    return tuple(sorted(contrasts, key=lambda contrast: contrast.seed.value))


def paired_bca_interval(
    contrasts: PairedContrasts,
    *,
    protocol: PairedInferenceProtocol,
    analysis_seed: Seed,
) -> BootstrapInterval:
    validated = _validate_or_block(
        contrasts,
        validator=lambda values: validate_confirmatory_contrasts(values, protocol),
        protocol=protocol,
        analysis_seed=analysis_seed,
    )
    return validated if isinstance(validated, BootstrapInterval) else _construct_bca_interval(validated, protocol, analysis_seed)


def supplementary_paired_bca_interval(
    contrasts: PairedContrasts,
    *,
    plan: SupplementaryPairedAnalysisPlan,
    analysis_seed: Seed,
) -> BootstrapInterval:
    protocol = plan.inference_protocol
    validated = _validate_or_block(
        contrasts,
        validator=lambda values: validate_supplementary_contrasts(values, plan),
        protocol=protocol,
        analysis_seed=analysis_seed,
    )
    return validated if isinstance(validated, BootstrapInterval) else _construct_bca_interval(validated, protocol, analysis_seed)


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


def _validate_or_block(
    contrasts: PairedContrasts,
    *,
    validator: Callable[[PairedContrasts], PairedContrasts],
    protocol: PairedInferenceProtocol,
    analysis_seed: Seed,
) -> PairedContrasts | BootstrapInterval:
    try:
        return validator(contrasts)
    except _PairedAnalysisContractError as error:
        return BootstrapInterval.blocked(
            protocol=protocol,
            analysis_seed=analysis_seed,
            point_estimate=_point_estimate_or_none(contrasts),
            reason=error.reason,
        )


def _require_fixed_design(contrasts: PairedContrasts) -> None:
    if not contrasts:
        raise _PairedAnalysisContractError(BcaReason.SEED_COHORT_MISMATCH)
    design = contrasts[0].design
    if any(contrast.design != design for contrast in contrasts[1:]):
        raise _PairedAnalysisContractError(BcaReason.FIXED_COORDINATE_MISMATCH)


def _construct_bca_interval(
    contrasts: PairedContrasts,
    protocol: PairedInferenceProtocol,
    analysis_seed: Seed,
) -> BootstrapInterval:
    bootstrap = _bootstrap_distribution(contrasts, protocol, analysis_seed)
    if bootstrap.degeneracy_reason is not None:
        return BootstrapInterval.degenerate(
            protocol=protocol,
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
        confidence_level=protocol.confidence_level.value,
    )
    if isinstance(interval, BcaReason):
        return BootstrapInterval.degenerate(
            protocol=protocol,
            analysis_seed=analysis_seed,
            point_estimate=bootstrap.estimate,
            reason=interval,
        )
    lower_bound, upper_bound, adjustment = interval
    return BootstrapInterval.available(
        protocol=protocol,
        analysis_seed=analysis_seed,
        point_estimate=bootstrap.estimate,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        adjustment=adjustment,
    )


def _bootstrap_distribution(
    contrasts: PairedContrasts,
    protocol: PairedInferenceProtocol,
    analysis_seed: Seed,
) -> _BootstrapDistribution:
    deltas = paired_deltas(contrasts)
    if not deltas.size:
        raise ValueError("bootstrap requires at least one paired contrast")
    estimate = MetricValue(float(np.mean(deltas)))
    if np.ptp(deltas) <= 0.0:
        return _BootstrapDistribution(estimate, deltas, None, BcaReason.IDENTICAL_PAIRED_DELTAS)
    rng = np.random.default_rng(analysis_seed.value)
    indexes = rng.integers(0, deltas.size, size=(protocol.bootstrap_replicates.value, deltas.size))
    values = np.mean(deltas[indexes], axis=1)
    if np.ptp(values) <= 0.0:
        return _BootstrapDistribution(estimate, deltas, None, BcaReason.DEGENERATE_BOOTSTRAP_DISTRIBUTION)
    return _BootstrapDistribution(estimate, deltas, values, None)


def _bca_interval_from_distribution(
    *,
    estimate: MetricValue,
    deltas: NDArray[np.float64],
    distribution: NDArray[np.float64],
    confidence_level: float,
) -> tuple[MetricValue, MetricValue, BcaAdjustment] | BcaReason:
    proportion_less = float(np.mean(distribution < estimate.value))
    if not 0.0 < proportion_less < 1.0:
        return BcaReason.INFINITE_BIAS_CORRECTION
    bias_correction = float(stats.norm.ppf(proportion_less))
    acceleration = _jackknife_acceleration(deltas)
    if acceleration is None:
        return BcaReason.UNDEFINED_ACCELERATION
    alpha = (1.0 - confidence_level) / 2.0
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
        BcaAdjustment(bias_correction=MetricValue(bias_correction), acceleration=MetricValue(acceleration)),
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


def _point_estimate_or_none(contrasts: PairedContrasts) -> MetricValue | None:
    deltas = paired_deltas(contrasts)
    return MetricValue(float(np.mean(deltas))) if deltas.size else None

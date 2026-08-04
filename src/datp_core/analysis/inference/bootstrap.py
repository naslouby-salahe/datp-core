"""Paired BCa interval estimation under typed inference protocols."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from numpy.typing import NDArray
from pydantic import model_validator
from scipy import stats

from datp_core.analysis.contrasts import (
    PairedContrasts,
    SupplementaryPairedAnalysisPlan,
)
from datp_core.analysis.inference.wilcoxon import paired_deltas
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    FederatedThresholdMethod,
    IntervalMethod,
)
from datp_core.domain.values import (
    BootstrapReplicateCount,
    ConfidenceLevel,
    MetricValue,
    Seed,
)
from datp_core.protocols.statistics import PairedInferenceProtocol
from datp_core.protocols.validation import CANONICAL_PROTOCOL_GRAPH


class BcaOutcome(StrEnum):
    AVAILABLE = "available"
    BLOCKED = "blocked"
    DEGENERATE = "degenerate"

    @property
    def availability(self) -> AvailabilityStatus:
        match self:
            case BcaOutcome.AVAILABLE:
                return AvailabilityStatus.AVAILABLE
            case BcaOutcome.BLOCKED:
                return AvailabilityStatus.UNAVAILABLE
            case BcaOutcome.DEGENERATE:
                return AvailabilityStatus.UNDEFINED


class BcaReason(StrEnum):
    CANONICAL_PROTOCOL_MISMATCH = "canonical_protocol_mismatch"
    DUPLICATE_SEED = "duplicate_seed"
    SEED_COHORT_MISMATCH = "seed_cohort_mismatch"
    CONFIRMATORY_ENDPOINT_MISMATCH = "confirmatory_endpoint_mismatch"
    FIXED_COORDINATE_MISMATCH = "fixed_coordinate_mismatch"
    IDENTICAL_PAIRED_DELTAS = "identical_paired_deltas"
    DEGENERATE_BOOTSTRAP_DISTRIBUTION = "degenerate_bootstrap_distribution"
    INFINITE_BIAS_CORRECTION = "infinite_bias_correction"
    UNDEFINED_ACCELERATION = "undefined_acceleration"
    INVALID_ADJUSTED_QUANTILES = "invalid_adjusted_quantiles"
    SUPPLEMENTARY_ANALYSIS_PLAN_MISMATCH = "supplementary_analysis_plan_mismatch"
    SUPPLEMENTARY_SEED_COHORT_MISMATCH = "supplementary_seed_cohort_mismatch"


class BcaAdjustment(StrictModel):
    bias_correction: MetricValue
    acceleration: MetricValue


class BootstrapInterval(StrictModel):
    method: IntervalMethod
    confidence_level: ConfidenceLevel
    replicate_count: BootstrapReplicateCount
    analysis_seed: Seed
    point_estimate: MetricValue | None
    lower_bound: MetricValue | None
    upper_bound: MetricValue | None
    adjustment: BcaAdjustment | None
    outcome: BcaOutcome
    reason: BcaReason | None

    @model_validator(mode="after")
    def validate_interval(self) -> "BootstrapInterval":
        bounds_present = self.lower_bound is not None and self.upper_bound is not None
        if (self.lower_bound is None) != (self.upper_bound is None):
            raise ValueError("bootstrap interval bounds must occur together")
        if bounds_present and self.lower_bound is not None and self.upper_bound is not None:
            if self.lower_bound.value > self.upper_bound.value:
                raise ValueError(
                    "bootstrap interval lower bound cannot exceed upper bound"
                )
        match self.outcome:
            case BcaOutcome.AVAILABLE:
                valid = (
                    self.point_estimate is not None
                    and bounds_present
                    and self.adjustment is not None
                    and self.reason is None
                )
            case BcaOutcome.BLOCKED:
                valid = (
                    not bounds_present
                    and self.adjustment is None
                    and self.reason is not None
                )
            case BcaOutcome.DEGENERATE:
                valid = (
                    self.point_estimate is not None
                    and not bounds_present
                    and self.adjustment is None
                    and self.reason is not None
                )
        if not valid:
            raise ValueError(f"invalid {self.outcome.value} BCa interval state")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        return self.outcome.availability

    @classmethod
    def available(
        cls,
        *,
        protocol: PairedInferenceProtocol,
        analysis_seed: Seed,
        point_estimate: MetricValue,
        lower_bound: MetricValue,
        upper_bound: MetricValue,
        adjustment: BcaAdjustment,
    ) -> "BootstrapInterval":
        return cls(
            method=protocol.interval_method,
            confidence_level=protocol.confidence_level,
            replicate_count=protocol.bootstrap_replicates,
            analysis_seed=analysis_seed,
            point_estimate=point_estimate,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            adjustment=adjustment,
            outcome=BcaOutcome.AVAILABLE,
            reason=None,
        )

    @classmethod
    def blocked(
        cls,
        *,
        protocol: PairedInferenceProtocol,
        analysis_seed: Seed,
        point_estimate: MetricValue | None,
        reason: BcaReason,
    ) -> "BootstrapInterval":
        return cls(
            method=protocol.interval_method,
            confidence_level=protocol.confidence_level,
            replicate_count=protocol.bootstrap_replicates,
            analysis_seed=analysis_seed,
            point_estimate=point_estimate,
            lower_bound=None,
            upper_bound=None,
            adjustment=None,
            outcome=BcaOutcome.BLOCKED,
            reason=reason,
        )

    @classmethod
    def degenerate(
        cls,
        *,
        protocol: PairedInferenceProtocol,
        analysis_seed: Seed,
        point_estimate: MetricValue,
        reason: BcaReason,
    ) -> "BootstrapInterval":
        return cls(
            method=protocol.interval_method,
            confidence_level=protocol.confidence_level,
            replicate_count=protocol.bootstrap_replicates,
            analysis_seed=analysis_seed,
            point_estimate=point_estimate,
            lower_bound=None,
            upper_bound=None,
            adjustment=None,
            outcome=BcaOutcome.DEGENERATE,
            reason=reason,
        )


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
            raise _PairedAnalysisContractError(
                BcaReason.CONFIRMATORY_ENDPOINT_MISMATCH
            )
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
        raise _PairedAnalysisContractError(
            BcaReason.SUPPLEMENTARY_SEED_COHORT_MISMATCH
        )
    for contrast in contrasts:
        if (
            contrast.coordinate.population is not plan.population
            or contrast.evidence_role is not plan.evidence_role
            or contrast.metric is not plan.metric
            or contrast.left_method is not plan.left_method
            or contrast.right_method is not plan.right_method
        ):
            raise _PairedAnalysisContractError(
                BcaReason.SUPPLEMENTARY_ANALYSIS_PLAN_MISMATCH
            )
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
    return (
        validated
        if isinstance(validated, BootstrapInterval)
        else _construct_bca_interval(validated, protocol, analysis_seed)
    )


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
    return (
        validated
        if isinstance(validated, BootstrapInterval)
        else _construct_bca_interval(validated, protocol, analysis_seed)
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
        return _BootstrapDistribution(
            estimate,
            deltas,
            None,
            BcaReason.IDENTICAL_PAIRED_DELTAS,
        )
    rng = np.random.default_rng(analysis_seed.value)
    indexes = rng.integers(
        0,
        deltas.size,
        size=(protocol.bootstrap_replicates.value, deltas.size),
    )
    values = np.mean(deltas[indexes], axis=1)
    if np.ptp(values) <= 0.0:
        return _BootstrapDistribution(
            estimate,
            deltas,
            None,
            BcaReason.DEGENERATE_BOOTSTRAP_DISTRIBUTION,
        )
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
    standard_quantiles = np.array(
        [stats.norm.ppf(alpha), stats.norm.ppf(1.0 - alpha)],
        dtype=np.float64,
    )
    shifted = bias_correction + standard_quantiles
    denominator = 1.0 - acceleration * shifted
    if np.any(np.abs(denominator) <= np.finfo(np.float64).eps):
        return BcaReason.INVALID_ADJUSTED_QUANTILES
    adjusted_quantiles = stats.norm.cdf(bias_correction + shifted / denominator)
    if np.any(~np.isfinite(adjusted_quantiles)) or np.any(
        (adjusted_quantiles < 0.0) | (adjusted_quantiles > 1.0)
    ):
        return BcaReason.INVALID_ADJUSTED_QUANTILES
    bounds = np.quantile(distribution, adjusted_quantiles, method="linear")
    return (
        MetricValue(float(bounds[0])),
        MetricValue(float(bounds[1])),
        BcaAdjustment(
            bias_correction=MetricValue(bias_correction),
            acceleration=MetricValue(acceleration),
        ),
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

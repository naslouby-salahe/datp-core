"""Numerical paired BCa interval estimation."""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import stats

from datp_core.analysis.contrasts import PairedContrasts, SupplementaryPairedAnalysisPlan
from datp_core.analysis.inference.bootstrap.contracts import (
    BcaAdjustment,
    BcaReason,
    BootstrapInterval,
)
from datp_core.analysis.inference.bootstrap.validation import (
    PairedAnalysisContractError,
    validate_confirmatory_contrasts,
    validate_supplementary_contrasts,
)
from datp_core.analysis.inference.wilcoxon import paired_deltas
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import ConfidenceLevel, MetricValue
from datp_core.protocols.statistics import PairedInferenceProtocol


@dataclass(frozen=True, slots=True, eq=False)
class BootstrapDistribution:
    estimate: MetricValue
    paired_deltas: NDArray[np.float64]
    values: NDArray[np.float64] | None
    degeneracy_reason: BcaReason | None


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
    except PairedAnalysisContractError as error:
        return BootstrapInterval.blocked(
            protocol=protocol,
            analysis_seed=analysis_seed,
            point_estimate=_point_estimate_or_none(contrasts),
            reason=error.reason,
        )


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
        confidence_level=protocol.confidence_level,
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
) -> BootstrapDistribution:
    deltas = paired_deltas(contrasts)
    if not deltas.size:
        raise ValueError("bootstrap requires at least one paired contrast")
    estimate = MetricValue(float(np.mean(deltas)))
    if np.ptp(deltas) <= 0.0:
        return BootstrapDistribution(
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
        return BootstrapDistribution(
            estimate,
            deltas,
            None,
            BcaReason.DEGENERATE_BOOTSTRAP_DISTRIBUTION,
        )
    return BootstrapDistribution(estimate, deltas, values, None)


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
    standard_quantiles = np.array(
        [stats.norm.ppf(alpha), stats.norm.ppf(1.0 - alpha)],
        dtype=np.float64,
    )
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

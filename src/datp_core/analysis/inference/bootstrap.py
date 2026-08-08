"""Generic paired BCa contracts, validation, and numerical estimation."""

from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from numpy.typing import NDArray
from pydantic import model_validator
from scipy import stats

from datp_core.analysis.inference.contrasts import FixedScorePairProvenance, PairedContrasts
from datp_core.analysis.inference.wilcoxon import PairedInferenceProtocol, paired_deltas
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import AvailabilityStatus, IntervalMethod
from datp_core.core.numeric import BootstrapReplicateCount, ConfidenceLevel, MetricValue, Seed


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
    EMPTY_CONTRASTS = "empty_contrasts"
    PAIR_COUNT_MISMATCH = "pair_count_mismatch"
    DUPLICATE_SEED = "duplicate_seed"
    FIXED_DESIGN_MISMATCH = "fixed_design_mismatch"
    PAIRED_METHOD_MISMATCH = "paired_method_mismatch"
    INCOMPLETE_FIXED_SCORE_PROVENANCE = "incomplete_fixed_score_provenance"
    IDENTICAL_PAIRED_DELTAS = "identical_paired_deltas"
    DEGENERATE_BOOTSTRAP_DISTRIBUTION = "degenerate_bootstrap_distribution"
    INFINITE_BIAS_CORRECTION = "infinite_bias_correction"
    UNDEFINED_ACCELERATION = "undefined_acceleration"
    INVALID_ADJUSTED_QUANTILES = "invalid_adjusted_quantiles"
    NONFINITE_SERIES = "nonfinite_series"


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
                raise ValueError("bootstrap interval lower bound cannot exceed upper bound")
        match self.outcome:
            case BcaOutcome.AVAILABLE:
                valid = (
                    self.point_estimate is not None
                    and bounds_present
                    and self.adjustment is not None
                    and self.reason is None
                )
            case BcaOutcome.BLOCKED:
                valid = not bounds_present and self.adjustment is None and self.reason is not None
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
    reason = validate_paired_design(contrasts, protocol)
    if reason is not None:
        return BootstrapInterval.blocked(
            protocol=protocol,
            analysis_seed=analysis_seed,
            point_estimate=_point_estimate_or_none(contrasts),
            reason=reason,
        )
    return _construct_bca_interval(contrasts, protocol, analysis_seed)


def validate_paired_design(
    contrasts: PairedContrasts,
    protocol: PairedInferenceProtocol,
) -> BcaReason | None:
    if not contrasts:
        return BcaReason.EMPTY_CONTRASTS
    if len(contrasts) != protocol.paired_seed_count.value:
        return BcaReason.PAIR_COUNT_MISMATCH
    seeds = tuple(contrast.seed for contrast in contrasts)
    if len(frozenset(seeds)) != len(seeds):
        return BcaReason.DUPLICATE_SEED
    design = contrasts[0].design
    if any(contrast.design != design for contrast in contrasts[1:]):
        return BcaReason.FIXED_DESIGN_MISMATCH
    method_pair = (contrasts[0].left_method, contrasts[0].right_method)
    if any((contrast.left_method, contrast.right_method) != method_pair for contrast in contrasts[1:]):
        return BcaReason.PAIRED_METHOD_MISMATCH
    if any(not _complete_fixed_score(contrast.fixed_score) for contrast in contrasts):
        return BcaReason.INCOMPLETE_FIXED_SCORE_PROVENANCE
    return None


def _complete_fixed_score(provenance: FixedScorePairProvenance) -> bool:
    checksums = (
        provenance.model_checksum,
        provenance.preprocessing_checksum,
        provenance.selected_checkpoint_checksum,
        provenance.split_manifest_checksum,
        provenance.calibration_score_checksum,
        provenance.evaluation_score_checksum,
        provenance.evaluation_label_checksum,
        provenance.source_row_checksum,
        provenance.score_order_checksum,
        provenance.client_inventory_checksum,
        provenance.eligibility_cohort_checksum,
    )
    return all(checksum.value for checksum in checksums)


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
    estimate = MetricValue(float(np.mean(deltas)))
    if np.ptp(deltas) <= 0.0:
        return BootstrapDistribution(
            estimate=estimate,
            paired_deltas=deltas,
            values=None,
            degeneracy_reason=BcaReason.IDENTICAL_PAIRED_DELTAS,
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
            estimate=estimate,
            paired_deltas=deltas,
            values=None,
            degeneracy_reason=BcaReason.DEGENERATE_BOOTSTRAP_DISTRIBUTION,
        )
    return BootstrapDistribution(
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
    standard_quantiles = np.array(
        [stats.norm.ppf(alpha), stats.norm.ppf(1.0 - alpha)],
        dtype=np.float64,
    )
    shifted = bias_correction + standard_quantiles
    denominator = 1.0 - acceleration * shifted
    if np.any(np.abs(denominator) <= np.finfo(np.float64).eps):
        return BcaReason.INVALID_ADJUSTED_QUANTILES
    adjusted_quantiles = np.asarray(
        stats.norm.cdf(bias_correction + shifted / denominator),
        dtype=np.float64,
    )
    if np.any(~np.isfinite(adjusted_quantiles)) or np.any((adjusted_quantiles < 0.0) | (adjusted_quantiles > 1.0)):
        return BcaReason.INVALID_ADJUSTED_QUANTILES
    lower = float(np.quantile(distribution, float(adjusted_quantiles[0]), method="linear"))
    upper = float(np.quantile(distribution, float(adjusted_quantiles[1]), method="linear"))
    return (
        MetricValue(lower),
        MetricValue(upper),
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
    if not contrasts:
        return None
    deltas = paired_deltas(contrasts)
    return MetricValue(float(np.mean(deltas))) if deltas.size else None


def seed_level_bca_interval(
    values: tuple[MetricValue, ...],
    *,
    protocol: PairedInferenceProtocol,
    analysis_seed: Seed,
    require_declared_count: bool = True,
) -> BootstrapInterval:
    if not values:
        return BootstrapInterval.blocked(
            protocol=protocol,
            analysis_seed=analysis_seed,
            point_estimate=None,
            reason=BcaReason.EMPTY_CONTRASTS,
        )
    point_estimate = MetricValue(float(np.mean(tuple(item.value for item in values))))
    if require_declared_count and len(values) != protocol.paired_seed_count.value:
        return BootstrapInterval.blocked(
            protocol=protocol,
            analysis_seed=analysis_seed,
            point_estimate=point_estimate,
            reason=BcaReason.PAIR_COUNT_MISMATCH,
        )
    array = np.fromiter((item.value for item in values), dtype=np.float64, count=len(values))
    if np.any(~np.isfinite(array)):
        return BootstrapInterval.blocked(
            protocol=protocol,
            analysis_seed=analysis_seed,
            point_estimate=None,
            reason=BcaReason.NONFINITE_SERIES,
        )
    if array.size < 2 or np.ptp(array) <= 0.0:
        return BootstrapInterval.degenerate(
            protocol=protocol,
            analysis_seed=analysis_seed,
            point_estimate=point_estimate,
            reason=BcaReason.IDENTICAL_PAIRED_DELTAS,
        )
    rng = np.random.default_rng(analysis_seed.value)
    indexes = rng.integers(0, array.size, size=(protocol.bootstrap_replicates.value, array.size))
    distribution = np.mean(array[indexes], axis=1)
    if np.ptp(distribution) <= 0.0:
        return BootstrapInterval.degenerate(
            protocol=protocol,
            analysis_seed=analysis_seed,
            point_estimate=point_estimate,
            reason=BcaReason.DEGENERATE_BOOTSTRAP_DISTRIBUTION,
        )
    interval = _bca_interval_from_distribution(
        estimate=point_estimate,
        deltas=array,
        distribution=distribution,
        confidence_level=protocol.confidence_level,
    )
    if isinstance(interval, BcaReason):
        return BootstrapInterval.degenerate(
            protocol=protocol,
            analysis_seed=analysis_seed,
            point_estimate=point_estimate,
            reason=interval,
        )
    lower_bound, upper_bound, adjustment = interval
    return BootstrapInterval.available(
        protocol=protocol,
        analysis_seed=analysis_seed,
        point_estimate=point_estimate,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        adjustment=adjustment,
    )

from dataclasses import dataclass
from math import isfinite
from typing import Protocol

import numpy as np
from scipy import stats
from scipy.spatial.distance import jensenshannon

from datp_core.application.ports.statistics import RunStatisticalAnalysisRequest, StatisticalProcedureRunner
from datp_core.domain.errors import StatisticsError
from datp_core.domain.evaluation.alert_burden import BootstrapResampleCount
from datp_core.domain.evaluation.statistical_results import (
    BootstrapIntervalOutcome,
    ClaimOutcome,
    CliffsDeltaResult,
    ConfidenceLevel,
    ConfirmatoryAnalysisResult,
    DegenerateBootstrapIntervalResult,
    PairedDeltaResult,
    StatisticalAnalysisResult,
    StatisticalMethod,
    ValidBootstrapIntervalResult,
    WilcoxonSignedRankResult,
)
from datp_core.domain.mathematics.effect_sizes import cliffs_delta
from datp_core.domain.runtime.seeds import Seed

_MINIMUM_BCA_SAMPLE_SIZE = 3
_MINIMUM_BCA_RESAMPLES = 2


@dataclass(frozen=True, slots=True, kw_only=True)
class BcaBootstrapRequest:
    values: tuple[float, ...]
    confidence: ConfidenceLevel
    resamples: BootstrapResampleCount
    bootstrap_seed: Seed


@dataclass(frozen=True, slots=True, kw_only=True)
class WilcoxonRequest:
    first: tuple[float, ...]
    second: tuple[float, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class SpearmanRequest:
    first: tuple[float, ...]
    second: tuple[float, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class SpearmanCorrelationResult:
    statistic: float
    p_value: float


@dataclass(frozen=True, slots=True, kw_only=True)
class JensenShannonRequest:
    first: tuple[float, ...]
    second: tuple[float, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class JensenShannonResult:
    value: float


@dataclass(frozen=True, slots=True, kw_only=True)
class CliffsDeltaRequest:
    first: tuple[float, ...]
    second: tuple[float, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class StatisticalInput:
    paired_delta: PairedDeltaResult
    bootstrap_seed: Seed


class StatisticalInputReader(Protocol):
    def read(self, request: RunStatisticalAnalysisRequest) -> StatisticalInput: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class SciPyStatisticsAdapter:
    def bca_bootstrap(self, request: BcaBootstrapRequest) -> BootstrapIntervalOutcome:
        if not request.values:
            raise _statistics_error(method="bca_bootstrap", sample_size=0, cause="non_empty_sample_required")
        if _bca_is_degenerate(request):
            return _degenerate_interval(request=request, reason=_bca_degeneracy_reason(request))
        try:
            result = stats.bootstrap(
                (np.asarray(request.values, dtype=np.float64),),
                np.mean,
                n_resamples=request.resamples.value,
                confidence_level=float(request.confidence.value),
                method="BCa",
                rng=np.random.default_rng(request.bootstrap_seed.value),
            )
        except (ArithmeticError, ValueError) as error:
            return _degenerate_interval(request=request, reason=f"scipy_bca_unavailable:{type(error).__name__}")
        interval = result.confidence_interval
        lower = float(interval.low)
        upper = float(interval.high)
        point_estimate = float(np.mean(np.asarray(request.values, dtype=np.float64)))
        if not all(isfinite(value) for value in (point_estimate, lower, upper)):
            return _degenerate_interval(request=request, reason="scipy_bca_non_finite_interval")
        if not lower <= point_estimate <= upper:
            return _degenerate_interval(request=request, reason="scipy_bca_excludes_point_estimate")
        return ValidBootstrapIntervalResult(
            method=StatisticalMethod.BCA_BOOTSTRAP,
            point_estimate=point_estimate,
            lower=lower,
            upper=upper,
            confidence=request.confidence,
            resamples=request.resamples,
        )

    def wilcoxon(self, request: WilcoxonRequest) -> WilcoxonSignedRankResult:
        _require_paired_finite(first=request.first, second=request.second, method="wilcoxon")
        try:
            result = stats.wilcoxon(request.first, request.second)
        except ValueError as error:
            raise _statistics_error(
                method="wilcoxon", sample_size=len(request.first), cause=type(error).__name__
            ) from error
        return WilcoxonSignedRankResult(statistic=float(result.statistic), p_value=float(result.pvalue))

    def spearman(self, request: SpearmanRequest) -> SpearmanCorrelationResult:
        _require_paired_finite(first=request.first, second=request.second, method="spearman")
        try:
            result = stats.spearmanr(request.first, request.second)
        except ValueError as error:
            raise _statistics_error(
                method="spearman", sample_size=len(request.first), cause=type(error).__name__
            ) from error
        if not all(isfinite(value) for value in (float(result.statistic), float(result.pvalue))):
            raise _statistics_error(method="spearman", sample_size=len(request.first), cause="non_finite_result")
        return SpearmanCorrelationResult(statistic=float(result.statistic), p_value=float(result.pvalue))

    def jensen_shannon(self, request: JensenShannonRequest) -> JensenShannonResult:
        _require_distribution(first=request.first, second=request.second)
        try:
            value = float(jensenshannon(request.first, request.second))
        except ValueError as error:
            raise _statistics_error(
                method="jensen_shannon", sample_size=len(request.first), cause=type(error).__name__
            ) from error
        if not isfinite(value):
            raise _statistics_error(method="jensen_shannon", sample_size=len(request.first), cause="non_finite_result")
        return JensenShannonResult(value=value)

    def cliffs_delta(self, request: CliffsDeltaRequest) -> CliffsDeltaResult:
        return CliffsDeltaResult(value=cliffs_delta(sample_a=request.first, sample_b=request.second))


@dataclass(frozen=True, slots=True, kw_only=True)
class SciPyStatisticalProcedureRunner(StatisticalProcedureRunner):
    adapter: SciPyStatisticsAdapter
    inputs: StatisticalInputReader

    def run(self, request: RunStatisticalAnalysisRequest) -> StatisticalAnalysisResult:
        if request.analysis.method is not StatisticalMethod.BCA_BOOTSTRAP:
            raise _statistics_error(
                method=request.analysis.method.value,
                sample_size=request.analysis.paired_seed_count,
                cause="requires_procedure_specific_adapter_method",
            )
        statistical_input = self.inputs.read(request)
        interval = self.adapter.bca_bootstrap(
            BcaBootstrapRequest(
                values=statistical_input.paired_delta.per_seed_delta,
                confidence=request.analysis.confidence,
                resamples=request.analysis.resamples,
                bootstrap_seed=statistical_input.bootstrap_seed,
            )
        )
        return ConfirmatoryAnalysisResult(paired=statistical_input.paired_delta, interval=interval)


def _bca_is_degenerate(request: BcaBootstrapRequest) -> bool:
    return (
        len(request.values) < _MINIMUM_BCA_SAMPLE_SIZE
        or request.resamples.value < _MINIMUM_BCA_RESAMPLES
        or not _has_finite_values(request.values)
        or len(set(request.values)) < 2
    )


def _bca_degeneracy_reason(request: BcaBootstrapRequest) -> str:
    if len(request.values) < _MINIMUM_BCA_SAMPLE_SIZE:
        return "sample_size_below_bca_minimum"
    if request.resamples.value < _MINIMUM_BCA_RESAMPLES:
        return "resamples_below_bca_minimum"
    if not _has_finite_values(request.values):
        return "non_finite_input"
    return "constant_input"


def _degenerate_interval(*, request: BcaBootstrapRequest, reason: str) -> DegenerateBootstrapIntervalResult:
    point_estimate = _mean_if_finite(request.values)
    return DegenerateBootstrapIntervalResult(
        method=StatisticalMethod.BCA_BOOTSTRAP,
        sample_size=len(request.values),
        degeneracy_reason=reason,
        attempted_resamples=request.resamples,
        available_point_estimate=point_estimate,
        wording_outcome=ClaimOutcome.MIXED,
    )


def _mean_if_finite(values: tuple[float, ...]) -> float | None:
    if not values or not _has_finite_values(values):
        return None
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def _require_paired_finite(*, first: tuple[float, ...], second: tuple[float, ...], method: str) -> None:
    if len(first) != len(second):
        raise _statistics_error(method=method, sample_size=len(first), cause="finite_equal_length_samples_required")
    _require_non_empty_finite(values=first, method=method, cause="finite_equal_length_samples_required")
    _require_non_empty_finite(values=second, method=method, cause="finite_equal_length_samples_required")


def _require_distribution(*, first: tuple[float, ...], second: tuple[float, ...]) -> None:
    cause = "finite_positive_mass_equal_length_distributions_required"
    if len(first) != len(second):
        raise _statistics_error(
            method="jensen_shannon",
            sample_size=len(first),
            cause=cause,
        )
    _require_non_empty_finite(values=first, method="jensen_shannon", cause=cause)
    _require_non_empty_finite(values=second, method="jensen_shannon", cause=cause)
    _require_non_negative_mass(values=first, cause=cause)
    _require_non_negative_mass(values=second, cause=cause)


def _require_non_empty_finite(*, values: tuple[float, ...], method: str, cause: str) -> None:
    if not _has_finite_values(values):
        raise _statistics_error(method=method, sample_size=len(values), cause=cause)


def _require_non_negative_mass(*, values: tuple[float, ...], cause: str) -> None:
    if any(value < 0 for value in values):
        raise _statistics_error(method="jensen_shannon", sample_size=len(values), cause=cause)
    if sum(values) == 0:
        raise _statistics_error(method="jensen_shannon", sample_size=len(values), cause=cause)


def _has_finite_values(values: tuple[float, ...]) -> bool:
    return bool(values) and all(isfinite(value) for value in values)


def _statistics_error(*, method: str, sample_size: int, cause: str) -> StatisticsError:
    return StatisticsError(
        detail="statistical procedure could not produce a valid result",
        method=method,
        sample_size=sample_size,
        cause=cause,
    )

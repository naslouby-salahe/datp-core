"""Quantile computation and shared/pooled/weighted/local/conformal/shrinkage estimators."""

from __future__ import annotations

import math

import numpy as np

from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.core.numbers import Probability, linear_quantile
from datp_core.thresholding.enums import ThresholdDiagnosticsKind, ThresholdPolicyKind, ThresholdScope
from datp_core.thresholding.models import (
    BenignCalibrationScores,
    CalibrationFallbackDiagnostics,
    ConformalDiagnostics,
    InsufficientCalibrationError,
    NonFiniteCalibrationError,
    ShrinkageDiagnostics,
    ThresholdConfigurationError,
    ThresholdRecord,
    ThresholdSet,
)


def quantile(values: tuple[float, ...], target_quantile: float) -> float:
    """Linear-interpolated order-statistic quantile."""
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0 or not np.all(np.isfinite(array)):
        raise NonFiniteCalibrationError("Threshold construction requires finite non-empty calibration scores")
    result = linear_quantile(values, target_quantile)
    if not math.isfinite(result):
        raise NonFiniteCalibrationError("Threshold construction produced a non-finite quantile")
    return result


def _local_quantiles(
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
) -> dict[str, float]:
    return {item.client_id.value: quantile(item.values, target_quantile.value) for item in calibration}


def estimate_shared_mean(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
) -> ThresholdSet:
    local = _local_quantiles(calibration, target_quantile)
    shared = float(np.mean(tuple(local.values())))
    return ThresholdSet(
        policy_id=policy_id,
        policy_kind=ThresholdPolicyKind.SHARED_MEAN,
        scope=ThresholdScope.SHARED,
        target_quantile=target_quantile,
        values=tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=shared,
                policy_kind=ThresholdPolicyKind.SHARED_MEAN,
                scope=ThresholdScope.SHARED,
            )
            for item in calibration
        ),
    )


def estimate_pooled(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
) -> ThresholdSet:
    pooled = tuple(value for item in calibration for value in item.values)
    threshold = quantile(pooled, target_quantile.value)
    return ThresholdSet(
        policy_id=policy_id,
        policy_kind=ThresholdPolicyKind.SHARED_POOLED,
        scope=ThresholdScope.SHARED,
        target_quantile=target_quantile,
        values=tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=threshold,
                policy_kind=ThresholdPolicyKind.SHARED_POOLED,
                scope=ThresholdScope.SHARED,
            )
            for item in calibration
        ),
    )


def estimate_shared_weighted(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
) -> ThresholdSet:
    local = _local_quantiles(calibration, target_quantile)
    count = sum(len(item.values) for item in calibration)
    if count == 0:
        raise InsufficientCalibrationError("Weighted threshold has no calibration rows")
    threshold = sum(len(item.values) * local[item.client_id.value] for item in calibration) / count
    return ThresholdSet(
        policy_id=policy_id,
        policy_kind=ThresholdPolicyKind.SHARED_WEIGHTED,
        scope=ThresholdScope.SHARED,
        target_quantile=target_quantile,
        values=tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=threshold,
                policy_kind=ThresholdPolicyKind.SHARED_WEIGHTED,
                scope=ThresholdScope.SHARED,
            )
            for item in calibration
        ),
    )


def estimate_local_quantile(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
) -> ThresholdSet:
    local = _local_quantiles(calibration, target_quantile)
    return ThresholdSet(
        policy_id=policy_id,
        policy_kind=ThresholdPolicyKind.LOCAL_QUANTILE,
        scope=ThresholdScope.CLIENT,
        target_quantile=target_quantile,
        values=tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=local[item.client_id.value],
                policy_kind=ThresholdPolicyKind.LOCAL_QUANTILE,
                scope=ThresholdScope.CLIENT,
            )
            for item in calibration
        ),
    )


def estimate_conformal(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    coverage_alpha: float,
    minimum_sample_count: int,
) -> ThresholdSet:
    nominal_coverage = 1.0 - coverage_alpha
    thresholds: dict[str, float] = {}
    ranks: dict[str, int] = {}
    for item in calibration:
        scores = np.sort(np.asarray(item.values, dtype=np.float64))
        if len(scores) < minimum_sample_count:
            raise InsufficientCalibrationError(
                f"Client '{item.client_id.value}' has {len(scores)} calibration rows, "
                f"needs at least {minimum_sample_count} for conformal rank"
            )
        rank = min(math.ceil((len(scores) + 1) * (1.0 - coverage_alpha)), len(scores))
        thresholds[item.client_id.value] = float(scores[rank - 1])
        ranks[item.client_id.value] = rank
    diagnostics = ConformalDiagnostics(
        kind=ThresholdDiagnosticsKind.CONFORMAL,
        ranks=tuple((cid, r) for cid, r in ranks.items()),
        coverage_alpha=coverage_alpha,
    )
    return ThresholdSet(
        policy_id=policy_id,
        policy_kind=ThresholdPolicyKind.CONFORMAL,
        scope=ThresholdScope.CLIENT,
        target_quantile=Probability(nominal_coverage),
        diagnostics=diagnostics,
        values=tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=thresholds[item.client_id.value],
                policy_kind=ThresholdPolicyKind.CONFORMAL,
                scope=ThresholdScope.CLIENT,
                finite_sample_rank=ranks[item.client_id.value],
            )
            for item in calibration
        ),
    )


def estimate_shrinkage(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
    coefficient: float,
) -> ThresholdSet:
    if not 0.0 <= coefficient <= 1.0:
        raise ThresholdConfigurationError("Shrinkage coefficient is outside the permitted range [0.0, 1.0]")
    local = _local_quantiles(calibration, target_quantile)
    shared = float(np.mean(tuple(local.values())))
    thresholds = {key: coefficient * value + (1.0 - coefficient) * shared for key, value in local.items()}
    diagnostics = ShrinkageDiagnostics(
        kind=ThresholdDiagnosticsKind.SHRINKAGE,
        effective_lambdas=tuple((cid, coefficient) for cid in local),
    )
    return ThresholdSet(
        policy_id=policy_id,
        policy_kind=ThresholdPolicyKind.SHRINKAGE,
        scope=ThresholdScope.CLIENT,
        target_quantile=target_quantile,
        diagnostics=diagnostics,
        values=tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=thresholds[item.client_id.value],
                policy_kind=ThresholdPolicyKind.SHRINKAGE,
                scope=ThresholdScope.CLIENT,
                effective_lambda=coefficient,
            )
            for item in calibration
        ),
    )


def estimate_calibration_fallback(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
    n_half: int,
) -> ThresholdSet:
    if n_half <= 0:
        raise ThresholdConfigurationError("Fallback threshold policy requires a positive n_half")
    local = _local_quantiles(calibration, target_quantile)
    shared = float(np.mean(tuple(local.values())))
    lambdas = {item.client_id.value: len(item.values) / (len(item.values) + n_half) for item in calibration}
    thresholds = {
        item.client_id.value: lambdas[item.client_id.value] * local[item.client_id.value]
        + (1.0 - lambdas[item.client_id.value]) * shared
        for item in calibration
    }
    diagnostics = CalibrationFallbackDiagnostics(
        kind=ThresholdDiagnosticsKind.CALIBRATION_FALLBACK,
        effective_lambdas=tuple((cid, lam) for cid, lam in lambdas.items()),
        n_half=n_half,
        calibration_counts=tuple((item.client_id.value, len(item.values)) for item in calibration),
    )
    return ThresholdSet(
        policy_id=policy_id,
        policy_kind=ThresholdPolicyKind.CALIBRATION_FALLBACK,
        scope=ThresholdScope.CLIENT,
        target_quantile=target_quantile,
        diagnostics=diagnostics,
        values=tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=thresholds[item.client_id.value],
                policy_kind=ThresholdPolicyKind.CALIBRATION_FALLBACK,
                scope=ThresholdScope.CLIENT,
                effective_lambda=lambdas[item.client_id.value],
            )
            for item in calibration
        ),
    )

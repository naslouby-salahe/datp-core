"""Quantile computation and shared/pooled/weighted/local/conformal/shrinkage estimators."""

from __future__ import annotations

import math

import numpy as np

from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.core.numbers import Probability, linear_quantile
from datp_core.thresholding.enums import ThresholdPolicyKind, ThresholdScope
from datp_core.thresholding.models import (
    BenignCalibrationScores,
    CalibrationFallbackDiagnostics,
    ConformalDiagnostics,
    InsufficientCalibrationError,
    NonFiniteCalibrationError,
    ShrinkageDiagnostics,
    ThresholdDiagnostics,
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


def _policy_quantile(policy: object) -> Probability:
    """Extract the effective target quantile from a policy."""
    if hasattr(policy, "coverage_alpha"):
        return Probability(float(getattr(policy, "nominal_coverage", 1.0 - policy.coverage_alpha)))
    if hasattr(policy, "quantile"):
        return Probability(float(policy.quantile))
    raise ValueError("Policy has no quantile or coverage field")


def _build_threshold_set(
    policy_id: ThresholdPolicyId,
    policy_kind: ThresholdPolicyKind,
    scope: ThresholdScope,
    calibration: tuple[BenignCalibrationScores, ...],
    thresholds: dict[str, float],
    target_quantile: Probability,
    *,
    effective_lambdas: dict[str, float] | None = None,
    cluster_labels: dict[str, int] | None = None,
    conformal_ranks: dict[str, int] | None = None,
    diagnostics: ThresholdDiagnostics | None = None,
) -> ThresholdSet:
    return ThresholdSet(
        policy_id=policy_id,
        policy_kind=policy_kind,
        scope=scope,
        target_quantile=target_quantile,
        diagnostics=diagnostics,
        values=tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=thresholds[item.client_id.value],
                policy_kind=policy_kind,
                scope=scope,
                effective_lambda=(None if effective_lambdas is None else effective_lambdas.get(item.client_id.value)),
                cluster_label=(None if cluster_labels is None else cluster_labels.get(item.client_id.value)),
                finite_sample_rank=(None if conformal_ranks is None else conformal_ranks.get(item.client_id.value)),
            )
            for item in calibration
        ),
    )


# ── Shared mean ────────────────────────────────────────────────────────────


def estimate_shared_mean(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
) -> ThresholdSet:
    local = _local_quantiles(calibration, target_quantile)
    shared = float(np.mean(tuple(local.values())))
    return _build_threshold_set(
        policy_id,
        ThresholdPolicyKind.SHARED_MEAN,
        ThresholdScope.SHARED,
        calibration,
        dict.fromkeys(local, shared),
        target_quantile,
    )


# ── Pooled ─────────────────────────────────────────────────────────────────


def estimate_pooled(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
) -> ThresholdSet:
    local = _local_quantiles(calibration, target_quantile)
    pooled = tuple(value for item in calibration for value in item.values)
    threshold = quantile(pooled, target_quantile.value)
    return _build_threshold_set(
        policy_id,
        ThresholdPolicyKind.SHARED_POOLED,
        ThresholdScope.SHARED,
        calibration,
        {k: threshold for k in local},
        target_quantile,
    )


# ── Weighted ───────────────────────────────────────────────────────────────


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
    return _build_threshold_set(
        policy_id,
        ThresholdPolicyKind.SHARED_WEIGHTED,
        ThresholdScope.SHARED,
        calibration,
        dict.fromkeys(local, threshold),
        target_quantile,
    )


# ── Local ──────────────────────────────────────────────────────────────────


def estimate_local_quantile(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
) -> ThresholdSet:
    local = _local_quantiles(calibration, target_quantile)
    return _build_threshold_set(
        policy_id,
        ThresholdPolicyKind.LOCAL_QUANTILE,
        ThresholdScope.CLIENT,
        calibration,
        local,
        target_quantile,
    )


# ── Conformal ──────────────────────────────────────────────────────────────


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
        ranks=tuple((cid, r) for cid, r in ranks.items()),
        coverage_alpha=coverage_alpha,
    )
    return _build_threshold_set(
        policy_id,
        ThresholdPolicyKind.CONFORMAL,
        ThresholdScope.CLIENT,
        calibration,
        thresholds,
        Probability(nominal_coverage),
        conformal_ranks=ranks,
        diagnostics=diagnostics,
    )


# ── Shrinkage ──────────────────────────────────────────────────────────────


def estimate_shrinkage(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
    coefficient: float,
) -> ThresholdSet:
    if not 0.0 <= coefficient <= 1.0:
        raise ValueError("Shrinkage coefficient is outside the permitted range [0.0, 1.0]")
    local = _local_quantiles(calibration, target_quantile)
    shared = float(np.mean(tuple(local.values())))
    thresholds = {key: coefficient * value + (1.0 - coefficient) * shared for key, value in local.items()}
    diagnostics = ShrinkageDiagnostics(
        effective_lambdas=tuple((cid, coefficient) for cid in local),
    )
    return _build_threshold_set(
        policy_id,
        ThresholdPolicyKind.SHRINKAGE,
        ThresholdScope.CLIENT,
        calibration,
        thresholds,
        target_quantile,
        effective_lambdas=dict.fromkeys(local, coefficient),
        diagnostics=diagnostics,
    )


# ── Calibration fallback ───────────────────────────────────────────────────


def estimate_calibration_fallback(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
    n_half: int,
) -> ThresholdSet:
    if n_half <= 0:
        raise ValueError("Fallback threshold policy requires a positive n_half")
    local = _local_quantiles(calibration, target_quantile)
    shared = float(np.mean(tuple(local.values())))
    lambdas = {item.client_id.value: len(item.values) / (len(item.values) + n_half) for item in calibration}
    thresholds = {
        item.client_id.value: lambdas[item.client_id.value] * local[item.client_id.value]
        + (1.0 - lambdas[item.client_id.value]) * shared
        for item in calibration
    }
    diagnostics = CalibrationFallbackDiagnostics(
        effective_lambdas=tuple((cid, lam) for cid, lam in lambdas.items()),
        n_half=n_half,
        calibration_counts=tuple((item.client_id.value, len(item.values)) for item in calibration),
    )
    return _build_threshold_set(
        policy_id,
        ThresholdPolicyKind.CALIBRATION_FALLBACK,
        ThresholdScope.CLIENT,
        calibration,
        thresholds,
        target_quantile,
        effective_lambdas=lambdas,
        diagnostics=diagnostics,
    )

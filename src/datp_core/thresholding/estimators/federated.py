"""Federated summary-statistic threshold estimators.

Each client contributes only aggregate summaries (count, sum, squared sum,
per-candidate exceedance counts). The server aggregates these summaries
without ever pooling raw client scores.
"""

from __future__ import annotations

import math

import numpy as np

from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.core.numbers import Probability
from datp_core.thresholding.enums import ThresholdPolicyKind, ThresholdScope
from datp_core.thresholding.models import (
    BenignCalibrationScores,
    FederatedFixedDiagnostics,
    FederatedMatchedDiagnostics,
    InsufficientCalibrationError,
    ThresholdingError,
    ThresholdRecord,
    ThresholdSet,
)


def federated_moments(
    calibration: tuple[BenignCalibrationScores, ...],
) -> tuple[float, float]:
    """Compute pooled mean and standard deviation from client-level summaries.

    Uses the standard federated decomposition:
        μ = Σ(n_k · μ_k) / Σ n_k
        σ² = Σ(n_k · σ²_k) / Σ n_k  +  Σ(n_k · (μ_k − μ)²) / Σ n_k
            └────── within ──────┘     └──────── between ─────────┘
    """
    counts = np.asarray([len(item.values) for item in calibration], dtype=np.float64)
    means = np.asarray([np.mean(item.values) for item in calibration], dtype=np.float64)
    variances = np.asarray([np.var(item.values) for item in calibration], dtype=np.float64)
    total = float(np.sum(counts))
    if total <= 0.0:
        raise InsufficientCalibrationError("Federated summary threshold has no calibration rows")
    mean = float(np.sum(counts * means) / total)
    variance = float(np.sum(counts * variances) / total + np.sum(counts * (means - mean) ** 2) / total)
    return mean, math.sqrt(variance)


def _build_candidate_grid(minimum: float, maximum: float, step: float) -> np.ndarray:
    """Construct deterministic candidate grid without floating-point drift."""
    num_steps = round((maximum - minimum) / step)
    return np.linspace(minimum, maximum, num_steps + 1, dtype=np.float64)


def estimate_federated_matched(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
    *,
    grid_minimum: float,
    grid_maximum: float,
    grid_step: float,
) -> ThresholdSet:
    """Matched-exceedance: select coefficient k* minimizing |achieved − target|.

    Each client's exceedance count per candidate is aggregated server-side.
    Raw scores are never pooled into a single array.
    """
    if grid_step <= 0.0:
        raise ThresholdingError("Candidate grid step must be positive")
    if grid_minimum >= grid_maximum:
        raise ThresholdingError("Candidate grid minimum must be less than maximum")

    mean, standard_deviation = federated_moments(calibration)
    if standard_deviation <= 0.0:
        raise ThresholdingError(
            "Federated pooled standard deviation is zero or negative; cannot construct candidate thresholds"
        )

    candidates = _build_candidate_grid(grid_minimum, grid_maximum, grid_step)
    target = 1.0 - target_quantile.value

    # Aggregate per-client exceedance counts — no raw-score pooling
    total_rows = sum(len(item.values) for item in calibration)
    exceedance_counts = np.zeros(len(candidates), dtype=np.float64)
    for item in calibration:
        client_scores = np.asarray(item.values, dtype=np.float64)
        for i, candidate in enumerate(candidates):
            threshold = mean + float(candidate) * standard_deviation
            exceedance_counts[i] += float(np.sum(client_scores > threshold))

    achieved = exceedance_counts / total_rows
    deviation = np.abs(achieved - target)
    min_deviation = np.min(deviation)
    winner_idx = int(np.flatnonzero(deviation == min_deviation)[-1])
    winner = float(candidates[winner_idx])

    threshold = mean + winner * standard_deviation
    diagnostics = FederatedMatchedDiagnostics(
        selected_coefficient=winner,
        candidate_grid_minimum=grid_minimum,
        candidate_grid_maximum=grid_maximum,
        candidate_grid_step=grid_step,
        pooled_mean=float(mean),
        pooled_standard_deviation=float(standard_deviation),
        achieved_exceedance=tuple((float(c), float(a)) for c, a in zip(candidates, achieved, strict=True)),
        tie_set=tuple(float(candidates[i]) for i in np.flatnonzero(deviation == min_deviation)),
    )
    return ThresholdSet(
        policy_id=policy_id,
        policy_kind=ThresholdPolicyKind.FEDERATED_MATCHED,
        scope=ThresholdScope.SHARED,
        target_quantile=target_quantile,
        values=tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=threshold,
                policy_kind=ThresholdPolicyKind.FEDERATED_MATCHED,
                scope=ThresholdScope.SHARED,
            )
            for item in calibration
        ),
        diagnostics=diagnostics,
    )


def estimate_federated_fixed(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
    coefficient: float,
) -> ThresholdSet:
    """Fixed-coefficient federated threshold: τ = μ + k · σ."""
    mean, standard_deviation = federated_moments(calibration)
    threshold = mean + coefficient * standard_deviation
    diagnostics = FederatedFixedDiagnostics(
        coefficient=coefficient,
        pooled_mean=float(mean),
        pooled_standard_deviation=float(standard_deviation),
    )
    return ThresholdSet(
        policy_id=policy_id,
        policy_kind=ThresholdPolicyKind.FEDERATED_FIXED,
        scope=ThresholdScope.SHARED,
        target_quantile=target_quantile,
        values=tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=threshold,
                policy_kind=ThresholdPolicyKind.FEDERATED_FIXED,
                scope=ThresholdScope.SHARED,
            )
            for item in calibration
        ),
        diagnostics=diagnostics,
    )

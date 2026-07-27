"""FPR dispersion, AUROC invariance, pairwise JS divergence, calibration variance."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from math import isfinite, sqrt
from statistics import mean

import polars as pl
from scipy.spatial.distance import jensenshannon

from datp_core.core.identifiers import ClientId
from datp_core.core.numbers import linear_quantile
from datp_core.evaluation.enums import MetricStatus
from datp_core.evaluation.models import FprDispersion, MetricValue, QuantileVarianceTerms


def calculate_fpr_dispersion(
    values: Iterable[float],
    *,
    cv_instability_threshold: float,
    ddof: int = 0,
) -> FprDispersion:
    fprs = tuple(values)
    if not fprs:
        unavailable = MetricValue.unavailable(MetricStatus.UNDEFINED_ZERO_DENOMINATOR)
        return FprDispersion(
            mean_fpr=unavailable,
            standard_deviation=unavailable,
            coefficient_of_variation=unavailable,
            iqr=unavailable,
            value_range=unavailable,
            worst_fpr=unavailable,
        )
    if cv_instability_threshold <= 0.0:
        raise ValueError("cv_instability_threshold must be positive")
    if any(not isfinite(value) for value in fprs):
        raise ValueError("FPR values must be finite")
    if any(value < 0.0 or value > 1.0 for value in fprs):
        raise ValueError("FPR values must be in [0, 1]")
    average = mean(fprs)
    n = len(fprs)
    if not (0 <= ddof < n):
        raise ValueError(f"ddof must satisfy 0 <= ddof < n, got ddof={ddof} with n={n}")
    variance = sum((value - average) ** 2 for value in fprs) / (n - ddof)
    if variance < 0.0:
        raise ValueError(f"Negative variance computed with ddof={ddof}")
    standard_deviation = sqrt(variance)
    q25 = linear_quantile(fprs, 0.25)
    q75 = linear_quantile(fprs, 0.75)
    if math.isclose(average, 0.0, abs_tol=0.0):
        cv = MetricValue.unavailable(MetricStatus.UNDEFINED_ZERO_DENOMINATOR)
    elif average < cv_instability_threshold:
        cv = MetricValue(value=standard_deviation / average, status=MetricStatus.UNDEFINED_NEAR_ZERO_DENOMINATOR)
    else:
        cv = MetricValue.available(standard_deviation / average)
    return FprDispersion(
        mean_fpr=MetricValue.available(average),
        standard_deviation=MetricValue.available(standard_deviation),
        coefficient_of_variation=cv,
        iqr=MetricValue.available(q75 - q25),
        value_range=MetricValue.available(max(fprs) - min(fprs)),
        worst_fpr=MetricValue.available(max(fprs)),
    )


def assert_auroc_invariant(values: Iterable[float], *, tolerance: float) -> None:
    scores = tuple(values)
    if tolerance < 0.0:
        raise ValueError("tolerance must be non-negative")
    if scores and max(scores) - min(scores) > tolerance:
        raise ValueError("AUROC must be invariant across fixed-score threshold policies")


def calculate_pairwise_js_divergence(
    client_scores: Sequence[tuple[ClientId, tuple[float, ...]]],
    *,
    histogram_bins: int,
    logarithm_base: int,
) -> float:
    if histogram_bins < 1 or logarithm_base < 2:
        raise ValueError("Pairwise JS divergence requires configured positive bins and logarithm base >= 2")
    if len(client_scores) < 2:
        raise ValueError("Pairwise JS divergence requires at least two clients")
    if any(not scores for _, scores in client_scores):
        raise ValueError("Pairwise JS divergence requires non-empty benign score distributions")
    values = tuple(score for _, scores in client_scores for score in scores)
    if not all(isfinite(score) and score >= 0.0 for score in values):
        raise ValueError("Pairwise JS divergence requires finite non-negative scores")
    lower, upper = min(values), max(values)

    def histogram(scores: tuple[float, ...]) -> tuple[float, ...]:
        counts = [0] * histogram_bins
        for score in scores:
            index = (
                0
                if lower == upper
                else min(int((score - lower) / (upper - lower) * histogram_bins), histogram_bins - 1)
            )
            counts[index] += 1
        return tuple(count / len(scores) for count in counts)

    distributions = tuple(histogram(scores) for _, scores in client_scores)
    divergences: list[float] = []
    for left_index, left in enumerate(distributions):
        for right in distributions[left_index + 1 :]:
            distance = jensenshannon(left, right, base=float(logarithm_base))
            if distance is None:
                raise ValueError("JS distance computation returned None")
            divergences.append(float(distance) ** 2)
    return mean(divergences)


def calculate_calibration_variance(calibration: pl.DataFrame, *, ddof: int = 0) -> QuantileVarianceTerms:
    if calibration.height == 0:
        raise ValueError("Calibration variance requires calibration scores")
    if "score" not in calibration.columns or "client_id" not in calibration.columns:
        raise ValueError("Calibration variance requires score and client_id columns")
    if ddof < 0:
        raise ValueError(f"ddof must be non-negative, got {ddof}")
    scores_col = calibration["score"]
    if scores_col.is_null().any() or scores_col.is_nan().any() or scores_col.is_infinite().any():
        raise ValueError("Calibration scores must be finite")
    pooled_mean = scores_col.mean()
    group_stats = calibration.group_by("client_id").agg(
        pl.len().alias("count"),
        pl.col("score").mean().alias("mean"),
        pl.col("score").var(ddof=ddof).alias("variance"),
    )
    insufficient = group_stats.filter(pl.col("count") <= ddof)
    if insufficient.height > 0:
        raise ValueError(
            f"Insufficient rows for ddof={ddof}: "
            f"{[(r['client_id'], r['count']) for r in insufficient.iter_rows(named=True)]}"
        )
    total_count = float(group_stats["count"].sum())
    within = float((group_stats["count"] * group_stats["variance"]).sum()) / total_count
    between = float((group_stats["count"] * (group_stats["mean"] - pooled_mean) ** 2).sum()) / total_count
    total = within + between
    between_ratio: float | None
    if total > 0.0 and math.isfinite(total):
        between_ratio = between / total
    else:
        between_ratio = None
    return QuantileVarianceTerms(
        within_term=within,
        between_term=between,
        between_ratio=between_ratio,
    )

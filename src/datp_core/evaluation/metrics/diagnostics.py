"""FPR dispersion, AUROC invariance, and pairwise JS divergence."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from math import isfinite, log, sqrt
from statistics import mean

from datp_core.core.identifiers import ClientId
from datp_core.core.numbers import linear_quantile
from datp_core.evaluation.metrics.models import FprDispersion, MetricStatus, MetricValue


def calculate_fpr_dispersion(values: Iterable[float], *, cv_instability_threshold: float) -> FprDispersion:
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
    if any(value < 0.0 or value > 1.0 for value in fprs):
        raise ValueError("FPR values must be in [0, 1]")
    average = mean(fprs)
    standard_deviation = sqrt(sum((value - average) ** 2 for value in fprs) / len(fprs))
    q25 = linear_quantile(fprs, 0.25)
    q75 = linear_quantile(fprs, 0.75)
    if math.isclose(average, 0.0, abs_tol=0.0):
        cv = MetricValue.unavailable(MetricStatus.UNDEFINED_ZERO_DENOMINATOR)
    elif average < cv_instability_threshold:
        cv = MetricValue(value=standard_deviation / average, status=MetricStatus.UNDEFINED_NEAR_ZERO_DENOMINATOR)
    else:
        cv = MetricValue.available(standard_deviation / average)
    stable = MetricValue.available
    return FprDispersion(
        mean_fpr=stable(average),
        standard_deviation=stable(standard_deviation),
        coefficient_of_variation=cv,
        iqr=stable(q75 - q25),
        value_range=stable(max(fprs) - min(fprs)),
        worst_fpr=stable(max(fprs)),
    )


def assert_auroc_invariant(values: Iterable[float], *, tolerance: float) -> None:
    scores = tuple(values)
    if tolerance < 0.0:
        raise ValueError("tolerance must be non-negative")
    if scores and max(scores) - min(scores) > tolerance:
        raise ValueError("AUROC must be invariant across fixed-score threshold policies")


def calculate_pairwise_js_divergence(
    client_scores: Sequence[tuple[ClientId, tuple[float, ...]]], *, histogram_bins: int, logarithm_base: int
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
    divergences = []
    for left_index, left in enumerate(distributions):
        for right in distributions[left_index + 1 :]:
            midpoint = tuple((first + second) / 2.0 for first, second in zip(left, right, strict=True))
            divergences.append(
                sum(
                    probability * log(probability / midpoint[index], logarithm_base)
                    for index, probability in enumerate(left)
                    if probability > 0.0
                )
                / 2.0
                + sum(
                    probability * log(probability / midpoint[index], logarithm_base)
                    for index, probability in enumerate(right)
                    if probability > 0.0
                )
                / 2.0
            )
    return mean(divergences)

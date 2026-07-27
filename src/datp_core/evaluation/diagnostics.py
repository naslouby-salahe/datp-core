"""Deterministic evaluation diagnostics."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from math import isfinite, sqrt
from statistics import mean

import numpy as np
import polars as pl
from scipy.spatial.distance import jensenshannon

from datp_core.core.numbers import linear_quantile
from datp_core.evaluation.enums import EvaluationColumn, MetricStatus
from datp_core.evaluation.models import (
    ClientScoreSeries,
    FprDispersion,
    MetricValue,
    QuantileVarianceTerms,
)


def calculate_fpr_dispersion(
    values: Iterable[float],
    *,
    cv_instability_threshold: float,
    ddof: int,
) -> FprDispersion:
    if (
        cv_instability_threshold <= 0.0
        or not isfinite(cv_instability_threshold)
    ):
        raise ValueError(
            "cv_instability_threshold must be finite and positive"
        )

    if ddof < 0:
        raise ValueError("ddof must be non-negative")

    fprs = tuple(values)

    if not fprs:
        unavailable = MetricValue.unavailable(
            MetricStatus.UNDEFINED_ZERO_DENOMINATOR
        )
        return FprDispersion(
            mean_fpr=unavailable,
            standard_deviation=unavailable,
            coefficient_of_variation=unavailable,
            iqr=unavailable,
            value_range=unavailable,
            worst_fpr=unavailable,
        )

    if ddof >= len(fprs):
        raise ValueError(
            "ddof must be smaller than the client count, "
            f"got {ddof} for {len(fprs)} clients"
        )

    if any(not isfinite(value) for value in fprs):
        raise ValueError("FPR values must be finite")

    if any(not 0.0 <= value <= 1.0 for value in fprs):
        raise ValueError("FPR values must be in [0, 1]")

    average = mean(fprs)
    variance = (
        sum((value - average) ** 2 for value in fprs)
        / (len(fprs) - ddof)
    )
    standard_deviation = sqrt(variance)

    q25 = linear_quantile(fprs, 0.25)
    q75 = linear_quantile(fprs, 0.75)

    if average == 0.0:
        coefficient_of_variation = MetricValue.unavailable(
            MetricStatus.UNDEFINED_ZERO_DENOMINATOR
        )
    elif average < cv_instability_threshold:
        coefficient_of_variation = MetricValue.warning(
            standard_deviation / average,
            MetricStatus.UNDEFINED_NEAR_ZERO_DENOMINATOR,
        )
    else:
        coefficient_of_variation = MetricValue.available(
            standard_deviation / average
        )

    return FprDispersion(
        mean_fpr=MetricValue.available(average),
        standard_deviation=MetricValue.available(standard_deviation),
        coefficient_of_variation=coefficient_of_variation,
        iqr=MetricValue.available(q75 - q25),
        value_range=MetricValue.available(max(fprs) - min(fprs)),
        worst_fpr=MetricValue.available(max(fprs)),
    )


def assert_auroc_invariant(
    values: Iterable[float],
    *,
    tolerance: float,
) -> None:
    if tolerance < 0.0 or not isfinite(tolerance):
        raise ValueError("tolerance must be finite and non-negative")

    aurocs = tuple(values)

    if any(
        not isfinite(value) or not 0.0 <= value <= 1.0
        for value in aurocs
    ):
        raise ValueError("AUROC values must be finite and in [0, 1]")

    if aurocs and max(aurocs) - min(aurocs) > tolerance:
        raise ValueError(
            "AUROC must be invariant across fixed-score threshold policies"
        )


def calculate_pairwise_js_divergence(
    client_scores: Sequence[ClientScoreSeries],
    *,
    histogram_bins: int,
    logarithm_base: int,
) -> float:
    if histogram_bins < 1:
        raise ValueError("histogram_bins must be positive")

    if logarithm_base < 2:
        raise ValueError("logarithm_base must be at least 2")

    if len(client_scores) < 2:
        raise ValueError(
            "Pairwise JS divergence requires at least two clients"
        )

    pooled = np.fromiter(
        (
            score
            for client in client_scores
            for score in client.scores
        ),
        dtype=np.float64,
    )

    lower = float(pooled.min())
    upper = float(pooled.max())

    if lower == upper:
        half_width = max(abs(lower), 1.0) * 0.5
        lower -= half_width
        upper += half_width

    edges = np.linspace(
        lower,
        upper,
        histogram_bins + 1,
        dtype=np.float64,
    )

    distributions = tuple(
        np.histogram(
            np.asarray(client.scores, dtype=np.float64),
            bins=edges,
        )[0].astype(np.float64)
        for client in client_scores
    )

    normalized = tuple(
        distribution / distribution.sum()
        for distribution in distributions
    )

    divergences: list[float] = []

    for left_index, left in enumerate(normalized):
        for right in normalized[left_index + 1 :]:
            distance = float(
                jensenshannon(
                    left,
                    right,
                    base=float(logarithm_base),
                )
            )

            if not isfinite(distance):
                raise ValueError(
                    "Jensen-Shannon distance must be finite"
                )

            divergences.append(distance * distance)

    return mean(divergences)


def calculate_calibration_variance(
    calibration: pl.DataFrame,
    *,
    ddof: int,
) -> QuantileVarianceTerms:
    if ddof < 0:
        raise ValueError("ddof must be non-negative")

    required = (
        EvaluationColumn.CLIENT_ID,
        EvaluationColumn.SCORE,
    )

    missing = tuple(
        column
        for column in required
        if column not in calibration.columns
    )

    if missing:
        raise ValueError(
            "Calibration frame is missing columns: "
            f"{[column.value for column in missing]}"
        )

    if calibration.is_empty():
        raise ValueError(
            "Calibration variance requires calibration scores"
        )

    normalized = calibration.select(
        pl.col(EvaluationColumn.CLIENT_ID).cast(
            pl.String,
            strict=True,
        ),
        pl.col(EvaluationColumn.SCORE).cast(
            pl.Float64,
            strict=True,
        ),
    )

    if normalized.get_column(
        EvaluationColumn.CLIENT_ID
    ).is_null().any():
        raise ValueError(
            "Calibration client IDs must not be null"
        )

    scores = normalized.get_column(EvaluationColumn.SCORE)

    if (
        scores.is_null().any()
        or scores.is_nan().any()
        or scores.is_infinite().any()
    ):
        raise ValueError("Calibration scores must be finite")

    counts = normalized.group_by(
        EvaluationColumn.CLIENT_ID
    ).agg(
        pl.len().alias("_count")
    )

    insufficient = counts.filter(
        pl.col("_count") <= ddof
    )

    if not insufficient.is_empty():
        offending = tuple(
            insufficient.iter_rows(named=False)
        )
        raise ValueError(
            f"Every client requires more than ddof={ddof} rows; "
            f"offending groups: {offending}"
        )

    pooled_mean_raw = scores.mean()

    if pooled_mean_raw is None:
        raise ValueError(
            "Calibration pooled mean is unavailable"
        )

    pooled_mean = float(pooled_mean_raw)

    group_stats = normalized.group_by(
        EvaluationColumn.CLIENT_ID
    ).agg(
        pl.len().alias("_count"),
        pl.col(EvaluationColumn.SCORE)
        .mean()
        .alias("_mean"),
        pl.col(EvaluationColumn.SCORE)
        .var(ddof=ddof)
        .alias("_variance"),
    )

    if group_stats.get_column(
        "_variance"
    ).is_null().any():
        raise ValueError(
            "Calibration variance produced null group variances"
        )

    total_count = float(
        group_stats.get_column("_count").sum()
    )

    within = float(
        (
            group_stats.get_column("_count")
            * group_stats.get_column("_variance")
        ).sum()
    ) / total_count

    between = float(
        (
            group_stats.get_column("_count")
            * (
                group_stats.get_column("_mean")
                - pooled_mean
            )
            ** 2
        ).sum()
    ) / total_count

    total = within + between

    return QuantileVarianceTerms(
        within_term=within,
        between_term=between,
        between_ratio=None if total == 0.0 else between / total,
    )
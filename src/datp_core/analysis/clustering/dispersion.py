"""Cluster dispersion primitives: within-cluster, between-cluster, and ablation observations."""

from __future__ import annotations

import math

import numpy as np
import polars as pl
from sklearn.metrics import adjusted_rand_score

from datp_core.analysis.contracts import ClusterDispersionResult
from datp_core.analysis.enums import ClusterDispersionKind, ClusterDispersionStatus


def compute_adjusted_rand_index(labels_true: np.ndarray, labels_pred: np.ndarray) -> float:
    """Compute adjusted Rand index (ARI) between ground truth and predicted cluster labels."""
    return float(adjusted_rand_score(labels_true, labels_pred))


def cluster_dispersion(
    frame: pl.DataFrame,
    *,
    kind: ClusterDispersionKind,
    expected_cluster_count: int,
    total_client_count: int | None = None,
    metric_covered_client_count: int | None = None,
) -> ClusterDispersionResult:
    """Compute within- or across-cluster dispersion with typed unavailability reasons.

    The caller-provided *frame* must have columns ``cluster_label`` (int or str) and
    ``value`` (float, nullable).  Every client in the population should appear exactly
    once; rows whose ``value`` is null represent clients assigned to a cluster but
    without a measurable quantity (e.g. unavailable FPR).

    Parameters
    ----------
    frame:
        Polars DataFrame with ``cluster_label`` and ``value`` columns.
    kind:
        WITHIN — std of values within each cluster, then mean of those stds.
        ACROSS — mean per cluster, then std of those cluster means.
    expected_cluster_count:
        Total number of clusters in the design (labels ``0 .. k-1``).
    total_client_count:
        Total number of clients in the population (used for the excluded-count
        denominator when the frame has fewer rows than the population).
    metric_covered_client_count:
        Number of clients that have any metric status (used for
        incomplete-metric-population detection).
    """
    observed_cluster_count = expected_cluster_count

    # Per-cluster summary: row count, non-null value count, std, and mean.
    per_cluster = frame.group_by("cluster_label").agg(
        pl.len().alias("total"),
        pl.col("value").is_not_null().sum().alias("non_null"),
        pl.col("value").std(ddof=0).alias("cluster_std"),
        pl.col("value").mean().alias("cluster_mean"),
    )

    non_empty = per_cluster.filter(pl.col("total") > 0)
    non_empty_count = non_empty.height

    excluded = int(per_cluster.select((pl.col("total") - pl.col("non_null")).sum()).item())

    # -- Empty cluster detection (Polars anti-join to avoid Python set diff) -----
    expected_clusters = pl.DataFrame({"cluster_label": [str(i) for i in range(expected_cluster_count)]})
    present_clusters = non_empty.select(pl.col("cluster_label").cast(pl.Utf8).unique().alias("cluster_label"))
    empty_labels = expected_clusters.join(present_clusters, on="cluster_label", how="anti").to_series().to_list()

    if empty_labels:
        return ClusterDispersionResult(
            status=ClusterDispersionStatus.UNAVAILABLE_EMPTY_CLUSTER,
            value=None,
            reason=f"cluster(s) {empty_labels} have no assigned clients",
            observed_cluster_count=observed_cluster_count,
            available_cluster_count=non_empty_count,
            excluded_client_count=0,
        )

    # -- Complete lack of metric coverage ---------------------------------------
    if metric_covered_client_count == 0 and total_client_count is not None:
        return ClusterDispersionResult(
            status=ClusterDispersionStatus.UNAVAILABLE_INCOMPLETE_METRIC_POPULATION,
            value=None,
            reason="no metric rows are available for any client in the threshold population",
            observed_cluster_count=observed_cluster_count,
            available_cluster_count=0,
            excluded_client_count=total_client_count,
        )

    # -- Clusters that exist but have zero non-null values ----------------------
    no_value = non_empty.filter(pl.col("non_null") == 0)
    if no_value.height > 0:
        no_value_labels = no_value.select(pl.col("cluster_label").cast(pl.Utf8).sort()).to_series().to_list()
        return ClusterDispersionResult(
            status=ClusterDispersionStatus.UNAVAILABLE_NO_AVAILABLE_FPR,
            value=None,
            reason=f"cluster(s) {no_value_labels} have no available false-positive-rate values",
            observed_cluster_count=observed_cluster_count,
            available_cluster_count=non_empty_count - no_value.height,
            excluded_client_count=excluded,
        )

    # -- Across-cluster dispersion needs >= 2 clusters with values -------------
    value_clusters = non_empty.filter(pl.col("non_null") > 0)
    value_cluster_count = value_clusters.height

    if kind == ClusterDispersionKind.ACROSS and value_cluster_count < 2:
        return ClusterDispersionResult(
            status=ClusterDispersionStatus.UNAVAILABLE_INSUFFICIENT_OBSERVATIONS,
            value=None,
            reason="fewer than two clusters contribute values; across-cluster dispersion is undefined",
            observed_cluster_count=observed_cluster_count,
            available_cluster_count=value_cluster_count,
            excluded_client_count=excluded,
        )

    # -- Actual computation ----------------------------------------------------
    if kind == ClusterDispersionKind.WITHIN:
        value = float(value_clusters.select(pl.col("cluster_std").mean()).item())
    else:
        value = float(value_clusters.select(pl.col("cluster_mean").std(ddof=0)).item())

    if not math.isfinite(value):
        return ClusterDispersionResult(
            status=ClusterDispersionStatus.UNAVAILABLE_NON_FINITE_INPUT,
            value=None,
            reason="dispersion computation produced a non-finite value",
            observed_cluster_count=observed_cluster_count,
            available_cluster_count=value_cluster_count,
            excluded_client_count=excluded,
        )

    return ClusterDispersionResult(
        status=ClusterDispersionStatus.AVAILABLE,
        value=value,
        reason=None,
        observed_cluster_count=observed_cluster_count,
        available_cluster_count=value_cluster_count,
        excluded_client_count=excluded,
    )

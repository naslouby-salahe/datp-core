"""Cluster threshold estimator (B4) with fingerprint construction, standardization, and KMeans."""

from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np
from scipy.stats import skew
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.core.numbers import Probability
from datp_core.thresholding.estimation.models import ThresholdSet, build_threshold_set
from datp_core.thresholding.policies.clustering import ClusterThresholdPolicyRecord
from datp_core.thresholding.policies.common import BenignCalibrationScores
from datp_core.thresholding.policies.enums import ClusterAggregation, ThresholdOwnerKind


def _aggregate(values: list[float], aggregation: ClusterAggregation) -> float:
    if aggregation is ClusterAggregation.ROBUST_MEDIAN:
        return float(np.quantile(values, 0.5, method="linear"))
    return float(np.mean(values))


def _safe_skew(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    result = float(skew(values, bias=True))
    if not math.isfinite(result):
        return 0.0
    return result


def _fingerprint_quantile(fingerprint_estimators: Mapping[str, str]) -> float:
    estimator = fingerprint_estimators.get("p95_error", "")
    if estimator.startswith("quantile_"):
        try:
            remainder = estimator[len("quantile_") :]
            suffix = "_linear_interpolated_order_statistic"
            if remainder.endswith(suffix):
                quantile_str = remainder[: -len(suffix)].replace("_", ".")
                return float(quantile_str)
        except (ValueError, IndexError):
            pass
    raise ValueError(
        f"Cannot determine fingerprint quantile from estimator: {estimator!r}. "
        f"Expected format: 'quantile_{{q}}_linear_interpolated_order_statistic'"
    )


def _canonicalize_cluster_labels(
    raw_labels: tuple[int, ...],
    local: dict[str, float],
    calibration: tuple[BenignCalibrationScores, ...],
    aggregation: ClusterAggregation,
) -> dict[int, int]:
    cluster_members: dict[int, list[str]] = {}
    cluster_local_values: dict[int, list[float]] = {}
    for item, raw_label in zip(calibration, raw_labels, strict=True):
        client_id = item.client_id.value
        cluster_members.setdefault(raw_label, []).append(client_id)
        cluster_local_values.setdefault(raw_label, []).append(local[client_id])

    cluster_thresholds: dict[int, float] = {
        label: _aggregate(values, aggregation) for label, values in cluster_local_values.items()
    }

    def _sort_key(raw_label: int) -> tuple[float, str]:
        return (cluster_thresholds[raw_label], min(cluster_members[raw_label]))

    sorted_raw_labels = sorted(cluster_thresholds.keys(), key=_sort_key)

    return {raw: canonical for canonical, raw in enumerate(sorted_raw_labels)}


def estimate_cluster(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
    policy: ClusterThresholdPolicyRecord,
    quantile_fn,
) -> ThresholdSet:
    if len(calibration) < policy.cluster_count:
        raise ValueError("Cluster threshold has fewer eligible clients than configured clusters")
    calibration = tuple(sorted(calibration, key=lambda item: item.client_id.value))
    feature_names = ("mean_error", "std_error", "skew_error", "p95_error")
    if any(feature not in feature_names for feature in policy.fingerprint.features):
        raise ValueError("Cluster policy declares an unsupported fingerprint feature")
    selected_feature_indexes = tuple(feature_names.index(feature) for feature in policy.fingerprint.features)
    fingerprint_p95_quantile = _fingerprint_quantile(policy.fingerprint.estimators)
    rows = []
    for item in calibration:
        values = np.asarray(item.values, dtype=np.float64)
        rows.append(
            (
                float(np.mean(values)),
                float(np.std(values, ddof=1)) if len(values) >= 2 else 0.0,
                _safe_skew(values),
                quantile_fn(item.values, fingerprint_p95_quantile),
            )
        )
    features = np.asarray(rows, dtype=np.float64)[:, selected_feature_indexes]
    if not np.isfinite(features).all():
        raise ValueError("Cluster threshold has a non-finite fingerprint component")
    if len(np.unique(features, axis=0)) < 2:
        raise ValueError("Cluster threshold has a degenerate fingerprint matrix")
    kmeans_cfg = policy.kmeans
    labels = KMeans(
        n_clusters=policy.cluster_count,
        random_state=int(kmeans_cfg.random_seed),
        n_init=int(kmeans_cfg.initialization_runs),  # type: ignore[arg-type]
        max_iter=int(kmeans_cfg.maximum_iterations),
        tol=float(kmeans_cfg.convergence_tolerance),
    ).fit_predict(StandardScaler().fit_transform(features))
    raw_labels = [int(label) for label in labels]

    canonical_map = _canonicalize_cluster_labels(
        tuple(raw_labels),
        local,
        calibration,
        policy.aggregation,
    )

    canonical_buckets: dict[int, list[float]] = {}
    for item, raw_label in zip(calibration, raw_labels, strict=True):
        canonical_buckets.setdefault(canonical_map[raw_label], []).append(local[item.client_id.value])
    canonical_thresholds = {
        canonical: _aggregate(values, policy.aggregation) for canonical, values in canonical_buckets.items()
    }

    thresholds = {
        item.client_id.value: canonical_thresholds[canonical_map[raw_label]]
        for item, raw_label in zip(calibration, raw_labels, strict=True)
    }
    cluster_labels = {
        item.client_id.value: canonical_map[raw_label] for item, raw_label in zip(calibration, raw_labels, strict=True)
    }
    return build_threshold_set(
        policy_id,
        calibration,
        thresholds,
        ThresholdOwnerKind.CLUSTER,
        target_quantile,
        cluster_labels=cluster_labels,
    )

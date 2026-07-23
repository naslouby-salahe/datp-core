"""Cluster (B4) threshold estimation: taxonomy-free groups from a 4-scalar benign fingerprint."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

import numpy as np
from scipy.stats import skew
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from datp_core.thresholding.models import (
    BenignCalibrationScores,
    ClusterThresholdPolicyRecord,
    Probability,
    ThresholdPolicyId,
    ThresholdSet,
    build_threshold_set,
)

_INVALID_CLUSTER_INT_PARAMS = "Cluster policy has invalid authored integer parameters"


def fingerprint_quantile(fingerprint_estimators: Mapping[str, str]) -> float:
    """Extract the p95 fingerprint quantile from the configured estimator name.

    The fingerprint_estimators mapping (from protocols.yaml) contains entries like
    ``"p95_error": "quantile_0_95_linear_interpolated_order_statistic"``.
    The quantile value is derived from the estimator name rather than hardcoded,
    keeping configuration as the sole authority for all scientific values.
    """
    estimator = fingerprint_estimators.get("p95_error", "")
    # Expected format: "quantile_{q}_linear_interpolated_order_statistic"
    # where q is the quantile value, e.g. "quantile_0_95_..."
    if estimator.startswith("quantile_"):
        try:
            # Extract "0_95" from "quantile_0_95_linear_interpolated_order_statistic"
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
    feature_names = ("mean_error", "std_error", "skew_error", "p95_error")
    if any(feature not in feature_names for feature in policy.fingerprint_features):
        raise ValueError("Cluster policy declares an unsupported fingerprint feature")
    selected_feature_indexes = tuple(feature_names.index(feature) for feature in policy.fingerprint_features)
    # p95_error quantile is derived from the configured fingerprint_estimators (protocols.yaml),
    # not hardcoded — keeping configuration as the sole scientific authority.
    fingerprint_p95_quantile = fingerprint_quantile(policy.fingerprint_estimators)
    rows = []
    for item in calibration:
        values = np.asarray(item.values, dtype=np.float64)
        rows.append(
            (
                float(np.mean(values)),
                float(np.std(values, ddof=1)) if len(values) >= 2 else 0.0,
                float(skew(values)) if len(values) > 2 else 0.0,
                # p95_error uses the configured fingerprint quantile (from protocols.yaml),
                # independently of this policy's own (possibly swept) threshold-construction quantile.
                quantile_fn(item.values, fingerprint_p95_quantile),
            )
        )
    features = np.asarray(rows, dtype=np.float64)[:, selected_feature_indexes]
    if len(np.unique(features, axis=0)) < 2:
        raise ValueError("Cluster threshold has a degenerate fingerprint matrix")
    clustering = policy.clustering
    random_seed = clustering.get("random_seed")
    runs = clustering.get("initialization_runs")
    maximum_iterations = clustering.get("maximum_iterations")
    tolerance = clustering.get("convergence_tolerance")
    if not isinstance(random_seed, int) or isinstance(random_seed, bool):
        raise ValueError(_INVALID_CLUSTER_INT_PARAMS)
    if not isinstance(runs, int) or isinstance(runs, bool):
        raise ValueError(_INVALID_CLUSTER_INT_PARAMS)
    if not isinstance(maximum_iterations, int) or isinstance(maximum_iterations, bool):
        raise ValueError(_INVALID_CLUSTER_INT_PARAMS)
    if not isinstance(tolerance, float):
        raise ValueError("Cluster policy has invalid authored convergence tolerance")
    labels = KMeans(
        n_clusters=policy.cluster_count,
        random_state=int(random_seed),
        n_init=cast(str, runs),
        max_iter=int(maximum_iterations),
        tol=tolerance,
    ).fit_predict(StandardScaler().fit_transform(features))
    buckets: dict[int, list[float]] = {}
    for item, label in zip(calibration, labels, strict=True):
        buckets.setdefault(int(label), []).append(local[item.client_id.value])
    aggregation = (
        (lambda vs: float(np.quantile(vs, 0.5, method="linear"))) if policy.aggregation == "robust_median" else np.mean
    )
    aggregate = {label: float(aggregation(values)) for label, values in buckets.items()}
    thresholds = {item.client_id.value: aggregate[int(label)] for item, label in zip(calibration, labels, strict=True)}
    return build_threshold_set(
        policy_id,
        calibration,
        thresholds,
        f"cluster_k{policy.cluster_count}",
        target_quantile,
        cluster_labels={item.client_id.value: int(label) for item, label in zip(calibration, labels, strict=True)},
    )

"""Pure threshold-estimator functions, organized by policy type: shared/local/family-mean
quantile estimators (B0-B3), split-conformal (B2-conf), cluster (B4), local-global shrinkage and
calibration-size-aware fallback, and federated summary-statistic (B-FedStatsBenign) estimators.

Local-global shrinkage and calibration-fallback are combined with the federated summary-statistic
estimators because both "combine already-computed local/shared thresholds" using shared
pooled-moment math.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import cast

import numpy as np
from scipy.stats import skew
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from datp_core.thresholding.models import (
    BenignCalibrationScores,
    CalibrationFallbackThresholdPolicyRecord,
    ClusterAggregation,
    ClusterThresholdPolicyRecord,
    ConformalAttainabilityStatus,
    FederatedMatchedExceedanceThresholdPolicyRecord,
    Probability,
    SplitConformalThresholdPolicyRecord,
    ThresholdPolicyId,
    ThresholdSet,
    build_threshold_set,
)

_INVALID_CLUSTER_INT_PARAMS = "Cluster policy has invalid authored integer parameters"


def estimate_shared_mean(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
) -> ThresholdSet:
    shared = float(np.mean(tuple(local.values())))
    return build_threshold_set(policy_id, calibration, dict.fromkeys(local, shared), "shared_mean", target_quantile)


def estimate_pooled(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
    quantile_fn,
) -> ThresholdSet:
    """Shared for `SharedPooledThresholdPolicyRecord` and `CentralizedPooledThresholdPolicyRecord`."""
    pooled = tuple(value for item in calibration for value in item.values)
    threshold = quantile_fn(pooled, target_quantile.value)
    return build_threshold_set(policy_id, calibration, {k: threshold for k in local}, "pooled", target_quantile)


def estimate_shared_weighted(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
) -> ThresholdSet:
    count = sum(len(item.values) for item in calibration)
    if count == 0:
        raise ValueError("Weighted threshold has no calibration rows")
    threshold = sum(len(item.values) * local[item.client_id.value] for item in calibration) / count
    return build_threshold_set(
        policy_id, calibration, dict.fromkeys(local, threshold), "shared_weighted", target_quantile
    )


def estimate_local_quantile(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
) -> ThresholdSet:
    return build_threshold_set(policy_id, calibration, local, "local", target_quantile)


def estimate_family_mean(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
    family_map: dict[str, str] | None,
) -> ThresholdSet:
    if family_map is None:
        raise ValueError("Family threshold requires an explicit resolved client-family mapping")
    families: dict[str, list[float]] = {}
    for item in calibration:
        family = family_map.get(item.client_id.value)
        if family is None:
            raise ValueError(f"Client '{item.client_id.value}' has no configured family")
        families.setdefault(family, []).append(local[item.client_id.value])
    family_thresholds = {family: float(np.mean(values)) for family, values in families.items()}
    thresholds = {item.client_id.value: family_thresholds[family_map[item.client_id.value]] for item in calibration}
    return build_threshold_set(policy_id, calibration, thresholds, "family_mean", target_quantile)


def estimate_conformal(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
    policy: SplitConformalThresholdPolicyRecord,
) -> ThresholdSet:
    thresholds: dict[str, float] = {}
    ranks: dict[str, int] = {}
    for item in calibration:
        scores = np.sort(np.asarray(item.values, dtype=np.float64))
        if len(scores) < policy.minimum_sample_count:
            raise ValueError("Conformal threshold is unattainable for the authored minimum sample count")
        rank = min(math.ceil((len(scores) + 1) * (1.0 - policy.coverage_alpha)), len(scores))
        thresholds[item.client_id.value] = float(scores[rank - 1])
        ranks[item.client_id.value] = rank
    return build_threshold_set(
        policy_id,
        calibration,
        thresholds,
        "split_conformal",
        target_quantile,
        conformal_ranks=ranks,
        conformal_attainability={item.client_id.value: ConformalAttainabilityStatus.ATTAINABLE for item in calibration},
    )


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
        (lambda vs: float(np.quantile(vs, 0.5, method="linear")))
        if policy.aggregation is ClusterAggregation.ROBUST_MEDIAN
        else np.mean
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


def estimate_shrinkage(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
    coefficient: float,
) -> ThresholdSet:
    if not 0.0 <= coefficient <= 1.0:
        raise ValueError("Shrinkage coefficient is outside the authored permitted range")
    shared = float(np.mean(tuple(local.values())))
    thresholds = {key: coefficient * value + (1.0 - coefficient) * shared for key, value in local.items()}
    return build_threshold_set(
        policy_id,
        calibration,
        thresholds,
        "local_global_shrinkage",
        target_quantile,
        dict.fromkeys(local, coefficient),
    )


def estimate_calibration_fallback(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
    policy: CalibrationFallbackThresholdPolicyRecord,
) -> ThresholdSet:
    half = policy.weight_formula_constants.get("n_half")
    if not isinstance(half, int) or half <= 0:
        raise ValueError("Fallback threshold policy requires a positive authored n_half")
    shared = float(np.mean(tuple(local.values())))
    lambdas = {item.client_id.value: len(item.values) / (len(item.values) + half) for item in calibration}
    thresholds = {
        item.client_id.value: lambdas[item.client_id.value] * local[item.client_id.value]
        + (1.0 - lambdas[item.client_id.value]) * shared
        for item in calibration
    }
    return build_threshold_set(policy_id, calibration, thresholds, "calibration_shrinkage", target_quantile, lambdas)


def federated_moments(calibration: tuple[BenignCalibrationScores, ...]) -> tuple[float, float]:
    counts = np.asarray([len(item.values) for item in calibration], dtype=np.float64)
    means = np.asarray([np.mean(item.values) for item in calibration], dtype=np.float64)
    variances = np.asarray([np.var(item.values) for item in calibration], dtype=np.float64)
    total = float(np.sum(counts))
    if total <= 0.0:
        raise ValueError("Federated summary threshold has no calibration rows")
    mean = float(np.sum(counts * means) / total)
    variance = float(np.sum(counts * variances) / total + np.sum(counts * (means - mean) ** 2) / total)
    return mean, math.sqrt(variance)


def estimate_federated_matched(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
    policy: FederatedMatchedExceedanceThresholdPolicyRecord,
) -> ThresholdSet:
    minimum = policy.candidate_grid.get("minimum")
    maximum = policy.candidate_grid.get("maximum")
    step = policy.candidate_grid.get("step")
    if not isinstance(minimum, float) or not isinstance(maximum, float) or not isinstance(step, float):
        raise ValueError("Matched-exceedance policy has an invalid authored candidate grid")
    if step <= 0.0:
        raise ValueError("Matched-exceedance policy has an invalid authored candidate grid")
    mean, standard_deviation = federated_moments(calibration)
    candidates = np.arange(minimum, maximum + step / 2.0, step)
    scores = np.asarray([score for item in calibration for score in item.values], dtype=np.float64)
    achieved = np.asarray([np.mean(scores > mean + candidate * standard_deviation) for candidate in candidates])
    deviation = np.abs(achieved - (1.0 - target_quantile.value))
    winner = candidates[np.flatnonzero(deviation == np.min(deviation))[-1]]
    threshold = mean + float(winner) * standard_deviation
    diagnostics: dict[str, object] = {
        "selected_coefficient": float(winner),
        "candidate_grid": {"minimum": minimum, "maximum": maximum, "step": step},
        "pooled_mean": float(mean),
        "pooled_standard_deviation": float(standard_deviation),
        "achieved_exceedance": {float(c): float(a) for c, a in zip(candidates, achieved, strict=True)},
        "tie_set": [float(candidates[i]) for i in np.flatnonzero(deviation == np.min(deviation))],
    }
    return build_threshold_set(
        policy_id,
        calibration,
        {item.client_id.value: threshold for item in calibration},
        "federated_matched_exceedance",
        target_quantile,
        diagnostics=diagnostics,
    )


def estimate_federated_fixed(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
    coefficient: float,
) -> ThresholdSet:
    mean, standard_deviation = federated_moments(calibration)
    threshold = mean + coefficient * standard_deviation
    return build_threshold_set(
        policy_id,
        calibration,
        {item.client_id.value: threshold for item in calibration},
        "federated_fixed_k",
        target_quantile,
    )

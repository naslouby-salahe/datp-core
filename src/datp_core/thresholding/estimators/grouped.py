"""Family-mean and cluster threshold estimators."""

from __future__ import annotations

import math

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.core.numbers import Probability
from datp_core.thresholding.enums import (
    ClusterAggregation,
    FingerprintFeature,
    ThresholdDiagnosticsKind,
    ThresholdPolicyKind,
    ThresholdScope,
)
from datp_core.thresholding.estimators.quantile import quantile
from datp_core.thresholding.models import (
    BenignCalibrationScores,
    ClusterDiagnostics,
    FamilyAssignments,
    InsufficientCalibrationError,
    NonFiniteCalibrationError,
    ThresholdConfigurationError,
    ThresholdRecord,
    ThresholdSet,
)


def estimate_family_mean(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
    family_assignments: FamilyAssignments,
) -> ThresholdSet:
    """Construct family-mean thresholds using validated FamilyAssignments."""
    cal_ids = {c.client_id for c in calibration}
    assigned_ids = {cid for cid, _ in family_assignments.mapping}
    missing = cal_ids - assigned_ids
    if missing:
        raise ThresholdConfigurationError(
            f"Calibration clients missing from family assignments: {[str(c) for c in sorted(missing)]}"
        )
    extra = assigned_ids - cal_ids
    if extra:
        raise ThresholdConfigurationError(
            f"Family assignments for clients not in calibration: {[str(c) for c in sorted(extra)]}"
        )
    family_map = {cid.value: family for cid, family in family_assignments.mapping}
    local = {item.client_id.value: quantile(item.values, target_quantile.value) for item in calibration}
    families: dict[str, list[float]] = {}
    for item in calibration:
        family = family_map[item.client_id.value]
        families.setdefault(family, []).append(local[item.client_id.value])
    family_thresholds = {family: float(np.mean(values)) for family, values in families.items()}
    thresholds = {item.client_id.value: family_thresholds[family_map[item.client_id.value]] for item in calibration}
    return ThresholdSet(
        policy_id=policy_id,
        policy_kind=ThresholdPolicyKind.FAMILY_MEAN,
        scope=ThresholdScope.FAMILY,
        target_quantile=target_quantile,
        values=tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=thresholds[item.client_id.value],
                policy_kind=ThresholdPolicyKind.FAMILY_MEAN,
                scope=ThresholdScope.FAMILY,
            )
            for item in calibration
        ),
    )


_FEATURE_ORDER: tuple[FingerprintFeature, ...] = (
    FingerprintFeature.MEAN_ERROR,
    FingerprintFeature.STD_ERROR,
    FingerprintFeature.SKEW_ERROR,
    FingerprintFeature.QUANTILE_ERROR,
)


def _aggregate(values: list[float], aggregation: ClusterAggregation) -> float:
    if aggregation is ClusterAggregation.ROBUST_MEDIAN:
        return float(np.quantile(values, 0.5, method="linear"))
    return float(np.mean(values))


def _safe_skew(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    from scipy.stats import skew

    result = float(skew(values, bias=True))
    if not math.isfinite(result):
        return 0.0
    return result


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
    target_quantile: Probability,
    *,
    cluster_count: int,
    aggregation: ClusterAggregation,
    fingerprint_features: tuple[FingerprintFeature, ...],
    fingerprint_quantile: float,
    kmeans_random_seed: int,
    kmeans_initialization_runs: int,
    kmeans_maximum_iterations: int,
    kmeans_convergence_tolerance: float,
) -> ThresholdSet:
    """Construct cluster thresholds with deterministic label canonicalization."""
    if len(calibration) < cluster_count:
        raise InsufficientCalibrationError(
            f"Cluster threshold has {len(calibration)} eligible clients but requires at least {cluster_count}"
        )
    calibration = tuple(sorted(calibration, key=lambda item: item.client_id.value))

    # Build client fingerprints
    feature_indexes = tuple(_FEATURE_ORDER.index(feature) for feature in fingerprint_features)
    rows = []
    for item in calibration:
        values = np.asarray(item.values, dtype=np.float64)
        rows.append(
            (
                float(np.mean(values)),
                float(np.std(values, ddof=1)) if len(values) >= 2 else 0.0,
                _safe_skew(values),
                quantile(item.values, fingerprint_quantile),
            )
        )
    features = np.asarray(rows, dtype=np.float64)[:, feature_indexes]
    if not np.isfinite(features).all():
        raise NonFiniteCalibrationError("Cluster threshold has a non-finite fingerprint component")
    unique_rows = len(np.unique(features, axis=0))
    if unique_rows < cluster_count:
        raise InsufficientCalibrationError(
            f"Cluster threshold requires at least {cluster_count} distinct fingerprint rows "
            f"but only {unique_rows} unique row(s) exist across {len(calibration)} eligible clients "
            f"using features {[f.value for f in fingerprint_features]}"
        )

    labels = KMeans(
        n_clusters=cluster_count,
        random_state=kmeans_random_seed,
        n_init=int(kmeans_initialization_runs),
        max_iter=kmeans_maximum_iterations,
        tol=kmeans_convergence_tolerance,
    ).fit_predict(StandardScaler().fit_transform(features))
    raw_labels = tuple(int(label) for label in labels)

    local = {item.client_id.value: quantile(item.values, target_quantile.value) for item in calibration}

    canonical_map = _canonicalize_cluster_labels(raw_labels, local, calibration, aggregation)

    canonical_members: dict[int, list[str]] = {}
    canonical_buckets: dict[int, list[float]] = {}
    for item, raw_label in zip(calibration, raw_labels, strict=True):
        canonical = canonical_map[raw_label]
        canonical_members.setdefault(canonical, []).append(item.client_id.value)
        canonical_buckets.setdefault(canonical, []).append(local[item.client_id.value])
    canonical_thresholds = {
        canonical: _aggregate(values, aggregation) for canonical, values in canonical_buckets.items()
    }

    thresholds = {
        item.client_id.value: canonical_thresholds[canonical_map[raw_label]]
        for item, raw_label in zip(calibration, raw_labels, strict=True)
    }

    diagnostics = ClusterDiagnostics(
        kind=ThresholdDiagnosticsKind.CLUSTER,
        cluster_count=cluster_count,
        eligible_client_count=len(calibration),
        unique_fingerprint_row_count=unique_rows,
        cluster_labels=tuple(
            (item.client_id.value, canonical_map[raw_label])
            for item, raw_label in zip(calibration, raw_labels, strict=True)
        ),
        aggregation=aggregation,
        fingerprint_features=fingerprint_features,
        fingerprint_quantile=fingerprint_quantile,
        kmeans_random_seed=kmeans_random_seed,
        kmeans_initialization_runs=kmeans_initialization_runs,
        kmeans_maximum_iterations=kmeans_maximum_iterations,
        kmeans_convergence_tolerance=kmeans_convergence_tolerance,
        cluster_members=tuple(
            (canonical, tuple(sorted(members))) for canonical, members in sorted(canonical_members.items())
        ),
        cluster_thresholds=tuple(
            (canonical, canonical_thresholds[canonical]) for canonical in sorted(canonical_thresholds)
        ),
    )
    return ThresholdSet(
        policy_id=policy_id,
        policy_kind=ThresholdPolicyKind.CLUSTER,
        scope=ThresholdScope.CLUSTER,
        target_quantile=target_quantile,
        values=tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=thresholds[item.client_id.value],
                policy_kind=ThresholdPolicyKind.CLUSTER,
                scope=ThresholdScope.CLUSTER,
                cluster_label=canonical_map[raw_label],
            )
            for item, raw_label in zip(calibration, raw_labels, strict=True)
        ),
        diagnostics=diagnostics,
    )

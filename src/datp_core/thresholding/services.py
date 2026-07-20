"""Concrete deterministic threshold estimators over benign-only score references."""

from __future__ import annotations

from collections.abc import Mapping
from math import ceil

from ..kernel.ids import ClientId
from ..kernel.values import Probability
from .domain import BenignCalibrationScores, ThresholdPolicyFamily, ThresholdPolicyId, ThresholdSet, ThresholdValue


def _quantile(values: tuple[float, ...], probability: Probability) -> float:
    ordered = tuple(sorted(values))
    position = (len(ordered) - 1) * probability.value
    lower, upper = int(position), ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def estimate_thresholds(
    family: ThresholdPolicyFamily,
    calibration: tuple[BenignCalibrationScores, ...],
    quantile: Probability,
    *,
    groups: Mapping[ClientId, str] | None = None,
    shrinkage_weight: Probability | None = None,
    minimum_count: int | None = None,
) -> ThresholdSet:
    if not calibration:
        raise ValueError("at least one benign calibration population is required")
    by_client = tuple(sorted(calibration, key=lambda item: item.client_id.value))
    local = {scores.client_id: _quantile(scores.values, quantile) for scores in by_client}
    pooled = tuple(value for scores in by_client for value in scores.values)
    shared = _quantile(pooled, quantile)
    if family is ThresholdPolicyFamily.QUANTILE:
        values = tuple(
            ThresholdValue(
                client_id=item.client_id,
                value=local[item.client_id],
                owner="client",
                calibration_count=len(item.values),
            )
            for item in by_client
        )
    elif family is ThresholdPolicyFamily.CONFORMAL:
        values = tuple(
            ThresholdValue(
                client_id=item.client_id,
                value=_conformal(item.values, quantile),
                owner="client",
                calibration_count=len(item.values),
            )
            for item in by_client
        )
    elif family is ThresholdPolicyFamily.SHRINKAGE:
        weight = shrinkage_weight or Probability(0.5)
        values = tuple(
            ThresholdValue(
                client_id=item.client_id,
                value=weight.value * local[item.client_id] + (1.0 - weight.value) * shared,
                owner="local_global",
                calibration_count=len(item.values),
            )
            for item in by_client
        )
    elif family is ThresholdPolicyFamily.CALIBRATION_FALLBACK:
        required = minimum_count if minimum_count is not None else 1
        values = tuple(
            ThresholdValue(
                client_id=item.client_id,
                value=local[item.client_id] if len(item.values) >= required else shared,
                owner="client" if len(item.values) >= required else "shared_fallback",
                calibration_count=len(item.values),
                fallback_used=len(item.values) < required,
            )
            for item in by_client
        )
    elif family is ThresholdPolicyFamily.FEDERATED_SUMMARY:
        values = tuple(
            ThresholdValue(
                client_id=item.client_id, value=shared, owner="federated_summary", calibration_count=len(item.values)
            )
            for item in by_client
        )
    else:
        values = _grouped(by_client, local, quantile, groups, family)
    return ThresholdSet(family=family, quantile=quantile, values=values)


def estimate_policy(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    quantile: Probability,
    *,
    groups: Mapping[ClientId, str] | None = None,
    shrinkage_weight: Probability | None = None,
    minimum_count: int | None = None,
    fixed_coefficient: float | None = None,
) -> ThresholdSet:
    """Dispatch all configured policies by policy identity, never experiment identity."""
    ordered = tuple(sorted(calibration, key=lambda item: item.client_id.value))
    if not ordered:
        raise ValueError("at least one benign calibration population is required")
    local = {item.client_id: _quantile(item.values, quantile) for item in ordered}
    pooled = _quantile(tuple(score for item in ordered for score in item.values), quantile)
    if policy_id is ThresholdPolicyId.LOCAL:
        return _threshold_set(ThresholdPolicyFamily.QUANTILE, quantile, ordered, local, "client")
    if policy_id in (ThresholdPolicyId.SHARED_POOLED, ThresholdPolicyId.CENTRALIZED):
        return _constant_set(ThresholdPolicyFamily.QUANTILE, quantile, ordered, pooled, "pooled")
    if policy_id is ThresholdPolicyId.SHARED_MEAN:
        threshold = sum(local.values()) / len(local)
        return _constant_set(ThresholdPolicyFamily.QUANTILE, quantile, ordered, threshold, "mean_local")
    if policy_id is ThresholdPolicyId.SHARED_WEIGHTED:
        total = sum(len(item.values) for item in ordered)
        threshold = sum(local[item.client_id] * len(item.values) for item in ordered) / total
        return _constant_set(ThresholdPolicyFamily.QUANTILE, quantile, ordered, threshold, "weighted_local")
    if policy_id is ThresholdPolicyId.FAMILY:
        values = _grouped(ordered, local, quantile, groups, ThresholdPolicyFamily.QUANTILE)
        return ThresholdSet(family=ThresholdPolicyFamily.QUANTILE, quantile=quantile, values=values)
    if policy_id in (
        ThresholdPolicyId.CLUSTER_K3_MEAN,
        ThresholdPolicyId.CLUSTER_K9_MEAN,
        ThresholdPolicyId.CLUSTER_K3_MEDIAN,
    ):
        values = _grouped(ordered, local, quantile, groups, ThresholdPolicyFamily.CLUSTER)
        return ThresholdSet(family=ThresholdPolicyFamily.CLUSTER, quantile=quantile, values=values)
    if policy_id is ThresholdPolicyId.CONFORMAL_LOCAL:
        values = tuple(
            ThresholdValue(
                client_id=item.client_id,
                value=_conformal(item.values, quantile),
                owner="client",
                calibration_count=len(item.values),
            )
            for item in ordered
        )
        return ThresholdSet(family=ThresholdPolicyFamily.CONFORMAL, quantile=quantile, values=values)
    if policy_id is ThresholdPolicyId.SHRINKAGE:
        return estimate_thresholds(
            ThresholdPolicyFamily.SHRINKAGE, ordered, quantile, shrinkage_weight=shrinkage_weight
        )
    if policy_id is ThresholdPolicyId.CALIBRATION_FALLBACK:
        return estimate_thresholds(
            ThresholdPolicyFamily.CALIBRATION_FALLBACK, ordered, quantile, minimum_count=minimum_count
        )
    if policy_id is ThresholdPolicyId.FEDERATED_FIXED and fixed_coefficient is None:
        raise ValueError("federated fixed-coefficient policy requires a configured coefficient")
    return _constant_set(ThresholdPolicyFamily.FEDERATED_SUMMARY, quantile, ordered, pooled, "federated_summary")


def _threshold_set(
    family: ThresholdPolicyFamily,
    quantile: Probability,
    calibration: tuple[BenignCalibrationScores, ...],
    thresholds: Mapping[ClientId, float],
    owner: str,
) -> ThresholdSet:
    values = tuple(
        ThresholdValue(
            client_id=item.client_id,
            value=thresholds[item.client_id],
            owner=owner,
            calibration_count=len(item.values),
        )
        for item in calibration
    )
    return ThresholdSet(family=family, quantile=quantile, values=values)


def _constant_set(
    family: ThresholdPolicyFamily,
    quantile: Probability,
    calibration: tuple[BenignCalibrationScores, ...],
    threshold: float,
    owner: str,
) -> ThresholdSet:
    values = tuple(
        ThresholdValue(
            client_id=item.client_id,
            value=threshold,
            owner=owner,
            calibration_count=len(item.values),
        )
        for item in calibration
    )
    return ThresholdSet(family=family, quantile=quantile, values=values)


def _conformal(values: tuple[float, ...], probability: Probability) -> float:
    rank = ceil((len(values) + 1) * probability.value)
    if rank > len(values):
        raise ValueError("configured conformal coverage is unattainable for calibration size")
    return tuple(sorted(values))[rank - 1]


def _grouped(
    calibration: tuple[BenignCalibrationScores, ...],
    local: Mapping[ClientId, float],
    quantile: Probability,
    groups: Mapping[ClientId, str] | None,
    family: ThresholdPolicyFamily,
) -> tuple[ThresholdValue, ...]:
    if groups is None:
        raise ValueError(f"{family.value} thresholds require explicit group ownership")
    buckets: dict[str, list[float]] = {}
    for item in calibration:
        buckets.setdefault(groups[item.client_id], []).append(local[item.client_id])
    owners = {group: _quantile(tuple(values), quantile) for group, values in buckets.items()}
    return tuple(
        ThresholdValue(
            client_id=item.client_id,
            value=owners[groups[item.client_id]],
            owner=groups[item.client_id],
            calibration_count=len(item.values),
        )
        for item in calibration
    )

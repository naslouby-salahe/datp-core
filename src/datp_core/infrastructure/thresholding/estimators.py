"""Configuration-driven implementations of every threshold policy."""

from __future__ import annotations

import math
from typing import cast

import numpy as np
from scipy.stats import skew
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from datp_core.domain.identifiers import ThresholdPolicyId
from datp_core.domain.thresholding import (
    BenignCalibrationScores,
    CalibrationFallbackThresholdPolicyRecord,
    CentralizedPooledThresholdPolicyRecord,
    ClusterThresholdPolicyRecord,
    FamilyMeanThresholdPolicyRecord,
    FederatedFixedCoefficientThresholdPolicyRecord,
    FederatedMatchedExceedanceThresholdPolicyRecord,
    LocalGlobalShrinkageThresholdPolicyRecord,
    LocalQuantileThresholdPolicyRecord,
    SharedMeanThresholdPolicyRecord,
    SharedPooledThresholdPolicyRecord,
    SharedWeightedThresholdPolicyRecord,
    SplitConformalThresholdPolicyRecord,
    ThresholdPolicyRecord,
    ThresholdRecord,
    ThresholdSet,
)
from datp_core.domain.values import Probability
from datp_core.infrastructure.thresholding.base import ThresholdConstructionRequest, ThresholdEstimator


def _quantile(values: tuple[float, ...], quantile: float) -> float:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError("Threshold construction requires finite non-empty calibration scores")
    result = float(np.quantile(array, quantile, method="linear"))
    if not math.isfinite(result):
        raise ValueError("Threshold construction produced a non-finite quantile")
    return result


def _policy_quantile(policy: ThresholdPolicyRecord) -> Probability:
    if isinstance(policy, SplitConformalThresholdPolicyRecord):
        return Probability(policy.nominal_coverage)
    return Probability(policy.quantile)


def _records(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    thresholds: dict[str, float],
    owner: str,
    quantile: Probability,
    lambdas: dict[str, float] | None = None,
) -> ThresholdSet:
    return ThresholdSet(
        policy_id=policy_id,
        target_quantile=quantile,
        values=tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=thresholds[item.client_id.value],
                owner=owner,
                effective_lambda=None if lambdas is None else lambdas[item.client_id.value],
            )
            for item in calibration
        ),
    )


class ConfiguredThresholdEstimator(ThresholdEstimator):
    """One immutable estimator bound to a single resolved policy configuration."""

    def __init__(self, policy_id: ThresholdPolicyId, policy: ThresholdPolicyRecord) -> None:
        self._policy_id = policy_id
        self._policy = policy

    @property
    def policy_id(self) -> ThresholdPolicyId:
        return self._policy_id

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet:
        if request.policy_id != self._policy_id or request.policy != self._policy:
            raise ValueError("Threshold estimator request does not match its resolved policy")
        calibration = request.calibration
        if not calibration:
            raise ValueError("Threshold construction requires at least one eligible client")
        policy = self._policy
        quantile = _policy_quantile(policy)
        local = {item.client_id.value: _quantile(item.values, quantile.value) for item in calibration}

        if isinstance(policy, SharedMeanThresholdPolicyRecord):
            shared = float(np.mean(tuple(local.values())))
            return _records(self._policy_id, calibration, {key: shared for key in local}, "shared_mean", quantile)
        if isinstance(policy, (SharedPooledThresholdPolicyRecord, CentralizedPooledThresholdPolicyRecord)):
            pooled = tuple(value for item in calibration for value in item.values)
            threshold = _quantile(pooled, quantile.value)
            return _records(self._policy_id, calibration, {key: threshold for key in local}, "pooled", quantile)
        if isinstance(policy, SharedWeightedThresholdPolicyRecord):
            count = sum(len(item.values) for item in calibration)
            if count == 0:
                raise ValueError("Weighted threshold has no calibration rows")
            threshold = sum(len(item.values) * local[item.client_id.value] for item in calibration) / count
            return _records(
                self._policy_id, calibration, {key: threshold for key in local}, "shared_weighted", quantile
            )
        if isinstance(policy, LocalQuantileThresholdPolicyRecord):
            return _records(self._policy_id, calibration, local, "local", quantile)
        if isinstance(policy, FamilyMeanThresholdPolicyRecord):
            if request.family_map is None:
                raise ValueError("Family threshold requires an explicit resolved client-family mapping")
            families: dict[str, list[float]] = {}
            for item in calibration:
                family = request.family_map.get(item.client_id.value)
                if family is None:
                    raise ValueError(f"Client '{item.client_id.value}' has no configured family")
                families.setdefault(family, []).append(local[item.client_id.value])
            family_thresholds = {family: float(np.mean(values)) for family, values in families.items()}
            thresholds = {
                item.client_id.value: family_thresholds[request.family_map[item.client_id.value]]
                for item in calibration
            }
            return _records(self._policy_id, calibration, thresholds, "family_mean", quantile)
        if isinstance(policy, ClusterThresholdPolicyRecord):
            return self._cluster(request, local, quantile)
        if isinstance(policy, SplitConformalThresholdPolicyRecord):
            return self._conformal(calibration, policy, quantile)
        if isinstance(policy, LocalGlobalShrinkageThresholdPolicyRecord):
            coefficient = (
                policy.shrinkage_weight if policy.shrinkage_weight is not None else request.selected_coefficient
            )
            if coefficient is None:
                raise ValueError("Shrinkage threshold requires an experiment-selected coefficient")
            return self._shrinkage(calibration, local, coefficient, quantile)
        if isinstance(policy, CalibrationFallbackThresholdPolicyRecord):
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
            return _records(self._policy_id, calibration, thresholds, "calibration_shrinkage", quantile, lambdas)
        if isinstance(policy, FederatedMatchedExceedanceThresholdPolicyRecord):
            return self._federated_matched(calibration, policy, quantile)
        if isinstance(policy, FederatedFixedCoefficientThresholdPolicyRecord):
            coefficient = policy.fixed_k if policy.fixed_k is not None else request.selected_coefficient
            if coefficient is None:
                raise ValueError("Fixed-k threshold requires an experiment-selected coefficient")
            return self._federated_fixed(calibration, coefficient, quantile)
        raise TypeError(f"Unsupported threshold policy configuration: {type(policy).__name__}")

    def _cluster(
        self,
        request: ThresholdConstructionRequest,
        local: dict[str, float],
        quantile: Probability,
    ) -> ThresholdSet:
        policy = self._policy
        assert isinstance(policy, ClusterThresholdPolicyRecord)
        calibration = request.calibration
        if len(calibration) < policy.cluster_count:
            raise ValueError("Cluster threshold has fewer eligible clients than configured clusters")
        rows = []
        for item in calibration:
            values = np.asarray(item.values, dtype=np.float64)
            rows.append(
                (
                    float(np.mean(values)),
                    float(np.std(values)),
                    float(skew(values)) if len(values) > 2 else 0.0,
                    local[item.client_id.value],
                )
            )
        features = np.asarray(rows, dtype=np.float64)
        if len(np.unique(features, axis=0)) < 2:
            raise ValueError("Cluster threshold has a degenerate fingerprint matrix")
        clustering = policy.clustering
        random_seed = clustering.get("random_seed")
        runs = clustering.get("initialization_runs")
        maximum_iterations = clustering.get("maximum_iterations")
        tolerance = clustering.get("convergence_tolerance")
        if not isinstance(random_seed, int) or isinstance(random_seed, bool):
            raise ValueError("Cluster policy has invalid authored integer parameters")
        if not isinstance(runs, int) or isinstance(runs, bool):
            raise ValueError("Cluster policy has invalid authored integer parameters")
        if not isinstance(maximum_iterations, int) or isinstance(maximum_iterations, bool):
            raise ValueError("Cluster policy has invalid authored integer parameters")
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
        aggregation = np.median if policy.aggregation == "robust_median" else np.mean
        aggregate = {label: float(aggregation(values)) for label, values in buckets.items()}
        thresholds = {
            item.client_id.value: aggregate[int(label)] for item, label in zip(calibration, labels, strict=True)
        }
        return _records(self._policy_id, calibration, thresholds, f"cluster_k{policy.cluster_count}", quantile)

    def _conformal(
        self,
        calibration: tuple[BenignCalibrationScores, ...],
        policy: SplitConformalThresholdPolicyRecord,
        quantile: Probability,
    ) -> ThresholdSet:
        thresholds: dict[str, float] = {}
        for item in calibration:
            scores = np.sort(np.asarray(item.values, dtype=np.float64))
            if len(scores) < policy.minimum_sample_count:
                raise ValueError("Conformal threshold is unattainable for the authored minimum sample count")
            rank = min(math.ceil((len(scores) + 1) * (1.0 - policy.coverage_alpha)), len(scores))
            thresholds[item.client_id.value] = float(scores[rank - 1])
        return _records(self._policy_id, calibration, thresholds, "split_conformal", quantile)

    def _shrinkage(
        self,
        calibration: tuple[BenignCalibrationScores, ...],
        local: dict[str, float],
        coefficient: float,
        quantile: Probability,
    ) -> ThresholdSet:
        if not 0.0 <= coefficient <= 1.0:
            raise ValueError("Shrinkage coefficient is outside the authored permitted range")
        shared = float(np.mean(tuple(local.values())))
        thresholds = {key: coefficient * value + (1.0 - coefficient) * shared for key, value in local.items()}
        return _records(
            self._policy_id,
            calibration,
            thresholds,
            "local_global_shrinkage",
            quantile,
            {key: coefficient for key in local},
        )

    def _federated_moments(self, calibration: tuple[BenignCalibrationScores, ...]) -> tuple[float, float]:
        counts = np.asarray([len(item.values) for item in calibration], dtype=np.float64)
        means = np.asarray([np.mean(item.values) for item in calibration], dtype=np.float64)
        variances = np.asarray([np.var(item.values) for item in calibration], dtype=np.float64)
        total = float(np.sum(counts))
        if total <= 0.0:
            raise ValueError("Federated summary threshold has no calibration rows")
        mean = float(np.sum(counts * means) / total)
        variance = float(np.sum(counts * variances) / total + np.sum(counts * (means - mean) ** 2) / total)
        return mean, math.sqrt(variance)

    def _federated_matched(
        self,
        calibration: tuple[BenignCalibrationScores, ...],
        policy: FederatedMatchedExceedanceThresholdPolicyRecord,
        quantile: Probability,
    ) -> ThresholdSet:
        minimum = policy.candidate_grid.get("minimum")
        maximum = policy.candidate_grid.get("maximum")
        step = policy.candidate_grid.get("step")
        if not isinstance(minimum, float) or not isinstance(maximum, float) or not isinstance(step, float):
            raise ValueError("Matched-exceedance policy has an invalid authored candidate grid")
        if step <= 0.0:
            raise ValueError("Matched-exceedance policy has an invalid authored candidate grid")
        mean, standard_deviation = self._federated_moments(calibration)
        candidates = np.arange(minimum, maximum + step / 2.0, step)
        scores = np.asarray([score for item in calibration for score in item.values], dtype=np.float64)
        achieved = np.asarray([np.mean(scores > mean + candidate * standard_deviation) for candidate in candidates])
        deviation = np.abs(achieved - (1.0 - quantile.value))
        winner = candidates[np.flatnonzero(deviation == np.min(deviation))[-1]]
        threshold = mean + float(winner) * standard_deviation
        return _records(
            self._policy_id,
            calibration,
            {item.client_id.value: threshold for item in calibration},
            "federated_matched_exceedance",
            quantile,
        )

    def _federated_fixed(
        self, calibration: tuple[BenignCalibrationScores, ...], coefficient: float, quantile: Probability
    ) -> ThresholdSet:
        mean, standard_deviation = self._federated_moments(calibration)
        threshold = mean + coefficient * standard_deviation
        return _records(
            self._policy_id,
            calibration,
            {item.client_id.value: threshold for item in calibration},
            "federated_fixed_k",
            quantile,
        )

"""All 14 scientific threshold estimator policy implementations."""

from __future__ import annotations

import numpy as np
from scipy.stats import skew
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from datp_core.domain.identifiers import ThresholdPolicyId
from datp_core.domain.thresholding import BenignCalibrationScores, ThresholdRecord, ThresholdSet
from datp_core.domain.values import Probability
from datp_core.infrastructure.thresholding.base import ThresholdEstimator

DEFAULT_Q = Probability(0.95)


def _quantile_1d(arr: np.ndarray, q: float) -> float:
    if len(arr) == 0:
        return 0.0
    return float(np.quantile(arr, q, method="linear"))


class SharedMeanThresholdEstimator(ThresholdEstimator):
    @property
    def policy_id(self) -> ThresholdPolicyId:
        return ThresholdPolicyId("shared_mean_p95")

    def estimate(
        self,
        calibration: tuple[BenignCalibrationScores, ...],
        quantile: Probability = DEFAULT_Q,
        **kwargs: object,
    ) -> ThresholdSet:
        local_quantiles = [
            _quantile_1d(np.array(item.values, dtype=np.float64), quantile.value)
            for item in calibration
        ]
        shared_val = float(np.mean(local_quantiles))
        values = tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=shared_val,
                owner="shared_global",
                effective_lambda=None,
            )
            for item in calibration
        )
        return ThresholdSet(policy_id=self.policy_id, values=values)


class PooledThresholdEstimator(ThresholdEstimator):
    def __init__(self, policy_name: str) -> None:
        self._policy_id = ThresholdPolicyId(policy_name)

    @property
    def policy_id(self) -> ThresholdPolicyId:
        return self._policy_id

    def estimate(
        self,
        calibration: tuple[BenignCalibrationScores, ...],
        quantile: Probability = DEFAULT_Q,
        **kwargs: object,
    ) -> ThresholdSet:
        all_scores = np.concatenate([np.array(item.values, dtype=np.float64) for item in calibration])
        pooled_thresh = _quantile_1d(all_scores, quantile.value)
        values = tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=pooled_thresh,
                owner="shared_pooled",
                effective_lambda=None,
            )
            for item in calibration
        )
        return ThresholdSet(policy_id=self.policy_id, values=values)


class WeightedSharedThresholdEstimator(ThresholdEstimator):
    @property
    def policy_id(self) -> ThresholdPolicyId:
        return ThresholdPolicyId("shared_weighted_p95")

    def estimate(
        self,
        calibration: tuple[BenignCalibrationScores, ...],
        quantile: Probability = DEFAULT_Q,
        **kwargs: object,
    ) -> ThresholdSet:
        counts = np.array([len(item.values) for item in calibration], dtype=np.float64)
        local_qs = np.array(
            [_quantile_1d(np.array(item.values, dtype=np.float64), quantile.value) for item in calibration],
            dtype=np.float64,
        )
        total = np.sum(counts)
        weighted_thresh = float(np.sum(local_qs * counts) / total) if total > 0 else float(np.mean(local_qs))
        values = tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=weighted_thresh,
                owner="shared_weighted",
                effective_lambda=None,
            )
            for item in calibration
        )
        return ThresholdSet(policy_id=self.policy_id, values=values)


class LocalQuantileThresholdEstimator(ThresholdEstimator):
    @property
    def policy_id(self) -> ThresholdPolicyId:
        return ThresholdPolicyId("local_quantile_p95")

    def estimate(
        self,
        calibration: tuple[BenignCalibrationScores, ...],
        quantile: Probability = DEFAULT_Q,
        **kwargs: object,
    ) -> ThresholdSet:
        values = tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=_quantile_1d(np.array(item.values, dtype=np.float64), quantile.value),
                owner="local_only",
                effective_lambda=None,
            )
            for item in calibration
        )
        return ThresholdSet(policy_id=self.policy_id, values=values)


class FamilyMeanThresholdEstimator(ThresholdEstimator):
    @property
    def policy_id(self) -> ThresholdPolicyId:
        return ThresholdPolicyId("family_mean_p95")

    def estimate(
        self,
        calibration: tuple[BenignCalibrationScores, ...],
        quantile: Probability = DEFAULT_Q,
        **kwargs: object,
    ) -> ThresholdSet:
        family_map = kwargs.get("family_map")
        if not isinstance(family_map, dict):
            raise ValueError("FamilyMeanThresholdEstimator requires explicit family group mapping")

        local_q = {
            item.client_id: _quantile_1d(np.array(item.values, dtype=np.float64), quantile.value)
            for item in calibration
        }
        buckets: dict[str, list[float]] = {}
        for item in calibration:
            fam = family_map.get(item.client_id.value, "unknown")
            buckets.setdefault(fam, []).append(local_q[item.client_id])

        fam_means = {fam: float(np.mean(vals)) for fam, vals in buckets.items()}
        values = tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=fam_means[family_map.get(item.client_id.value, "unknown")],
                owner="family_mean",
                effective_lambda=None,
            )
            for item in calibration
        )
        return ThresholdSet(policy_id=self.policy_id, values=values)


class ClusterThresholdEstimator(ThresholdEstimator):
    def __init__(self, policy_name: str, k_clusters: int, use_median: bool = False) -> None:
        self._policy_id = ThresholdPolicyId(policy_name)
        self._k = k_clusters
        self._use_median = use_median

    @property
    def policy_id(self) -> ThresholdPolicyId:
        return self._policy_id

    def estimate(
        self,
        calibration: tuple[BenignCalibrationScores, ...],
        quantile: Probability = DEFAULT_Q,
        **kwargs: object,
    ) -> ThresholdSet:
        local_q = [_quantile_1d(np.array(item.values, dtype=np.float64), quantile.value) for item in calibration]
        features = []
        for item, lq in zip(calibration, local_q, strict=False):
            arr = np.array(item.values, dtype=np.float64)
            m = float(np.mean(arr))
            s = float(np.std(arr))
            sk = float(skew(arr)) if len(arr) > 2 else 0.0
            features.append([m, s, sk, lq])

        feat_arr = np.array(features, dtype=np.float64)
        scaler = StandardScaler()
        scaled_feat = scaler.fit_transform(feat_arr)

        kmeans = KMeans(n_clusters=self._k, random_state=42, n_init="auto", max_iter=300, tol=1e-4)
        labels = kmeans.fit_predict(scaled_feat)

        cluster_buckets: dict[int, list[float]] = {}
        for idx, lbl in enumerate(labels):
            cluster_buckets.setdefault(int(lbl), []).append(local_q[idx])

        agg_func = np.median if self._use_median else np.mean
        cluster_thresh = {c: float(agg_func(vals)) for c, vals in cluster_buckets.items()}

        values = tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=cluster_thresh[int(labels[i])],
                owner=f"cluster_k{self._k}",
                effective_lambda=None,
            )
            for i, item in enumerate(calibration)
        )
        return ThresholdSet(policy_id=self.policy_id, values=values)


class SplitConformalThresholdEstimator(ThresholdEstimator):
    @property
    def policy_id(self) -> ThresholdPolicyId:
        return ThresholdPolicyId("conformal_local_p95")

    def estimate(
        self,
        calibration: tuple[BenignCalibrationScores, ...],
        quantile: Probability = DEFAULT_Q,
        **kwargs: object,
    ) -> ThresholdSet:
        alpha = 1.0 - quantile.value
        min_req = int(kwargs.get("minimum_count", 100))  # type: ignore

        records = []
        for item in calibration:
            scores = np.sort(np.array(item.values, dtype=np.float64))
            n = len(scores)
            if n < min_req:
                msg = (
                    f"Conformal quantile unattainable for client {item.client_id.value} "
                    f"(sample size n={n} < min={min_req})"
                )
                raise ValueError(msg)
            k = int(np.ceil((n + 1) * (1.0 - alpha)))
            k_clamped = min(max(k, 1), n)
            conformal_t = float(scores[k_clamped - 1])
            records.append(
                ThresholdRecord(
                    client_id=item.client_id,
                    threshold=conformal_t,
                    owner="conformal_split",
                    effective_lambda=None,
                )
            )
        return ThresholdSet(policy_id=self.policy_id, values=tuple(records))


class LocalGlobalShrinkageEstimator(ThresholdEstimator):
    @property
    def policy_id(self) -> ThresholdPolicyId:
        return ThresholdPolicyId("local_global_shrinkage_p95")

    def estimate(
        self,
        calibration: tuple[BenignCalibrationScores, ...],
        quantile: Probability = DEFAULT_Q,
        **kwargs: object,
    ) -> ThresholdSet:
        lam = float(kwargs.get("shrinkage_weight", 0.5))  # type: ignore
        if not (0.0 <= lam <= 1.0):
            raise ValueError("Shrinkage weight lambda must be in [0, 1]")

        local_q = {
            item.client_id: _quantile_1d(np.array(item.values, dtype=np.float64), quantile.value)
            for item in calibration
        }
        shared_val = float(np.mean(list(local_q.values())))

        records = tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=lam * local_q[item.client_id] + (1.0 - lam) * shared_val,
                owner="local_global",
                effective_lambda=lam,
            )
            for item in calibration
        )
        return ThresholdSet(policy_id=self.policy_id, values=records)


class CalibrationFallbackEstimator(ThresholdEstimator):
    @property
    def policy_id(self) -> ThresholdPolicyId:
        return ThresholdPolicyId("calibration_fallback_p95")

    def estimate(
        self,
        calibration: tuple[BenignCalibrationScores, ...],
        quantile: Probability = DEFAULT_Q,
        **kwargs: object,
    ) -> ThresholdSet:
        min_req = int(kwargs.get("minimum_count", 100))  # type: ignore
        local_q = {
            item.client_id: _quantile_1d(np.array(item.values, dtype=np.float64), quantile.value)
            for item in calibration
        }
        shared_val = float(np.mean(list(local_q.values())))

        records = []
        for item in calibration:
            if len(item.values) < min_req:
                thresh = shared_val
                owner = "fallback_global"
                eff_lam = 0.0
            else:
                thresh = local_q[item.client_id]
                owner = "local_only"
                eff_lam = 1.0

            records.append(
                ThresholdRecord(
                    client_id=item.client_id,
                    threshold=thresh,
                    owner=owner,
                    effective_lambda=eff_lam,
                )
            )

        return ThresholdSet(policy_id=self.policy_id, values=tuple(records))


class FederatedMatchedExceedanceEstimator(ThresholdEstimator):
    @property
    def policy_id(self) -> ThresholdPolicyId:
        return ThresholdPolicyId("federated_matched_exceedance_p95")

    def estimate(
        self,
        calibration: tuple[BenignCalibrationScores, ...],
        quantile: Probability = DEFAULT_Q,
        **kwargs: object,
    ) -> ThresholdSet:
        pooled = np.concatenate([np.array(item.values, dtype=np.float64) for item in calibration])
        matched_thresh = _quantile_1d(pooled, quantile.value)
        values = tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=matched_thresh,
                owner="federated_exceedance",
                effective_lambda=None,
            )
            for item in calibration
        )
        return ThresholdSet(policy_id=self.policy_id, values=values)


class FederatedFixedCoefficientEstimator(ThresholdEstimator):
    @property
    def policy_id(self) -> ThresholdPolicyId:
        return ThresholdPolicyId("federated_fixed_k30")

    def estimate(
        self,
        calibration: tuple[BenignCalibrationScores, ...],
        quantile: Probability = DEFAULT_Q,
        **kwargs: object,
    ) -> ThresholdSet:
        k = float(kwargs.get("fixed_k", 3.0))  # type: ignore
        records = []
        for item in calibration:
            arr = np.array(item.values, dtype=np.float64)
            mu = float(np.mean(arr))
            sigma = float(np.std(arr))
            records.append(
                ThresholdRecord(
                    client_id=item.client_id,
                    threshold=mu + k * sigma,
                    owner="federated_fixed_coeff",
                    effective_lambda=None,
                )
            )
        return ThresholdSet(policy_id=self.policy_id, values=tuple(records))

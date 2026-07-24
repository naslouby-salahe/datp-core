"""Runtime threshold models: ThresholdRecord, ThresholdSet, ThresholdConstructionRequest, and typed diagnostics."""

from __future__ import annotations

import math
from dataclasses import dataclass

from attrs import define

from datp_core.core.identifiers import ClientId, PopulationId, ThresholdPolicyId
from datp_core.core.numbers import NonNegativeFloat, Probability
from datp_core.thresholding.policies.common import BenignCalibrationScores
from datp_core.thresholding.policies.enums import ConformalAttainabilityStatus, ThresholdOwnerKind
from datp_core.thresholding.policies.union import ThresholdPolicyRecord


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdRecord:
    client_id: ClientId
    threshold: NonNegativeFloat | float
    owner: ThresholdOwnerKind
    effective_lambda: float | None = None
    cluster_label: int | None = None
    finite_sample_rank: int | None = None
    attainability_status: ConformalAttainabilityStatus | None = None

    def __post_init__(self) -> None:
        val = float(self.threshold)
        if not math.isfinite(val):
            raise ValueError("Produced threshold value must be finite")
        if val < 0.0:
            raise ValueError("Produced threshold value cannot be negative")
        if self.finite_sample_rank is not None and self.finite_sample_rank < 1:
            raise ValueError("Conformal finite-sample rank must be positive")
        if self.cluster_label is not None and self.cluster_label < 0:
            raise ValueError("Cluster label must be non-negative")


@define(frozen=True, slots=True, kw_only=True)
class MatchedExceedanceDiagnostics:
    selected_coefficient: float
    candidate_grid_minimum: float
    candidate_grid_maximum: float
    candidate_grid_step: float
    pooled_mean: float
    pooled_standard_deviation: float
    achieved_exceedance: tuple[tuple[float, float], ...]
    tie_set: tuple[float, ...]


@define(frozen=True, slots=True, kw_only=True)
class ClusterDiagnostics:
    cluster_count: int
    cluster_labels: tuple[tuple[str, int], ...]


ThresholdDiagnostics = MatchedExceedanceDiagnostics | ClusterDiagnostics | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdSet:
    policy_id: ThresholdPolicyId
    values: tuple[ThresholdRecord, ...]
    target_quantile: Probability
    diagnostics: object = None

    def get_client_threshold(self, client_id: ClientId) -> ThresholdRecord:
        for rec in self.values:
            if rec.client_id == client_id:
                return rec
        raise KeyError(f"No threshold record for client: {client_id}")


@define(frozen=True, slots=True, kw_only=True)
class ThresholdConstructionRequest:
    policy_id: ThresholdPolicyId
    policy: ThresholdPolicyRecord
    calibration: tuple[BenignCalibrationScores, ...]
    population_id: PopulationId
    family_map: dict[str, str] | None = None
    selected_coefficient: float | None = None


def build_threshold_set(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    thresholds: dict[str, float],
    owner: ThresholdOwnerKind,
    target_quantile: Probability,
    lambdas: dict[str, float] | None = None,
    cluster_labels: dict[str, int] | None = None,
    conformal_ranks: dict[str, int] | None = None,
    conformal_attainability: dict[str, ConformalAttainabilityStatus] | None = None,
    diagnostics: object = None,
) -> ThresholdSet:
    return ThresholdSet(
        policy_id=policy_id,
        target_quantile=target_quantile,
        diagnostics=diagnostics,
        values=tuple(
            ThresholdRecord(
                client_id=item.client_id,
                threshold=thresholds[item.client_id.value],
                owner=owner,
                effective_lambda=None if lambdas is None else lambdas.get(item.client_id.value),
                cluster_label=None if cluster_labels is None else cluster_labels.get(item.client_id.value),
                finite_sample_rank=None if conformal_ranks is None else conformal_ranks.get(item.client_id.value),
                attainability_status=(
                    None if conformal_attainability is None else conformal_attainability.get(item.client_id.value)
                ),
            )
            for item in calibration
        ),
    )

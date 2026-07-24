"""Immutable stage-job identity context with cross-field validation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from datp_core.core.identifiers import ExperimentId, PopulationId, ThresholdPolicyId

if TYPE_CHECKING:
    from datp_core.experiments.catalogue.evaluations import RecalibrationMode


@dataclass(frozen=True, slots=True, kw_only=True)
class StageJobContext:
    experiment_id: ExperimentId
    seed: int | None = None
    evaluation_label: str | None = None
    population_id: PopulationId | None = None
    recalibration_mode: RecalibrationMode | None = None  # type: ignore[valid-type]
    threshold_policy_id: ThresholdPolicyId | None = None
    dataset_setup_id: str | None = None
    materialization_id: str | None = None
    partition_condition: str | None = None
    federated_proximal_mu: float | None = None
    ditto_proximal_weight: float | None = None
    threshold_quantile: float | None = None
    shrinkage_weight: float | None = None
    federated_summary_fixed_k: float | None = None
    calibration_sample_count: int | None = None
    calibration_replicate: int | None = None
    fingerprint_features: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        _validate_context(self)


def _validate_context(ctx: StageJobContext) -> None:
    if ctx.evaluation_label is not None and ctx.evaluation_label == "":
        raise ValueError("evaluation_label must not be blank")

    if ctx.partition_condition is not None and ctx.partition_condition == "":
        raise ValueError("partition_condition must not be blank")

    has_count = ctx.calibration_sample_count is not None
    has_replicate = ctx.calibration_replicate is not None
    if has_count != has_replicate:
        raise ValueError(
            "calibration_sample_count and calibration_replicate must be present together or absent together"
        )
    if has_count and ctx.calibration_sample_count is not None and ctx.calibration_sample_count < 1:
        raise ValueError("calibration_sample_count must be positive")
    if has_replicate and ctx.calibration_replicate is not None and ctx.calibration_replicate < 0:
        raise ValueError("calibration_replicate must be non-negative")

    for name in ("federated_proximal_mu", "ditto_proximal_weight", "threshold_quantile", "shrinkage_weight"):
        value = getattr(ctx, name)
        if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
            raise ValueError(f"{name} must be a finite number")

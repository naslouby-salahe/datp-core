"""Immutable typed stage-job context families with cross-field validation.

DataContext  — materialization / data-prep stages
TrainingContext — model training (adds FedProx/Ditto params)
EvaluationContext — threshold construction & operating-point evaluation
AnalysisContext — statistical analysis
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from datp_core.analysis.contracts import PrerequisiteExperimentResult
from datp_core.core.identifiers import ExperimentId, PopulationId, ThresholdPolicyId
from datp_core.experiments.catalogue.evaluations import RecalibrationMode


@dataclass(frozen=True, slots=True, kw_only=True)
class DataContext:
    """Context for data-materialization and data-prep pipeline stages."""

    experiment_id: ExperimentId
    seed: int | None = None
    population_id: PopulationId | None = None
    partition_condition: str | None = None

    def __post_init__(self) -> None:
        _validate_data_context(self)


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainingContext(DataContext):
    """Context for model-training stages (may carry FedProx / Ditto parameters)."""

    federated_proximal_mu: float | None = None
    ditto_proximal_weight: float | None = None

    def __post_init__(self) -> None:
        DataContext.__post_init__(self)
        _validate_training_context(self)


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluationContext(TrainingContext):
    """Context for threshold-construction and operating-point-evaluation stages."""

    evaluation_label: str | None = None
    threshold_policy_id: ThresholdPolicyId | None = None
    threshold_quantile: float | None = None
    shrinkage_weight: float | None = None
    federated_summary_fixed_k: float | None = None
    fingerprint_features: tuple[str, ...] | None = None
    calibration_sample_count: int | None = None
    calibration_replicate: int | None = None
    recalibration_mode: RecalibrationMode | None = None  # type: ignore[valid-type]

    def __post_init__(self) -> None:
        TrainingContext.__post_init__(self)
        _validate_evaluation_context(self)


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisContext:
    """Context for statistical-analysis stages."""

    experiment_id: ExperimentId
    analysis_label: str | None = None
    prerequisite_results: tuple[PrerequisiteExperimentResult, ...] = ()

    def __post_init__(self) -> None:
        _validate_analysis_context(self)


# -- Validators ----------------------------------------------------------------


def _validate_data_context(ctx: DataContext) -> None:
    if ctx.partition_condition is not None and ctx.partition_condition == "":
        raise ValueError("partition_condition must not be blank")


def _validate_training_context(ctx: TrainingContext) -> None:
    for name in ("federated_proximal_mu", "ditto_proximal_weight"):
        value = getattr(ctx, name)
        if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
            raise ValueError(f"{name} must be a finite number")


def _validate_evaluation_context(ctx: EvaluationContext) -> None:
    if ctx.evaluation_label is not None and ctx.evaluation_label == "":
        raise ValueError("evaluation_label must not be blank")

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

    for name in ("threshold_quantile", "shrinkage_weight"):
        value = getattr(ctx, name)
        if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
            raise ValueError(f"{name} must be a finite number")


def _validate_analysis_context(ctx: AnalysisContext) -> None:
    if ctx.analysis_label is not None and ctx.analysis_label == "":
        raise ValueError("analysis_label must not be blank")


# -- Context transformations ---------------------------------------------------


def score_context(context: TrainingContext | EvaluationContext) -> TrainingContext:
    """Derive a score-generation context preserving training/materialization identity.

    Strips evaluation-only fields: the returned ``TrainingContext`` is suitable
    for score-generation jobs or artifact lookups that share a training cell's
    identity.
    """
    return TrainingContext(
        experiment_id=context.experiment_id,
        seed=context.seed,
        partition_condition=context.partition_condition,
        population_id=context.population_id,
        federated_proximal_mu=context.federated_proximal_mu,
        ditto_proximal_weight=context.ditto_proximal_weight,
    )

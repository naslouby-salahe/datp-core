"""Expands validated experiment configuration into typed, executable paired-analysis cells.

Replaces implicit tuple-of-optionals sweep expansion with an explicit ``PairedAnalysisCell``: each
cell is one valid combination of the sweep dimensions a paired-threshold analysis can vary over
(partition condition, FedProx mu, Ditto weight, threshold quantile, shrinkage weight, calibration
sample count).
"""

from __future__ import annotations

from collections.abc import Mapping

from attrs import define

from datp_core.experiments.models import (
    ConditionSweepRecord,
    ExperimentRecord,
    PairedThresholdAnalysisRecord,
    ValueSweepRecord,
)
from datp_core.experiments.planning import calibration_sample_counts
from datp_core.learning.models import PersonalizationStrategy, TrainingProfileRecord


@define(frozen=True, slots=True, kw_only=True)
class PairedAnalysisCell:
    partition_condition: str | None
    proximal_mu: float | None
    ditto_weight: float | None
    threshold_quantile: float | None
    shrinkage_weight: float | None
    calibration_sample_count: int | None


@define(frozen=True, slots=True, kw_only=True)
class SweepDimensions:
    conditions: tuple[str | None, ...]
    mus: tuple[float | None, ...]
    ditto_weights: tuple[float | None, ...]
    threshold_quantiles: tuple[float | None, ...]
    shrinkage_weights: tuple[float | None, ...]
    calibration_sample_count_values: tuple[int | None, ...]


def resolve_sweep_dimensions(experiment: ExperimentRecord, training_profile: TrainingProfileRecord) -> SweepDimensions:
    conditions = tuple(
        condition.name
        for sweep in experiment.sweeps
        if isinstance(sweep, ConditionSweepRecord)
        for condition in sweep.conditions
    ) or (None,)
    mu_sweep = experiment.training_overrides.get("mu") if experiment.training_overrides is not None else None
    mu_sweep_name = mu_sweep.get("from_sweep") if isinstance(mu_sweep, Mapping) else None
    mus = tuple(
        float(value)
        for sweep in experiment.sweeps
        if isinstance(sweep, ValueSweepRecord) and sweep.name == mu_sweep_name
        for value in sweep.values
        if isinstance(value, float)
    ) or (None,)
    ditto_weights = (
        training_profile.personalization_parameter_grid or (None,)
        if training_profile.personalization == PersonalizationStrategy.DITTO
        else (None,)
    )
    threshold_quantiles = tuple(
        float(value)
        for sweep in experiment.sweeps
        if isinstance(sweep, ValueSweepRecord) and sweep.name == "threshold_quantile"
        for value in sweep.values
        if isinstance(value, float)
    ) or (None,)
    shrinkage_weights = tuple(
        float(value)
        for sweep in experiment.sweeps
        if isinstance(sweep, ValueSweepRecord) and sweep.name == "shrinkage_weight"
        for value in sweep.values
        if isinstance(value, float)
    ) or (None,)
    return SweepDimensions(
        conditions=conditions,
        mus=mus,
        ditto_weights=ditto_weights,
        threshold_quantiles=threshold_quantiles,
        shrinkage_weights=shrinkage_weights,
        calibration_sample_count_values=calibration_sample_counts(experiment),
    )


def expand_paired_analysis_cells(
    analysis: PairedThresholdAnalysisRecord, dimensions: SweepDimensions
) -> tuple[PairedAnalysisCell, ...]:
    calibration_sample_counts_for_analysis = (
        dimensions.calibration_sample_count_values if analysis.per_sweep_cell == "calibration_sample_count" else (None,)
    )
    return tuple(
        PairedAnalysisCell(
            partition_condition=condition,
            proximal_mu=proximal_mu,
            ditto_weight=ditto_weight,
            threshold_quantile=threshold_quantile,
            shrinkage_weight=shrinkage_weight,
            calibration_sample_count=calibration_sample_count,
        )
        for condition in dimensions.conditions
        for proximal_mu in dimensions.mus
        for ditto_weight in dimensions.ditto_weights
        for threshold_quantile in dimensions.threshold_quantiles
        for shrinkage_weight in dimensions.shrinkage_weights
        for calibration_sample_count in calibration_sample_counts_for_analysis
    )


__all__ = [
    "PairedAnalysisCell",
    "SweepDimensions",
    "expand_paired_analysis_cells",
    "resolve_sweep_dimensions",
]

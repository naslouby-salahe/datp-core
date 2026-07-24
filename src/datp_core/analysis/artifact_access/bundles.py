"""Typed multi-artifact bundles reused by more than one analysis capability."""

from __future__ import annotations

import polars as pl

from datp_core.analysis.artifact_access.metric_query import experiment_evaluation
from datp_core.analysis.artifact_access.reader import read_parquet_frame
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.artifacts.schemas.scores import validate_calibration_score_frame
from datp_core.artifacts.schemas.thresholds import validate_threshold_frame
from datp_core.core.identifiers import ExperimentId
from datp_core.experiments import ExperimentRecord
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.planning import score_context
from datp_core.pipeline.stages.context import StageJobContext


def threshold_and_calibration_frame(
    *,
    repository: ArtifactRepository,
    experiment: ExperimentRecord,
    seed: int,
    label: str,
    experiment_id: ExperimentId,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    evaluation = experiment_evaluation(experiment, label)
    context = StageJobContext(
        experiment_id=experiment.identifier,
        seed=seed,
        evaluation_label=label,
        population_id=evaluation.population_id,
        recalibration_mode=evaluation.recalibration_mode,
    )
    threshold = validate_threshold_frame(
        read_parquet_frame(
            repository,
            experiment_id,
            IdentityBuilder.threshold_node_key(context),
            missing_message=f"Quantile-estimation artifacts are unavailable for seed {seed}, label '{label}'",
        )
    )
    calibration = validate_calibration_score_frame(
        read_parquet_frame(
            repository,
            experiment_id,
            IdentityBuilder.calibration_score_node_key(score_context(context)),
            missing_message=f"Quantile-estimation artifacts are unavailable for seed {seed}, label '{label}'",
        )
    )
    return threshold, calibration


__all__ = ["threshold_and_calibration_frame"]

"""Deterministic output layouts derived only from scientific coordinates."""

from enum import StrEnum
from pathlib import Path

from datp_core.pipeline.planning import ExperimentCoordinate


class PublicationPathSegment(StrEnum):
    METRICS = "metrics"
    NO_MODEL_COEFFICIENT = "no_model_coefficient"
    NON_TEMPORAL = "non_temporal"


def evaluation_run_directory(root: Path, coordinate: ExperimentCoordinate) -> Path:
    """Metric-independent detector, threshold, and evaluation publication root."""
    temporal = (
        coordinate.temporal_state.value
        if coordinate.temporal_state is not None
        else PublicationPathSegment.NON_TEMPORAL.value
    )
    coefficient = (
        str(coordinate.model_coefficient.value)
        if coordinate.model_coefficient is not None
        else PublicationPathSegment.NO_MODEL_COEFFICIENT.value
    )
    return (
        root
        / coordinate.experiment.value
        / coordinate.evidence_role.value
        / coordinate.dataset.value
        / coordinate.population.value
        / coordinate.training_model.value
        / str(coordinate.training_seed.value)
        / coordinate.split_protocol.value
        / coordinate.preprocessing_protocol.value
        / coefficient
        / coordinate.threshold_method.value
        / temporal
    )


def experiment_output_directory(root: Path, coordinate: ExperimentCoordinate) -> Path:
    """Metric-specific analysis and completion root."""
    return (
        evaluation_run_directory(root, coordinate)
        / PublicationPathSegment.METRICS.value
        / coordinate.metric.value
    )


def artifact_path(root: Path, coordinate: ExperimentCoordinate, filename: str) -> Path:
    if not filename or filename in {".", ".."} or Path(filename).name != filename:
        raise ValueError("artifact filenames must be simple non-empty names")
    return experiment_output_directory(root, coordinate) / filename

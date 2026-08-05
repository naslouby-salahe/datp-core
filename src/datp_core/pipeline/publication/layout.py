"""Deterministic output layout derived only from scientific coordinates."""

from pathlib import Path

from datp_core.pipeline.planning import ExperimentCoordinate


def experiment_output_directory(root: Path, coordinate: ExperimentCoordinate) -> Path:
    temporal = coordinate.temporal_state.value if coordinate.temporal_state is not None else "static"
    coefficient = f"{coordinate.model_coefficient.value}" if coordinate.model_coefficient is not None else "unweighted"
    return (
        root
        / coordinate.experiment.value
        / coordinate.population.value
        / coordinate.training_model.value
        / str(coordinate.training_seed.value)
        / coordinate.preprocessing_protocol.value
        / coefficient
        / coordinate.threshold_method.value
        / coordinate.metric.value
        / temporal
    )


def artifact_path(root: Path, coordinate: ExperimentCoordinate, filename: str) -> Path:
    if not filename or filename in {".", ".."} or Path(filename).name != filename:
        raise ValueError("artifact filenames must be simple non-empty names")
    return experiment_output_directory(root, coordinate) / filename

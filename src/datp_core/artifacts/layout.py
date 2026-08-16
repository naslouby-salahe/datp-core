from enum import StrEnum
from pathlib import Path

from datp_core.experiments.common.coordinates import CoordinateIdentitySegment, ExperimentCoordinate


class PublicationArtifactDirectory(StrEnum):
    METRICS = "metrics"


def evaluation_run_directory(root: Path, coordinate: ExperimentCoordinate) -> Path:
    temporal = (
        coordinate.temporal_state.value
        if coordinate.temporal_state is not None
        else CoordinateIdentitySegment.NON_TEMPORAL.value
    )
    coefficient = (
        str(coordinate.model_coefficient.value)
        if coordinate.model_coefficient is not None
        else CoordinateIdentitySegment.NO_MODEL_COEFFICIENT.value
    )
    quantile = (
        f"q{coordinate.threshold_quantile.value}"
        if coordinate.threshold_quantile is not None
        else CoordinateIdentitySegment.CANONICAL_QUANTILE.value
    )
    kll_sketch_size = f"k{coordinate.kll_sketch_size.value}" if coordinate.kll_sketch_size is not None else "no_kll"
    if coordinate.controlled_partition_kind is None:
        partition = CoordinateIdentitySegment.NO_CONTROLLED_PARTITION.value
    elif coordinate.dirichlet_concentration is not None:
        partition = f"{coordinate.controlled_partition_kind.value}:{coordinate.dirichlet_concentration.value}"
    else:
        partition = coordinate.controlled_partition_kind.value
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
        / quantile
        / partition
        / kll_sketch_size
        / coordinate.threshold_estimator.value
    )


def experiment_output_directory(root: Path, coordinate: ExperimentCoordinate) -> Path:
    return (
        evaluation_run_directory(root, coordinate)
        / PublicationArtifactDirectory.METRICS.value
        / coordinate.metric.value
    )

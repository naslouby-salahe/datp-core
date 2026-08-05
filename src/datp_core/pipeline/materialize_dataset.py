"""Canonical dataset materialization stage owned by the pipeline."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.datasets.catalogue import DatasetPublication, dataset_binding
from datp_core.datasets.core.contracts import raw_dataset_root
from datp_core.domain.enums import DatasetId, ReusableDataCoordinateKind
from datp_core.pipeline.execution import PipelineStage


@dataclass(frozen=True, slots=True, kw_only=True)
class MaterializeDatasetRequest:
    data_root: Path
    datasets: tuple[DatasetId, ...]

    def __post_init__(self) -> None:
        if not self.datasets or len(self.datasets) != len(frozenset(self.datasets)):
            raise ValueError("dataset materialization requires unique dataset identities")


@dataclass(frozen=True, slots=True, kw_only=True)
class MaterializeDatasetResult:
    stage: PipelineStage
    publications: tuple[DatasetPublication, ...]


def materialize_dataset(request: MaterializeDatasetRequest) -> MaterializeDatasetResult:
    canonical_root = request.data_root / ReusableDataCoordinateKind.CANONICAL
    publications = tuple(
        dataset_binding(dataset).publish(raw_dataset_root(dataset), canonical_root) for dataset in request.datasets
    )
    return MaterializeDatasetResult(
        stage=PipelineStage.MATERIALIZE_DATASET,
        publications=publications,
    )

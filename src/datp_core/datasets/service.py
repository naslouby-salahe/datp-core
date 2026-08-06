"""Application service for canonical dataset publication."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.datasets.paths import canonical_root_under, raw_dataset_root
from datp_core.datasets.registry import DatasetPublication, dataset_binding
from datp_core.domain.enums import DatasetId


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetMaterializationRequest:
    data_root: Path
    datasets: tuple[DatasetId, ...]

    def __post_init__(self) -> None:
        if not self.datasets or len(self.datasets) != len(frozenset(self.datasets)):
            raise ValueError("dataset materialization requires unique dataset identities")


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetMaterializationResult:
    publications: tuple[DatasetPublication, ...]


def materialize_datasets(request: DatasetMaterializationRequest) -> DatasetMaterializationResult:
    """Publish every requested dataset through its authoritative binding."""
    publications = tuple(
        dataset_binding(dataset).publish(
            raw_dataset_root(request.data_root, dataset),
            canonical_root_under(request.data_root, dataset).parent,
        )
        for dataset in request.datasets
    )
    return DatasetMaterializationResult(publications=publications)

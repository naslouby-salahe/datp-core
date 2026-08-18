from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

from datp_core.core.identifiers import DatasetId
from datp_core.data.materialization import MaterializationProgress
from datp_core.data.paths import canonical_root_under, raw_dataset_root
from datp_core.data.registry import DatasetPublication, dataset_binding


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetMaterializationRequest:
    data_root: Path
    datasets: tuple[DatasetId, ...]
    overwrite: bool

    def __post_init__(self) -> None:
        if not self.datasets or len(self.datasets) != len(frozenset(self.datasets)):
            raise ValueError("dataset materialization requires unique dataset identities")


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetMaterializationResult:
    publications: tuple[DatasetPublication, ...]


def materialize_datasets(
    request: DatasetMaterializationRequest,
    *,
    progress: MaterializationProgress | None = None,
) -> DatasetMaterializationResult:
    publications: list[DatasetPublication] = []
    for dataset in request.datasets:
        canonical_root = canonical_root_under(request.data_root, dataset)
        if request.overwrite and canonical_root.exists():
            rmtree(canonical_root)
        publications.append(
            dataset_binding(dataset).publish(
                raw_dataset_root(request.data_root, dataset),
                canonical_root.parent,
                progress=progress,
            )
        )
    return DatasetMaterializationResult(publications=tuple(publications))

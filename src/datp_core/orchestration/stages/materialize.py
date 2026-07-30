"""Stage: publish or reuse canonical dataset materializations under the data root."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.artifacts.coordinates import raw_dataset_root
from datp_core.datasets.catalogue import DatasetPublication, dataset_binding
from datp_core.domain.enums import DatasetId, ReusableDataCoordinateKind, StageOperationId


@dataclass(frozen=True, slots=True)
class MaterializeCanonicalDatasetsRequest:
    data_root: Path
    datasets: tuple[DatasetId, ...]


@dataclass(frozen=True, slots=True)
class MaterializeCanonicalDatasetsResult:
    stage: StageOperationId
    publications: tuple[DatasetPublication, ...]


def materialize_canonical_datasets_stage(
    request: MaterializeCanonicalDatasetsRequest,
) -> MaterializeCanonicalDatasetsResult:
    """Materialize every requested dataset under the canonical root of data_root."""
    canonical_root = request.data_root / ReusableDataCoordinateKind.CANONICAL
    publications = tuple(
        dataset_binding(dataset).publish(raw_dataset_root(dataset), canonical_root) for dataset in request.datasets
    )
    return MaterializeCanonicalDatasetsResult(
        stage=StageOperationId.MATERIALIZE,
        publications=publications,
    )

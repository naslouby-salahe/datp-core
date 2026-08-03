"""Stage: publish or reuse canonical dataset materializations under the data root."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.artifacts.coordinates import raw_dataset_root
from datp_core.datasets.catalogue import DatasetPublication, dataset_binding
from datp_core.domain.enums import DatasetId, ReusableDataCoordinateKind


@dataclass(frozen=True, slots=True)
class MaterializeCanonicalDatasetsRequest:
    data_root: Path
    datasets: tuple[DatasetId, ...]


def materialize_canonical_datasets_stage(
    request: MaterializeCanonicalDatasetsRequest,
) -> tuple[DatasetPublication, ...]:
    """Materialize every requested dataset under the canonical root of data_root."""
    canonical_root = request.data_root / ReusableDataCoordinateKind.CANONICAL
    return tuple(
        dataset_binding(dataset).publish(raw_dataset_root(dataset), canonical_root) for dataset in request.datasets
    )

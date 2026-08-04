"""Stage: compose canonical dataset materialization."""

from datp_core.artifacts.coordinates import raw_dataset_root
from datp_core.datasets.catalogue import dataset_binding
from datp_core.domain.enums import ReusableDataCoordinateKind
from datp_core.orchestration.commands.datasets import (
    MaterializeCanonicalDatasetsRequest as _MaterializeCanonicalDatasetsRequest,
    MaterializeCanonicalDatasetsResult as _MaterializeCanonicalDatasetsResult,
)


def materialize_canonical_datasets_stage(
    request: _MaterializeCanonicalDatasetsRequest,
) -> _MaterializeCanonicalDatasetsResult:
    canonical_root = request.data_root / ReusableDataCoordinateKind.CANONICAL
    return _MaterializeCanonicalDatasetsResult(
        publications=tuple(
            dataset_binding(dataset).publish(raw_dataset_root(dataset), canonical_root)
            for dataset in request.datasets
        )
    )

from datp_core.datasets.catalogue import dataset_binding
from datp_core.domain.enums import DatasetId


def test_catalogue_dispatches_every_dataset_id() -> None:
    assert tuple(dataset_binding(dataset_id).schema.dataset for dataset_id in DatasetId) == tuple(DatasetId)


def test_catalogue_rejects_invalid_runtime_identity() -> None:
    try:
        dataset_binding.__call__("invalid")
    except ValueError:
        return
    raise AssertionError("invalid dataset identity was accepted")

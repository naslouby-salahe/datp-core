from datp_core.application.ports.data import DatasetSourceInspector, InspectDatasetSourceRequest
from datp_core.domain.data.datasets import DatasetSourceInspectionResult, DatasetSpec


def inspect_dataset(*, inspector: DatasetSourceInspector, dataset: DatasetSpec) -> DatasetSourceInspectionResult:
    return inspector.inspect(InspectDatasetSourceRequest(dataset=dataset))

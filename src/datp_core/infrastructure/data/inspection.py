from dataclasses import dataclass

import pyarrow as pa

from datp_core.application.ports.data import InspectDatasetSourceRequest
from datp_core.domain.data.datasets import DatasetSourceInspectionResult
from datp_core.domain.errors import DatasetError
from datp_core.infrastructure.data.streaming import ParquetBatchStream


@dataclass(frozen=True, slots=True, kw_only=True)
class PyArrowDatasetSourceInspector:
    stream: ParquetBatchStream
    feature_columns: tuple[str, ...]
    result: DatasetSourceInspectionResult

    def inspect(self, request: InspectDatasetSourceRequest) -> DatasetSourceInspectionResult:
        if len(self.feature_columns) != request.dataset.input_dim:
            raise _dataset_error(request, "configured feature columns do not match the dataset input dimension")
        _validate_feature_columns(request, self.stream.schema(), self.feature_columns)
        for batch in self.stream.batches():
            _validate_feature_columns(request, batch.schema, self.feature_columns)
        return self.result


def _dataset_error(request: InspectDatasetSourceRequest, coverage: str) -> DatasetError:
    return DatasetError(dataset=request.dataset.dataset.value, regime="unresolved", coverage=coverage, detail=coverage)


def _validate_feature_columns(
    request: InspectDatasetSourceRequest,
    schema: pa.Schema,
    feature_columns: tuple[str, ...],
) -> None:
    missing_columns = tuple(column for column in feature_columns if schema.get_field_index(column) < 0)
    if missing_columns:
        raise _dataset_error(request, f"source is missing configured feature columns: {missing_columns!r}")

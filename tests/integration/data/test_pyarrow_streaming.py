from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from datp_core.application.ports.data import InspectDatasetSourceRequest
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.lineage import DatasetSourceIdentity, FeatureSchemaIdentity
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.data.datasets import Dataset, DatasetSourceInspectionResult, DatasetSpec
from datp_core.domain.data.preprocessing import (
    FittedStatisticPolicy,
    NormalizationScope,
    NormalizationStrategy,
    PreprocessingChunkSpec,
    PreprocessingSpec,
)
from datp_core.domain.data.splitting import SplitRole
from datp_core.domain.errors import DatasetError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.runtime.admissibility import ChunkRowCount
from datp_core.infrastructure.data.inspection import PyArrowDatasetSourceInspector
from datp_core.infrastructure.data.materialization import PartitionedParquetMaterializer
from datp_core.infrastructure.data.partitioning import ClientPartitionStream
from datp_core.infrastructure.data.preprocessing import TwoPassNumericPreprocessor
from datp_core.infrastructure.data.splitting import ClientSplitStream, stable_client_split_order
from datp_core.infrastructure.data.streaming import ParquetBatchStream, numeric_column_statistics


def _write_synthetic_parquet(path: Path) -> None:
    pq.write_table(
        pa.table({"row": list(range(17)), "value": [float(index * 3) for index in range(17)]}),
        path,
        row_group_size=4,
    )


def _write_synthetic_partition(path: Path, rows: range) -> None:
    pq.write_table(
        pa.table({"row": list(rows), "value": [float(index * 3) for index in rows]}),
        path,
        row_group_size=4,
    )


def _artifact_ref(character: str, artifact_type: ArtifactType) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value="artifact-" + character * 64),
        artifact_type=artifact_type,
        content_hash=character * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.PARQUET,
    )


def _inspection_result() -> DatasetSourceInspectionResult:
    return DatasetSourceInspectionResult(
        source_manifest=_artifact_ref("a", ArtifactType.SOURCE_INSPECTION),
        feature_schema_manifest=_artifact_ref("b", ArtifactType.FEATURE_SCHEMA_MANIFEST),
        source_row_identity=DatasetSourceIdentity(value=StageFingerprint(value="c" * 64)),
        timestamp_evidence=None,
    )


def _inspection_request() -> InspectDatasetSourceRequest:
    return InspectDatasetSourceRequest(
        dataset=DatasetSpec(
            dataset=Dataset.N_BAIOT,
            input_dim=2,
            feature_schema_identity=FeatureSchemaIdentity(value=StageFingerprint(value="d" * 64)),
            feature_count_verified=True,
        )
    )


def test_streaming_batches_are_bounded_and_order_is_stable(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.parquet"
    _write_synthetic_parquet(path)
    stream = ParquetBatchStream(path=path, batch_rows=ChunkRowCount(value=3))

    first_batches = tuple(stream.batches())
    second_batches = tuple(stream.batches())

    assert all(batch.num_rows <= 3 for batch in first_batches)
    assert tuple(batch.column(0).to_pylist() for batch in first_batches) == tuple(
        batch.column(0).to_pylist() for batch in second_batches
    )
    first_checksum = stream.row_order_checksum()
    repeated_checksum = stream.row_order_checksum()
    assert first_checksum == repeated_checksum


def test_row_order_checksum_is_independent_of_the_batch_size(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.parquet"
    _write_synthetic_parquet(path)

    single_batch_checksum = ParquetBatchStream(path=path, batch_rows=ChunkRowCount(value=17)).row_order_checksum()
    many_batch_checksum = ParquetBatchStream(path=path, batch_rows=ChunkRowCount(value=1)).row_order_checksum()

    assert single_batch_checksum == many_batch_checksum


def test_chunked_statistics_match_the_single_pass_synthetic_reference(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.parquet"
    _write_synthetic_parquet(path)

    statistics = numeric_column_statistics(
        ParquetBatchStream(path=path, batch_rows=ChunkRowCount(value=3)),
        "value",
    )
    expected = tuple(float(index * 3) for index in range(17))

    assert statistics.row_count == len(expected)
    assert statistics.minimum == min(expected)
    assert statistics.maximum == max(expected)
    assert statistics.mean == sum(expected) / len(expected)
    assert statistics.mean is not None
    assert statistics.variance == (sum(value * value for value in expected) / len(expected)) - statistics.mean**2


def test_bounded_pandas_conversion_never_exceeds_the_declared_batch_size(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.parquet"
    _write_synthetic_parquet(path)

    chunks = tuple(ParquetBatchStream(path=path, batch_rows=ChunkRowCount(value=3)).bounded_pandas_chunks())

    assert chunks
    assert all(chunk.row_count <= 3 for chunk in chunks)


def test_inspector_validates_feature_schema_with_a_bounded_scan(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.parquet"
    _write_synthetic_parquet(path)
    inspector = PyArrowDatasetSourceInspector(
        stream=ParquetBatchStream(path=path, batch_rows=ChunkRowCount(value=3)),
        feature_columns=("row", "value"),
        result=_inspection_result(),
    )

    assert inspector.inspect(_inspection_request()) == _inspection_result()

    missing_column_inspector = PyArrowDatasetSourceInspector(
        stream=ParquetBatchStream(path=path, batch_rows=ChunkRowCount(value=3)),
        feature_columns=("row", "missing"),
        result=_inspection_result(),
    )
    inspection_request = _inspection_request()
    with pytest.raises(DatasetError):
        missing_column_inspector.inspect(inspection_request)


def test_partitioned_materialization_preserves_synthetic_source_rows_and_order(tmp_path: Path) -> None:
    source_path = tmp_path / "synthetic.parquet"
    _write_synthetic_parquet(source_path)
    source = ClientSplitStream(
        partition=ClientPartitionStream(
            client_id=ClientId(value="client-a"),
            source_row_identity=_inspection_result().source_row_identity,
            stream=ParquetBatchStream(path=source_path, batch_rows=ChunkRowCount(value=3)),
        ),
        split_role=SplitRole.TRAIN,
    )

    materialized = PartitionedParquetMaterializer(output_root=tmp_path / "processed").materialize(source)
    output_stream = ParquetBatchStream(path=materialized.path, batch_rows=ChunkRowCount(value=3))

    assert materialized.path == tmp_path / "processed" / "client-a" / "train" / "processed.parquet"
    assert materialized.row_count == 17
    assert materialized.source_row_identity == source.partition.source_row_identity
    assert materialized.row_order_checksum == source.partition.stream.row_order_checksum()
    assert output_stream.row_order_checksum() == source.partition.stream.row_order_checksum()


def test_exact_two_pass_fit_matches_the_single_pass_synthetic_reference(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.parquet"
    _write_synthetic_parquet(path)
    chunk_rows = ChunkRowCount(value=3)
    fitted = TwoPassNumericPreprocessor(
        training=ParquetBatchStream(path=path, batch_rows=chunk_rows),
        feature_columns=("value",),
        preprocessing=PreprocessingSpec(
            strategy=NormalizationStrategy.STANDARD,
            scope=NormalizationScope.GLOBAL_TRAIN,
            fitted_stat_policy=FittedStatisticPolicy.EXACT_TWO_PASS,
            chunking=PreprocessingChunkSpec(
                source_scan_batch_rows=chunk_rows,
                preprocessing_chunk_rows=chunk_rows,
                parquet_write_batch_rows=chunk_rows,
            ),
        ),
    ).fit()
    expected = tuple(float(index * 3) for index in range(17))

    assert (
        fitted.training_row_order_checksum == ParquetBatchStream(path=path, batch_rows=chunk_rows).row_order_checksum()
    )
    assert fitted.statistics[0].mean == sum(expected) / len(expected)
    assert (
        fitted.statistics[0].variance
        == (sum(value * value for value in expected) / len(expected)) - (sum(expected) / len(expected)) ** 2
    )


def test_client_and_split_boundaries_preserve_every_synthetic_row_once(tmp_path: Path) -> None:
    first_path = tmp_path / "first.parquet"
    second_path = tmp_path / "second.parquet"
    _write_synthetic_partition(first_path, range(9))
    _write_synthetic_partition(second_path, range(9, 17))
    source_identity = _inspection_result().source_row_identity
    first_partition = ClientPartitionStream(
        client_id=ClientId(value="client-a"),
        source_row_identity=source_identity,
        stream=ParquetBatchStream(path=first_path, batch_rows=ChunkRowCount(value=3)),
    )
    second_partition = ClientPartitionStream(
        client_id=ClientId(value="client-b"),
        source_row_identity=source_identity,
        stream=ParquetBatchStream(path=second_path, batch_rows=ChunkRowCount(value=3)),
    )
    sources = (
        ClientSplitStream(partition=second_partition, split_role=SplitRole.TRAIN),
        ClientSplitStream(partition=first_partition, split_role=SplitRole.TRAIN),
    )

    materialized = PartitionedParquetMaterializer(output_root=tmp_path / "processed").materialize_all(sources)
    ordered_sources = stable_client_split_order(sources)
    output_rows = tuple(
        row
        for partition in materialized
        for batch in ParquetBatchStream(path=partition.path, batch_rows=ChunkRowCount(value=3)).batches()
        for row in batch.column(0).to_pylist()
    )

    assert tuple(partition.client_id for partition in materialized) == (
        ordered_sources[0].partition.client_id,
        ordered_sources[1].partition.client_id,
    )
    assert output_rows == tuple(range(17))

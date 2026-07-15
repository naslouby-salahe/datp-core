from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from blake3 import blake3

from datp_core.domain.artifacts.lineage import DatasetSourceIdentity
from datp_core.domain.data.splitting import SplitRole
from datp_core.domain.errors import PreprocessingError
from datp_core.domain.experiments.identities import ClientId
from datp_core.infrastructure.data.splitting import ClientSplitStream, stable_client_split_order
from datp_core.infrastructure.data.streaming import update_row_order_checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class MaterializedParquetPartition:
    client_id: ClientId
    split_role: SplitRole
    path: Path
    source_row_identity: DatasetSourceIdentity
    row_count: int
    row_order_checksum: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PartitionedParquetMaterializer:
    output_root: Path

    def materialize_all(self, sources: tuple[ClientSplitStream, ...]) -> tuple[MaterializedParquetPartition, ...]:
        return tuple(self.materialize(source) for source in stable_client_split_order(sources))

    def materialize(self, source: ClientSplitStream) -> MaterializedParquetPartition:
        partition = source.partition
        destination = self.output_root / partition.client_id.value / source.split_role.value / "processed.parquet"
        destination.parent.mkdir(parents=True, exist_ok=True)
        batches = partition.stream.batches()
        first_batch = next(batches, None)
        if first_batch is None:
            raise _preprocessing_error(source, "cannot materialize an empty source split")
        row_count = 0
        hasher = blake3()
        context = _MaterializationContext(
            source=source,
            expected_schema=first_batch.schema,
            hasher=hasher,
        )
        with pq.ParquetWriter(destination, first_batch.schema) as writer:
            row_count = _write_batch(writer, first_batch, context, row_count)
            for batch in batches:
                row_count = _write_batch(writer, batch, context, row_count)
        return MaterializedParquetPartition(
            client_id=partition.client_id,
            split_role=source.split_role,
            path=destination,
            source_row_identity=partition.source_row_identity,
            row_count=row_count,
            row_order_checksum=hasher.hexdigest(),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class _MaterializationContext:
    source: ClientSplitStream
    expected_schema: pa.Schema
    hasher: blake3


def _write_batch(
    writer: pq.ParquetWriter,
    batch: pa.RecordBatch,
    context: _MaterializationContext,
    row_count: int,
) -> int:
    if batch.num_rows > context.source.partition.stream.batch_rows.value:
        raise _preprocessing_error(context.source, "source scanner exceeded its frozen batch-row limit")
    if batch.schema != context.expected_schema:
        raise _preprocessing_error(context.source, "source stream changed schema during materialization")
    writer.write_batch(batch, row_group_size=context.source.partition.stream.batch_rows.value)
    update_row_order_checksum(context.hasher, batch)
    return row_count + batch.num_rows


def _preprocessing_error(source: ClientSplitStream, detail: str) -> PreprocessingError:
    return PreprocessingError(
        detail=detail,
        strategy="unresolved",
        scope=f"{source.partition.client_id.value}/{source.split_role.value}",
    )

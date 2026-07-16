from dataclasses import dataclass, field, replace
from pathlib import Path

import msgspec
import pyarrow as pa
import pyarrow.parquet as pq
from blake3 import blake3

from datp_core.application.ports.data import FitPreprocessorRequest, MaterializeProcessedSplitsRequest
from datp_core.application.ports.persistence import WriteArtifactRequest
from datp_core.domain.artifacts.keys import ArtifactNamespace, DatasetArtifactKey, SerializationFormat, WriteDisposition
from datp_core.domain.artifacts.lineage import DatasetSourceIdentity, FittedPreprocessorIdentity
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.data.datasets import Dataset, SourceTrafficLabel
from datp_core.domain.data.preprocessing import (
    ClientFeatureStatistics,
    FeatureStatistics,
    FittedPreprocessorManifest,
    FittedPreprocessorResult,
    FittedStatisticPolicy,
    NormalizationScope,
    NormalizationStrategy,
    PreprocessingChunkSpec,
    PreprocessingSpec,
    ProcessedSplitResult,
)
from datp_core.domain.data.splitting import RegimeAStaticSplitBoundarySpec, SplitRole
from datp_core.domain.errors import PreprocessingError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.runtime.policies import StreamingChunkPolicy
from datp_core.infrastructure.data.nbaiot_inspection import sorted_device_directories
from datp_core.infrastructure.data.nbaiot_source import SOURCE_LABEL_COLUMN_NAME
from datp_core.infrastructure.data.nbaiot_split import benign_split_boundaries, row_range_roles
from datp_core.infrastructure.data.preprocessing import TwoPassNumericPreprocessor
from datp_core.infrastructure.data.streaming import ParquetBatchStream, update_row_order_checksum
from datp_core.infrastructure.persistence.artifacts import FileArtifactStore
from datp_core.infrastructure.persistence.hashing import blake3_bytes_content_hash, blake3_file_content_hash
from datp_core.infrastructure.persistence.paths import ArtifactPathResolver, ResolveArtifactLocationRequest
from datp_core.infrastructure.persistence.roots import BoundStorageRoot


def _preprocessing_error(coverage: str) -> PreprocessingError:
    return PreprocessingError(detail=coverage, strategy="standard", scope="per_client_train")


def is_authorized_nbaiot_policy(
    *, strategy: NormalizationStrategy, scope: NormalizationScope, fitted_stat_policy: FittedStatisticPolicy
) -> bool:
    return (
        strategy is NormalizationStrategy.STANDARD
        and scope is NormalizationScope.PER_CLIENT_TRAIN
        and fitted_stat_policy is FittedStatisticPolicy.EXACT_TWO_PASS
    )


def _validate_locked_preprocessing_policy(preprocessing: PreprocessingSpec) -> None:
    if is_authorized_nbaiot_policy(
        strategy=preprocessing.strategy, scope=preprocessing.scope, fitted_stat_policy=preprocessing.fitted_stat_policy
    ):
        return
    raise _preprocessing_error("N-BaIoT anchor preprocessing requires STANDARD/PER_CLIENT_TRAIN/EXACT_TWO_PASS")


def _count_benign_rows(stream: ParquetBatchStream, label_column_index: int) -> int:
    count = 0
    for batch in stream.batches():
        labels = batch.column(label_column_index).to_pylist()
        matching = sum(1 for label in labels if label == SourceTrafficLabel.BENIGN.value)
        count += matching
        if matching != batch.num_rows:
            break
    return count


def _client_boundaries(
    materialized_path: Path,
    *,
    boundary_spec: RegimeAStaticSplitBoundarySpec,
    streaming_chunk_policy: StreamingChunkPolicy,
) -> tuple[int, int, int, int]:
    stream = ParquetBatchStream(path=materialized_path, batch_rows=streaming_chunk_policy.parquet_batch_rows)
    label_column_index = stream.schema().get_field_index(SOURCE_LABEL_COLUMN_NAME)
    if label_column_index < 0:
        raise _preprocessing_error(f"{materialized_path} is missing the {SOURCE_LABEL_COLUMN_NAME!r} column")
    return benign_split_boundaries(_count_benign_rows(stream, label_column_index), boundary_spec=boundary_spec)


def _feature_only_batch(batch: pa.RecordBatch, feature_columns: tuple[str, ...]) -> pa.RecordBatch:
    columns = [batch.column(batch.schema.get_field_index(name)) for name in feature_columns]
    return pa.RecordBatch.from_arrays(columns, list(feature_columns))


@dataclass(frozen=True, slots=True, kw_only=True)
class _ClientFitPlan:
    feature_columns: tuple[str, ...]
    scratch_root: Path
    boundary_spec: RegimeAStaticSplitBoundarySpec
    streaming_chunk_policy: StreamingChunkPolicy
    preprocessing: PreprocessingSpec


def _extract_train_raw(
    *,
    materialized_path: Path,
    plan: _ClientFitPlan,
    boundaries: tuple[int, int, int, int],
    destination: Path,
) -> tuple[int, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    stream = ParquetBatchStream(path=materialized_path, batch_rows=plan.streaming_chunk_policy.parquet_batch_rows)
    hasher = blake3()
    row_count = 0
    writer: pq.ParquetWriter | None = None
    global_index = 0
    try:
        for batch in stream.batches():
            for offset, length, role in row_range_roles(
                batch_start=global_index, batch_length=batch.num_rows, boundaries=boundaries
            ):
                if role is not SplitRole.TRAIN:
                    continue
                feature_batch = _feature_only_batch(batch.slice(offset, length), plan.feature_columns)
                if writer is None:
                    writer = pq.ParquetWriter(destination, feature_batch.schema)
                writer.write_batch(feature_batch)
                update_row_order_checksum(hasher, feature_batch)
                row_count += length
            global_index += batch.num_rows
    finally:
        if writer is not None:
            writer.close()
    if row_count == 0:
        raise _preprocessing_error(f"{materialized_path} produced no authorized TRAIN rows to fit")
    return row_count, hasher.hexdigest()


def _client_feature_statistics(
    fitted_statistics: tuple[float, ...], feature_columns: tuple[str, ...], variances: tuple[float, ...]
) -> tuple[FeatureStatistics, ...]:
    return tuple(
        FeatureStatistics(feature=name, mean=mean, variance=variance)
        for name, mean, variance in zip(feature_columns, fitted_statistics, variances, strict=True)
    )


def _fit_client(*, client_id: ClientId, materialized_path: Path, plan: _ClientFitPlan) -> ClientFeatureStatistics:
    boundaries = _client_boundaries(
        materialized_path, boundary_spec=plan.boundary_spec, streaming_chunk_policy=plan.streaming_chunk_policy
    )
    feature_columns = plan.feature_columns
    train_raw_path = plan.scratch_root / client_id.value / "train_raw.parquet"
    row_count, checksum = _extract_train_raw(
        materialized_path=materialized_path,
        plan=plan,
        boundaries=boundaries,
        destination=train_raw_path,
    )
    chunk_rows = plan.streaming_chunk_policy.parquet_batch_rows
    resolved_preprocessing = replace(
        plan.preprocessing,
        chunking=PreprocessingChunkSpec(
            source_scan_batch_rows=chunk_rows,
            preprocessing_chunk_rows=chunk_rows,
            parquet_write_batch_rows=chunk_rows,
        ),
    )
    fitted = TwoPassNumericPreprocessor(
        training=ParquetBatchStream(path=train_raw_path, batch_rows=chunk_rows),
        feature_columns=feature_columns,
        preprocessing=resolved_preprocessing,
    ).fit()
    means = tuple(_finite_or_error(statistic.mean, "mean") for statistic in fitted.statistics)
    variances = tuple(_finite_or_error(statistic.variance, "variance") for statistic in fitted.statistics)
    statistics = _client_feature_statistics(means, feature_columns, variances)
    return ClientFeatureStatistics(
        client_id=client_id,
        feature_columns=feature_columns,
        statistics=statistics,
        training_row_count=row_count,
        training_row_order_checksum=checksum,
    )


def _finite_or_error(value: float | None, name: str) -> float:
    if value is None:
        raise _preprocessing_error(f"fitted {name} is undefined for an authorized non-empty TRAIN split")
    return value


def _aggregate_checksum(client_statistics: tuple[ClientFeatureStatistics, ...]) -> str:
    hasher = blake3()
    for entry in sorted(client_statistics, key=lambda item: item.client_id.value):
        hasher.update(entry.training_row_order_checksum.encode())
    return hasher.hexdigest()


def _persisted_manifest(
    manifest: FittedPreprocessorManifest, *, artifact_store: FileArtifactStore
) -> tuple[ArtifactRef, str]:
    content = msgspec.json.encode(manifest)
    content_hash = blake3_bytes_content_hash(content)
    artifact = ArtifactRef(
        artifact_id=ArtifactId(value=f"artifact-{content_hash}"),
        artifact_type=ArtifactType.FITTED_PREPROCESSOR,
        content_hash=content_hash,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.JSON,
    )
    key = DatasetArtifactKey(
        artifact_type=ArtifactType.FITTED_PREPROCESSOR,
        dataset=Dataset.N_BAIOT,
        stage_identity=StageFingerprint(value=content_hash),
        namespace=ArtifactNamespace.DATP_ANCHOR,
    )
    write_result = artifact_store.write_atomically(
        WriteArtifactRequest(
            key=key, artifact=artifact, content=content, write_disposition=WriteDisposition.CREATE_IF_ABSENT
        )
    )
    return write_result.artifact, content_hash


@dataclass(frozen=True, slots=True, kw_only=True)
class NBaIoTPreprocessorFitter:
    raw_root: Path
    materialized_root: Path
    scratch_root: Path
    artifact_store: FileArtifactStore
    feature_columns: tuple[str, ...]
    boundary_spec: RegimeAStaticSplitBoundarySpec
    streaming_chunk_policy: StreamingChunkPolicy

    def fit(self, request: FitPreprocessorRequest) -> FittedPreprocessorResult:
        _validate_locked_preprocessing_policy(request.preprocessing)
        device_ids = tuple(path.name for path in sorted_device_directories(self.raw_root))
        plan = _ClientFitPlan(
            feature_columns=self.feature_columns,
            scratch_root=self.scratch_root,
            boundary_spec=self.boundary_spec,
            streaming_chunk_policy=self.streaming_chunk_policy,
            preprocessing=request.preprocessing,
        )
        client_statistics = tuple(
            _fit_client(
                client_id=ClientId(value=device_id),
                materialized_path=self.materialized_root / device_id / "source.parquet",
                plan=plan,
            )
            for device_id in device_ids
        )
        manifest = FittedPreprocessorManifest(
            strategy=request.preprocessing.strategy,
            scope=request.preprocessing.scope,
            feature_columns=self.feature_columns,
            client_statistics=client_statistics,
        )
        artifact, content_hash = _persisted_manifest(manifest, artifact_store=self.artifact_store)
        return FittedPreprocessorResult(
            artifact=artifact,
            identity=FittedPreprocessorIdentity(value=StageFingerprint(value=content_hash)),
            training_row_order_checksum=_aggregate_checksum(client_statistics),
        )


def _read_fitted_manifest(*, artifact: ArtifactRef, bound_root: BoundStorageRoot) -> FittedPreprocessorManifest:
    key = DatasetArtifactKey(
        artifact_type=ArtifactType.FITTED_PREPROCESSOR,
        dataset=Dataset.N_BAIOT,
        stage_identity=StageFingerprint(value=artifact.content_hash),
        namespace=ArtifactNamespace.DATP_ANCHOR,
    )
    path = (
        ArtifactPathResolver()
        .resolve(ResolveArtifactLocationRequest(key=key, root=bound_root, artifact=artifact))
        .absolute_path
    )
    return msgspec.json.decode(path.read_bytes(), type=FittedPreprocessorManifest)


def _normalized_batch(
    batch: pa.RecordBatch, feature_columns: tuple[str, ...], statistics: tuple[FeatureStatistics, ...]
) -> pa.RecordBatch:
    arrays = [
        _normalized_column(batch, name, statistic) for name, statistic in zip(feature_columns, statistics, strict=True)
    ]
    return pa.RecordBatch.from_arrays(arrays, list(feature_columns))


def _normalized_column(batch: pa.RecordBatch, name: str, statistic: FeatureStatistics) -> pa.Array:
    values = batch.column(batch.schema.get_field_index(name)).to_pylist()
    standard_deviation = statistic.variance**0.5
    normalized = [_normalized_value(value, statistic.mean, standard_deviation) for value in values]
    return pa.array(normalized, type=pa.float64())


def _normalized_value(value: object, mean: float, standard_deviation: float) -> float:
    numeric_value = float(value) if isinstance(value, int | float) else 0.0
    return (numeric_value - mean) / standard_deviation if standard_deviation > 0 else 0.0


_ROLES = (SplitRole.TRAIN, SplitRole.CALIBRATION, SplitRole.TEST)


@dataclass(slots=True)
class _RoleWriteState:
    destination: Path
    hasher: blake3 = field(default_factory=blake3)
    row_count: int = 0
    writer: pq.ParquetWriter | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class _ClientTransformContext:
    feature_columns: tuple[str, ...]
    statistics: tuple[FeatureStatistics, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class _RoleWritePlan:
    boundaries: tuple[int, int, int, int]
    states: dict[SplitRole, _RoleWriteState]
    context: _ClientTransformContext


def _role_write_states(*, client_id: ClientId, processed_root: Path) -> dict[SplitRole, _RoleWriteState]:
    states: dict[SplitRole, _RoleWriteState] = {}
    for role in _ROLES:
        destination = processed_root / client_id.value / role.value / "processed.parquet"
        destination.parent.mkdir(parents=True, exist_ok=True)
        states[role] = _RoleWriteState(destination=destination)
    return states


def _write_all_roles(*, stream: ParquetBatchStream, plan: _RoleWritePlan) -> None:
    global_index = 0
    try:
        for batch in stream.batches():
            _write_batch_roles(batch=batch, global_index=global_index, plan=plan)
            global_index += batch.num_rows
    finally:
        for state in plan.states.values():
            if state.writer is not None:
                state.writer.close()


def _write_batch_roles(*, batch: pa.RecordBatch, global_index: int, plan: _RoleWritePlan) -> None:
    for offset, length, role in row_range_roles(
        batch_start=global_index, batch_length=batch.num_rows, boundaries=plan.boundaries
    ):
        if role is None:
            continue
        _write_normalized_segment(
            state=plan.states[role], batch=batch.slice(offset, length), context=plan.context, length=length
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class _ClientMaterializationPlan:
    processed_root: Path
    boundary_spec: RegimeAStaticSplitBoundarySpec
    streaming_chunk_policy: StreamingChunkPolicy


def _materialize_client(
    *,
    client_id: ClientId,
    materialized_path: Path,
    materialization_plan: _ClientMaterializationPlan,
    context: _ClientTransformContext,
) -> tuple[Path, ...]:
    boundaries = _client_boundaries(
        materialized_path,
        boundary_spec=materialization_plan.boundary_spec,
        streaming_chunk_policy=materialization_plan.streaming_chunk_policy,
    )
    stream = ParquetBatchStream(
        path=materialized_path, batch_rows=materialization_plan.streaming_chunk_policy.parquet_batch_rows
    )
    states = _role_write_states(client_id=client_id, processed_root=materialization_plan.processed_root)
    role_write_plan = _RoleWritePlan(boundaries=boundaries, states=states, context=context)
    _write_all_roles(stream=stream, plan=role_write_plan)
    return tuple(state.destination for state in states.values() if state.row_count > 0)


def _write_normalized_segment(
    *, state: _RoleWriteState, batch: pa.RecordBatch, context: _ClientTransformContext, length: int
) -> None:
    normalized = _normalized_batch(batch, context.feature_columns, context.statistics)
    if state.writer is None:
        state.writer = pq.ParquetWriter(state.destination, normalized.schema)
    state.writer.write_batch(normalized)
    update_row_order_checksum(state.hasher, normalized)
    state.row_count += length


def _registered_parquet_artifact(path: Path) -> ArtifactRef:
    content_hash = blake3_file_content_hash(path)
    return ArtifactRef(
        artifact_id=ArtifactId(value=f"artifact-{content_hash}"),
        artifact_type=ArtifactType.PROCESSED_SPLIT,
        content_hash=content_hash,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.PARQUET,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class NBaIoTProcessedSplitMaterializer:
    raw_root: Path
    materialized_root: Path
    processed_root: Path
    manifest_root: BoundStorageRoot
    feature_columns: tuple[str, ...]
    source_row_identity: DatasetSourceIdentity
    boundary_spec: RegimeAStaticSplitBoundarySpec
    streaming_chunk_policy: StreamingChunkPolicy

    def materialize(self, request: MaterializeProcessedSplitsRequest) -> ProcessedSplitResult:
        manifest = _read_fitted_manifest(artifact=request.fitted_preprocessor.artifact, bound_root=self.manifest_root)
        statistics_by_client = {entry.client_id.value: entry.statistics for entry in manifest.client_statistics}
        device_ids = tuple(path.name for path in sorted_device_directories(self.raw_root))
        materialization_plan = _ClientMaterializationPlan(
            processed_root=self.processed_root,
            boundary_spec=self.boundary_spec,
            streaming_chunk_policy=self.streaming_chunk_policy,
        )
        artifacts: list[ArtifactRef] = []
        for device_id in device_ids:
            if device_id not in statistics_by_client:
                raise _preprocessing_error(f"no fitted statistics available for client {device_id!r}")
            paths = _materialize_client(
                client_id=ClientId(value=device_id),
                materialized_path=self.materialized_root / device_id / "source.parquet",
                materialization_plan=materialization_plan,
                context=_ClientTransformContext(
                    feature_columns=self.feature_columns, statistics=statistics_by_client[device_id]
                ),
            )
            artifacts.extend(_registered_parquet_artifact(path) for path in paths)
        return ProcessedSplitResult(
            artifacts=tuple(artifacts),
            split_manifest_identity=request.split_manifest.split_identities.training.split_identity,
            preprocessor_identity=request.fitted_preprocessor.identity,
            source_row_lineage=(self.source_row_identity,),
        )

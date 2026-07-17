from pathlib import Path

import pyarrow.parquet as pq
import pytest

from datp_core.application.ports.data import FitPreprocessorRequest, MaterializeProcessedSplitsRequest
from datp_core.domain.artifacts.keys import SerializationFormat, StorageRootKind, StorageRootSpec, StorageVisibility
from datp_core.domain.artifacts.lineage import DatasetSourceIdentity, PartitionIdentity, SplitIdentity
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.data.preprocessing import (
    FittedStatisticPolicy,
    NormalizationScope,
    NormalizationStrategy,
    PreprocessingChunkSpec,
    PreprocessingSpec,
)
from datp_core.domain.data.splitting import (
    LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY,
    BenignCalibrationSplitSpec,
    SplitCollectionSpec,
    SplitManifestResult,
    TestSplitSpec,
    TrainingSplitSpec,
)
from datp_core.domain.errors import PreprocessingError
from datp_core.domain.runtime.admissibility import ChunkRowCount, CsvBlockBytes
from datp_core.domain.runtime.policies import StreamingChunkPolicy
from datp_core.infrastructure.data.nbaiot.preprocessing import (
    NBaIoTPreprocessorFitter,
    NBaIoTProcessedSplitMaterializer,
)
from datp_core.infrastructure.data.nbaiot.source import NBaIoTChunkedSourceAdapter
from datp_core.infrastructure.persistence.artifacts import FileArtifactStore
from datp_core.infrastructure.persistence.roots import BoundStorageRoot, bind_storage_root

_FEATURE_COLUMNS = ("feature_a", "feature_b", "feature_c")
_HEADER = ",".join(_FEATURE_COLUMNS)
_PARTITION_IDENTITY = PartitionIdentity(value=StageFingerprint(value="d" * 64))
_SOURCE_ROW_IDENTITY = DatasetSourceIdentity(value=StageFingerprint(value="a" * 64))
_STREAMING_CHUNK_POLICY = StreamingChunkPolicy(
    csv_block_bytes=CsvBlockBytes(value=8 * 1024 * 1024), parquet_batch_rows=ChunkRowCount(value=50_000)
)


def _write_csv(path: Path, *, rows: int, offset: int = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [_HEADER]
    lines.extend(f"{index + offset}.0,{(index + offset) * 2}.0,{(index + offset) * 3}.0" for index in range(rows))
    path.write_text("\n".join(lines) + "\n")


def _materialize(
    raw_root: Path, materialized_root: Path, *, device_id: str, benign_rows: int, attack_rows: int
) -> None:
    _write_csv(raw_root / device_id / "benign_traffic.csv", rows=benign_rows)
    _write_csv(raw_root / device_id / "gafgyt_attacks" / "combo.csv", rows=attack_rows, offset=benign_rows)
    NBaIoTChunkedSourceAdapter(
        raw_root=raw_root, output_root=materialized_root, csv_block_bytes=_STREAMING_CHUNK_POLICY.csv_block_bytes.value
    ).materialize_device(device_id)


def _dummy_ref() -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value="artifact-" + "b" * 64),
        artifact_type=ArtifactType.SOURCE_INSPECTION,
        content_hash="b" * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.JSON,
    )


def _split_collection_spec() -> SplitCollectionSpec:
    return SplitCollectionSpec(
        training=TrainingSplitSpec(
            split_identity=SplitIdentity(value=StageFingerprint(value="1" * 64)), partition_identity=_PARTITION_IDENTITY
        ),
        calibration=BenignCalibrationSplitSpec(
            split_identity=SplitIdentity(value=StageFingerprint(value="2" * 64)), partition_identity=_PARTITION_IDENTITY
        ),
        test=TestSplitSpec(
            split_identity=SplitIdentity(value=StageFingerprint(value="3" * 64)), partition_identity=_PARTITION_IDENTITY
        ),
    )


def _split_manifest_result() -> SplitManifestResult:
    return SplitManifestResult(
        split_manifest=_dummy_ref(), split_identities=_split_collection_spec(), partition_identity=_PARTITION_IDENTITY
    )


def _preprocessing_spec(*, strategy: NormalizationStrategy = NormalizationStrategy.STANDARD) -> PreprocessingSpec:
    chunk_rows = ChunkRowCount(value=50_000)
    return PreprocessingSpec(
        strategy=strategy,
        scope=NormalizationScope.PER_CLIENT_TRAIN,
        fitted_stat_policy=FittedStatisticPolicy.EXACT_TWO_PASS,
        chunking=PreprocessingChunkSpec(
            source_scan_batch_rows=chunk_rows, preprocessing_chunk_rows=chunk_rows, parquet_write_batch_rows=chunk_rows
        ),
    )


def _bound_manifest_root(tmp_path: Path) -> BoundStorageRoot:
    return bind_storage_root(
        spec=StorageRootSpec(kind=StorageRootKind.PROCESSED_DATA, visibility=StorageVisibility.SCIENTIFIC_OUTPUT),
        absolute_path=tmp_path / "manifests",
    )


def test_fit_uses_only_train_rows_and_transform_preserves_feature_order_with_chunk_equivalence(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    materialized_root = tmp_path / "materialized"
    _materialize(raw_root, materialized_root, device_id="DeviceOne", benign_rows=1000, attack_rows=100)
    bound_root = _bound_manifest_root(tmp_path)

    fitter = NBaIoTPreprocessorFitter(
        raw_root=raw_root,
        materialized_root=materialized_root,
        scratch_root=tmp_path / "scratch",
        artifact_store=FileArtifactStore(root=bound_root),
        feature_columns=_FEATURE_COLUMNS,
        boundary_spec=LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY,
        streaming_chunk_policy=_STREAMING_CHUNK_POLICY,
    )
    fitted = fitter.fit(
        FitPreprocessorRequest(split_manifest=_split_manifest_result(), preprocessing=_preprocessing_spec())
    )

    materializer = NBaIoTProcessedSplitMaterializer(
        raw_root=raw_root,
        materialized_root=materialized_root,
        processed_root=tmp_path / "processed",
        manifest_root=bound_root,
        feature_columns=_FEATURE_COLUMNS,
        source_row_identity=_SOURCE_ROW_IDENTITY,
        boundary_spec=LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY,
        streaming_chunk_policy=_STREAMING_CHUNK_POLICY,
    )
    result = materializer.materialize(
        MaterializeProcessedSplitsRequest(split_manifest=_split_manifest_result(), fitted_preprocessor=fitted)
    )

    assert len(result.artifacts) == 3
    train_table = pq.read_table(tmp_path / "processed" / "DeviceOne" / "train" / "processed.parquet")
    assert train_table.schema.names == list(_FEATURE_COLUMNS)
    assert train_table.num_rows == 600
    calibration_table = pq.read_table(tmp_path / "processed" / "DeviceOne" / "calibration" / "processed.parquet")
    assert calibration_table.num_rows == 200
    test_table = pq.read_table(tmp_path / "processed" / "DeviceOne" / "test" / "processed.parquet")
    assert test_table.num_rows == 280  # 180 held-out benign + 100 attack


def test_transform_is_deterministic_across_repeated_runs(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    materialized_root = tmp_path / "materialized"
    _materialize(raw_root, materialized_root, device_id="DeviceOne", benign_rows=800, attack_rows=80)
    bound_root = _bound_manifest_root(tmp_path)
    fitter = NBaIoTPreprocessorFitter(
        raw_root=raw_root,
        materialized_root=materialized_root,
        scratch_root=tmp_path / "scratch",
        artifact_store=FileArtifactStore(root=bound_root),
        feature_columns=_FEATURE_COLUMNS,
        boundary_spec=LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY,
        streaming_chunk_policy=_STREAMING_CHUNK_POLICY,
    )
    request = FitPreprocessorRequest(split_manifest=_split_manifest_result(), preprocessing=_preprocessing_spec())

    first = fitter.fit(request)
    second = fitter.fit(request)

    assert first.artifact.content_hash == second.artifact.content_hash
    assert first.training_row_order_checksum == second.training_row_order_checksum


def test_fit_rejects_an_unauthorized_preprocessing_policy(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    materialized_root = tmp_path / "materialized"
    _materialize(raw_root, materialized_root, device_id="DeviceOne", benign_rows=500, attack_rows=50)
    store = FileArtifactStore(root=_bound_manifest_root(tmp_path))
    fitter = NBaIoTPreprocessorFitter(
        raw_root=raw_root,
        materialized_root=materialized_root,
        scratch_root=tmp_path / "scratch",
        artifact_store=store,
        feature_columns=_FEATURE_COLUMNS,
        boundary_spec=LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY,
        streaming_chunk_policy=_STREAMING_CHUNK_POLICY,
    )
    request = FitPreprocessorRequest(
        split_manifest=_split_manifest_result(),
        preprocessing=_preprocessing_spec(strategy=NormalizationStrategy.MIN_MAX),
    )

    with pytest.raises(PreprocessingError):
        fitter.fit(request)

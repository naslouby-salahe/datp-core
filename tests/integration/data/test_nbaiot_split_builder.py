from pathlib import Path

import msgspec
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from datp_core.application.ports.data import BuildSplitManifestRequest
from datp_core.domain.artifacts.keys import (
    ArtifactNamespace,
    DatasetArtifactKey,
    SerializationFormat,
    StorageRootKind,
    StorageRootSpec,
    StorageVisibility,
)
from datp_core.domain.artifacts.lineage import PartitionIdentity, SplitIdentity
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.data.datasets import Dataset
from datp_core.domain.data.partitioning import ClientPartitionResult
from datp_core.domain.data.splitting import (
    LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY,
    BenignCalibrationSplitSpec,
    SplitCollectionSpec,
    SplitManifest,
    TestSplitSpec,
    TrainingSplitSpec,
)
from datp_core.domain.errors import SplitError
from datp_core.domain.evaluation.operating_points import ClientEligibilityStatus
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import ClientRoster
from datp_core.domain.mathematics.pooled_statistics import (
    PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES,
    ProtocolEligibilitySpec,
)
from datp_core.domain.runtime.admissibility import ChunkRowCount, CsvBlockBytes
from datp_core.domain.runtime.policies import StreamingChunkPolicy
from datp_core.infrastructure.data.nbaiot_source import NBaIoTChunkedSourceAdapter
from datp_core.infrastructure.data.nbaiot_split import RegimeAStaticSplitBuilder
from datp_core.infrastructure.persistence.artifacts import FileArtifactStore
from datp_core.infrastructure.persistence.paths import ArtifactPathResolver, ResolveArtifactLocationRequest
from datp_core.infrastructure.persistence.roots import BoundStorageRoot, bind_storage_root

_FEATURE_COLUMNS = "feature_a,feature_b,feature_c"
_STREAMING_CHUNK_POLICY = StreamingChunkPolicy(
    csv_block_bytes=CsvBlockBytes(value=8 * 1024 * 1024), parquet_batch_rows=ChunkRowCount(value=50_000)
)
_PROTOCOL_ELIGIBILITY = ProtocolEligibilitySpec(
    minimum_calibration_samples=PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES
)


def _write_csv(path: Path, *, rows: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [_FEATURE_COLUMNS]
    lines.extend(f"{index}.0,{index * 2}.0,{index * 3}.0" for index in range(rows))
    path.write_text("\n".join(lines) + "\n")


def _materialize_device(
    raw_root: Path, materialized_root: Path, *, device_id: str, benign_rows: int, attack_rows: int
) -> None:
    _write_csv(raw_root / device_id / "benign_traffic.csv", rows=benign_rows)
    _write_csv(raw_root / device_id / "gafgyt_attacks" / "combo.csv", rows=attack_rows)
    NBaIoTChunkedSourceAdapter(
        raw_root=raw_root, output_root=materialized_root, csv_block_bytes=_STREAMING_CHUNK_POLICY.csv_block_bytes.value
    ).materialize_device(device_id)


def _bound_root(tmp_path: Path) -> BoundStorageRoot:
    return bind_storage_root(
        spec=StorageRootSpec(kind=StorageRootKind.PROCESSED_DATA, visibility=StorageVisibility.SCIENTIFIC_OUTPUT),
        absolute_path=tmp_path / "manifests",
    )


def _dummy_ref() -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value="artifact-" + "b" * 64),
        artifact_type=ArtifactType.SOURCE_INSPECTION,
        content_hash="b" * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.JSON,
    )


def _partition_result(client_ids: tuple[str, ...]) -> ClientPartitionResult:
    roster = ClientRoster(
        client_ids=tuple(sorted((ClientId(value=value) for value in client_ids), key=lambda c: c.value))
    )
    return ClientPartitionResult(
        partition_manifest=_dummy_ref(),
        client_roster=roster,
        partition_identity=PartitionIdentity(value=StageFingerprint(value="d" * 64)),
    )


def _split_collection_spec(partition_identity: PartitionIdentity) -> SplitCollectionSpec:
    return SplitCollectionSpec(
        training=TrainingSplitSpec(
            split_identity=SplitIdentity(value=StageFingerprint(value="1" * 64)), partition_identity=partition_identity
        ),
        calibration=BenignCalibrationSplitSpec(
            split_identity=SplitIdentity(value=StageFingerprint(value="2" * 64)), partition_identity=partition_identity
        ),
        test=TestSplitSpec(
            split_identity=SplitIdentity(value=StageFingerprint(value="3" * 64)), partition_identity=partition_identity
        ),
    )


def _request(client_ids: tuple[str, ...]) -> BuildSplitManifestRequest:
    partition = _partition_result(client_ids)
    return BuildSplitManifestRequest(partition=partition, splits=_split_collection_spec(partition.partition_identity))


def _read_manifest(*, result_ref: ArtifactRef, bound_root: BoundStorageRoot) -> SplitManifest:
    path = (
        ArtifactPathResolver()
        .resolve(
            ResolveArtifactLocationRequest(
                key=DatasetArtifactKey(
                    artifact_type=ArtifactType.SPLIT_MANIFEST,
                    dataset=Dataset.N_BAIOT,
                    stage_identity=StageFingerprint(value=result_ref.content_hash),
                    namespace=ArtifactNamespace.DATP_ANCHOR,
                ),
                root=bound_root,
                artifact=result_ref,
            )
        )
        .absolute_path
    )
    return msgspec.json.decode(path.read_bytes(), type=SplitManifest)


def test_split_builder_excludes_attack_rows_from_calibration_and_reports_no_overlap(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    materialized_root = tmp_path / "materialized"
    _materialize_device(raw_root, materialized_root, device_id="DeviceOne", benign_rows=1000, attack_rows=200)
    bound_root = _bound_root(tmp_path)
    builder = RegimeAStaticSplitBuilder(
        materialized_root=materialized_root,
        artifact_store=FileArtifactStore(root=bound_root),
        boundary_spec=LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY,
        streaming_chunk_policy=_STREAMING_CHUNK_POLICY,
        protocol_eligibility=_PROTOCOL_ELIGIBILITY,
    )

    result = builder.build(_request(("DeviceOne",)))
    manifest = _read_manifest(result_ref=result.split_manifest, bound_root=bound_root)

    (membership,) = manifest.client_memberships
    assert membership.train_row_count == 600
    assert membership.calibration_row_count == 200
    assert membership.test_row_count == 380  # 180 held-out benign + 200 attack, gaps (10+10) discarded
    assert membership.train_row_count + membership.calibration_row_count + membership.test_row_count + 20 == 1200


def test_split_builder_is_deterministic_across_repeated_runs(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    materialized_root = tmp_path / "materialized"
    _materialize_device(raw_root, materialized_root, device_id="DeviceOne", benign_rows=500, attack_rows=50)
    request = _request(("DeviceOne",))

    first = RegimeAStaticSplitBuilder(
        materialized_root=materialized_root,
        artifact_store=FileArtifactStore(root=_bound_root(tmp_path / "first")),
        boundary_spec=LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY,
        streaming_chunk_policy=_STREAMING_CHUNK_POLICY,
        protocol_eligibility=_PROTOCOL_ELIGIBILITY,
    ).build(request)
    second = RegimeAStaticSplitBuilder(
        materialized_root=materialized_root,
        artifact_store=FileArtifactStore(root=_bound_root(tmp_path / "second")),
        boundary_spec=LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY,
        streaming_chunk_policy=_STREAMING_CHUNK_POLICY,
        protocol_eligibility=_PROTOCOL_ELIGIBILITY,
    ).build(request)

    assert first.split_manifest.content_hash == second.split_manifest.content_hash


def test_split_builder_marks_a_small_client_as_fallback_and_a_large_client_as_eligible(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    materialized_root = tmp_path / "materialized"
    _materialize_device(raw_root, materialized_root, device_id="TinyDevice", benign_rows=50, attack_rows=5)
    _materialize_device(raw_root, materialized_root, device_id="BigDevice", benign_rows=5000, attack_rows=500)
    bound_root = _bound_root(tmp_path)
    builder = RegimeAStaticSplitBuilder(
        materialized_root=materialized_root,
        artifact_store=FileArtifactStore(root=bound_root),
        boundary_spec=LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY,
        streaming_chunk_policy=_STREAMING_CHUNK_POLICY,
        protocol_eligibility=_PROTOCOL_ELIGIBILITY,
    )

    result = builder.build(_request(("TinyDevice", "BigDevice")))
    manifest = _read_manifest(result_ref=result.split_manifest, bound_root=bound_root)

    memberships = {membership.client_id.value: membership for membership in manifest.client_memberships}
    assert memberships["TinyDevice"].calibration_row_count == 10  # 50 * 0.20 = 10 < n_min=100
    assert memberships["TinyDevice"].eligibility.status is ClientEligibilityStatus.FALLBACK_ASSIGNED
    assert memberships["BigDevice"].calibration_row_count == 1000  # 5000 * 0.20 = 1000 >= n_min=100
    assert memberships["BigDevice"].eligibility.status is ClientEligibilityStatus.ELIGIBLE


def test_split_builder_rejects_a_materialized_file_missing_the_label_column(tmp_path: Path) -> None:
    materialized_root = tmp_path / "materialized"
    device_dir = materialized_root / "DeviceOne"
    device_dir.mkdir(parents=True)
    pq.write_table(pa.table({"feature_a": [1.0, 2.0, 3.0]}), device_dir / "source.parquet")
    builder = RegimeAStaticSplitBuilder(
        materialized_root=materialized_root,
        artifact_store=FileArtifactStore(root=_bound_root(tmp_path)),
        boundary_spec=LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY,
        streaming_chunk_policy=_STREAMING_CHUNK_POLICY,
        protocol_eligibility=_PROTOCOL_ELIGIBILITY,
    )
    request = _request(("DeviceOne",))

    with pytest.raises(SplitError):
        builder.build(request)

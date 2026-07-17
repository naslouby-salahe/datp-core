from pathlib import Path
from tempfile import TemporaryDirectory

import msgspec
from hypothesis import given, settings
from hypothesis import strategies as st

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
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import ClientRoster
from datp_core.domain.mathematics.pooled_statistics import (
    PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES,
    ProtocolEligibilitySpec,
)
from datp_core.domain.runtime.admissibility import ChunkRowCount, CsvBlockBytes
from datp_core.domain.runtime.policies import StreamingChunkPolicy
from datp_core.infrastructure.data.nbaiot.source import NBaIoTChunkedSourceAdapter
from datp_core.infrastructure.data.nbaiot.split import NBaIoTRegimeAStaticSplitBuilder
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


def _dummy_ref() -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value="artifact-" + "b" * 64),
        artifact_type=ArtifactType.SOURCE_INSPECTION,
        content_hash="b" * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.JSON,
    )


def _request() -> BuildSplitManifestRequest:
    roster = ClientRoster(client_ids=(ClientId(value="DeviceOne"),))
    partition_identity = PartitionIdentity(value=StageFingerprint(value="d" * 64))
    partition = ClientPartitionResult(
        partition_manifest=_dummy_ref(), client_roster=roster, partition_identity=partition_identity
    )
    splits = SplitCollectionSpec(
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
    return BuildSplitManifestRequest(partition=partition, splits=splits)


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


@settings(deadline=1500)
@given(benign_rows=st.integers(min_value=600, max_value=2000), attack_rows=st.integers(min_value=0, max_value=200))
def test_calibration_never_exceeds_the_benign_row_count_and_split_is_deterministic(
    benign_rows: int, attack_rows: int
) -> None:
    with TemporaryDirectory() as raw_directory, TemporaryDirectory() as manifest_directory:
        raw_root = Path(raw_directory)
        _write_csv(raw_root / "DeviceOne" / "benign_traffic.csv", rows=benign_rows)
        if attack_rows:
            _write_csv(raw_root / "DeviceOne" / "gafgyt_attacks" / "combo.csv", rows=attack_rows)
        materialized_root = Path(manifest_directory) / "materialized"
        NBaIoTChunkedSourceAdapter(
            raw_root=raw_root,
            output_root=materialized_root,
            csv_block_bytes=_STREAMING_CHUNK_POLICY.csv_block_bytes.value,
        ).materialize_device("DeviceOne")
        bound_root = bind_storage_root(
            spec=StorageRootSpec(kind=StorageRootKind.PROCESSED_DATA, visibility=StorageVisibility.SCIENTIFIC_OUTPUT),
            absolute_path=Path(manifest_directory) / "manifests",
        )
        store = FileArtifactStore(root=bound_root)
        builder = NBaIoTRegimeAStaticSplitBuilder(
            materialized_root=materialized_root,
            artifact_store=store,
            boundary_spec=LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY,
            streaming_chunk_policy=_STREAMING_CHUNK_POLICY,
            protocol_eligibility=_PROTOCOL_ELIGIBILITY,
        )
        request = _request()

        first = builder.build(request)
        second = builder.build(request)

        assert first.split_manifest.content_hash == second.split_manifest.content_hash

        manifest = _read_manifest(result_ref=first.split_manifest, bound_root=bound_root)
        (membership,) = manifest.client_memberships
        # calibration is a 0.20-fraction slice of the benign-only prefix; even if every
        # attack row were (incorrectly) counted, the total could never stay within this
        # bound once attack_rows is large relative to a small calibration slice — this
        # bounds calibration strictly by the benign total, never by benign+attack.
        assert membership.calibration_row_count <= int(benign_rows * 0.20) + 1
        assert membership.train_row_count + membership.calibration_row_count + membership.test_row_count <= (
            benign_rows + attack_rows
        )

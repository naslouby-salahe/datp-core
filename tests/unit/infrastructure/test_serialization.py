from datetime import UTC, datetime

from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.manifests import ArtifactType, ManifestType
from datp_core.domain.artifacts.provenance import (
    CodeState,
    DependencyLockState,
    EnvironmentInventory,
    ProvenanceRecord,
)
from datp_core.domain.artifacts.references import (
    ArtifactId,
    ArtifactRef,
    ArtifactReferenceCollection,
    ArtifactSchemaVersion,
    ExecutionAttemptId,
    RunIdentity,
    StageFingerprint,
    StageRunIdentity,
)
from datp_core.domain.learning.scores import ScoringBatchSpec
from datp_core.domain.learning.training import (
    ClientBatchPartitioning,
    DeterminismLevel,
    OptimizerStepSemantics,
    PrecisionMode,
    TrainingBatchSpec,
)
from datp_core.domain.runtime.admissibility import BatchSize, GradientAccumulationSteps, WorkerCount
from datp_core.domain.runtime.policies import DevicePolicy, DeviceSpec, HardwareInventory, PipelineStage
from datp_core.infrastructure.persistence.serialization import (
    DecodedManifestRecord,
    DecodedProvenanceRecord,
    IncompatibleSchemaVersion,
    ManifestRecord,
    ProvenanceRecordEnvelope,
    deserialize_manifest_record,
    deserialize_provenance_record,
    serialize_manifest_record,
    serialize_provenance_record,
)


def _record(*, schema_version: str = "v1") -> ManifestRecord:
    version = ArtifactSchemaVersion(value=schema_version)
    return ManifestRecord(
        manifest_type=ManifestType.SPLIT,
        artifact=ArtifactRef(
            artifact_id=ArtifactId(value="artifact-" + "a" * 64),
            artifact_type=ArtifactType.SPLIT_MANIFEST,
            content_hash="b" * 64,
            schema_version=version,
            serialization_format=SerializationFormat.JSON,
        ),
        schema_version=version,
        payload=b"",
    )


def _provenance_record() -> ProvenanceRecordEnvelope:
    version = ArtifactSchemaVersion(value="v1")
    artifact = _provenance_artifact(version)
    stage_fingerprint = StageFingerprint(value="e" * 64)
    record = ProvenanceRecord(
        artifact=artifact,
        produced_by=StageRunIdentity(
            run_identity=RunIdentity(value="run-" + "f" * 64),
            execution_attempt_id=ExecutionAttemptId(value="attempt-123e4567-e89b-42d3-a456-426614174000"),
            stage=PipelineStage.SPLIT_BUILD,
            stage_fingerprint=stage_fingerprint,
        ),
        stage_fingerprint=stage_fingerprint,
        inputs=ArtifactReferenceCollection(references=()),
        consumed_by=(),
        code_state=CodeState(commit_identity=None, is_dirty=False, dirty_diff_hash=None, source_package_version=None),
        dependency_lock_state=DependencyLockState(
            lock_identity=None,
            scikit_learn_version=None,
            pyarrow_version=None,
            numpy_version=None,
            scipy_version=None,
            blake3_version=None,
            msgspec_version=None,
        ),
        environment=_environment(),
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return ProvenanceRecordEnvelope(schema_version=version, record=record)


def _provenance_artifact(version: ArtifactSchemaVersion) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value="artifact-" + "c" * 64),
        artifact_type=ArtifactType.SPLIT_MANIFEST,
        content_hash="d" * 64,
        schema_version=version,
        serialization_format=SerializationFormat.JSON,
    )


def _environment() -> EnvironmentInventory:
    return EnvironmentInventory(
        hardware=HardwareInventory(
            cuda_available=False,
            gpu_name=None,
            gpu_count=0,
            vram_bytes=None,
            torch_version=None,
            cuda_runtime=None,
            driver_version=None,
            cpu_count=1,
            ram_bytes=None,
        ),
        selected_device=DeviceSpec(policy=DevicePolicy.CPU_ALLOWED, gpu_index=None),
        precision=PrecisionMode.FP32,
        determinism=DeterminismLevel.STRICT,
        training_batch=TrainingBatchSpec(
            micro_batch_size=BatchSize(value=1),
            gradient_accumulation_steps=GradientAccumulationSteps(value=1),
            effective_batch_size=BatchSize(value=1),
            dataloader_batch_size=BatchSize(value=1),
            client_batch_partitioning=ClientBatchPartitioning.WHOLE_CLIENT,
            optimizer_step_semantics=OptimizerStepSemantics.AFTER_GRADIENT_ACCUMULATION,
        ),
        scoring_batch=ScoringBatchSpec(
            calibration_batch_size=BatchSize(value=1),
            test_batch_size=BatchSize(value=1),
            temporal_batch_size=BatchSize(value=1),
        ),
        dataloader_workers=WorkerCount(value=0),
        scikit_learn_version=None,
        pyarrow_version=None,
        numpy_version=None,
        scipy_version=None,
        blake3_version=None,
        msgspec_version=None,
    )


def test_manifest_round_trip_preserves_empty_payload_and_schema_version_exactly() -> None:
    record = _record()
    serialized = serialize_manifest_record(record)

    result = deserialize_manifest_record(serialized, expected_schema_version=record.schema_version)

    assert result == DecodedManifestRecord(record=record)


def test_schema_version_mismatch_is_reported_as_incompatible_without_coercion() -> None:
    serialized = serialize_manifest_record(_record(schema_version="v1"))

    result = deserialize_manifest_record(serialized, expected_schema_version=ArtifactSchemaVersion(value="v2"))

    assert result == IncompatibleSchemaVersion(
        expected=ArtifactSchemaVersion(value="v2"), actual=ArtifactSchemaVersion(value="v1")
    )


def test_manifest_record_rejects_an_artifact_with_a_different_schema_version() -> None:
    version = ArtifactSchemaVersion(value="v1")
    artifact = ArtifactRef(
        artifact_id=ArtifactId(value="artifact-" + "a" * 64),
        artifact_type=ArtifactType.SPLIT_MANIFEST,
        content_hash="b" * 64,
        schema_version=version,
        serialization_format=SerializationFormat.JSON,
    )

    try:
        ManifestRecord(
            manifest_type=ManifestType.SPLIT,
            artifact=artifact,
            schema_version=ArtifactSchemaVersion(value="v2"),
            payload=b"synthetic",
        )
    except ValueError as error:
        assert str(error) == "manifest record schema version must match its artifact reference"
    else:
        raise AssertionError("mismatched schema versions must be rejected")


def test_provenance_round_trip_preserves_every_typed_field() -> None:
    record = _provenance_record()

    result = deserialize_provenance_record(
        serialize_provenance_record(record), expected_schema_version=record.schema_version
    )

    assert result == DecodedProvenanceRecord(record=record)

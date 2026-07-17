from datp_core.domain.artifacts.keys import (
    ArtifactNamespace,
    SerializationFormat,
    StorageRootKind,
    StorageVisibility,
    WriteDisposition,
)
from datp_core.domain.artifacts.lineage import IntegrityStatus, SchemaCompatibility
from datp_core.domain.artifacts.manifests import ArtifactType, ManifestType
from datp_core.domain.artifacts.references import LockScope, ValidationStatus


def test_storage_and_namespace_vocabularies_are_complete() -> None:
    assert len(StorageRootKind) == 13
    assert tuple(StorageVisibility) == (
        StorageVisibility.EXTERNAL_READONLY,
        StorageVisibility.SCIENTIFIC_OUTPUT,
        StorageVisibility.EPHEMERAL,
        StorageVisibility.TEST_ISOLATED,
    )
    assert tuple(ArtifactNamespace) == (
        ArtifactNamespace.DATP_ANCHOR,
        ArtifactNamespace.COMPLETE,
        ArtifactNamespace.RECOVERY,
        ArtifactNamespace.CACHE,
        ArtifactNamespace.STAGING,
        ArtifactNamespace.TEST_SANDBOX,
    )
    assert ArtifactNamespace.DATP_ANCHOR is not ArtifactNamespace.COMPLETE


def test_serialization_and_write_vocabularies_are_complete() -> None:
    assert tuple(SerializationFormat) == (
        SerializationFormat.PARQUET,
        SerializationFormat.JSON,
        SerializationFormat.CSV,
        SerializationFormat.MARKDOWN,
        SerializationFormat.LATEX,
        SerializationFormat.SVG,
        SerializationFormat.PNG,
        SerializationFormat.PDF,
        SerializationFormat.TORCH_STATE,
    )
    assert len(WriteDisposition) == 3


def test_manifest_and_artifact_types_cover_every_persisted_entity_once() -> None:
    assert len(ManifestType) == 13
    assert tuple(ArtifactType) == (
        ArtifactType.ARTIFACT_BUNDLE,
        ArtifactType.RAW_DATASET_REF,
        ArtifactType.SOURCE_INSPECTION,
        ArtifactType.FEATURE_SCHEMA_MANIFEST,
        ArtifactType.PARTITION_MANIFEST,
        ArtifactType.SPLIT_MANIFEST,
        ArtifactType.FITTED_PREPROCESSOR,
        ArtifactType.PROCESSED_SPLIT,
        ArtifactType.SCIENTIFIC_CHECKPOINT,
        ArtifactType.CHECKPOINT_SELECTION,
        ArtifactType.RECOVERY_CHECKPOINT,
        ArtifactType.FEASIBILITY_RESULT,
        ArtifactType.CALIBRATION_SCORE_SET,
        ArtifactType.TEST_SCORE_SET,
        ArtifactType.TEMPORAL_SCORE_SET,
        ArtifactType.THRESHOLD_OUTPUT,
        ArtifactType.METRIC_OUTPUT,
        ArtifactType.RESOURCE_COST_OUTPUT,
        ArtifactType.STATISTICAL_OUTPUT,
        ArtifactType.ANCHOR_REPRODUCTION_RESULT,
        ArtifactType.RESOLVED_CONFIGURATION,
        ArtifactType.DRAFT_EXECUTION_PLAN,
        ArtifactType.FINAL_EXECUTION_PLAN,
        ArtifactType.RESULT_FREEZE,
        ArtifactType.TABLE_INPUT,
        ArtifactType.FIGURE_INPUT,
        ArtifactType.RENDERED_TABLE,
        ArtifactType.RENDERED_FIGURE,
        ArtifactType.WORDING_OUTPUT,
        ArtifactType.CODE_STATE,
        ArtifactType.DEPENDENCY_LOCK_STATE,
        ArtifactType.REUSE_LEDGER,
        ArtifactType.RUN_STATE_RECORD,
        ArtifactType.EXPERIMENT_MANIFEST,
    )
    assert len({artifact_type.value for artifact_type in ArtifactType}) == len(ArtifactType)


def test_lock_validation_integrity_and_schema_vocabularies_are_complete() -> None:
    assert len(LockScope) == 2
    assert len(ValidationStatus) == 3
    assert len(IntegrityStatus) == 4
    assert len(SchemaCompatibility) == 3

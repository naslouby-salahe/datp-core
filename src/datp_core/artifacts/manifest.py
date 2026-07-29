"""Manifest helpers for reusable processed-data publications."""

from pathlib import Path

from datp_core.artifacts.layout import ProcessedAssetName
from datp_core.artifacts.serialization import serialize_json_model
from datp_core.domain.errors import ArtifactIntegrityError
from datp_core.domain.values import Checksum
from datp_core.preprocessing.models import PreprocessingManifest, PreprocessingValidationReport, TransformedSchema


def write_preprocessing_manifest(directory: Path, manifest: PreprocessingManifest) -> Checksum:
    return serialize_json_model(manifest, directory / ProcessedAssetName.PREPROCESSING_MANIFEST)


def write_transformed_schema(directory: Path, schema: TransformedSchema) -> Checksum:
    return serialize_json_model(schema, directory / ProcessedAssetName.SCHEMA)


def write_validation_report(directory: Path, report: PreprocessingValidationReport) -> Checksum:
    return serialize_json_model(report, directory / ProcessedAssetName.VALIDATION_REPORT)


def read_preprocessing_manifest(directory: Path) -> PreprocessingManifest:
    path = directory / ProcessedAssetName.PREPROCESSING_MANIFEST
    if not path.is_file():
        raise ArtifactIntegrityError("missing preprocessing manifest", subject=str(directory))
    return PreprocessingManifest.model_validate_json(path.read_text(encoding="utf-8"))


def read_transformed_schema(directory: Path) -> TransformedSchema:
    path = directory / ProcessedAssetName.SCHEMA
    if not path.is_file():
        raise ArtifactIntegrityError("missing transformed schema", subject=str(directory))
    return TransformedSchema.model_validate_json(path.read_text(encoding="utf-8"))


def read_validation_report(directory: Path) -> PreprocessingValidationReport:
    path = directory / ProcessedAssetName.VALIDATION_REPORT
    if not path.is_file():
        raise ArtifactIntegrityError("missing preprocessing validation report", subject=str(directory))
    return PreprocessingValidationReport.model_validate_json(path.read_text(encoding="utf-8"))

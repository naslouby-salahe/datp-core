"""Generic JSON manifest helpers for reusable processed-data publications."""

from pathlib import Path

from pydantic import BaseModel

from datp_core.artifacts.layout import ProcessedAssetName
from datp_core.artifacts.serialization import serialize_json_model
from datp_core.domain.errors import ArtifactIntegrityError
from datp_core.domain.values import Checksum


def write_json_model(directory: Path, asset_name: ProcessedAssetName, model: BaseModel) -> Checksum:
    return serialize_json_model(model, directory / asset_name)


def read_json_model[ModelT: BaseModel](
    directory: Path, asset_name: ProcessedAssetName, model_type: type[ModelT]
) -> ModelT:
    path = directory / asset_name
    if not path.is_file():
        raise ArtifactIntegrityError(f"missing {asset_name.value}", subject=str(directory))
    return model_type.model_validate_json(path.read_text(encoding="utf-8"))


def write_preprocessing_manifest(directory: Path, manifest: BaseModel) -> Checksum:
    return write_json_model(directory, ProcessedAssetName.PREPROCESSING_MANIFEST, manifest)


def write_transformed_schema(directory: Path, schema: BaseModel) -> Checksum:
    return write_json_model(directory, ProcessedAssetName.SCHEMA, schema)


def write_validation_report(directory: Path, report: BaseModel) -> Checksum:
    return write_json_model(directory, ProcessedAssetName.VALIDATION_REPORT, report)


def read_preprocessing_manifest[ModelT: BaseModel](directory: Path, model_type: type[ModelT]) -> ModelT:
    return read_json_model(directory, ProcessedAssetName.PREPROCESSING_MANIFEST, model_type)


def read_transformed_schema[ModelT: BaseModel](directory: Path, model_type: type[ModelT]) -> ModelT:
    return read_json_model(directory, ProcessedAssetName.SCHEMA, model_type)


def read_validation_report[ModelT: BaseModel](directory: Path, model_type: type[ModelT]) -> ModelT:
    return read_json_model(directory, ProcessedAssetName.VALIDATION_REPORT, model_type)

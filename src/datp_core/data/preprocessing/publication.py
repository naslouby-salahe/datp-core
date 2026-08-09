from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ValidationError

from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.repositories.publication import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    complete_digest,
    publish_artifact,
)
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.errors import (
    ArtifactIntegrityError,
    ErrorMessage,
)
from datp_core.core.identifiers import (
    ArtifactFileName,
    ContractSubject,
    PublicationStatus,
    SerializedDocumentText,
)
from datp_core.data.preprocessing.artifacts import ProcessedAssetName


@dataclass(frozen=True, slots=True)
class ProcessedPublication[ManifestT: BaseModel, SchemaT: BaseModel, ReportT: BaseModel]:
    coordinate_directory: Path
    manifest: ManifestT
    schema: SchemaT
    writer: Callable[[Path], ReportT]
    required_assets: tuple[ProcessedAssetName, ...]
    overwrite: bool
    manifest_type: type[ManifestT]
    schema_type: type[SchemaT]
    report_type: type[ReportT]


@dataclass(frozen=True, slots=True)
class ProcessedPublicationResult[ManifestT: BaseModel]:
    coordinate_directory: Path
    publication_status: PublicationStatus
    manifest: ManifestT


def publish_processed[ManifestT: BaseModel, SchemaT: BaseModel, ReportT: BaseModel](
    publication: ProcessedPublication[ManifestT, SchemaT, ReportT],
) -> ProcessedPublicationResult[ManifestT]:
    outcome = publish_artifact(
        ArtifactPublication(
            target=publication.coordinate_directory,
            request=publication,
            codec=FunctionalArtifactCodec(
                writer=_write_processed,
                validator=_is_reusable,
                loader=_load_manifest,
                rebaser=lambda manifest, _directory: manifest,
            ),
            overwrite=publication.overwrite,
            complete_marker=ArtifactFileName(ProcessedAssetName.COMPLETE),
        )
    )
    return ProcessedPublicationResult(
        coordinate_directory=publication.coordinate_directory,
        publication_status=outcome.status,
        manifest=outcome.value,
    )


def _write_processed[ManifestT: BaseModel, SchemaT: BaseModel, ReportT: BaseModel](
    publication: ProcessedPublication[ManifestT, SchemaT, ReportT],
    directory: Path,
) -> ManifestT:
    report = publication.writer(directory)
    manifest_payload = _write_model(publication.manifest, directory.joinpath(ProcessedAssetName.PREPROCESSING_MANIFEST))
    schema_payload = _write_model(publication.schema, directory.joinpath(ProcessedAssetName.SCHEMA))
    _write_model(report, directory.joinpath(ProcessedAssetName.VALIDATION_REPORT))

    digest = complete_digest(manifest_payload, schema_payload)
    directory.joinpath(ProcessedAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")

    _assert_required_assets(directory, publication.required_assets)
    if not _is_reusable(publication, directory):
        raise ArtifactIntegrityError(
            ErrorMessage("processed publication failed complete-asset validation"),
            subject=ContractSubject.ARTIFACT_PATH,
        )
    return publication.manifest


def _load_manifest[ManifestT: BaseModel, SchemaT: BaseModel, ReportT: BaseModel](
    publication: ProcessedPublication[ManifestT, SchemaT, ReportT],
    directory: Path,
) -> ManifestT:
    return _read_model(directory, ProcessedAssetName.PREPROCESSING_MANIFEST, publication.manifest_type)


def _is_reusable[ManifestT: BaseModel, SchemaT: BaseModel, ReportT: BaseModel](
    publication: ProcessedPublication[ManifestT, SchemaT, ReportT],
    directory: Path,
) -> bool:
    try:
        manifest_path = directory.joinpath(ProcessedAssetName.PREPROCESSING_MANIFEST)
        schema_path = directory.joinpath(ProcessedAssetName.SCHEMA)
        complete_path = directory.joinpath(ProcessedAssetName.COMPLETE)

        if not (manifest_path.is_file() and schema_path.is_file() and complete_path.is_file()):
            return False

        manifest_text = manifest_path.read_text(encoding="utf-8")
        schema_text = schema_path.read_text(encoding="utf-8")

        expected = complete_digest(
            SerializedDocumentText(manifest_text),
            SerializedDocumentText(schema_text),
        )
        actual = Checksum(complete_path.read_text(encoding="utf-8").strip())

        if actual != expected:
            return False

        manifest = publication.manifest_type.model_validate_json(manifest_text)
        schema = publication.schema_type.model_validate_json(schema_text)
        _read_model(directory, ProcessedAssetName.VALIDATION_REPORT, publication.report_type)

    except (OSError, ValidationError, ArtifactIntegrityError, ValueError):
        return False

    return (
        manifest == publication.manifest
        and schema == publication.schema
        and _assets_exist(directory, publication.required_assets)
    )


def _write_model(model: BaseModel, destination: Path) -> SerializedDocumentText:
    payload = canonical_json_text(model)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(payload, encoding="utf-8")
    return payload


def _read_model[ModelT: BaseModel](
    directory: Path,
    asset: ProcessedAssetName,
    model_type: type[ModelT],
) -> ModelT:
    path = directory.joinpath(asset)
    if not path.is_file():
        raise ArtifactIntegrityError(
            ErrorMessage(f"missing {asset.value}"),
            subject=ContractSubject.ARTIFACT_PATH,
        )
    try:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as error:
        raise ArtifactIntegrityError(
            ErrorMessage(f"invalid {asset.value}"),
            subject=ContractSubject.ARTIFACT_PATH,
        ) from error


def _assets_exist(directory: Path, required_assets: tuple[ProcessedAssetName, ...]) -> bool:
    return all(directory.joinpath(asset).is_file() for asset in required_assets)


def _assert_required_assets(directory: Path, required_assets: tuple[ProcessedAssetName, ...]) -> None:
    missing = tuple(asset for asset in required_assets if not directory.joinpath(asset).is_file())
    if missing:
        raise ArtifactIntegrityError(
            ErrorMessage(f"processed publication missing assets: {', '.join(asset.value for asset in missing)}"),
            subject=ContractSubject.ARTIFACT_PATH,
        )

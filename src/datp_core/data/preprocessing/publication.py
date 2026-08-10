from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.errors import ArtifactIntegrityError, ErrorMessage
from datp_core.core.identifiers import ContractSubject
from datp_core.data.preprocessing.artifacts import ProcessedAssetName
from datp_core.runtime.filesystem import cleanup_staging_on_failure, create_staging_directory, replace_directory


@dataclass(frozen=True, slots=True)
class ProcessedPublication[ManifestT: BaseModel, SchemaT: BaseModel, ReportT: BaseModel]:
    coordinate_directory: Path
    manifest: ManifestT
    schema: SchemaT
    writer: Callable[[Path], ReportT]
    required_assets: tuple[ProcessedAssetName, ...]
    manifest_type: type[ManifestT]
    schema_type: type[SchemaT]
    report_type: type[ReportT]


@dataclass(frozen=True, slots=True)
class ProcessedPublicationResult[ManifestT: BaseModel]:
    coordinate_directory: Path
    manifest: ManifestT


def publish_processed[ManifestT: BaseModel, SchemaT: BaseModel, ReportT: BaseModel](
    publication: ProcessedPublication[ManifestT, SchemaT, ReportT],
) -> ProcessedPublicationResult[ManifestT]:
    temporary = create_staging_directory(publication.coordinate_directory)
    with cleanup_staging_on_failure(temporary):
        report = publication.writer(temporary)
        _write_model(publication.manifest, temporary / ProcessedAssetName.PREPROCESSING_MANIFEST)
        _write_model(publication.schema, temporary / ProcessedAssetName.SCHEMA)
        _write_model(report, temporary / ProcessedAssetName.VALIDATION_REPORT)
        _assert_required_assets(temporary, publication.required_assets)
        replace_directory(temporary, publication.coordinate_directory)
    return ProcessedPublicationResult(publication.coordinate_directory, publication.manifest)


def _write_model(model: BaseModel, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(canonical_json_text(model), encoding="utf-8")


def _assert_required_assets(directory: Path, required_assets: tuple[ProcessedAssetName, ...]) -> None:
    missing = tuple(asset for asset in required_assets if not (directory / asset).is_file())
    if missing:
        raise ArtifactIntegrityError(
            ErrorMessage(f"processed publication missing assets: {', '.join(asset.value for asset in missing)}"),
            subject=ContractSubject.ARTIFACT_PATH,
        )

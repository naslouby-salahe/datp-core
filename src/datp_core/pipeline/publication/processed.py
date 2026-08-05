"""Processed preprocessing publication, validation, reuse, and completion."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from pydantic import BaseModel

from datp_core.domain.enums import ContractSubject, PublicationStatus
from datp_core.domain.errors import ArtifactIntegrityError
from datp_core.domain.values import Checksum
from datp_core.pipeline.publication.codec import ArtifactCodec, ArtifactPublication, publish_artifact
from datp_core.pipeline.publication.completion import complete_digest
from datp_core.pipeline.publication.serialization import load_model_file, serialize_json_model
from datp_core.preprocessing.contracts import ProcessedAssetName


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


@dataclass(frozen=True, slots=True)
class _ProcessedArtifactCodec[ManifestT: BaseModel, SchemaT: BaseModel, ReportT: BaseModel](
    ArtifactCodec[ProcessedPublication[ManifestT, SchemaT, ReportT], ManifestT]
):
    def write(
        self,
        request: ProcessedPublication[ManifestT, SchemaT, ReportT],
        directory: Path,
    ) -> ManifestT:
        return _write_processed(directory, request)

    def validate(
        self,
        request: ProcessedPublication[ManifestT, SchemaT, ReportT],
        directory: Path,
    ) -> bool:
        return _is_reusable(directory, request)

    def load(
        self,
        request: ProcessedPublication[ManifestT, SchemaT, ReportT],
        directory: Path,
    ) -> ManifestT:
        return _read_model(directory, ProcessedAssetName.PREPROCESSING_MANIFEST, request.manifest_type)

    def rebase(self, result: ManifestT, directory: Path) -> ManifestT:
        del directory
        return result


def publish_processed[ManifestT: BaseModel, SchemaT: BaseModel, ReportT: BaseModel](
    publication: ProcessedPublication[ManifestT, SchemaT, ReportT],
) -> ProcessedPublicationResult[ManifestT]:
    outcome = publish_artifact(
        ArtifactPublication(
            target=publication.coordinate_directory,
            request=publication,
            codec=cast(
                ArtifactCodec[ProcessedPublication[ManifestT, SchemaT, ReportT], ManifestT],
                _ProcessedArtifactCodec(),
            ),
            overwrite=publication.overwrite,
        )
    )
    return ProcessedPublicationResult(
        coordinate_directory=publication.coordinate_directory,
        publication_status=outcome.status,
        manifest=outcome.value,
    )


def _write_processed[ManifestT: BaseModel, SchemaT: BaseModel, ReportT: BaseModel](
    temporary: Path,
    publication: ProcessedPublication[ManifestT, SchemaT, ReportT],
) -> ManifestT:
    report = publication.writer(temporary)
    serialize_json_model(publication.manifest, temporary / ProcessedAssetName.PREPROCESSING_MANIFEST)
    serialize_json_model(publication.schema, temporary / ProcessedAssetName.SCHEMA)
    serialize_json_model(report, temporary / ProcessedAssetName.VALIDATION_REPORT)
    digest = complete_digest(
        (temporary / ProcessedAssetName.PREPROCESSING_MANIFEST).read_text(encoding="utf-8"),
        (temporary / ProcessedAssetName.SCHEMA).read_text(encoding="utf-8"),
    )
    (temporary / ProcessedAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")
    _assert_required_assets(temporary, publication.required_assets)
    if not _is_reusable(temporary, publication):
        raise ArtifactIntegrityError(
            "processed publication failed complete-asset validation",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    return publication.manifest


def _is_reusable[ManifestT: BaseModel, SchemaT: BaseModel, ReportT: BaseModel](
    target: Path,
    publication: ProcessedPublication[ManifestT, SchemaT, ReportT],
) -> bool:
    try:
        manifest = _read_model(target, ProcessedAssetName.PREPROCESSING_MANIFEST, publication.manifest_type)
        schema = _read_model(target, ProcessedAssetName.SCHEMA, publication.schema_type)
        _read_model(target, ProcessedAssetName.VALIDATION_REPORT, publication.report_type)
        expected = complete_digest(
            (target / ProcessedAssetName.PREPROCESSING_MANIFEST).read_text(encoding="utf-8"),
            (target / ProcessedAssetName.SCHEMA).read_text(encoding="utf-8"),
        )
        actual = Checksum((target / ProcessedAssetName.COMPLETE).read_text(encoding="utf-8").strip())
    except (OSError, ArtifactIntegrityError, ValueError):
        return False
    return (
        actual == expected
        and manifest == publication.manifest
        and schema == publication.schema
        and _assets_exist(target, publication.required_assets)
    )


def _read_model[ModelT: BaseModel](
    directory: Path,
    asset_name: ProcessedAssetName,
    model_type: type[ModelT],
) -> ModelT:
    path = directory / asset_name
    if not path.is_file():
        raise ArtifactIntegrityError(f"missing {asset_name.value}", subject=ContractSubject.ARTIFACT_PATH)
    return load_model_file(model_type, path)


def _assets_exist(directory: Path, required_assets: tuple[ProcessedAssetName, ...]) -> bool:
    return all((directory / asset).is_file() for asset in required_assets)


def _assert_required_assets(directory: Path, required_assets: tuple[ProcessedAssetName, ...]) -> None:
    missing = tuple(asset for asset in required_assets if not (directory / asset).is_file())
    if missing:
        raise ArtifactIntegrityError(
            f"processed publication missing assets: {', '.join(asset.value for asset in missing)}",
            subject=ContractSubject.ARTIFACT_PATH,
        )

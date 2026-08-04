"""Processed-data publication codec and artifact-specific validation."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from pydantic import BaseModel

from datp_core.artifacts.completion import assert_complete_digest, complete_digest, write_complete_marker
from datp_core.artifacts.layout import ProcessedAssetName
from datp_core.artifacts.manifest import (
    read_preprocessing_manifest,
    read_transformed_schema,
    read_validation_report,
    write_preprocessing_manifest,
    write_transformed_schema,
    write_validation_report,
)
from datp_core.domain.enums import ContractSubject, PublicationStatus
from datp_core.domain.errors import ArtifactIntegrityError
from datp_core.pipeline.publication.atomic import (
    PublicationOutcome,
    cleanup_staging_directory,
    create_staging_directory,
    publish_atomically,
    replace_directory,
)
from datp_core.pipeline.publication.codec import (
    ArtifactCodec,
    ArtifactPublication,
    publish_artifact,
)


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
        return read_preprocessing_manifest(directory, request.manifest_type)

    def rebase(self, result: ManifestT, directory: Path) -> ManifestT:
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
    write_preprocessing_manifest(temporary, publication.manifest)
    write_transformed_schema(temporary, publication.schema)
    write_validation_report(temporary, report)
    digest = complete_digest(
        (temporary / ProcessedAssetName.PREPROCESSING_MANIFEST).read_text(encoding="utf-8"),
        (temporary / ProcessedAssetName.SCHEMA).read_text(encoding="utf-8"),
    )
    write_complete_marker(temporary, digest)
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
        manifest = read_preprocessing_manifest(target, publication.manifest_type)
        schema = read_transformed_schema(target, publication.schema_type)
        read_validation_report(target, publication.report_type)
    except (OSError, ArtifactIntegrityError, ValueError):
        return False
    expected = complete_digest(
        (target / ProcessedAssetName.PREPROCESSING_MANIFEST).read_text(encoding="utf-8"),
        (target / ProcessedAssetName.SCHEMA).read_text(encoding="utf-8"),
    )
    try:
        assert_complete_digest(target, expected)
    except ArtifactIntegrityError:
        return False
    return (
        manifest == publication.manifest
        and schema == publication.schema
        and _assets_exist(target, publication.required_assets)
    )


def _assets_exist(directory: Path, required_assets: tuple[ProcessedAssetName, ...]) -> bool:
    return all((directory / asset).is_file() for asset in required_assets)


def _assert_required_assets(directory: Path, required_assets: tuple[ProcessedAssetName, ...]) -> None:
    missing = tuple(asset for asset in required_assets if not (directory / asset).is_file())
    if missing:
        raise ArtifactIntegrityError(
            f"processed publication missing assets: {', '.join(asset.value for asset in missing)}",
            subject=ContractSubject.ARTIFACT_PATH,
        )

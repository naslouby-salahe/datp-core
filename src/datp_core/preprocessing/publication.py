"""Atomic publication and reload validation for fitted preprocessing outputs."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from filelock import FileLock
from pydantic import BaseModel, ValidationError

from datp_core.domain.enums import ContractSubject, PublicationStatus
from datp_core.domain.errors import ArtifactIntegrityError
from datp_core.domain.provenance import canonical_json_text
from datp_core.domain.values.checksums import Checksum, checksum_text
from datp_core.preprocessing.contracts import ProcessedAssetName
from datp_core.runtime.filesystem import (
    cleanup_staging_on_failure,
    create_staging_directory,
    remove_stale_staging_directories,
    replace_directory,
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


def publish_processed[ManifestT: BaseModel, SchemaT: BaseModel, ReportT: BaseModel](
    publication: ProcessedPublication[ManifestT, SchemaT, ReportT],
) -> ProcessedPublicationResult[ManifestT]:
    target = publication.coordinate_directory
    target.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(f"{target}.lock"):
        remove_stale_staging_directories(target)
        if not publication.overwrite and _is_reusable(target, publication):
            return ProcessedPublicationResult(
                coordinate_directory=target,
                publication_status=PublicationStatus.REUSED,
                manifest=_read_model(
                    target,
                    ProcessedAssetName.PREPROCESSING_MANIFEST,
                    publication.manifest_type,
                ),
            )
        staging = create_staging_directory(target)
        with cleanup_staging_on_failure(staging):
            _write_processed(staging, publication)
            replace_directory(staging, target)
    return ProcessedPublicationResult(
        coordinate_directory=target,
        publication_status=PublicationStatus.PUBLISHED,
        manifest=publication.manifest,
    )


def complete_digest(manifest_payload: str, schema_payload: str) -> Checksum:
    return checksum_text(f"{manifest_payload}\n{schema_payload}")


def _write_processed[ManifestT: BaseModel, SchemaT: BaseModel, ReportT: BaseModel](
    directory: Path,
    publication: ProcessedPublication[ManifestT, SchemaT, ReportT],
) -> None:
    report = publication.writer(directory)
    _write_model(publication.manifest, directory / ProcessedAssetName.PREPROCESSING_MANIFEST)
    _write_model(publication.schema, directory / ProcessedAssetName.SCHEMA)
    _write_model(report, directory / ProcessedAssetName.VALIDATION_REPORT)
    digest = complete_digest(
        (directory / ProcessedAssetName.PREPROCESSING_MANIFEST).read_text(encoding="utf-8"),
        (directory / ProcessedAssetName.SCHEMA).read_text(encoding="utf-8"),
    )
    (directory / ProcessedAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")
    _assert_required_assets(directory, publication.required_assets)
    if not _is_reusable(directory, publication):
        raise ArtifactIntegrityError(
            "processed publication failed complete-asset validation",
            subject=ContractSubject.ARTIFACT_PATH,
        )


def _is_reusable[ManifestT: BaseModel, SchemaT: BaseModel, ReportT: BaseModel](
    directory: Path,
    publication: ProcessedPublication[ManifestT, SchemaT, ReportT],
) -> bool:
    try:
        manifest = _read_model(
            directory,
            ProcessedAssetName.PREPROCESSING_MANIFEST,
            publication.manifest_type,
        )
        schema = _read_model(directory, ProcessedAssetName.SCHEMA, publication.schema_type)
        _read_model(directory, ProcessedAssetName.VALIDATION_REPORT, publication.report_type)
        expected = complete_digest(
            (directory / ProcessedAssetName.PREPROCESSING_MANIFEST).read_text(encoding="utf-8"),
            (directory / ProcessedAssetName.SCHEMA).read_text(encoding="utf-8"),
        )
        actual = Checksum((directory / ProcessedAssetName.COMPLETE).read_text(encoding="utf-8").strip())
    except (OSError, UnicodeError, ValidationError, ArtifactIntegrityError, ValueError):
        return False
    return (
        actual == expected
        and manifest == publication.manifest
        and schema == publication.schema
        and _assets_exist(directory, publication.required_assets)
    )


def _write_model(model: BaseModel, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(canonical_json_text(model), encoding="utf-8")


def _read_model[ModelT: BaseModel](
    directory: Path,
    asset: ProcessedAssetName,
    model_type: type[ModelT],
) -> ModelT:
    path = directory / asset
    if not path.is_file():
        raise ArtifactIntegrityError(
            f"missing {asset.value}",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    try:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError, ValueError) as error:
        raise ArtifactIntegrityError(
            f"invalid {asset.value}",
            subject=ContractSubject.ARTIFACT_PATH,
        ) from error


def _assets_exist(directory: Path, required_assets: tuple[ProcessedAssetName, ...]) -> bool:
    return all((directory / asset).is_file() for asset in required_assets)


def _assert_required_assets(directory: Path, required_assets: tuple[ProcessedAssetName, ...]) -> None:
    missing = tuple(asset for asset in required_assets if not (directory / asset).is_file())
    if missing:
        raise ArtifactIntegrityError(
            f"processed publication missing assets: {', '.join(asset.value for asset in missing)}",
            subject=ContractSubject.ARTIFACT_PATH,
        )

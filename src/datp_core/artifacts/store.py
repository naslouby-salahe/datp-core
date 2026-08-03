"""Atomic publication and reuse of processed-data coordinates."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

from filelock import FileLock
from pydantic import BaseModel

from datp_core.artifacts.completion import (
    assert_complete_digest,
    complete_digest,
    write_complete_marker,
)
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
class AtomicPublication:
    target: Path
    overwrite: bool
    is_reusable: Callable[[Path], bool]
    write: Callable[[Path], None]
    remove_target: Callable[[Path], None]


def publish_atomically(publication: AtomicPublication) -> bool:
    """Run the common lock, temporary-directory, and atomic-replacement lifecycle."""
    target = publication.target
    with FileLock(f"{target}.lock"):
        _remove_stale_temporary_directories(target)
        if not publication.overwrite and publication.is_reusable(target):
            return True
        if target.exists():
            publication.remove_target(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(mkdtemp(prefix=f".{target.name}.", dir=target.parent))
        try:
            publication.write(temporary)
            temporary.replace(target)
        except Exception:
            rmtree(temporary, ignore_errors=True)
            raise
    return False


def publish_processed[ManifestT: BaseModel, SchemaT: BaseModel, ReportT: BaseModel](
    publication: ProcessedPublication[ManifestT, SchemaT, ReportT],
) -> ProcessedPublicationResult[ManifestT]:
    target = publication.coordinate_directory
    reused = publish_atomically(
        AtomicPublication(
            target=target,
            overwrite=publication.overwrite,
            is_reusable=lambda directory: _is_reusable(directory, publication),
            write=lambda temporary: _write_processed(temporary, publication),
            remove_target=lambda directory: rmtree(directory),
        )
    )
    manifest = read_preprocessing_manifest(target, publication.manifest_type) if reused else publication.manifest
    status = PublicationStatus.REUSED if reused else PublicationStatus.PUBLISHED
    return ProcessedPublicationResult(target, status, manifest)


def _write_processed[ManifestT: BaseModel, SchemaT: BaseModel, ReportT: BaseModel](
    temporary: Path, publication: ProcessedPublication[ManifestT, SchemaT, ReportT]
) -> None:
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
            "processed publication failed complete-asset validation", subject=ContractSubject.ARTIFACT_PATH
        )


def _is_reusable[ManifestT: BaseModel, SchemaT: BaseModel, ReportT: BaseModel](
    target: Path, publication: ProcessedPublication[ManifestT, SchemaT, ReportT]
) -> bool:
    try:
        manifest = read_preprocessing_manifest(target, publication.manifest_type)
        schema = read_transformed_schema(target, publication.schema_type)
        _report = read_validation_report(target, publication.report_type)
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
    if manifest != publication.manifest:
        return False
    if schema != publication.schema:
        return False
    return _assets_exist(target, publication.required_assets)


def _assets_exist(directory: Path, required_assets: tuple[ProcessedAssetName, ...]) -> bool:
    return all((directory / asset).is_file() for asset in required_assets)


def _assert_required_assets(directory: Path, required_assets: tuple[ProcessedAssetName, ...]) -> None:
    missing = tuple(asset for asset in required_assets if not (directory / asset).is_file())
    if missing:
        raise ArtifactIntegrityError(
            f"processed publication missing assets: {', '.join(asset.value for asset in missing)}",
            subject=ContractSubject.ARTIFACT_PATH,
        )


def _remove_stale_temporary_directories(target: Path) -> None:
    parent = target.parent
    if not parent.is_dir():
        return
    prefix = f".{target.name}."
    for candidate in sorted(parent.iterdir()):
        if candidate.is_dir() and candidate.name.startswith(prefix):
            rmtree(candidate, ignore_errors=True)

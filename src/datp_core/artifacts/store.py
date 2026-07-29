"""Atomic publication and reuse of processed-data coordinates."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

from filelock import FileLock

from datp_core.artifacts.completion import (
    assert_complete_digest,
    complete_digest,
    read_complete_marker,
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
from datp_core.domain.errors import ArtifactIntegrityError
from datp_core.preprocessing.models import PreprocessingManifest, PreprocessingValidationReport, TransformedSchema


@dataclass(frozen=True, slots=True)
class ProcessedPublication:
    coordinate_directory: Path
    manifest: PreprocessingManifest
    schema: TransformedSchema
    validation_report: PreprocessingValidationReport
    writer: Callable[[Path], None]
    required_assets: tuple[str, ...]
    overwrite: bool


@dataclass(frozen=True, slots=True)
class ProcessedPublicationResult:
    coordinate_directory: Path
    reused: bool
    manifest: PreprocessingManifest


def publish_processed(publication: ProcessedPublication) -> ProcessedPublicationResult:
    target = publication.coordinate_directory
    lock_path = f"{target}.lock"
    with FileLock(lock_path):
        _remove_stale_temporary_directories(target)
        if not publication.overwrite and _is_reusable(target, publication):
            return ProcessedPublicationResult(target, True, read_preprocessing_manifest(target))
        if target.exists():
            rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(mkdtemp(prefix=f".{target.name}.", dir=target.parent))
        try:
            publication.writer(temporary)
            write_preprocessing_manifest(temporary, publication.manifest)
            write_transformed_schema(temporary, publication.schema)
            write_validation_report(temporary, publication.validation_report)
            manifest_payload = (temporary / ProcessedAssetName.PREPROCESSING_MANIFEST).read_text(encoding="utf-8")
            schema_payload = (temporary / ProcessedAssetName.SCHEMA).read_text(encoding="utf-8")
            digest = complete_digest(manifest_payload, schema_payload)
            write_complete_marker(temporary, digest)
            _assert_required_assets(temporary, publication.required_assets)
            if not _is_reusable(temporary, publication):
                raise ArtifactIntegrityError(
                    "processed publication failed complete-asset validation",
                    subject=str(target),
                )
            temporary.replace(target)
        except Exception:
            rmtree(temporary, ignore_errors=True)
            raise
    return ProcessedPublicationResult(target, False, publication.manifest)


def _is_reusable(target: Path, publication: ProcessedPublication) -> bool:
    try:
        manifest = read_preprocessing_manifest(target)
        schema = read_transformed_schema(target)
        report = read_validation_report(target)
        digest = read_complete_marker(target)
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
    if digest != expected:
        return False
    if manifest != publication.manifest:
        return False
    if schema != publication.schema:
        return False
    if report != publication.validation_report:
        return False
    return _assets_exist(target, publication.required_assets)


def _assets_exist(directory: Path, required_assets: tuple[str, ...]) -> bool:
    return all((directory / asset).is_file() for asset in required_assets)


def _assert_required_assets(directory: Path, required_assets: tuple[str, ...]) -> None:
    missing = tuple(asset for asset in required_assets if not (directory / asset).is_file())
    if missing:
        raise ArtifactIntegrityError(
            f"processed publication missing assets: {', '.join(missing)}",
            subject=str(directory),
        )


def _remove_stale_temporary_directories(target: Path) -> None:
    parent = target.parent
    if not parent.is_dir():
        return
    prefix = f".{target.name}."
    for candidate in sorted(parent.iterdir()):
        if candidate.is_dir() and candidate.name.startswith(prefix):
            rmtree(candidate, ignore_errors=True)

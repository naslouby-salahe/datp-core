"""Persist validated population membership and split assignment artifacts."""

from enum import StrEnum
from pathlib import Path
from shutil import rmtree

from datp_core.artifacts.provenance import Checksum, checksum_file
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.artifacts.serializers.parquet import read_frame, write_frame
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ArtifactIntegrityError
from datp_core.data.populations.contracts import (
    ClientFamilyIdentity,
    PopulationManifest,
    PopulationManifestDocument,
    SplitManifest,
    SplitManifestDocument,
)


class PopulationAsset(StrEnum):
    MEMBERSHIP = "membership.parquet"
    MANIFEST = "population_manifest.json"
    FAMILY = "family_taxonomy.json"
    COMPLETE = "COMPLETE"


class SplitAsset(StrEnum):
    ASSIGNMENTS = "assignments.parquet"
    MANIFEST = "split_manifest.json"
    COMPLETE = "COMPLETE"


class PopulationPublication(StrictModel):
    directory: Path
    document: PopulationManifestDocument
    membership_checksum: Checksum
    family_by_client: tuple[ClientFamilyIdentity, ...]
    complete_digest: Checksum


class SplitPublication(StrictModel):
    directory: Path
    document: SplitManifestDocument
    complete_digest: Checksum


def publish_population(
    manifest: PopulationManifest,
    directory: Path,
    *,
    overwrite: bool,
) -> PopulationPublication:
    if directory.exists() and not overwrite:
        return load_population(directory)
    _prepare(directory)
    membership_checksum, _ = write_frame(manifest.membership, directory / PopulationAsset.MEMBERSHIP.value)
    (directory / PopulationAsset.MANIFEST.value).write_text(canonical_json_text(manifest.document), encoding="utf-8")
    (directory / PopulationAsset.FAMILY.value).write_text(
        canonical_json_text(manifest.family_by_client), encoding="utf-8"
    )
    digest = _completion_digest(
        directory,
        (PopulationAsset.MANIFEST.value, PopulationAsset.FAMILY.value, PopulationAsset.MEMBERSHIP.value),
    )
    (directory / PopulationAsset.COMPLETE.value).write_text(digest.value, encoding="utf-8")
    return PopulationPublication(
        directory=directory,
        document=manifest.document,
        membership_checksum=membership_checksum,
        family_by_client=manifest.family_by_client,
        complete_digest=digest,
    )


def load_population(directory: Path) -> PopulationPublication:
    _require_complete(directory, PopulationAsset.COMPLETE.value)
    document = PopulationManifestDocument.model_validate_json(
        (directory / PopulationAsset.MANIFEST.value).read_text(encoding="utf-8")
    )
    from pydantic import TypeAdapter

    family = TypeAdapter(tuple[ClientFamilyIdentity, ...]).validate_json(
        (directory / PopulationAsset.FAMILY.value).read_text(encoding="utf-8")
    )
    membership = read_frame(directory / PopulationAsset.MEMBERSHIP.value)
    if membership.height != document.total_membership_rows.value:
        raise ArtifactIntegrityError("population membership row count disagrees with its manifest")
    digest = _completion_digest(
        directory,
        (PopulationAsset.MANIFEST.value, PopulationAsset.FAMILY.value, PopulationAsset.MEMBERSHIP.value),
    )
    if (directory / PopulationAsset.COMPLETE.value).read_text(encoding="utf-8").strip() != digest.value:
        raise ArtifactIntegrityError("population completion digest mismatch")
    return PopulationPublication(
        directory=directory,
        document=document,
        membership_checksum=checksum_file(directory / PopulationAsset.MEMBERSHIP.value),
        family_by_client=family,
        complete_digest=digest,
    )


def reload_population(publication: PopulationPublication) -> PopulationManifest:
    membership = read_frame(
        publication.directory / PopulationAsset.MEMBERSHIP.value,
        expected_checksum=publication.membership_checksum,
        expected_row_count=publication.document.total_membership_rows,
    )
    return PopulationManifest(
        document=publication.document,
        membership=membership,
        family_by_client=publication.family_by_client,
    )


def publish_split(split: SplitManifest, directory: Path, *, overwrite: bool) -> SplitPublication:
    if directory.exists() and not overwrite:
        return load_split(directory)
    _prepare(directory)
    write_frame(split.assignments, directory / SplitAsset.ASSIGNMENTS.value)
    (directory / SplitAsset.MANIFEST.value).write_text(canonical_json_text(split.document), encoding="utf-8")
    digest = _completion_digest(directory, (SplitAsset.MANIFEST.value, SplitAsset.ASSIGNMENTS.value))
    (directory / SplitAsset.COMPLETE.value).write_text(digest.value, encoding="utf-8")
    return SplitPublication(directory=directory, document=split.document, complete_digest=digest)


def load_split(directory: Path) -> SplitPublication:
    _require_complete(directory, SplitAsset.COMPLETE.value)
    document = SplitManifestDocument.model_validate_json(
        (directory / SplitAsset.MANIFEST.value).read_text(encoding="utf-8")
    )
    assignments = read_frame(directory / SplitAsset.ASSIGNMENTS.value)
    if assignments.height != document.assignment_row_count.value:
        raise ArtifactIntegrityError("split assignment row count disagrees with its manifest")
    digest = _completion_digest(directory, (SplitAsset.MANIFEST.value, SplitAsset.ASSIGNMENTS.value))
    if (directory / SplitAsset.COMPLETE.value).read_text(encoding="utf-8").strip() != digest.value:
        raise ArtifactIntegrityError("split completion digest mismatch")
    return SplitPublication(directory=directory, document=document, complete_digest=digest)


def reload_split(publication: SplitPublication) -> SplitManifest:
    assignments = read_frame(
        publication.directory / SplitAsset.ASSIGNMENTS.value,
        expected_checksum=publication.document.assignment_checksum,
        expected_row_count=publication.document.assignment_row_count,
    )
    return SplitManifest(document=publication.document, assignments=assignments)


def _prepare(directory: Path) -> None:
    if directory.exists():
        rmtree(directory)
    directory.mkdir(parents=True, exist_ok=False)


def _require_complete(directory: Path, marker: str) -> None:
    if not (directory / marker).is_file():
        raise ArtifactIntegrityError(f"artifact publication is incomplete: {directory}")


def _completion_digest(directory: Path, names: tuple[str, ...]) -> Checksum:
    from datp_core.artifacts.provenance import canonical_checksum

    return canonical_checksum(tuple((name, checksum_file(directory / name)) for name in names))

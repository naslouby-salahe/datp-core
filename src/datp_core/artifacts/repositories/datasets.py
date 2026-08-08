"""Persist lossless canonical dataset frames independently of population construction."""

from enum import StrEnum
from pathlib import Path
from shutil import rmtree

import polars as pl

from datp_core.artifacts.provenance import Checksum, checksum_file
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.artifacts.serializers.parquet import read_frame, write_frame
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ArtifactIntegrityError
from datp_core.core.identifiers import DatasetId, FeatureNameSequence
from datp_core.core.numeric import RowCount


class DatasetAsset(StrEnum):
    DATA = "canonical.parquet"
    MANIFEST = "manifest.json"
    COMPLETE = "COMPLETE"


class CanonicalDatasetManifest(StrictModel):
    dataset: DatasetId
    feature_names: FeatureNameSequence
    data_checksum: Checksum
    row_count: RowCount
    schema_checksum: Checksum


class CanonicalDatasetPublication(StrictModel):
    directory: Path
    manifest: CanonicalDatasetManifest
    complete_digest: Checksum


def publish_canonical_dataset(
    *,
    dataset: DatasetId,
    feature_names: FeatureNameSequence,
    frame: pl.DataFrame,
    schema_checksum: Checksum,
    directory: Path,
    overwrite: bool,
) -> CanonicalDatasetPublication:
    if directory.exists() and not overwrite:
        return load_canonical_dataset(directory)
    if directory.exists():
        rmtree(directory)
    directory.mkdir(parents=True, exist_ok=False)
    data_checksum, row_count = write_frame(frame, directory / DatasetAsset.DATA.value)
    manifest = CanonicalDatasetManifest(
        dataset=dataset,
        feature_names=feature_names,
        data_checksum=data_checksum,
        row_count=row_count,
        schema_checksum=schema_checksum,
    )
    path = directory / DatasetAsset.MANIFEST.value
    path.write_text(canonical_json_text(manifest), encoding="utf-8")
    digest = checksum_file(path)
    (directory / DatasetAsset.COMPLETE.value).write_text(digest.value, encoding="utf-8")
    return CanonicalDatasetPublication(directory=directory, manifest=manifest, complete_digest=digest)


def load_canonical_dataset(directory: Path) -> CanonicalDatasetPublication:
    manifest_path = directory / DatasetAsset.MANIFEST.value
    complete_path = directory / DatasetAsset.COMPLETE.value
    if not manifest_path.is_file() or not complete_path.is_file():
        raise ArtifactIntegrityError(f"canonical dataset publication is incomplete: {directory}")
    manifest = CanonicalDatasetManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    digest = checksum_file(manifest_path)
    if complete_path.read_text(encoding="utf-8").strip() != digest.value:
        raise ArtifactIntegrityError(f"canonical dataset completion digest mismatch: {directory}")
    read_frame(
        directory / DatasetAsset.DATA.value,
        expected_checksum=manifest.data_checksum,
        expected_row_count=manifest.row_count,
    )
    return CanonicalDatasetPublication(directory=directory, manifest=manifest, complete_digest=digest)


def reload_canonical_frame(publication: CanonicalDatasetPublication) -> pl.DataFrame:
    return read_frame(
        publication.directory / DatasetAsset.DATA.value,
        expected_checksum=publication.manifest.data_checksum,
        expected_row_count=publication.manifest.row_count,
    )

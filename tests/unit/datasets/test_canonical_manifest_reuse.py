from pathlib import Path

import pytest

from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.errors import ArtifactIntegrityError
from datp_core.core.identifiers import (
    AvailabilityStatus,
    CanonicalAssetRoleToken,
    CanonicalizationContractName,
    CanonicalSourcePath,
    ColumnName,
    DatasetId,
)
from datp_core.core.numeric import RowCount, SourceFileCount, ValidationIssueCount
from datp_core.data.contracts import (
    CanonicalManifestDocument,
    ManifestAssetEntry,
    ManifestInventoryEntry,
    ManifestValidationReportEntry,
)
from datp_core.data.materialization import (
    DATASET_MANIFEST_FILENAME,
    canonical_dataset_is_materialized,
    load_canonical_manifest,
)


def _manifest(dataset: DatasetId) -> CanonicalManifestDocument:
    return CanonicalManifestDocument(
        assets=(
            ManifestAssetEntry(
                columns=(ColumnName("feature_0"),),
                path=CanonicalSourcePath("data/part-0.parquet"),
                row_count=RowCount(1),
                role=CanonicalAssetRoleToken("primary"),
            ),
        ),
        canonicalization_contract=CanonicalizationContractName("test_contract"),
        chronology=(),
        dataset=dataset,
        inventory=ManifestInventoryEntry(
            dataset=dataset,
            sources=(),
            accepted_source_count=SourceFileCount(0),
            excluded_source_count=SourceFileCount(0),
            excluded_sources=(),
        ),
        validation_report=ManifestValidationReportEntry(
            dataset=dataset,
            issues=(),
            exclusions=(),
            accepted_rows=RowCount(1),
            excluded_rows=RowCount(0),
            invalid_rows=RowCount(0),
            warning_count=ValidationIssueCount(0),
            status=AvailabilityStatus.AVAILABLE,
        ),
    )


def _write_manifest(root: Path, dataset: DatasetId) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / DATASET_MANIFEST_FILENAME).write_text(canonical_json_text(_manifest(dataset)), encoding="utf-8")


def test_load_canonical_manifest_reads_matching_dataset(tmp_path: Path) -> None:
    _write_manifest(tmp_path, DatasetId.NBAIOT)

    document = load_canonical_manifest(tmp_path, DatasetId.NBAIOT)

    assert document.dataset is DatasetId.NBAIOT
    assert canonical_dataset_is_materialized(tmp_path, DatasetId.NBAIOT)


def test_canonical_dataset_is_materialized_is_false_without_a_manifest(tmp_path: Path) -> None:
    assert not canonical_dataset_is_materialized(tmp_path, DatasetId.NBAIOT)
    with pytest.raises(ArtifactIntegrityError):
        load_canonical_manifest(tmp_path, DatasetId.NBAIOT)


def test_load_canonical_manifest_raises_on_corrupt_json(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / DATASET_MANIFEST_FILENAME).write_text("not valid json", encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError):
        load_canonical_manifest(tmp_path, DatasetId.NBAIOT)


def test_load_canonical_manifest_raises_on_dataset_identity_mismatch(tmp_path: Path) -> None:
    _write_manifest(tmp_path, DatasetId.NBAIOT)

    with pytest.raises(ArtifactIntegrityError):
        load_canonical_manifest(tmp_path, DatasetId.CICIOT2023)
    assert not canonical_dataset_is_materialized(tmp_path, DatasetId.CICIOT2023)

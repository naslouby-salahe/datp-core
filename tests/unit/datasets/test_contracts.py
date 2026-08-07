from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pyarrow as pa
import pytest

from datp_core.datasets.canonical_cache import canonical_directory
from datp_core.datasets.ciciot2023.schema import (
    CICIOT2023_MODEL_INPUT_ELIGIBILITY_POLICY,
    CICIoT2023EligibilityReason,
)
from datp_core.datasets.contracts import (
    CanonicalManifestDocument,
    ChronologyValidation,
    RawSourceFile,
    SourceFileRole,
    SourceStateEntryDocument,
    _ChronologyEntry,
)
from datp_core.datasets.materialization import canonical_schema_checksum
from datp_core.datasets.nbaiot.schema import NBAIOT_ARROW_SCHEMA, NBAIOT_CANONICAL_COLUMNS, NBAIOT_SCHEMA
from datp_core.domain.enums import AvailabilityStatus, DatasetId
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import (
    ByteCount,
    CanonicalColumnPosition,
    RowCount,
    SourceFileCount,
    SourceRowIndex,
    ValidationIssueCount,
)


def test_raw_source_is_immutable_and_relative() -> None:
    source = RawSourceFile(
        DatasetId.NBAIOT,
        Path("N-BaIoT/device/benign_traffic.csv"),
        ByteCount(1),
        Checksum("a"),
        SourceFileRole.BENIGN,
        RowCount(1),
    )
    with pytest.raises(FrozenInstanceError):
        source.__setattr__("relative_path", Path("other.csv"))
    with pytest.raises(ValueError):
        RawSourceFile(
            DatasetId.NBAIOT, Path("/absolute.csv"), ByteCount(1), Checksum("a"), SourceFileRole.BENIGN, RowCount(1)
        )


def test_chronology_preserves_static_and_temporal_status() -> None:
    result = ChronologyValidation(
        "Modbus",
        AvailabilityStatus.UNAVAILABLE,
        RowCount(1),
        RowCount(0),
        RowCount(1),
        RowCount(0),
        True,
        "address literal",
        False,
    )
    assert result.temporal_eligible is False
    assert result.total_rows.value == result.parseable_rows.value + result.invalid_rows.value


def test_chronology_rejects_raw_duplicate_timestamp_count() -> None:
    with pytest.raises(TypeError, match="typed row counts"):
        ChronologyValidation(
            "Modbus",
            AvailabilityStatus.UNAVAILABLE,
            RowCount(1),
            RowCount(0),
            RowCount(1),
            0,  # type: ignore[arg-type]
            True,
            "address literal",
            False,
        )


def test_manifest_chronology_rehydrates_typed_duplicate_count() -> None:
    entry = _ChronologyEntry.model_validate_json(
        """{
            "group_identity": "Modbus",
            "status": "available",
            "total_rows": 10,
            "parseable_rows": 10,
            "invalid_rows": 0,
            "duplicate_timestamp_count": 2,
            "is_monotonic": true,
            "reason": "verified chronology",
            "temporal_eligible": true
        }"""
    )
    assert entry.duplicate_timestamp_count == RowCount(2)


def test_manifest_rehydrates_all_semantic_counts_and_indices() -> None:
    manifest = CanonicalManifestDocument.model_validate_json(
        """{
            "assets": [{
                "checksum": "asset",
                "columns": ["feature"],
                "path": "data/canonical.parquet",
                "row_count": 10,
                "role": "canonical_data"
            }],
            "canonicalization_contract": "contract",
            "chronology": [{
                "group_identity": "Modbus",
                "status": "available",
                "total_rows": 10,
                "parseable_rows": 10,
                "invalid_rows": 0,
                "duplicate_timestamp_count": 1,
                "is_monotonic": true,
                "reason": "verified chronology",
                "temporal_eligible": true,
                "evidence_row_count": 10,
                "skipped_evidence_rows": 0,
                "trailing_evidence_rows": 0
            }],
            "dataset": "nbaiot",
            "inventory": {
                "dataset": "nbaiot",
                "sources": [{
                    "dataset": "nbaiot",
                    "relative_path": "N-BaIoT/device/benign.csv",
                    "size_bytes": 100,
                    "checksum": "source",
                    "role": "benign",
                    "observed_row_count": 10
                }],
                "accepted_source_count": 1,
                "excluded_source_count": 0,
                "excluded_sources": [],
                "accepted_row_count": 10,
                "checksum": "inventory"
            },
            "schema_checksum": "schema",
            "validation_report": {
                "dataset": "nbaiot",
                "issues": [{
                    "severity": "warning",
                    "code": "invalid_chronology",
                    "dataset": "nbaiot",
                    "source_context": "Modbus",
                    "reason": "diagnostic",
                    "affected_count": 1
                }],
                "exclusions": [{
                    "dataset": "nbaiot",
                    "source_path": "N-BaIoT/device/benign.csv",
                    "source_row": {
                        "source": {
                            "dataset": "nbaiot",
                            "relative_path": "N-BaIoT/device/benign.csv",
                            "size_bytes": 100,
                            "checksum": "source",
                            "role": "benign",
                            "observed_row_count": 10
                        },
                        "zero_based_row_index": 3
                    },
                    "reason": "invalid_value",
                    "evidence": "diagnostic",
                    "affected_count": 1
                }],
                "accepted_rows": 9,
                "excluded_rows": 1,
                "invalid_rows": 1,
                "warning_count": 1,
                "status": "available"
            }
        }"""
    )
    asset = manifest.assets[0]
    chronology = manifest.chronology[0]
    inventory = manifest.inventory
    report = manifest.validation_report
    assert asset.row_count == RowCount(10)
    assert chronology.total_rows == RowCount(10)
    assert chronology.evidence_row_count == RowCount(10)
    assert inventory.sources[0].size_bytes == ByteCount(100)
    assert inventory.sources[0].observed_row_count == RowCount(10)
    assert inventory.accepted_source_count == SourceFileCount(1)
    assert inventory.accepted_row_count == RowCount(10)
    assert report.issues[0].affected_count == RowCount(1)
    assert report.exclusions[0].source_row is not None
    assert report.exclusions[0].source_row.zero_based_row_index == SourceRowIndex(3)
    assert report.warning_count == ValidationIssueCount(1)
    assert '"row_count":10' in manifest.model_dump_json()


def test_source_state_rehydrates_typed_byte_count() -> None:
    entry = SourceStateEntryDocument.model_validate_json(
        '{"modified_time_nanoseconds":1,"path":"source.csv","size_bytes":100}'
    )
    assert entry.size_bytes == ByteCount(100)


def test_canonical_columns_reject_raw_positions() -> None:
    with pytest.raises(TypeError, match="typed position"):
        replace(NBAIOT_CANONICAL_COLUMNS[0], position=0)
    assert isinstance(NBAIOT_CANONICAL_COLUMNS[0].position, CanonicalColumnPosition)


def test_canonical_coordinate_is_a_stable_human_readable_dataset_root(tmp_path) -> None:
    changed_schema = replace(NBAIOT_SCHEMA, checksum=Checksum("different"))
    assert canonical_directory(tmp_path, NBAIOT_SCHEMA) == tmp_path / "nbaiot"
    assert canonical_directory(tmp_path, NBAIOT_SCHEMA) == canonical_directory(tmp_path, changed_schema)


def test_physical_schema_is_part_of_the_canonical_schema_checksum() -> None:
    changed_arrow_schema = NBAIOT_ARROW_SCHEMA.set(0, pa.field("MI_dir_L5_weight", pa.float32()))
    assert (
        canonical_schema_checksum(DatasetId.NBAIOT, NBAIOT_CANONICAL_COLUMNS, changed_arrow_schema)
        != NBAIOT_SCHEMA.checksum
    )


def test_model_input_eligibility_policy_is_immutable_and_enum_backed() -> None:
    policy = CICIOT2023_MODEL_INPUT_ELIGIBILITY_POLICY
    assert policy.exclusion_reasons == (
        CICIoT2023EligibilityReason.MISSING_OR_UNRECOGNIZED_LABEL,
        CICIoT2023EligibilityReason.NONFINITE_FEATURE,
    )
    with pytest.raises(FrozenInstanceError):
        policy.__setattr__("label_column", "other")

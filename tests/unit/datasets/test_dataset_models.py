from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pyarrow as pa
import pytest

from datp_core.datasets.canonical_cache import canonical_directory
from datp_core.datasets.ciciot2023.schema import (
    CICIOT2023_MODEL_INPUT_ELIGIBILITY_POLICY,
    CICIoT2023EligibilityReason,
)
from datp_core.datasets.materialization import canonical_schema_checksum
from datp_core.datasets.models import ChronologyValidation, RawSourceFile, SourceFileRole
from datp_core.datasets.nbaiot.schema import NBAIOT_ARROW_SCHEMA, NBAIOT_CANONICAL_COLUMNS, NBAIOT_SCHEMA
from datp_core.domain.enums import AvailabilityStatus, DatasetId
from datp_core.domain.values import ByteCount, Checksum, RowCount


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
        0,
        True,
        "address literal",
        False,
    )
    assert result.temporal_eligible is False
    assert result.total_rows.value == result.parseable_rows.value + result.invalid_rows.value


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

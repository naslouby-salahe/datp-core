from pathlib import Path

import polars as pl
import pytest

from datp_core.core.identifiers import (
    DatasetId,
    FeatureName,
    FeatureNameSequence,
    PopulationId,
    SplitProtocolId,
    StableRowId,
)
from datp_core.data.populations.contracts import (
    CLIENT_ID_COLUMN,
    OUTCOME_LABEL_COLUMN,
    PARTITION_ROLE_COLUMN,
    STABLE_ROW_ID_COLUMN,
)
from datp_core.data.preprocessing.ciciot_file_clients import _client_group_key
from datp_core.data.preprocessing.client_partitions import (
    client_partitions,
    exclude_nonfinite_model_input_rows,
    write_model_input_exclusion_evidence,
)


def _feature_names(*names: str) -> FeatureNameSequence:
    return FeatureNameSequence(tuple(FeatureName(name) for name in names))


def test_client_partitions_emit_bare_manifest_client_tokens() -> None:
    rows = pl.DataFrame(
        {
            CLIENT_ID_COLUMN: [
                "danmini_doorbell",
                "danmini_doorbell",
                "danmini_doorbell",
                "ecobee_thermostat",
                "ecobee_thermostat",
                "ecobee_thermostat",
            ],
            STABLE_ROW_ID_COLUMN: ["a", "b", "c", "d", "e", "f"],
            PARTITION_ROLE_COLUMN: ["train", "calibration", "evaluation", "train", "calibration", "evaluation"],
            OUTCOME_LABEL_COLUMN: ["benign", "benign", "benign", "benign", "benign", "benign"],
            "feature_one": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        }
    )

    partitions = client_partitions(
        rows,
        _feature_names("feature_one"),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
    )

    assert tuple(item.client.value for item in partitions.items) == (
        "danmini_doorbell",
        "ecobee_thermostat",
    )


def test_excludes_row_with_null_numeric_model_input_feature() -> None:
    joined = pl.DataFrame(
        {
            "stable_row_id": ["a", "b", "c"],
            "feature_one": [1.0, None, 3.0],
            "feature_two": [4.0, 5.0, 6.0],
        }
    )

    result = exclude_nonfinite_model_input_rows(
        joined,
        _feature_names("feature_one", "feature_two"),
        dataset=DatasetId.EDGE_IIOTSET,
        population=PopulationId.EDGE_SENSOR_CLIENTS,
    )

    assert result.eligible_rows.get_column("stable_row_id").to_list() == ["a", "c"]
    assert result.exclusion_evidence.excluded_stable_row_ids == (StableRowId("b"),)
    assert result.exclusion_evidence.excluded_row_count.value == 1


def test_excludes_row_with_non_finite_numeric_model_input_feature() -> None:
    joined = pl.DataFrame(
        {
            "stable_row_id": ["a", "b"],
            "feature_one": [1.0, float("inf")],
        }
    )

    result = exclude_nonfinite_model_input_rows(
        joined,
        _feature_names("feature_one"),
        dataset=DatasetId.EDGE_IIOTSET,
        population=PopulationId.EDGE_SENSOR_CLIENTS,
    )

    assert result.eligible_rows.get_column("stable_row_id").to_list() == ["a"]
    assert result.exclusion_evidence.excluded_stable_row_ids == (StableRowId("b"),)


def test_never_fills_or_fabricates_a_replacement_value() -> None:
    joined = pl.DataFrame(
        {
            "stable_row_id": ["a", "b"],
            "feature_one": [1.0, None],
        }
    )

    result = exclude_nonfinite_model_input_rows(
        joined,
        _feature_names("feature_one"),
        dataset=DatasetId.EDGE_IIOTSET,
        population=PopulationId.EDGE_SENSOR_CLIENTS,
    )

    assert result.eligible_rows.get_column("feature_one").null_count() == 0
    assert result.eligible_rows.height == 1


def test_all_rows_retained_when_every_feature_is_finite() -> None:
    joined = pl.DataFrame(
        {
            "stable_row_id": ["a", "b"],
            "feature_one": [1.0, 2.0],
        }
    )

    result = exclude_nonfinite_model_input_rows(
        joined,
        _feature_names("feature_one"),
        dataset=DatasetId.EDGE_IIOTSET,
        population=PopulationId.EDGE_SENSOR_CLIENTS,
    )

    assert result.eligible_rows.height == joined.height
    assert result.exclusion_evidence.excluded_row_count.value == 0


def test_exclusion_evidence_is_persisted_with_stable_row_identities(tmp_path: Path) -> None:
    joined = pl.DataFrame(
        {
            "stable_row_id": ["row_a", "row_b"],
            "feature_one": [1.0, None],
        }
    )
    result = exclude_nonfinite_model_input_rows(
        joined,
        _feature_names("feature_one"),
        dataset=DatasetId.EDGE_IIOTSET,
        population=PopulationId.EDGE_SENSOR_CLIENTS,
    )
    destination = tmp_path / "model_input_exclusions.json"
    write_model_input_exclusion_evidence(destination, result.exclusion_evidence)
    payload = destination.read_text(encoding="utf-8")
    assert "row_b" in payload
    assert "nonfinite_or_null_numeric_model_input_feature" in payload
def test_ciciot_client_group_key_normalizes_polars_single_column_keys() -> None:
    assert _client_group_key(("Merged01",)) == "Merged01"
    assert _client_group_key("Merged01") == "Merged01"


def test_ciciot_client_group_key_rejects_multiple_group_columns() -> None:
    with pytest.raises(ValueError, match="exactly one key"):
        _client_group_key(("Merged01", "unexpected"))

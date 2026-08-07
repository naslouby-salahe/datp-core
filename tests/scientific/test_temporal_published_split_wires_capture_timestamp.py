"""Published temporal splits must receive genuine capture timestamps (SF-01)."""

from datetime import UTC, datetime

import polars as pl
import pytest

from datp_core.datasets.edge_iiotset.schema import EdgeCanonicalColumn
from datp_core.datasets.partitioning.contracts import (
    CLIENT_ID_COLUMN,
    OUTCOME_LABEL_COLUMN,
    SOURCE_ROW_INDEX_COLUMN,
    STABLE_ROW_ID_COLUMN,
    PopulationOutcomeLabel,
    SplitConstructionRequest,
    membership_column_names,
)
from datp_core.datasets.partitioning.splits import split_membership
from datp_core.domain.enums import DatasetId, PopulationId, SplitProtocolId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.identifiers import CaptureTimestampColumn
from datp_core.pipeline.preparation.populations import _capture_timestamp_column_for_split


def _temporal_membership(rows_per_client: int = 40) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    base = datetime(2020, 1, 1, tzinfo=UTC)
    for client_index, client_id in enumerate(("sensor_a", "sensor_b")):
        for row_index in range(rows_per_client):
            rows.append(
                {
                    CLIENT_ID_COLUMN: client_id,
                    STABLE_ROW_ID_COLUMN: f"{client_id}:{row_index}",
                    SOURCE_ROW_INDEX_COLUMN: row_index,
                    OUTCOME_LABEL_COLUMN: PopulationOutcomeLabel.BENIGN.value,
                    "source_path": f"{client_id}.csv",
                    EdgeCanonicalColumn.CAPTURE_TIMESTAMP.value: base.replace(
                        day=1 + (client_index * rows_per_client + row_index) % 28
                    ),
                }
            )
    frame = pl.DataFrame(rows).sort(CLIENT_ID_COLUMN, EdgeCanonicalColumn.CAPTURE_TIMESTAMP.value)
    # Ensure required membership columns are present even when extras (timestamp) are carried.
    required = membership_column_names()
    for column in required:
        if column not in frame.columns:
            raise AssertionError(f"test fixture missing membership column {column}")
    return frame


def test_capture_timestamp_helper_requires_column_for_temporal_protocol() -> None:
    membership = _temporal_membership().drop(EdgeCanonicalColumn.CAPTURE_TIMESTAMP.value)
    with pytest.raises(ScientificContractError, match="capture-timestamp"):
        _capture_timestamp_column_for_split(SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE, membership)


def test_capture_timestamp_helper_is_none_for_non_temporal_protocol() -> None:
    membership = _temporal_membership()
    assert _capture_timestamp_column_for_split(SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS, membership) is None


def test_published_temporal_resolution_enables_chronological_split() -> None:
    membership = _temporal_membership()
    column = _capture_timestamp_column_for_split(SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE, membership)
    assert column == CaptureTimestampColumn(EdgeCanonicalColumn.CAPTURE_TIMESTAMP.value)
    assignments, manifest = split_membership(
        SplitConstructionRequest(
            membership=membership,
            population=PopulationId.EDGE_TEMPORAL_GROUPS,
            dataset=DatasetId.EDGE_IIOTSET,
            partition_seed=Seed(0),
            split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
            population_manifest_checksum=Checksum("a" * 64),
            capture_timestamp_column=column,
        )
    )
    assert manifest.split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
    assert assignments.height == membership.height

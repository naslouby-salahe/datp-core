"""Federated checkpoint artifact identities and exact Parquet schemas."""

from dataclasses import dataclass
from enum import StrEnum

import polars as pl


class FederatedHistoryAssetName(StrEnum):
    ROUND_SUMMARY = "round_summary.parquet"
    CLIENT_ROUNDS = "client_rounds.parquet"
    PERSONALIZED_ROUNDS = "personalized_rounds.parquet"
    DEVICE_NAME = "device_name.txt"
    CANDIDATE_MANIFEST = "candidate_manifest.json"
    COMPLETE = "COMPLETE"


class FederatedHistoryColumn(StrEnum):
    ROUND_NUMBER = "round_number"
    AGGREGATE_LOSS = "aggregate_loss"
    UPLOAD_BYTES = "upload_bytes"
    DOWNLOAD_BYTES = "download_bytes"
    GLOBAL_STATE_CHECKSUM = "global_state_checksum"
    CLIENT_ID = "client_id"
    SAMPLE_COUNT = "sample_count"
    LOCAL_LOSS = "local_loss"
    STATE_CHECKSUM = "state_checksum"


class CandidateManifestKind(StrEnum):
    GLOBAL = "global"
    PERSONALIZED = "personalized"


@dataclass(frozen=True, slots=True, kw_only=True)
class ParquetColumnSpec:
    identity: FederatedHistoryColumn
    dtype: type[pl.DataType]


ROUND_SUMMARY_SCHEMA = (
    ParquetColumnSpec(identity=FederatedHistoryColumn.ROUND_NUMBER, dtype=pl.Int64),
    ParquetColumnSpec(identity=FederatedHistoryColumn.AGGREGATE_LOSS, dtype=pl.Float64),
    ParquetColumnSpec(identity=FederatedHistoryColumn.UPLOAD_BYTES, dtype=pl.Int64),
    ParquetColumnSpec(identity=FederatedHistoryColumn.DOWNLOAD_BYTES, dtype=pl.Int64),
    ParquetColumnSpec(identity=FederatedHistoryColumn.GLOBAL_STATE_CHECKSUM, dtype=pl.String),
)
CLIENT_ROUNDS_SCHEMA = (
    ParquetColumnSpec(identity=FederatedHistoryColumn.ROUND_NUMBER, dtype=pl.Int64),
    ParquetColumnSpec(identity=FederatedHistoryColumn.CLIENT_ID, dtype=pl.String),
    ParquetColumnSpec(identity=FederatedHistoryColumn.SAMPLE_COUNT, dtype=pl.Int64),
    ParquetColumnSpec(identity=FederatedHistoryColumn.LOCAL_LOSS, dtype=pl.Float64),
)
PERSONALIZED_ROUNDS_SCHEMA = (
    ParquetColumnSpec(identity=FederatedHistoryColumn.ROUND_NUMBER, dtype=pl.Int64),
    ParquetColumnSpec(identity=FederatedHistoryColumn.CLIENT_ID, dtype=pl.String),
    ParquetColumnSpec(identity=FederatedHistoryColumn.LOCAL_LOSS, dtype=pl.Float64),
    ParquetColumnSpec(identity=FederatedHistoryColumn.STATE_CHECKSUM, dtype=pl.String),
)

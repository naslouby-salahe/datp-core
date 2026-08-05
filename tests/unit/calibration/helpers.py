"""Shared miniature fixtures for calibration unit tests."""

from pathlib import Path

import polars as pl
from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.domain.enums import PartitionRole, ScoreFrameColumn, SerializationFormat
from datp_core.domain.values import Checksum, FeatureCount, RoundNumber, RowCount, Seed, checksum_file
from datp_core.populations.models import ClientIdentity, PopulationOutcomeLabel
from datp_core.protocols.inference import ScoreRecord


def write_score_parquet(
    path: Path,
    *,
    stable_row_ids: tuple[str, ...],
    labels: tuple[str, ...],
    scores: tuple[float, ...],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        {
            ScoreFrameColumn.STABLE_ROW_ID.value: list(stable_row_ids),
            ScoreFrameColumn.OUTCOME_LABEL.value: list(labels),
            ScoreFrameColumn.RECONSTRUCTION_ERROR.value: list(scores),
        }
    ).write_parquet(path)


def benign_score_record(
    tmp_path: Path,
    client_id: str,
    scores: tuple[float, ...],
    *,
    seed: Seed | None = None,
    partition_role: PartitionRole = PartitionRole.CALIBRATION,
    row_id_prefix: str | None = None,
) -> ScoreRecord:
    prefix = row_id_prefix if row_id_prefix is not None else f"{client_id}-{partition_role.value}"
    stable_row_ids = tuple(f"{prefix}-{index}" for index in range(len(scores)))
    labels = tuple(PopulationOutcomeLabel.BENIGN.value for _ in scores)
    path = tmp_path / client_id / f"{partition_role.value}.parquet"
    write_score_parquet(path, stable_row_ids=stable_row_ids, labels=labels, scores=scores)
    return ScoreRecord(
        coordinate=fedavg_coordinate(seed if seed is not None else Seed(0)),
        scored_client=client_identity(client_id),
        partition_role=partition_role,
        checkpoint_round=RoundNumber(2),
        checkpoint_checksum=Checksum("a" * 64),
        path=path,
        checksum=checksum_file(path),
        row_count=RowCount(len(scores)),
        feature_count=FeatureCount(4),
        serialization_format=SerializationFormat.PARQUET,
    )


def attack_score_record(tmp_path: Path, client_id: str, scores: tuple[float, ...]) -> ScoreRecord:
    stable_row_ids = tuple(f"{client_id}-attack-{index}" for index in range(len(scores)))
    labels = tuple(PopulationOutcomeLabel.ATTACK.value for _ in scores)
    path = tmp_path / client_id / "calibration_with_attack.parquet"
    write_score_parquet(path, stable_row_ids=stable_row_ids, labels=labels, scores=scores)
    return ScoreRecord(
        coordinate=fedavg_coordinate(Seed(0)),
        scored_client=client_identity(client_id),
        partition_role=PartitionRole.CALIBRATION,
        checkpoint_round=RoundNumber(2),
        checkpoint_checksum=Checksum("a" * 64),
        path=path,
        checksum=checksum_file(path),
        row_count=RowCount(len(scores)),
        feature_count=FeatureCount(4),
        serialization_format=SerializationFormat.PARQUET,
    )


def some_client(client_id: str = "client_a") -> ClientIdentity:
    return client_identity(client_id)

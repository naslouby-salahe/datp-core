"""Shared Polars contracts for centralized and federated score generation."""

from pathlib import Path

import numpy as np
import numpy.typing as npt
import polars as pl

from datp_core.domain.enums import ContractSubject, PartitionRole, ScoreFrameColumn
from datp_core.domain.errors import ArtifactIntegrityError, LeakageError, ScientificContractError
from datp_core.domain.values import Checksum, FeatureNameSequence, RowCount, checksum_file
from datp_core.learning.autoencoder import LEARNING_DTYPE
from datp_core.populations.models import OUTCOME_LABEL_COLUMN, STABLE_ROW_ID_COLUMN, PopulationOutcomeLabel

SCORE_FRAME_COLUMNS = (
    ScoreFrameColumn.STABLE_ROW_ID.value,
    ScoreFrameColumn.OUTCOME_LABEL.value,
    ScoreFrameColumn.RECONSTRUCTION_ERROR.value,
)
SCORE_FRAME_DTYPES = (pl.Utf8, pl.Utf8, pl.Float64)
CALIBRATION_PARTITIONS = frozenset(
    {
        PartitionRole.CALIBRATION,
        PartitionRole.FUTURE_RECALIBRATION,
    }
)


def validate_score_input_frame(
    frame: pl.DataFrame,
    partition_role: PartitionRole,
    feature_names: FeatureNameSequence,
) -> None:
    """Validate the shared input contract without materializing whole columns in Python."""
    if frame.height == 0 and partition_role in CALIBRATION_PARTITIONS:
        raise ScientificContractError(
            f"{partition_role.value} partition must not be empty",
            subject=ContractSubject.ROWS,
        )
    _require_columns(frame, partition_role, feature_names)
    _require_identity_columns(frame, partition_role)
    _require_feature_columns(frame, partition_role, feature_names)
    if partition_role in CALIBRATION_PARTITIONS:
        _require_benign_calibration(frame)


def extract_score_arrays(
    frame: pl.DataFrame,
    feature_names: FeatureNameSequence,
) -> tuple[npt.NDArray[np.float32], tuple[str, ...], tuple[str, ...]]:
    matrix = frame.select(feature_names.as_list()).to_numpy().astype(LEARNING_DTYPE, copy=False)
    labels = tuple(str(value) for value in frame.get_column(OUTCOME_LABEL_COLUMN).to_list())
    row_ids = tuple(str(value) for value in frame.get_column(STABLE_ROW_ID_COLUMN).to_list())
    return matrix, labels, row_ids


def score_frame(
    row_ids: tuple[str, ...],
    labels: tuple[str, ...],
    scores: npt.NDArray[np.float64],
) -> pl.DataFrame:
    if len(row_ids) != len(labels) or len(row_ids) != scores.shape[0]:
        raise ScientificContractError(
            "score output columns must preserve one-to-one row alignment",
            subject=ContractSubject.SCORES,
        )
    return pl.DataFrame(
        (
            pl.Series(SCORE_FRAME_COLUMNS[0], row_ids, dtype=pl.Utf8),
            pl.Series(SCORE_FRAME_COLUMNS[1], labels, dtype=pl.Utf8),
            pl.Series(SCORE_FRAME_COLUMNS[2], scores.tolist(), dtype=pl.Float64),
        )
    )


def validate_persisted_score_frame(
    path: Path,
    checksum: Checksum,
    row_count: RowCount,
) -> pl.DataFrame:
    if not path.is_file():
        raise ArtifactIntegrityError("score artifact is missing", subject=ContractSubject.ARTIFACT_PATH)
    if checksum_file(path) != checksum:
        raise ArtifactIntegrityError("score checksum changed after write", subject=ContractSubject.ARTIFACT_PATH)
    frame = pl.read_parquet(path)
    if frame.height != row_count.value:
        raise ArtifactIntegrityError("score artifact row count mismatch", subject=ContractSubject.ARTIFACT_PATH)
    if tuple(frame.columns) != SCORE_FRAME_COLUMNS:
        raise ArtifactIntegrityError("score artifact schema mismatch", subject=ContractSubject.SCHEMA)
    observed_dtypes = tuple(frame.schema[column] for column in SCORE_FRAME_COLUMNS)
    if observed_dtypes != SCORE_FRAME_DTYPES:
        raise ArtifactIntegrityError("score artifact column dtype mismatch", subject=ContractSubject.SCHEMA)
    return frame


def _require_columns(
    frame: pl.DataFrame,
    partition_role: PartitionRole,
    feature_names: FeatureNameSequence,
) -> None:
    required = (STABLE_ROW_ID_COLUMN, OUTCOME_LABEL_COLUMN, *feature_names)
    missing = tuple(name for name in required if name not in frame.columns)
    if missing:
        raise ScientificContractError(
            f"{partition_role.value} frame missing declared columns: {', '.join(missing)}",
            subject=ContractSubject.SCHEMA,
        )


def _require_identity_columns(frame: pl.DataFrame, partition_role: PartitionRole) -> None:
    row_ids = frame.get_column(STABLE_ROW_ID_COLUMN)
    if row_ids.null_count() > 0:
        raise ScientificContractError(
            f"stable row IDs must not be null in {partition_role.value} partition",
            subject=ContractSubject.ROWS,
        )
    if row_ids.n_unique() != frame.height:
        raise ScientificContractError(
            f"stable row IDs must be unique within {partition_role.value} partition",
            subject=ContractSubject.ROWS,
        )
    if frame.get_column(OUTCOME_LABEL_COLUMN).null_count() > 0:
        raise ScientificContractError(
            f"outcome labels must not be null in {partition_role.value} partition",
            subject=ContractSubject.LABEL,
        )


def _require_feature_columns(
    frame: pl.DataFrame,
    partition_role: PartitionRole,
    feature_names: FeatureNameSequence,
) -> None:
    for name in feature_names:
        dtype = frame.schema[name]
        if not dtype.is_numeric():
            raise ScientificContractError(
                f"feature column '{name}' in {partition_role.value} partition must be numeric, got {dtype}",
                subject=ContractSubject.FEATURES,
            )
        has_non_finite = frame.select(
            (pl.col(name).is_not_null() & ~pl.col(name).is_finite()).any()
        ).item()
        if has_non_finite:
            raise ScientificContractError(
                f"feature column '{name}' in {partition_role.value} partition contains non-finite values",
                subject=ContractSubject.FEATURES,
            )


def _require_benign_calibration(frame: pl.DataFrame) -> None:
    attack_rows = frame.filter(pl.col(OUTCOME_LABEL_COLUMN) != PopulationOutcomeLabel.BENIGN.value).height
    if attack_rows:
        raise LeakageError(
            "attack-labelled rows cannot enter benign calibration construction",
            subject=ContractSubject.CALIBRATION,
        )

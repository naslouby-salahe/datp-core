from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
import polars as pl
import pyarrow.parquet as pq
import torch

from datp_core.core.errors import (
    ArtifactIntegrityError,
    ErrorMessage,
    LeakageError,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    ContractSubject,
    FeatureNameSequence,
    OutcomeLabel,
    OutcomeLabelSequence,
    PartitionRole,
    ScoreFrameColumn,
    StableRowId,
    StableRowIdSequence,
)
from datp_core.core.numeric import BatchSize, FeatureCount, RowCount
from datp_core.data.populations.contracts import (
    OUTCOME_LABEL_COLUMN,
    STABLE_ROW_ID_COLUMN,
    PopulationOutcomeLabel,
)
from datp_core.detector.autoencoder import (
    AutoencoderModelState,
    ReconstructionAutoencoder,
    reconstruction_errors,
)
from datp_core.detector.scoring.models import PersistedScoreFrame
from datp_core.detector.training.contracts import AutoencoderProtocol

SCORE_FRAME_COLUMNS = (
    ScoreFrameColumn.STABLE_ROW_ID.value,
    ScoreFrameColumn.OUTCOME_LABEL.value,
    ScoreFrameColumn.ATTACK_FAMILY.value,
    ScoreFrameColumn.RECONSTRUCTION_ERROR.value,
)
SCORE_FRAME_DTYPES = (pl.Utf8, pl.Utf8, pl.Utf8, pl.Float64)
CALIBRATION_PARTITIONS = frozenset(
    {
        PartitionRole.CALIBRATION,
        PartitionRole.FUTURE_RECALIBRATION,
    }
)


@dataclass(frozen=True, slots=True)
class ScoreArrays:
    feature_matrix: npt.NDArray[np.float32]
    row_ids: StableRowIdSequence
    labels: OutcomeLabelSequence


def validate_score_input_frame(
    frame: pl.DataFrame,
    partition_role: PartitionRole,
    feature_names: FeatureNameSequence,
) -> None:

    if frame.height == 0 and partition_role in CALIBRATION_PARTITIONS:
        raise ScientificContractError(
            ErrorMessage(f"{partition_role.value} partition must not be empty"),
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
) -> ScoreArrays:
    matrix = frame.select([pl.col(name).cast(pl.Float32) for name in feature_names.as_list()]).to_numpy(writable=True)
    labels = OutcomeLabelSequence(
        tuple(OutcomeLabel(str(value)) for value in frame.get_column(OUTCOME_LABEL_COLUMN).to_list())
    )
    row_ids = StableRowIdSequence(
        tuple(StableRowId(str(value)) for value in frame.get_column(STABLE_ROW_ID_COLUMN).to_list())
    )
    return ScoreArrays(feature_matrix=matrix, row_ids=row_ids, labels=labels)


def score_frame(
    row_ids: StableRowIdSequence,
    labels: OutcomeLabelSequence,
    attack_families: tuple[str | None, ...],
    scores: npt.NDArray[np.float64],
) -> pl.DataFrame:
    if len(row_ids) != len(labels) or len(labels) != len(attack_families) or len(row_ids) != scores.shape[0]:
        raise ScientificContractError(
            ErrorMessage("score output columns must preserve one-to-one row alignment"),
            subject=ContractSubject.SCORES,
        )
    return pl.DataFrame(
        (
            pl.Series(SCORE_FRAME_COLUMNS[0], tuple(str(rid) for rid in row_ids.row_ids), dtype=pl.Utf8),
            pl.Series(SCORE_FRAME_COLUMNS[1], tuple(str(lbl) for lbl in labels.labels), dtype=pl.Utf8),
            pl.Series(
                SCORE_FRAME_COLUMNS[2],
                attack_families,
                dtype=pl.Utf8,
            ),
            pl.Series(
                SCORE_FRAME_COLUMNS[3],
                scores.tolist(),
                dtype=pl.Float64,
            ),
        )
    )


def validate_persisted_score_frame(
    path: Path,
    row_count: RowCount,
    partition_role: PartitionRole,
) -> pl.DataFrame:
    if path.is_symlink() or not path.is_file():
        raise ArtifactIntegrityError(
            ErrorMessage("score artifact is missing"),
            subject=ContractSubject.ARTIFACT_PATH,
        )
    frame = pl.read_parquet(path)
    if frame.height != row_count.value:
        raise ArtifactIntegrityError(
            ErrorMessage("score artifact row count mismatch"),
            subject=ContractSubject.ARTIFACT_PATH,
        )
    if tuple(frame.columns) != SCORE_FRAME_COLUMNS:
        raise ArtifactIntegrityError(
            ErrorMessage("score artifact schema mismatch"),
            subject=ContractSubject.SCHEMA,
        )
    observed_dtypes = tuple(frame.schema[column] for column in SCORE_FRAME_COLUMNS)
    if observed_dtypes != SCORE_FRAME_DTYPES:
        raise ArtifactIntegrityError(
            ErrorMessage("score artifact column dtype mismatch"),
            subject=ContractSubject.SCHEMA,
        )
    _require_identity_columns(frame, partition_role)
    labels = tuple(OutcomeLabel(str(value)) for value in frame.get_column(OUTCOME_LABEL_COLUMN).to_list())
    if any(not str(value) for value in labels):
        raise ArtifactIntegrityError(
            ErrorMessage("score artifact contains an empty outcome label"), subject=ContractSubject.LABEL
        )
    scores = frame.get_column(ScoreFrameColumn.RECONSTRUCTION_ERROR.value).to_numpy()
    if not np.isfinite(scores).all():
        raise ArtifactIntegrityError(
            ErrorMessage("score artifact contains non-finite reconstruction errors"), subject=ContractSubject.SCORES
        )
    if partition_role in CALIBRATION_PARTITIONS:
        _require_benign_calibration(frame)
    return frame


def score_and_persist_autoencoder_frame(
    *,
    frame: pl.DataFrame,
    partition_role: PartitionRole,
    feature_names: FeatureNameSequence,
    model: ReconstructionAutoencoder,
    batch_size: BatchSize,
    device: torch.device,
    destination: Path,
) -> PersistedScoreFrame:
    validate_score_input_frame(frame, partition_role, feature_names)
    arrays = extract_score_arrays(frame, feature_names)
    scores = reconstruction_errors(model, arrays.feature_matrix, batch_size=batch_size, device=device)
    if scores.shape[0] != arrays.feature_matrix.shape[0]:
        raise ScientificContractError(
            ErrorMessage("score count must equal partition row count"),
            subject=partition_role,
        )
    if not np.isfinite(scores).all():
        raise ScientificContractError(
            ErrorMessage(f"generated scores must be finite in {partition_role.value} partition"),
            subject=ContractSubject.SCORES,
        )
    attack_families = (
        tuple(
            str(value) if value is not None else None
            for value in frame.get_column(ScoreFrameColumn.ATTACK_FAMILY.value)
        )
        if ScoreFrameColumn.ATTACK_FAMILY.value in frame.columns
        else (None,) * frame.height
    )
    output = score_frame(arrays.row_ids, arrays.labels, attack_families, scores)
    destination.parent.mkdir(parents=True, exist_ok=True)
    output.write_parquet(destination)
    written_row_count = pq.ParquetFile(destination).metadata.num_rows
    if written_row_count != output.height:
        raise ArtifactIntegrityError(
            ErrorMessage("score artifact row count mismatch after publication"),
            subject=ContractSubject.ARTIFACT_PATH,
        )
    return PersistedScoreFrame(
        path=destination,
        row_count=RowCount(output.height),
        feature_count=FeatureCount(len(feature_names)),
    )


def model_from_terminal_state(
    model_state: AutoencoderModelState,
    autoencoder: AutoencoderProtocol,
    device: torch.device,
) -> ReconstructionAutoencoder:
    if device.type != "cuda":
        raise ScientificContractError(
            ErrorMessage("scoring requires a CUDA device"),
            subject=ContractSubject.CUDA,
        )
    model = ReconstructionAutoencoder(autoencoder.widths).to(device)
    model_state.apply_to(model)
    model.eval()
    return model


def _require_columns(
    frame: pl.DataFrame,
    partition_role: PartitionRole,
    feature_names: FeatureNameSequence,
) -> None:
    required = (STABLE_ROW_ID_COLUMN, OUTCOME_LABEL_COLUMN, *feature_names)
    missing = tuple(name for name in required if name not in frame.columns)
    if missing:
        raise ScientificContractError(
            ErrorMessage(f"{partition_role.value} frame missing declared columns: {', '.join(missing)}"),
            subject=ContractSubject.SCHEMA,
        )


def _require_identity_columns(
    frame: pl.DataFrame,
    partition_role: PartitionRole,
) -> None:
    row_ids = frame.get_column(STABLE_ROW_ID_COLUMN)
    if row_ids.null_count() > 0:
        raise ScientificContractError(
            ErrorMessage(f"stable row IDs must not be null in {partition_role.value} partition"),
            subject=ContractSubject.ROWS,
        )
    if row_ids.n_unique() != frame.height:
        raise ScientificContractError(
            ErrorMessage(f"stable row IDs must be unique within {partition_role.value} partition"),
            subject=ContractSubject.ROWS,
        )
    if frame.get_column(OUTCOME_LABEL_COLUMN).null_count() > 0:
        raise ScientificContractError(
            ErrorMessage(f"outcome labels must not be null in {partition_role.value} partition"),
            subject=ContractSubject.LABEL,
        )


def _require_feature_columns(
    frame: pl.DataFrame,
    partition_role: PartitionRole,
    feature_names: FeatureNameSequence,
) -> None:
    for name in feature_names:
        column = frame.get_column(name)
        dtype = column.dtype
        if not dtype.is_numeric():
            raise ScientificContractError(
                ErrorMessage(
                    f"feature column '{name}' in {partition_role.value} partition must be numeric, got {dtype}"
                ),
                subject=ContractSubject.FEATURES,
            )
        if column.null_count() > 0:
            raise ScientificContractError(
                ErrorMessage(f"feature column '{name}' in {partition_role.value} partition contains null values"),
                subject=ContractSubject.FEATURES,
            )
        has_non_finite = frame.select((~pl.col(name).is_finite()).any()).item()
        if has_non_finite:
            raise ScientificContractError(
                ErrorMessage(f"feature column '{name}' in {partition_role.value} partition contains non-finite values"),
                subject=ContractSubject.FEATURES,
            )


def _require_benign_calibration(frame: pl.DataFrame) -> None:
    attack_rows = frame.filter(pl.col(OUTCOME_LABEL_COLUMN) != PopulationOutcomeLabel.BENIGN.value).height
    if attack_rows:
        raise LeakageError(
            ErrorMessage("attack-labelled rows cannot enter benign calibration construction"),
            subject=ContractSubject.CALIBRATION,
        )

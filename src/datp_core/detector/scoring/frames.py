"""Score-frame schema validation, construction, and persisted-frame integrity."""

from pathlib import Path

import numpy as np
import numpy.typing as npt
import polars as pl
import torch
from safetensors.torch import load_file

from datp_core.data.populations.contracts import (
    OUTCOME_LABEL_COLUMN,
    STABLE_ROW_ID_COLUMN,
    PopulationOutcomeLabel,
)
from datp_core.core.errors import (
    ArtifactIntegrityError,
    LeakageError,
    ScientificContractError,
)
from datp_core.artifacts.provenance import Checksum, checksum_file
from datp_core.core.identifiers import ContractSubject, FeatureNameSequence, PartitionRole, ScoreFrameColumn
from datp_core.core.numeric import BatchSize, FeatureCount, RowCount
from datp_core.learning.autoencoder import LEARNING_DTYPE, ReconstructionAutoencoder, reconstruction_errors
from datp_core.learning.federated.models import CheckpointCandidate
from datp_core.pipeline.scoring.models import PersistedScoreFrame
from datp_core.detector.checkpoints.contracts import validate_persisted_checkpoint_file
from datp_core.protocols.training import AutoencoderProtocol

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
    """Validate score inputs without materializing complete columns in Python."""
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
            pl.Series(
                SCORE_FRAME_COLUMNS[2],
                scores.tolist(),
                dtype=pl.Float64,
            ),
        )
    )


def validate_persisted_score_frame(
    path: Path,
    checksum: Checksum,
    row_count: RowCount,
) -> pl.DataFrame:
    if not path.is_file():
        raise ArtifactIntegrityError(
            "score artifact is missing",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    if checksum_file(path) != checksum:
        raise ArtifactIntegrityError(
            "score checksum changed after write",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    frame = pl.read_parquet(path)
    if frame.height != row_count.value:
        raise ArtifactIntegrityError(
            "score artifact row count mismatch",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    if tuple(frame.columns) != SCORE_FRAME_COLUMNS:
        raise ArtifactIntegrityError(
            "score artifact schema mismatch",
            subject=ContractSubject.SCHEMA,
        )
    observed_dtypes = tuple(frame.schema[column] for column in SCORE_FRAME_COLUMNS)
    if observed_dtypes != SCORE_FRAME_DTYPES:
        raise ArtifactIntegrityError(
            "score artifact column dtype mismatch",
            subject=ContractSubject.SCHEMA,
        )
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
    matrix, labels, row_ids = extract_score_arrays(frame, feature_names)
    scores = reconstruction_errors(model, matrix, batch_size=batch_size, device=device)
    if scores.shape[0] != matrix.shape[0]:
        raise ScientificContractError(
            "score count must equal partition row count",
            subject=partition_role,
        )
    if not np.isfinite(scores).all():
        raise ScientificContractError(
            f"generated scores must be finite in {partition_role.value} partition",
            subject=ContractSubject.SCORES,
        )
    output = score_frame(row_ids, labels, scores)
    destination.parent.mkdir(parents=True, exist_ok=True)
    output.write_parquet(destination)
    persisted = PersistedScoreFrame(
        path=destination,
        checksum=checksum_file(destination),
        row_count=RowCount(output.height),
        feature_count=FeatureCount(len(feature_names)),
    )
    reloaded = validate_persisted_score_frame(
        persisted.path,
        persisted.checksum,
        persisted.row_count,
    )
    if output.shape != reloaded.shape:
        raise ArtifactIntegrityError(
            "score reload shape mismatch",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    if not output.equals(reloaded):
        raise ArtifactIntegrityError(
            "score reload equality failed",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    return persisted


def load_checkpoint_model(
    checkpoint: CheckpointCandidate,
    autoencoder: AutoencoderProtocol,
    device: torch.device,
) -> ReconstructionAutoencoder:
    if device.type != "cuda":
        raise ScientificContractError(
            "scoring requires a CUDA device",
            subject=ContractSubject.CUDA,
        )
    validate_persisted_checkpoint_file(checkpoint.tensor_path, checkpoint.tensor_checksum)
    model = ReconstructionAutoencoder(autoencoder.widths).to(device)
    state = load_file(str(checkpoint.tensor_path), device=str(device))
    model.load_state_dict(state, strict=True)
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
            f"{partition_role.value} frame missing declared columns: {', '.join(missing)}",
            subject=ContractSubject.SCHEMA,
        )


def _require_identity_columns(
    frame: pl.DataFrame,
    partition_role: PartitionRole,
) -> None:
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
        column = frame.get_column(name)
        dtype = column.dtype
        if not dtype.is_numeric():
            raise ScientificContractError(
                f"feature column '{name}' in {partition_role.value} partition must be numeric, got {dtype}",
                subject=ContractSubject.FEATURES,
            )
        if column.null_count() > 0:
            raise ScientificContractError(
                f"feature column '{name}' in {partition_role.value} partition contains null values",
                subject=ContractSubject.FEATURES,
            )
        has_non_finite = frame.select((~pl.col(name).is_finite()).any()).item()
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

"""Shared score generation and persistence service for autoencoder branches."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
import torch

from datp_core.domain.enums import ContractSubject, PartitionRole
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    FeatureCount,
    FeatureNameSequence,
    RowCount,
    checksum_file,
)
from datp_core.learning.autoencoder import ReconstructionAutoencoder, reconstruction_errors
from datp_core.pipeline.scoring.frame_contract import (
    extract_score_arrays,
    score_frame,
    validate_persisted_score_frame,
    validate_score_input_frame,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class PersistedScoreFrame:
    path: Path
    checksum: Checksum
    row_count: RowCount
    feature_count: FeatureCount


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
    """Validate, score, persist, reload, and verify one ordered partition."""
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

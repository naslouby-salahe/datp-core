"""Typed scoring commands and stage outcomes."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import polars as pl

from datp_core.centralized_reference.checkpointing import CentralizedCheckpointCandidate
from datp_core.centralized_reference.scoring import CentralizedScoringResult
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import PublicationStatus, StageOperationId
from datp_core.domain.values import BatchSize, Checksum, FeatureNameSequence
from datp_core.learning.federated.models import CheckpointCandidate
from datp_core.protocols.models import AutoencoderProtocol
from datp_core.scoring.generation import ClientScoringInput
from datp_core.scoring.models import ScoreGenerationResult


@dataclass(slots=True, eq=False)
class ScoreFederatedRequest:
    checkpoint: CheckpointCandidate
    autoencoder: AutoencoderProtocol
    feature_names: FeatureNameSequence
    clients: tuple[ClientScoringInput, ...]
    batch_size: BatchSize
    output_directory: Path
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    overwrite: bool


@dataclass(frozen=True, slots=True)
class ScoreFederatedStageResult:
    stage: ClassVar[StageOperationId] = StageOperationId.SCORE_FEDERATED
    publication_status: PublicationStatus
    result: ScoreGenerationResult


@dataclass(slots=True, eq=False)
class ScoreCentralizedReferenceRequest:
    coordinate: CentralizedTrainingCoordinate
    checkpoint: CentralizedCheckpointCandidate
    autoencoder: AutoencoderProtocol
    feature_names: FeatureNameSequence
    calibration_features: pl.DataFrame
    evaluation_features: pl.DataFrame
    batch_size: BatchSize
    output_directory: Path
    preprocessing_state_checksum: Checksum
    overwrite: bool


@dataclass(frozen=True, slots=True)
class ScoreCentralizedReferenceResult:
    stage: ClassVar[StageOperationId] = StageOperationId.SCORE_CENTRALIZED_REFERENCE
    publication_status: PublicationStatus
    scoring: CentralizedScoringResult
    complete_digest: Checksum

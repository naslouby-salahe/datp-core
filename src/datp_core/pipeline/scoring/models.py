"""Shared score-artifact contracts, persisted frames, and typed bindings."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.detector.scoring.contracts import (
    ScoreArtifact,
    ScoreArtifactManifest,
    ScoreGenerationResult,
    ScoreRecord,
)
from datp_core.detector.training.centralized import CentralizedTrainingCoordinate
from datp_core.domain.enums import PartitionRole, PublicationStatus, SplitProtocolId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import BatchSize, FeatureCount, RoundNumber, RowCount
from datp_core.domain.values.identifiers import FeatureNameSequence
from datp_core.detector.training.models import CheckpointCandidate, FederatedTrainingCoordinate
from datp_core.pipeline.checkpoints.models import CentralizedCheckpointCandidate
from datp_core.protocols.training import AutoencoderProtocol

type FederatedScoreRecord = ScoreRecord[FederatedTrainingCoordinate, ClientIdentity]
type FederatedScoreArtifactManifest = ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]
type FederatedScoreGenerationResult = ScoreGenerationResult[FederatedTrainingCoordinate, ClientIdentity]


class FederatedScoreAssetName(StrEnum):
    CALIBRATION = "calibration.parquet"
    EVALUATION = "evaluation.parquet"
    FUTURE_RECALIBRATION = "future_recalibration.parquet"
    COMPLETE = "COMPLETE"


class CentralizedScoreAssetName(StrEnum):
    CALIBRATION_SCORES = "calibration_scores.parquet"
    EVALUATION_SCORES = "evaluation_scores.parquet"
    SCORE_MANIFEST = "score_manifest.json"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True, kw_only=True)
class PersistedScoreFrame:
    path: Path
    checksum: Checksum
    row_count: RowCount
    feature_count: FeatureCount


@dataclass(frozen=True, slots=True, eq=False)
class ClientScoringInput:
    client: ClientIdentity
    calibration_features: pl.DataFrame
    evaluation_features: pl.DataFrame
    future_recalibration_features: pl.DataFrame | None = None

    def features_for(self, role: PartitionRole) -> pl.DataFrame:
        match role:
            case PartitionRole.CALIBRATION:
                return self.calibration_features
            case PartitionRole.FUTURE_RECALIBRATION:
                if self.future_recalibration_features is None:
                    raise ScientificContractError(
                        "temporal score input is missing future recalibration features",
                        subject=role,
                    )
                return self.future_recalibration_features
            case PartitionRole.EVALUATION:
                return self.evaluation_features
            case PartitionRole.TRAIN:
                raise ScientificContractError("training rows are never scored", subject=role)
            case PartitionRole.STATIC_REFERENCE_RESERVE:
                raise ScientificContractError("static-reference reserve rows are never scored", subject=role)


@dataclass(frozen=True, slots=True)
class ScoreGenerationRequest:
    checkpoint: CheckpointCandidate
    scored_split_protocol: SplitProtocolId
    autoencoder: AutoencoderProtocol
    feature_names: FeatureNameSequence
    clients: tuple[ClientScoringInput, ...]
    batch_size: BatchSize
    output_directory: Path
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum


@dataclass(slots=True, eq=False, kw_only=True)
class GenerateFederatedScoresRequest:
    checkpoint: CheckpointCandidate
    scored_split_protocol: SplitProtocolId
    autoencoder: AutoencoderProtocol
    feature_names: FeatureNameSequence
    clients: tuple[ClientScoringInput, ...]
    batch_size: BatchSize
    output_directory: Path
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    overwrite: bool


@dataclass(frozen=True, slots=True)
class PooledScoreArtifact(ScoreArtifact[CentralizedTrainingCoordinate]):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class ScorePartitionBinding:
    partition_role: PartitionRole
    row_count: RowCount
    ordered_identity_checksum: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedScoringPublicationBinding:
    coordinate: CentralizedTrainingCoordinate
    checkpoint_round: RoundNumber
    checkpoint_checksum: Checksum
    preprocessing_state_checksum: Checksum
    split_manifest_checksum: Checksum
    feature_names: FeatureNameSequence
    batch_size: BatchSize
    calibration_input: ScorePartitionBinding
    evaluation_input: ScorePartitionBinding
    calibration_score_checksum: Checksum
    evaluation_score_checksum: Checksum


@dataclass(frozen=True, slots=True)
class CentralizedScoringResult:
    calibration_scores: PooledScoreArtifact
    evaluation_scores: PooledScoreArtifact
    model_tensor_checksum: Checksum
    preprocessing_state_checksum: Checksum


@dataclass(frozen=True, slots=True, eq=False)
class CentralizedScoringRequest:
    coordinate: CentralizedTrainingCoordinate
    checkpoint: CentralizedCheckpointCandidate
    autoencoder: AutoencoderProtocol
    feature_names: FeatureNameSequence
    calibration_features: pl.DataFrame
    evaluation_features: pl.DataFrame
    batch_size: BatchSize
    output_directory: Path
    preprocessing_state_checksum: Checksum


@dataclass(slots=True, eq=False, kw_only=True)
class GenerateCentralizedScoresRequest:
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


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateCentralizedScoresResult:
    publication_status: PublicationStatus
    scoring: CentralizedScoringResult
    complete_digest: Checksum

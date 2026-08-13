from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import FeatureNameSequence, PartitionRole, SplitProtocolId
from datp_core.core.numeric import BatchSize, FeatureCount, RowCount
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.autoencoder import AutoencoderModelState
from datp_core.detector.scoring.contracts import (
    ScoreArtifact,
    ScoreArtifactManifest,
    ScoreGenerationResult,
    ScoreRecord,
)
from datp_core.detector.training.centralized import CentralizedTrainingCoordinate, CentralizedTrainingResult
from datp_core.detector.training.contracts import AutoencoderProtocol
from datp_core.detector.training.models import FederatedTrainingCoordinate, FederatedTrainingResult

type FederatedScoreRecord = ScoreRecord[FederatedTrainingCoordinate, ClientIdentity]
type FederatedScoreArtifactManifest = ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]
type FederatedScoreGenerationResult = ScoreGenerationResult[FederatedTrainingCoordinate, ClientIdentity]


@dataclass(frozen=True, slots=True)
class TerminalFederatedScoringModel:
    """Frozen terminal model state and provenance for federated score generation."""

    coordinate: FederatedTrainingCoordinate
    terminal_model_state: AutoencoderModelState
    batch_size_used: BatchSize


type FederatedScoringModel = FederatedTrainingResult | TerminalFederatedScoringModel


class FederatedScoreAssetName(StrEnum):
    CALIBRATION = "calibration.parquet"
    EVALUATION = "evaluation.parquet"
    FUTURE_RECALIBRATION = "future_recalibration.parquet"
    MANIFEST = "score_manifest.json"


class CentralizedScoreAssetName(StrEnum):
    CALIBRATION_SCORES = "calibration_scores.parquet"
    EVALUATION_SCORES = "evaluation_scores.parquet"


@dataclass(frozen=True, slots=True, kw_only=True)
class PersistedScoreFrame:
    path: Path
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
                        ErrorMessage("temporal score input is missing future recalibration features"),
                        subject=role,
                    )
                return self.future_recalibration_features
            case PartitionRole.EVALUATION:
                return self.evaluation_features
            case PartitionRole.TRAIN:
                raise ScientificContractError(ErrorMessage("training rows are never scored"), subject=role)
            case PartitionRole.STATIC_REFERENCE_RESERVE:
                raise ScientificContractError(
                    ErrorMessage("static-reference reserve rows are never scored"), subject=role
                )
            case PartitionRole.DISCARDED:
                raise ScientificContractError(ErrorMessage("discarded rows are never scored"), subject=role)


@dataclass(frozen=True, slots=True)
class ScoreGenerationRequest:
    training: FederatedScoringModel
    scored_split_protocol: SplitProtocolId
    autoencoder: AutoencoderProtocol
    feature_names: FeatureNameSequence
    clients: tuple[ClientScoringInput, ...]
    batch_size: BatchSize
    output_directory: Path


@dataclass(slots=True, eq=False, kw_only=True)
class GenerateFederatedScoresRequest:
    training: FederatedScoringModel
    scored_split_protocol: SplitProtocolId
    autoencoder: AutoencoderProtocol
    feature_names: FeatureNameSequence
    clients: tuple[ClientScoringInput, ...]
    batch_size: BatchSize
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True)
class PooledScoreArtifact(ScoreArtifact[CentralizedTrainingCoordinate]):
    pass


@dataclass(frozen=True, slots=True)
class CentralizedScoringResult:
    calibration_scores: PooledScoreArtifact
    evaluation_scores: PooledScoreArtifact


@dataclass(frozen=True, slots=True, eq=False)
class CentralizedScoringRequest:
    coordinate: CentralizedTrainingCoordinate
    training: CentralizedTrainingResult
    autoencoder: AutoencoderProtocol
    feature_names: FeatureNameSequence
    calibration_features: pl.DataFrame
    evaluation_features: pl.DataFrame
    batch_size: BatchSize
    output_directory: Path


@dataclass(slots=True, eq=False, kw_only=True)
class GenerateCentralizedScoresRequest:
    coordinate: CentralizedTrainingCoordinate
    training: CentralizedTrainingResult
    autoencoder: AutoencoderProtocol
    feature_names: FeatureNameSequence
    calibration_features: pl.DataFrame
    evaluation_features: pl.DataFrame
    batch_size: BatchSize
    output_directory: Path


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateCentralizedScoresResult:
    scoring: CentralizedScoringResult

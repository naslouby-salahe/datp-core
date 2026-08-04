"""Typed training commands and stage outcomes."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import polars as pl

from datp_core.centralized_reference.checkpointing import CentralizedCheckpointCandidate
from datp_core.centralized_reference.training import (
    CentralizedTrainingCoordinate,
    CentralizedTrainingResult,
)
from datp_core.domain.contracts import ClientCollection
from datp_core.domain.enums import PublicationStatus, StageOperationId
from datp_core.domain.values import Checksum, FeatureNameSequence, Seed
from datp_core.learning.federated.common import GlobalFederatedProtocol
from datp_core.learning.federated.ditto import DittoTrainingRequest
from datp_core.learning.federated.models import CheckpointCandidate, FederatedTrainingResult
from datp_core.learning.federated.training import FederatedTrainingRequest
from datp_core.populations.models import ClientIdentity
from datp_core.preprocessing.models import CentralizedFittedPreprocessingState
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol


@dataclass(frozen=True, slots=True)
class TrainFederatedRequest:
    request: FederatedTrainingRequest[GlobalFederatedProtocol]
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TrainDittoRequest:
    request: DittoTrainingRequest
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TrainFederatedStageResult:
    stage: ClassVar[StageOperationId] = StageOperationId.TRAIN_FEDERATED
    publication_status: PublicationStatus
    training: FederatedTrainingResult
    candidates: tuple[CheckpointCandidate, ...]


@dataclass(frozen=True, slots=True)
class TrainDittoStageResult:
    stage: ClassVar[StageOperationId] = StageOperationId.TRAIN_FEDERATED
    publication_status: PublicationStatus
    global_training: FederatedTrainingResult
    global_candidates: tuple[CheckpointCandidate, ...]
    personalized_candidates: ClientCollection[ClientIdentity, tuple[CheckpointCandidate, ...]]


@dataclass(slots=True, eq=False)
class TrainCentralizedReferenceRequest:
    coordinate: CentralizedTrainingCoordinate
    training_features: pl.DataFrame
    feature_names: FeatureNameSequence
    preprocessing_state: CentralizedFittedPreprocessingState
    split_manifest_checksum: Checksum
    output_directory: Path
    training_seed: Seed
    autoencoder: AutoencoderProtocol
    checkpoint_protocol: CheckpointProtocol
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TrainCentralizedReferenceResult:
    stage: ClassVar[StageOperationId] = StageOperationId.TRAIN_CENTRALIZED_REFERENCE
    publication_status: PublicationStatus
    training: CentralizedTrainingResult
    candidates: tuple[CentralizedCheckpointCandidate, ...]
    complete_digest: Checksum

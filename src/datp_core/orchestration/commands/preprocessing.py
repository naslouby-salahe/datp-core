"""Typed preprocessing commands and stage outcomes."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from datp_core.domain.enums import (
    DatasetId,
    PopulationId,
    PreprocessingProtocolId,
    PublicationStatus,
    SplitProtocolId,
    StageOperationId,
)
from datp_core.domain.values import ClientPublicationCount, Seed
from datp_core.experiments.models import ExternalTemporalExecutionIdentity
from datp_core.populations.models import ControlledPartitionCondition
from datp_core.preprocessing.models import (
    ClientPreprocessingResult,
    PooledPreprocessingResult,
    PreprocessingPartitions,
    PreprocessingPublishContext,
)


@dataclass(frozen=True, slots=True)
class PreprocessFederatedRequest:
    population: PopulationId
    partition_seed: Seed
    split_protocol: SplitProtocolId
    preprocessing_identity: PreprocessingProtocolId
    data_root: Path
    dirichlet_condition: ControlledPartitionCondition | None
    capture_timestamp_column: str | None


@dataclass(frozen=True, slots=True)
class PreprocessFederatedArtifactsRequest:
    execution_identity: ExternalTemporalExecutionIdentity
    population_directory: Path
    split_directory: Path
    preprocessing_identity: PreprocessingProtocolId
    data_root: Path
    capture_timestamp_column: str | None = None


@dataclass(frozen=True, slots=True)
class PreprocessFederatedResult:
    stage: ClassVar[StageOperationId] = StageOperationId.PREPROCESS_FEDERATED
    population: PopulationId
    dataset: DatasetId
    partition_seed: Seed
    split_protocol: SplitProtocolId
    preprocessing_identity: PreprocessingProtocolId
    client_publications: tuple[ClientPreprocessingResult, ...]
    published_count: ClientPublicationCount
    reused_count: ClientPublicationCount
    execution_identity: ExternalTemporalExecutionIdentity | None = None


@dataclass(slots=True, eq=False)
class PreprocessCentralizedReferenceRequest:
    dataset_context: PreprocessingPublishContext
    partitions: PreprocessingPartitions


@dataclass(frozen=True, slots=True)
class PreprocessCentralizedPopulationRequest:
    population: PopulationId
    partition_seed: Seed
    split_protocol: SplitProtocolId
    data_root: Path
    dirichlet_condition: ControlledPartitionCondition | None
    capture_timestamp_column: str | None


@dataclass(frozen=True, slots=True)
class PreprocessCentralizedReferenceResult:
    stage: ClassVar[StageOperationId] = StageOperationId.PREPROCESS_CENTRALIZED_REFERENCE
    result: PooledPreprocessingResult
    population: PopulationId
    partition_seed: Seed
    preprocessing_identity: PreprocessingProtocolId
    publication_status: PublicationStatus
    dataset: DatasetId

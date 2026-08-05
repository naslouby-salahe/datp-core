"""Federated and centralized preprocessing composition under one pipeline owner."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.domain.enums import (
    DatasetId,
    PopulationId,
    PreprocessingProtocolId,
    PublicationStatus,
    SplitProtocolId,
)
from datp_core.domain.values import ClientPublicationCount, Seed
from datp_core.pipeline.execution import PipelineStage
from datp_core.populations.models import ControlledPartitionCondition
from datp_core.preprocessing.centralized import (
    CentralizedPopulationPreprocessingRequest,
    CentralizedPreprocessingOutcome,
    CentralizedPreprocessingRequest,
    preprocess_centralized,
    preprocess_centralized_population,
)
from datp_core.preprocessing.models import (
    ClientPreprocessingResult,
    PooledPreprocessingResult,
    PreprocessingPartitions,
    PreprocessingPublishContext,
)
from datp_core.preprocessing.service import (
    FederatedPreprocessingOutcome,
    FederatedPreprocessingRequest,
    PublishedFederatedPreprocessingRequest,
    preprocess_federated,
    preprocess_published_federated,
)
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity


@dataclass(frozen=True, slots=True, kw_only=True)
class FitFederatedPreprocessingRequest:
    population: PopulationId
    partition_seed: Seed
    split_protocol: SplitProtocolId
    preprocessing_identity: PreprocessingProtocolId
    data_root: Path
    dirichlet_condition: ControlledPartitionCondition | None
    capture_timestamp_column: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class FitPublishedFederatedPreprocessingRequest:
    execution_identity: ExternalTemporalExecutionIdentity
    population_directory: Path
    split_directory: Path
    preprocessing_identity: PreprocessingProtocolId
    data_root: Path
    capture_timestamp_column: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class FitFederatedPreprocessingResult:
    stage: PipelineStage
    population: PopulationId
    dataset: DatasetId
    partition_seed: Seed
    split_protocol: SplitProtocolId
    preprocessing_identity: PreprocessingProtocolId
    client_publications: tuple[ClientPreprocessingResult, ...]
    published_count: ClientPublicationCount
    reused_count: ClientPublicationCount
    execution_identity: ExternalTemporalExecutionIdentity | None = None


@dataclass(slots=True, eq=False, kw_only=True)
class FitCentralizedPreprocessingRequest:
    dataset_context: PreprocessingPublishContext
    partitions: PreprocessingPartitions


@dataclass(frozen=True, slots=True, kw_only=True)
class FitCentralizedPopulationPreprocessingRequest:
    population: PopulationId
    partition_seed: Seed
    split_protocol: SplitProtocolId
    data_root: Path
    dirichlet_condition: ControlledPartitionCondition | None
    capture_timestamp_column: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class FitCentralizedPreprocessingResult:
    stage: PipelineStage
    result: PooledPreprocessingResult
    population: PopulationId
    partition_seed: Seed
    preprocessing_identity: PreprocessingProtocolId
    publication_status: PublicationStatus
    dataset: DatasetId


def fit_federated_preprocessing(
    request: FitFederatedPreprocessingRequest,
) -> FitFederatedPreprocessingResult:
    return _federated_result(
        preprocess_federated(
            FederatedPreprocessingRequest(
                population=request.population,
                partition_seed=request.partition_seed,
                split_protocol=request.split_protocol,
                preprocessing_identity=request.preprocessing_identity,
                data_root=request.data_root,
                dirichlet_condition=request.dirichlet_condition,
                capture_timestamp_column=request.capture_timestamp_column,
            )
        )
    )


def fit_published_federated_preprocessing(
    request: FitPublishedFederatedPreprocessingRequest,
) -> FitFederatedPreprocessingResult:
    return _federated_result(
        preprocess_published_federated(
            PublishedFederatedPreprocessingRequest(
                execution_identity=request.execution_identity,
                population_directory=request.population_directory,
                split_directory=request.split_directory,
                preprocessing_identity=request.preprocessing_identity,
                data_root=request.data_root,
                capture_timestamp_column=request.capture_timestamp_column,
            )
        )
    )


def fit_centralized_preprocessing(
    request: FitCentralizedPreprocessingRequest,
) -> FitCentralizedPreprocessingResult:
    return _centralized_result(
        preprocess_centralized(
            CentralizedPreprocessingRequest(
                dataset_context=request.dataset_context,
                partitions=request.partitions,
            )
        )
    )


def fit_centralized_population_preprocessing(
    request: FitCentralizedPopulationPreprocessingRequest,
) -> FitCentralizedPreprocessingResult:
    return _centralized_result(
        preprocess_centralized_population(
            CentralizedPopulationPreprocessingRequest(
                population=request.population,
                partition_seed=request.partition_seed,
                split_protocol=request.split_protocol,
                data_root=request.data_root,
                dirichlet_condition=request.dirichlet_condition,
                capture_timestamp_column=request.capture_timestamp_column,
            )
        )
    )


def _federated_result(outcome: FederatedPreprocessingOutcome) -> FitFederatedPreprocessingResult:
    return FitFederatedPreprocessingResult(
        stage=PipelineStage.FIT_PREPROCESSING,
        population=outcome.population,
        dataset=outcome.dataset,
        partition_seed=outcome.partition_seed,
        split_protocol=outcome.split_protocol,
        preprocessing_identity=outcome.preprocessing_identity,
        client_publications=outcome.client_publications,
        published_count=outcome.published_count,
        reused_count=outcome.reused_count,
        execution_identity=outcome.execution_identity,
    )


def _centralized_result(outcome: CentralizedPreprocessingOutcome) -> FitCentralizedPreprocessingResult:
    return FitCentralizedPreprocessingResult(
        stage=PipelineStage.FIT_PREPROCESSING,
        result=outcome.result,
        population=outcome.population,
        partition_seed=outcome.partition_seed,
        preprocessing_identity=outcome.preprocessing_identity,
        publication_status=outcome.publication_status,
        dataset=outcome.dataset,
    )

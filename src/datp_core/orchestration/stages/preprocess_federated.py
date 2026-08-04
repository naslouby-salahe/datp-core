"""Stage: compose federated preprocessing workflows."""

from datp_core.orchestration.commands.preprocessing import (
    PreprocessFederatedArtifactsRequest as _PreprocessFederatedArtifactsRequest,
    PreprocessFederatedRequest as _PreprocessFederatedRequest,
    PreprocessFederatedResult as _PreprocessFederatedResult,
)
from datp_core.preprocessing.service import (
    FederatedPreprocessingOutcome,
    FederatedPreprocessingRequest,
    PublishedFederatedPreprocessingRequest,
    preprocess_federated,
    preprocess_published_federated,
)


def preprocess_federated_stage(
    request: _PreprocessFederatedRequest,
) -> _PreprocessFederatedResult:
    outcome = preprocess_federated(
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
    return _stage_result(outcome)


def preprocess_federated_artifacts_stage(
    request: _PreprocessFederatedArtifactsRequest,
) -> _PreprocessFederatedResult:
    outcome = preprocess_published_federated(
        PublishedFederatedPreprocessingRequest(
            execution_identity=request.execution_identity,
            population_directory=request.population_directory,
            split_directory=request.split_directory,
            preprocessing_identity=request.preprocessing_identity,
            data_root=request.data_root,
            capture_timestamp_column=request.capture_timestamp_column,
        )
    )
    return _stage_result(outcome)


def _stage_result(outcome: FederatedPreprocessingOutcome) -> _PreprocessFederatedResult:
    return _PreprocessFederatedResult(
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

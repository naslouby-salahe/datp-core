"""Stage: compose centralized-reference preprocessing workflows."""

from datp_core.orchestration.commands.preprocessing import (
    PreprocessCentralizedPopulationRequest as _PreprocessCentralizedPopulationRequest,
)
from datp_core.orchestration.commands.preprocessing import (
    PreprocessCentralizedReferenceRequest as _PreprocessCentralizedReferenceRequest,
)
from datp_core.orchestration.commands.preprocessing import (
    PreprocessCentralizedReferenceResult as _PreprocessCentralizedReferenceResult,
)
from datp_core.preprocessing.centralized import (
    CentralizedPopulationPreprocessingRequest,
    CentralizedPreprocessingOutcome,
    CentralizedPreprocessingRequest,
    preprocess_centralized,
    preprocess_centralized_population,
)


def preprocess_centralized_reference_stage(
    request: _PreprocessCentralizedReferenceRequest,
) -> _PreprocessCentralizedReferenceResult:
    return _stage_result(
        preprocess_centralized(
            CentralizedPreprocessingRequest(
                dataset_context=request.dataset_context,
                partitions=request.partitions,
            )
        )
    )


def preprocess_centralized_reference_population_stage(
    request: _PreprocessCentralizedPopulationRequest,
) -> _PreprocessCentralizedReferenceResult:
    return _stage_result(
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


def _stage_result(
    outcome: CentralizedPreprocessingOutcome,
) -> _PreprocessCentralizedReferenceResult:
    return _PreprocessCentralizedReferenceResult(
        result=outcome.result,
        population=outcome.population,
        partition_seed=outcome.partition_seed,
        preprocessing_identity=outcome.preprocessing_identity,
        publication_status=outcome.publication_status,
        dataset=outcome.dataset,
    )

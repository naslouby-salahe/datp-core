"""Independent pooled preprocessing for the centralized reference branch."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import polars as pl

from datp_core.artifacts.coordinates import ReusableDataCoordinate
from datp_core.artifacts.layout import ProcessedAssetName, branch_asset_path, centralized_branch_directory
from datp_core.artifacts.serialization import TrustedScaler
from datp_core.domain.enums import PartitionRole, PreprocessingFitScope, ProcessedDataBranch
from datp_core.domain.errors import LeakageError
from datp_core.preprocessing.models import (
    FittedPreprocessingState,
    FittedStatePublishSpec,
    PooledPreprocessingResult,
    PreprocessingFitBatch,
    PreprocessingProtocol,
    PreprocessingPublishContext,
)
from datp_core.preprocessing.validation import (
    core_processed_assets,
    fit_trusted_batch,
    fitted_state_after_publish,
    publish_preprocessed_partitions,
    validate_branch_isolation,
)


@dataclass(frozen=True, slots=True)
class PooledPublishRequest:
    context: PreprocessingPublishContext
    fitted_estimator: TrustedScaler
    partitions: Mapping[PartitionRole, pl.DataFrame]
    row_ids: Mapping[PartitionRole, Sequence[str]]


def fit_pooled_preprocessing(
    protocol: PreprocessingProtocol,
    estimator: TrustedScaler,
    batch: PreprocessingFitBatch,
) -> TrustedScaler:
    return fit_trusted_batch(protocol, estimator, batch, subject=PreprocessingFitScope.POOLED_TRAINING)


def publish_pooled_preprocessing(request: PooledPublishRequest) -> PooledPreprocessingResult:
    context = request.context
    branch_coordinate_directory = centralized_branch_directory(
        context.data_root,
        ReusableDataCoordinate(
            dataset=context.dataset,
            population=context.population,
            partition_seed=context.partition_seed,
            split_protocol_identity=context.split_protocol_identity,
            preprocessing_identity=context.protocol.identity,
            branch=ProcessedDataBranch.CENTRALIZED_REFERENCE,
            client_identity=None,
        ),
    )
    assets = core_processed_assets()
    result = publish_preprocessed_partitions(
        context=context,
        branch=ProcessedDataBranch.CENTRALIZED_REFERENCE,
        coordinate_directory=branch_coordinate_directory,
        fitted_estimator=request.fitted_estimator,
        partitions=request.partitions,
        row_ids=request.row_ids,
        fit_scope=PreprocessingFitScope.POOLED_TRAINING,
        asset_paths=tuple(asset.value for asset in assets),
    )
    state = fitted_state_after_publish(
        FittedStatePublishSpec(
            protocol=context.protocol,
            branch=ProcessedDataBranch.CENTRALIZED_REFERENCE,
            estimator_path=branch_asset_path(result.coordinate_directory, ProcessedAssetName.STATE),
            fit_row_count=request.partitions[PartitionRole.TRAIN].height,
        )
    )
    validate_branch_isolation(state, ProcessedDataBranch.CENTRALIZED_REFERENCE, None)
    return PooledPreprocessingResult(
        train_path=branch_asset_path(result.coordinate_directory, ProcessedAssetName.TRAIN),
        calibration_path=branch_asset_path(result.coordinate_directory, ProcessedAssetName.CALIBRATION),
        evaluation_path=branch_asset_path(result.coordinate_directory, ProcessedAssetName.EVALUATION),
        fitted_state=state,
        transformed_schema=context.protocol.transformed_schema,
        publication_status=result.publication_status,
    )


def reject_federated_state_for_pooled(state: FittedPreprocessingState) -> None:
    if state.branch is not ProcessedDataBranch.CENTRALIZED_REFERENCE:
        raise LeakageError(
            "federated client fitted state cannot be reused by the centralized reference",
            subject=state.branch,
        )

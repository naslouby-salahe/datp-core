"""Client-local federated preprocessing fit and transform."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import polars as pl

from datp_core.artifacts.coordinates import ReusableDataCoordinate
from datp_core.artifacts.layout import (
    ProcessedAssetName,
    client_asset_path,
    federated_client_directory,
)
from datp_core.artifacts.serialization import TrustedScaler
from datp_core.domain.enums import PartitionRole, PreprocessingFitScope, ProcessedDataBranch
from datp_core.domain.errors import LeakageError
from datp_core.domain.values import ClientIdentity
from datp_core.preprocessing.models import (
    ClientPreprocessingResult,
    FittedPreprocessingState,
    FittedStatePublishSpec,
    PreprocessingFitBatch,
    PreprocessingProtocol,
    PreprocessingPublishContext,
)
from datp_core.preprocessing.validation import (
    core_processed_assets,
    fit_trusted_batch,
    fitted_state_after_publish,
    publish_preprocessed_partitions,
    transform_feature_matrix,
    validate_branch_isolation,
)


@dataclass(frozen=True, slots=True)
class ClientPublishRequest:
    context: PreprocessingPublishContext
    client_identity: ClientIdentity
    fitted_estimator: TrustedScaler
    partitions: Mapping[PartitionRole, pl.DataFrame]
    row_ids: Mapping[PartitionRole, Sequence[str]]


def fit_client_preprocessing(
    protocol: PreprocessingProtocol,
    estimator: TrustedScaler,
    batch: PreprocessingFitBatch,
) -> TrustedScaler:
    return fit_trusted_batch(protocol, estimator, batch, subject=PreprocessingFitScope.CLIENT_LOCAL_TRAINING)


def transform_partition(fitted_estimator: TrustedScaler, matrix: np.ndarray, subject: PartitionRole) -> np.ndarray:
    return transform_feature_matrix(fitted_estimator, matrix, subject)


def publish_client_preprocessing(request: ClientPublishRequest) -> ClientPreprocessingResult:
    context = request.context
    relative_client = federated_client_directory(
        ReusableDataCoordinate(
            dataset=context.dataset,
            population=context.population,
            partition_seed=context.partition_seed,
            split_protocol_identity=context.split_protocol_identity,
            preprocessing_identity=context.protocol.identity,
            branch=ProcessedDataBranch.FEDERATED,
            client_identity=request.client_identity,
        )
    )
    assets = core_processed_assets()
    result = publish_preprocessed_partitions(
        context=context,
        branch=ProcessedDataBranch.FEDERATED,
        relative_coordinate=relative_client,
        fitted_estimator=request.fitted_estimator,
        partitions=request.partitions,
        row_ids=request.row_ids,
        fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        asset_paths=tuple(f"{request.client_identity.value}/{asset.value}" for asset in assets),
    )
    state = fitted_state_after_publish(
        FittedStatePublishSpec(
            protocol=context.protocol,
            branch=ProcessedDataBranch.FEDERATED,
            estimator_path=client_asset_path(result.coordinate_directory, ProcessedAssetName.STATE),
            fit_row_count=request.partitions[PartitionRole.TRAIN].height,
            client_identity=request.client_identity,
        )
    )
    validate_branch_isolation(state, ProcessedDataBranch.FEDERATED, request.client_identity)
    return ClientPreprocessingResult(
        client_identity=request.client_identity,
        train_path=client_asset_path(result.coordinate_directory, ProcessedAssetName.TRAIN),
        calibration_path=client_asset_path(result.coordinate_directory, ProcessedAssetName.CALIBRATION),
        evaluation_path=client_asset_path(result.coordinate_directory, ProcessedAssetName.EVALUATION),
        fitted_state=state,
        transformed_schema=context.protocol.transformed_schema,
    )


def reject_centralized_state_for_client(state: FittedPreprocessingState) -> None:
    if state.branch is not ProcessedDataBranch.FEDERATED:
        raise LeakageError("centralized fitted state cannot be used for federated clients", subject=state.branch)

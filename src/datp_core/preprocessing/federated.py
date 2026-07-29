"""Client-local federated preprocessing fit and transform."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import polars as pl

from datp_core.artifacts.layout import (
    ProcessedAssetName,
    client_asset_path,
    federated_client_directory,
)
from datp_core.artifacts.serialization import TrustedScaler
from datp_core.artifacts.store import ProcessedPublication, publish_processed
from datp_core.domain.enums import PartitionRole, ProcessedDataBranch
from datp_core.domain.errors import LeakageError
from datp_core.preprocessing.models import (
    ClientPreprocessingResult,
    FittedPreprocessingState,
    FittedStatePublishSpec,
    PreprocessingFitBatch,
    PreprocessingProtocol,
    PreprocessingPublishContext,
    ReusableDataCoordinate,
)
from datp_core.preprocessing.validation import (
    build_preprocessing_manifest,
    fit_trusted_batch,
    fitted_state_after_publish,
    publication_target,
    require_core_partitions,
    required_core_asset_values,
    successful_preprocessing_validation_report,
    transform_feature_matrix,
    validate_branch_isolation,
    validate_no_partition_overlap,
    validate_train_only_fit,
    validate_transformed_schema,
    write_fitted_transformed_partitions,
)


@dataclass(frozen=True, slots=True)
class ClientPublishRequest:
    context: PreprocessingPublishContext
    client_identity: str
    fitted_estimator: TrustedScaler
    partitions: Mapping[PartitionRole, pl.DataFrame]
    row_ids: Mapping[PartitionRole, Sequence[str]]


def fit_client_preprocessing(
    protocol: PreprocessingProtocol,
    estimator: TrustedScaler,
    batch: PreprocessingFitBatch,
) -> TrustedScaler:
    return fit_trusted_batch(protocol, estimator, batch, subject="training")


def transform_partition(fitted_estimator: TrustedScaler, matrix: np.ndarray, subject: PartitionRole) -> np.ndarray:
    return transform_feature_matrix(fitted_estimator, matrix, subject)


def publish_client_preprocessing(request: ClientPublishRequest) -> ClientPreprocessingResult:
    context = request.context
    validate_train_only_fit(PartitionRole.TRAIN)
    require_core_partitions(request.partitions, request.row_ids, subject="federated")
    validate_no_partition_overlap(
        request.row_ids[PartitionRole.TRAIN],
        request.row_ids[PartitionRole.CALIBRATION],
        request.row_ids[PartitionRole.EVALUATION],
    )
    validate_transformed_schema(context.protocol, context.protocol.transformed_schema)
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
    target = publication_target(context.data_root, relative_client)
    asset_values = required_core_asset_values()
    manifest = build_preprocessing_manifest(
        context,
        branch=ProcessedDataBranch.FEDERATED,
        asset_paths=tuple(f"{request.client_identity}/{asset}" for asset in asset_values),
    )
    result = publish_processed(
        ProcessedPublication(
            coordinate_directory=target,
            manifest=manifest,
            schema=context.protocol.transformed_schema,
            validation_report=successful_preprocessing_validation_report(),
            writer=lambda temporary: write_fitted_transformed_partitions(
                temporary,
                protocol=context.protocol,
                fitted_estimator=request.fitted_estimator,
                partitions=request.partitions,
            ),
            required_assets=asset_values,
            overwrite=False,
        )
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
        raise LeakageError("centralized fitted state cannot be used for federated clients", subject=state.branch.value)

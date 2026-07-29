"""Independent pooled preprocessing for the centralized reference branch."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import polars as pl

from datp_core.artifacts.coordinates import ReusableDataCoordinate
from datp_core.artifacts.layout import ProcessedAssetName, branch_asset_path, centralized_branch_directory
from datp_core.artifacts.serialization import TrustedScaler
from datp_core.artifacts.store import ProcessedPublication, publish_processed
from datp_core.domain.enums import PartitionRole, PreprocessingFitScope, ProcessedDataBranch
from datp_core.domain.errors import LeakageError
from datp_core.preprocessing.models import (
    FittedPreprocessingState,
    FittedStatePublishSpec,
    PooledPreprocessingResult,
    PreprocessingFitBatch,
    PreprocessingManifest,
    PreprocessingProtocol,
    PreprocessingPublishContext,
    PreprocessingValidationReport,
    TransformedSchema,
)
from datp_core.preprocessing.validation import (
    build_preprocessing_manifest,
    fit_trusted_batch,
    fitted_state_after_publish,
    publication_target,
    require_core_partitions,
    required_core_asset_values,
    successful_preprocessing_validation_report,
    validate_branch_isolation,
    validate_no_partition_overlap,
    validate_train_only_fit,
    validate_transformed_schema,
    write_fitted_transformed_partitions,
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
    validate_train_only_fit(PartitionRole.TRAIN)
    require_core_partitions(
        request.partitions,
        request.row_ids,
        subject=PreprocessingFitScope.POOLED_TRAINING,
    )
    validate_no_partition_overlap(
        request.row_ids[PartitionRole.TRAIN],
        request.row_ids[PartitionRole.CALIBRATION],
        request.row_ids[PartitionRole.EVALUATION],
    )
    validate_transformed_schema(context.protocol, context.protocol.transformed_schema)
    relative_branch = centralized_branch_directory(
        ReusableDataCoordinate(
            dataset=context.dataset,
            population=context.population,
            partition_seed=context.partition_seed,
            split_protocol_identity=context.split_protocol_identity,
            preprocessing_identity=context.protocol.identity,
            branch=ProcessedDataBranch.CENTRALIZED_REFERENCE,
            client_identity=None,
        )
    )
    target = publication_target(context.data_root, relative_branch)
    asset_values = required_core_asset_values()
    manifest = build_preprocessing_manifest(
        context,
        branch=ProcessedDataBranch.CENTRALIZED_REFERENCE,
        asset_paths=asset_values,
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
            manifest_type=PreprocessingManifest,
            schema_type=TransformedSchema,
            report_type=PreprocessingValidationReport,
        )
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
    )


def reject_federated_state_for_pooled(state: FittedPreprocessingState) -> None:
    if state.branch is not ProcessedDataBranch.CENTRALIZED_REFERENCE:
        raise LeakageError(
            "federated client fitted state cannot be reused by the centralized reference",
            subject=state.branch.value,
        )

"""Independent pooled preprocessing for the centralized reference branch."""

from dataclasses import dataclass

from datp_core.artifacts.coordinates import ReusableDataCoordinate
from datp_core.artifacts.layout import (
    ProcessedAssetName,
    RelativeAssetPathSequence,
    asset_for_partition,
    branch_asset_path,
    canonical_relative_asset_path,
    centralized_branch_directory,
    partition_roles,
    processed_asset_names,
)
from datp_core.artifacts.serialization import TrustedScaler
from datp_core.domain.enums import PartitionRole, PreprocessingFitScope, ProcessedDataBranch
from datp_core.domain.errors import LeakageError
from datp_core.domain.values import RowCount
from datp_core.preprocessing.models import (
    CentralizedFittedStatePublishSpec,
    FederatedFittedPreprocessingState,
    FittedPreprocessingState,
    PooledPreprocessingResult,
    PreprocessedPartitionPaths,
    PreprocessingFitBatch,
    PreprocessingPartitionSet,
    PreprocessingProtocol,
    PreprocessingPublishContext,
)
from datp_core.preprocessing.validation import (
    centralized_fitted_state_after_publish,
    fit_trusted_batch,
    publish_preprocessed_partitions,
)


@dataclass(frozen=True, slots=True)
class PooledPublishRequest:
    context: PreprocessingPublishContext
    fitted_estimator: TrustedScaler
    partitions: PreprocessingPartitionSet


def fit_pooled_preprocessing(
    protocol: PreprocessingProtocol,
    batch: PreprocessingFitBatch,
) -> TrustedScaler:
    return fit_trusted_batch(protocol, batch, subject=PreprocessingFitScope.POOLED_TRAINING)


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
    asset_names = processed_asset_names(context.split_protocol_identity)
    asset_paths = RelativeAssetPathSequence(
        tuple(
            canonical_relative_asset_path(asset, ProcessedDataBranch.CENTRALIZED_REFERENCE, None)
            for asset in asset_names
        )
    )
    result = publish_preprocessed_partitions(
        context=context,
        branch=ProcessedDataBranch.CENTRALIZED_REFERENCE,
        coordinate_directory=branch_coordinate_directory,
        fitted_estimator=request.fitted_estimator,
        partitions=request.partitions,
        asset_paths=asset_paths,
    )
    state = centralized_fitted_state_after_publish(
        CentralizedFittedStatePublishSpec(
            protocol=context.protocol,
            estimator_path=branch_asset_path(result.coordinate_directory, ProcessedAssetName.STATE),
            fit_row_count=RowCount(request.partitions.require(PartitionRole.TRAIN).frame.height),
        )
    )
    roles = partition_roles(context.split_protocol_identity)
    paths_by_role = {role: branch_asset_path(result.coordinate_directory, asset_for_partition(role)) for role in roles}
    paths = PreprocessedPartitionPaths(
        train=paths_by_role[PartitionRole.TRAIN],
        calibration=paths_by_role[PartitionRole.CALIBRATION],
        evaluation=paths_by_role[PartitionRole.EVALUATION],
        future_recalibration=paths_by_role.get(PartitionRole.FUTURE_RECALIBRATION),
        static_reference_reserve=paths_by_role.get(PartitionRole.STATIC_REFERENCE_RESERVE),
    )
    return PooledPreprocessingResult(
        paths=paths,
        fitted_state=state,
        publication_status=result.publication_status,
    )


def reject_federated_state_for_pooled(state: FittedPreprocessingState) -> None:
    if isinstance(state, FederatedFittedPreprocessingState):
        raise LeakageError(
            "federated client fitted state cannot be reused by the centralized reference",
            subject=ProcessedDataBranch.FEDERATED,
        )

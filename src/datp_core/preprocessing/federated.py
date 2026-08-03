"""Client-local federated preprocessing fit and transform."""

import numpy as np

from datp_core.artifacts.coordinates import ReusableDataCoordinate
from datp_core.artifacts.layout import (
    ProcessedAssetName,
    RelativeAssetPathSequence,
    asset_for_partition,
    canonical_relative_asset_path,
    client_asset_path,
    federated_client_directory,
    partition_roles,
    processed_asset_names,
)
from datp_core.domain.enums import ContractSubject, PartitionRole, PreprocessingFitScope, ProcessedDataBranch
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import OutcomeLabelSequence, RowCount, StableRowIdSequence
from datp_core.preprocessing.models import (
    ClientFittedEstimator,
    ClientLocalFittedEstimators,
    ClientPreprocessingPartitionSet,
    ClientPreprocessingResult,
    ClientPublishRequest,
    FederatedFittedEstimators,
    FederatedFittedStatePublishSpec,
    PooledFittedEstimator,
    PreprocessedPartitionPaths,
    PreprocessingFitBatch,
    PreprocessingProtocol,
)
from datp_core.preprocessing.validation import (
    federated_fitted_state_after_publish,
    fit_trusted_batch,
    publish_preprocessed_partitions,
    require_columns,
)


def fit_estimators_for_federated_clients(
    protocol: PreprocessingProtocol,
    client_partitions: ClientPreprocessingPartitionSet,
) -> FederatedFittedEstimators:
    """Fit client-local or pooled federated estimators from extracted partition sets."""
    match protocol.fit_scope:
        case PreprocessingFitScope.CLIENT_LOCAL_TRAINING:
            return _fit_client_local_estimators(protocol, client_partitions)
        case PreprocessingFitScope.POOLED_TRAINING:
            return _fit_pooled_estimators(protocol, client_partitions)
        case _:
            raise ScientificContractError(
                "unsupported federated preprocessing fit scope",
                subject=protocol.fit_scope,
            )


def _fit_client_local_estimators(
    protocol: PreprocessingProtocol,
    client_partitions: ClientPreprocessingPartitionSet,
) -> ClientLocalFittedEstimators:
    fitted_list: list[ClientFittedEstimator] = []
    feature_names = protocol.input_feature_names
    for client_item in client_partitions.clients:
        train_partition = client_item.partitions.require(PartitionRole.TRAIN)
        require_columns(train_partition.frame, feature_names.names, subject=ContractSubject.SCHEMA)
        matrix = train_partition.frame.select(list(feature_names)).to_numpy()
        fitted = fit_trusted_batch(
            protocol,
            PreprocessingFitBatch(
                training_matrix=matrix,
                training_row_ids=train_partition.row_ids,
                training_labels=train_partition.outcome_labels,
            ),
            subject=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        )
        fitted_list.append(ClientFittedEstimator(client_identity=client_item.client_identity, estimator=fitted))
    return ClientLocalFittedEstimators(estimators=tuple(fitted_list))


def _fit_pooled_estimators(
    protocol: PreprocessingProtocol,
    client_partitions: ClientPreprocessingPartitionSet,
) -> PooledFittedEstimator:
    feature_names = protocol.input_feature_names
    train_partitions = tuple(
        client_item.partitions.require(PartitionRole.TRAIN) for client_item in client_partitions.clients
    )
    for partition in train_partitions:
        require_columns(partition.frame, feature_names.names, subject=ContractSubject.SCHEMA)
    matrices = tuple(partition.frame.select(list(feature_names)).to_numpy() for partition in train_partitions)
    pooled_matrix = np.vstack(matrices)
    pooled_row_ids = StableRowIdSequence(
        tuple(item for partition in train_partitions for item in partition.row_ids.row_ids)
    )
    pooled_labels = OutcomeLabelSequence(
        tuple(item for partition in train_partitions for item in partition.outcome_labels.labels)
    )

    pooled = fit_trusted_batch(
        protocol,
        PreprocessingFitBatch(
            training_matrix=pooled_matrix,
            training_row_ids=pooled_row_ids,
            training_labels=pooled_labels,
        ),
        subject=PreprocessingFitScope.POOLED_TRAINING,
    )
    return PooledFittedEstimator(estimator=pooled)


def publish_client_preprocessing(request: ClientPublishRequest) -> ClientPreprocessingResult:
    context = request.context
    client_coordinate_directory = federated_client_directory(
        context.data_root,
        ReusableDataCoordinate(
            dataset=context.dataset,
            population=context.population,
            partition_seed=context.partition_seed,
            split_protocol_identity=context.split_protocol_identity,
            preprocessing_identity=context.protocol.identity,
            branch=ProcessedDataBranch.FEDERATED,
            client_identity=request.client_identity,
        ),
    )
    asset_names = processed_asset_names(context.split_protocol_identity)
    asset_paths = RelativeAssetPathSequence(
        tuple(
            canonical_relative_asset_path(asset, ProcessedDataBranch.FEDERATED, request.client_identity)
            for asset in asset_names
        )
    )
    result = publish_preprocessed_partitions(
        context=context,
        branch=ProcessedDataBranch.FEDERATED,
        coordinate_directory=client_coordinate_directory,
        fitted_estimator=request.fitted_estimator,
        partitions=request.partitions,
        asset_paths=asset_paths,
    )
    state = federated_fitted_state_after_publish(
        FederatedFittedStatePublishSpec(
            protocol=context.protocol,
            estimator_path=client_asset_path(result.coordinate_directory, ProcessedAssetName.STATE),
            fit_row_count=RowCount(request.partitions.require(PartitionRole.TRAIN).frame.height),
            client_identity=request.client_identity,
        )
    )
    roles = partition_roles(context.split_protocol_identity)
    paths_by_role = {role: client_asset_path(result.coordinate_directory, asset_for_partition(role)) for role in roles}
    paths = PreprocessedPartitionPaths(
        train=paths_by_role[PartitionRole.TRAIN],
        calibration=paths_by_role[PartitionRole.CALIBRATION],
        evaluation=paths_by_role[PartitionRole.EVALUATION],
        future_recalibration=paths_by_role.get(PartitionRole.FUTURE_RECALIBRATION),
        static_reference_reserve=paths_by_role.get(PartitionRole.STATIC_REFERENCE_RESERVE),
    )
    return ClientPreprocessingResult(
        client_identity=request.client_identity,
        paths=paths,
        fitted_state=state,
        publication_status=result.publication_status,
    )

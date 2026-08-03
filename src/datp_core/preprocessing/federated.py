"""Client-local federated preprocessing fit and transform."""

from dataclasses import dataclass

import numpy as np

from datp_core.artifacts.coordinates import ReusableDataCoordinate
from datp_core.artifacts.layout import (
    ProcessedAssetName,
    canonical_relative_asset_path,
    client_asset_path,
    federated_client_directory,
    partition_roles,
    processed_asset_names,
)
from datp_core.artifacts.serialization import construct_trusted_estimator
from datp_core.domain.enums import PartitionRole, PreprocessingFitScope, ProcessedDataBranch
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import ClientPathToken, OutcomeLabelSequence, RowCount, StableRowIdSequence
from datp_core.preprocessing.models import (
    ClientFittedEstimator,
    ClientLocalFittedEstimators,
    ClientPreprocessingResult,
    ClientPublishRequest,
    FederatedFittedEstimators,
    FittedStatePublishSpec,
    PooledFittedEstimator,
    PreprocessedPartitionPaths,
    PreprocessingFitBatch,
    PreprocessingPartitionSet,
    PreprocessingProtocol,
)
from datp_core.preprocessing.validation import (
    fit_trusted_batch,
    fitted_state_after_publish,
    publish_preprocessed_partitions,
    validate_branch_isolation,
)


@dataclass(frozen=True, slots=True)
class ClientPreprocessingPartitions:
    client_identity: ClientPathToken
    partitions: PreprocessingPartitionSet


def fit_estimators_for_federated_clients(
    protocol: PreprocessingProtocol,
    client_ids: tuple[ClientPathToken, ...],
    client_partitions: tuple[ClientPreprocessingPartitions, ...],
) -> FederatedFittedEstimators:
    """Fit client-local or pooled federated estimators from extracted partition sets."""
    match protocol.fit_scope:
        case PreprocessingFitScope.CLIENT_LOCAL_TRAINING:
            return _fit_client_local_estimators(protocol, client_ids, client_partitions)
        case PreprocessingFitScope.POOLED_TRAINING:
            return _fit_pooled_estimators(protocol, client_ids, client_partitions)
        case _:
            raise ScientificContractError(
                "unsupported federated preprocessing fit scope",
                subject=protocol.fit_scope,
            )


def _fit_client_local_estimators(
    protocol: PreprocessingProtocol,
    client_ids: tuple[ClientPathToken, ...],
    client_partitions: tuple[ClientPreprocessingPartitions, ...],
) -> ClientLocalFittedEstimators:
    partitions_by_client = {cp.client_identity: cp.partitions for cp in client_partitions}
    fitted_list: list[ClientFittedEstimator] = []
    feature_names = protocol.input_feature_names.as_list()
    for client_id in client_ids:
        partitions = partitions_by_client[client_id]
        train_partition = partitions.require(PartitionRole.TRAIN)
        matrix = train_partition.frame.select(feature_names).to_numpy()
        estimator = construct_trusted_estimator(protocol.estimator_class_name)
        fitted = fit_trusted_batch(
            protocol,
            estimator,
            PreprocessingFitBatch(
                training_matrix=matrix,
                training_row_ids=train_partition.row_ids,
                training_labels=train_partition.outcome_labels,
            ),
            subject=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        )
        fitted_list.append(ClientFittedEstimator(client_identity=client_id, estimator=fitted))
    return ClientLocalFittedEstimators(estimators=tuple(fitted_list))


def _fit_pooled_estimators(
    protocol: PreprocessingProtocol,
    client_ids: tuple[ClientPathToken, ...],
    client_partitions: tuple[ClientPreprocessingPartitions, ...],
) -> PooledFittedEstimator:
    partitions_by_client = {cp.client_identity: cp.partitions for cp in client_partitions}
    feature_names = protocol.input_feature_names.as_list()
    matrices: list[np.ndarray] = []
    row_ids: list[str] = []
    labels: list[str] = []

    for client_id in client_ids:
        train_partition = partitions_by_client[client_id].require(PartitionRole.TRAIN)
        matrices.append(train_partition.frame.select(feature_names).to_numpy())
        row_ids.extend(train_partition.row_ids.row_ids)
        labels.extend(train_partition.outcome_labels.labels)

    estimator = construct_trusted_estimator(protocol.estimator_class_name)
    pooled = fit_trusted_batch(
        protocol,
        estimator,
        PreprocessingFitBatch(
            training_matrix=np.vstack(matrices),
            training_row_ids=StableRowIdSequence(tuple(row_ids)),
            training_labels=OutcomeLabelSequence(tuple(labels)),
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
    result = publish_preprocessed_partitions(
        context=context,
        branch=ProcessedDataBranch.FEDERATED,
        coordinate_directory=client_coordinate_directory,
        fitted_estimator=request.fitted_estimator,
        partitions=request.partitions,
        fit_scope=context.protocol.fit_scope,
        asset_paths=tuple(
            canonical_relative_asset_path(asset, ProcessedDataBranch.FEDERATED, request.client_identity)
            for asset in asset_names
        ),
    )
    state = fitted_state_after_publish(
        FittedStatePublishSpec(
            protocol=context.protocol,
            branch=ProcessedDataBranch.FEDERATED,
            estimator_path=client_asset_path(result.coordinate_directory, ProcessedAssetName.STATE),
            fit_row_count=RowCount(request.partitions.require(PartitionRole.TRAIN).frame.height),
            client_identity=request.client_identity,
        )
    )
    validate_branch_isolation(state, ProcessedDataBranch.FEDERATED, request.client_identity)
    roles = partition_roles(context.split_protocol_identity)
    paths_by_role = {
        role: client_asset_path(result.coordinate_directory, ProcessedAssetName(f"{role.value}.parquet"))
        for role in roles
    }
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

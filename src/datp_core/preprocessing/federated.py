"""Client-local federated preprocessing fit and transform."""

import numpy as np

from datp_core.domain.contracts import ClientCollection, ClientOwned
from datp_core.domain.enums import (
    ContractSubject,
    PartitionRole,
    ProcessedDataBranch,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.counts import RowCount
from datp_core.domain.values.identifiers import FeatureNameSequence, OutcomeLabelSequence, StableRowIdSequence
from datp_core.domain.values.paths import ClientPathToken
from datp_core.preprocessing.contracts import (
    PreprocessingFitScope,
    ProcessedAssetName,
    RelativeAssetPathSequence,
    ReusableDataCoordinate,
    asset_for_partition,
    canonical_relative_asset_path,
    client_asset_path,
    federated_client_directory,
    partition_roles,
    processed_asset_names,
)
from datp_core.preprocessing.models import (
    ClientPreprocessingResult,
    ClientPublishRequest,
    FederatedFittedEstimators,
    FittedStatePublishSpec,
    PreprocessedPartitionPaths,
    PreprocessingFitBatch,
    PreprocessingPartition,
    PreprocessingPartitions,
    PreprocessingProtocol,
)
from datp_core.preprocessing.state import TrustedScaler
from datp_core.preprocessing.validation import (
    federated_fitted_state_after_publish,
    fit_trusted_batch,
    publish_preprocessed_partitions,
    require_columns,
)


def fit_estimators_for_federated_clients(
    protocol: PreprocessingProtocol,
    client_partitions: ClientCollection[ClientPathToken, PreprocessingPartitions],
) -> FederatedFittedEstimators:
    """Fit client-local or pooled estimators from benign training partitions only."""
    match protocol.fit_scope:
        case PreprocessingFitScope.CLIENT_LOCAL_TRAINING:
            return _fit_client_local_estimators(protocol, client_partitions)
        case PreprocessingFitScope.POOLED_TRAINING:
            return _fit_pooled_estimator(protocol, client_partitions)
        case _:
            raise ScientificContractError(
                "unsupported federated preprocessing fit scope",
                subject=protocol.fit_scope,
            )


def _fit_client_local_estimators(
    protocol: PreprocessingProtocol,
    client_partitions: ClientCollection[ClientPathToken, PreprocessingPartitions],
) -> ClientCollection[ClientPathToken, TrustedScaler]:
    feature_names = protocol.input_feature_names
    fitted = tuple(
        ClientOwned(
            item.client,
            fit_trusted_batch(
                protocol,
                _fit_batch(item.value.require(PartitionRole.TRAIN), feature_names),
                subject=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
            ),
        )
        for item in client_partitions.items
    )
    if len({id(item.value) for item in fitted}) != len(fitted):
        raise ScientificContractError(
            "client-local estimators must be distinct objects",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    return ClientCollection(fitted)


def _fit_pooled_estimator(
    protocol: PreprocessingProtocol,
    client_partitions: ClientCollection[ClientPathToken, PreprocessingPartitions],
) -> TrustedScaler:
    feature_names = protocol.input_feature_names
    training = tuple(item.value.require(PartitionRole.TRAIN) for item in client_partitions.items)
    for partition in training:
        require_columns(partition.frame, feature_names.names, subject=ContractSubject.SCHEMA)
    return fit_trusted_batch(
        protocol,
        PreprocessingFitBatch(
            training_matrix=np.vstack(
                tuple(partition.frame.select(list(feature_names)).to_numpy() for partition in training)
            ),
            training_row_ids=StableRowIdSequence(
                tuple(row_id for partition in training for row_id in partition.row_ids.row_ids)
            ),
            training_labels=OutcomeLabelSequence(
                tuple(label for partition in training for label in partition.outcome_labels.labels)
            ),
        ),
        subject=PreprocessingFitScope.POOLED_TRAINING,
    )


def _fit_batch(
    partition: PreprocessingPartition,
    feature_names: FeatureNameSequence,
) -> PreprocessingFitBatch:
    require_columns(partition.frame, feature_names.names, subject=ContractSubject.SCHEMA)
    return PreprocessingFitBatch(
        training_matrix=partition.frame.select(list(feature_names)).to_numpy(),
        training_row_ids=partition.row_ids,
        training_labels=partition.outcome_labels,
    )


def publish_client_preprocessing(request: ClientPublishRequest) -> ClientPreprocessingResult:
    context = request.context
    coordinate_directory = federated_client_directory(
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
    asset_paths = RelativeAssetPathSequence(
        tuple(
            canonical_relative_asset_path(asset, ProcessedDataBranch.FEDERATED, request.client_identity)
            for asset in processed_asset_names(context.split_protocol_identity)
        )
    )
    publication = publish_preprocessed_partitions(
        context=context,
        branch=ProcessedDataBranch.FEDERATED,
        coordinate_directory=coordinate_directory,
        fitted_estimator=request.fitted_estimator,
        partitions=request.partitions,
        asset_paths=asset_paths,
    )
    state = federated_fitted_state_after_publish(
        FittedStatePublishSpec(
            protocol=context.protocol,
            estimator_path=client_asset_path(publication.coordinate_directory, ProcessedAssetName.STATE),
            fit_row_count=RowCount(request.partitions.require(PartitionRole.TRAIN).frame.height),
            owner=request.client_identity,
        )
    )
    roles = partition_roles(context.split_protocol_identity)
    paths_by_role = {
        role: client_asset_path(publication.coordinate_directory, asset_for_partition(role)) for role in roles
    }

    def row_count(role: PartitionRole) -> RowCount:
        return RowCount(request.partitions.require(role).frame.height) if role in roles else RowCount(0)

    return ClientPreprocessingResult(
        client_identity=request.client_identity,
        paths=PreprocessedPartitionPaths(
            train=paths_by_role[PartitionRole.TRAIN],
            calibration=paths_by_role[PartitionRole.CALIBRATION],
            evaluation=paths_by_role[PartitionRole.EVALUATION],
            future_recalibration=paths_by_role.get(PartitionRole.FUTURE_RECALIBRATION),
            static_reference_reserve=paths_by_role.get(PartitionRole.STATIC_REFERENCE_RESERVE),
        ),
        fitted_state=state,
        publication_status=publication.publication_status,
        train_row_count=row_count(PartitionRole.TRAIN),
        calibration_row_count=row_count(PartitionRole.CALIBRATION),
        evaluation_row_count=row_count(PartitionRole.EVALUATION),
        future_recalibration_row_count=row_count(PartitionRole.FUTURE_RECALIBRATION),
        static_reference_reserve_row_count=row_count(PartitionRole.STATIC_REFERENCE_RESERVE),
    )

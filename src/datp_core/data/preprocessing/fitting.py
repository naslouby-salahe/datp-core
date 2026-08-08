import itertools

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
    PreprocessingFitBatch,
    PreprocessingPartition,
    PreprocessingPartitions,
    PreprocessingProtocol,
)
from datp_core.preprocessing.paths import build_preprocessed_partition_paths
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
    feature_names_list = feature_names.as_list()
    fitted = tuple(
        ClientOwned(
            item.client,
            fit_trusted_batch(
                protocol,
                _fit_batch(item.value.require(PartitionRole.TRAIN), feature_names, feature_names_list),
                subject=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
            ),
        )
        for item in client_partitions.items
    )
    if len(set(id(item.value) for item in fitted)) != len(fitted):
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
    feature_names_list = feature_names.as_list()
    training = tuple(item.value.require(PartitionRole.TRAIN) for item in client_partitions.items)

    for partition in training:
        require_columns(partition.frame, feature_names.names, subject=ContractSubject.SCHEMA)

    return fit_trusted_batch(
        protocol,
        PreprocessingFitBatch(
            training_matrix=np.concatenate(
                [partition.frame.select(feature_names_list).to_numpy() for partition in training]
            ),
            training_row_ids=StableRowIdSequence(
                tuple(itertools.chain.from_iterable(p.row_ids.row_ids for p in training))
            ),
            training_labels=OutcomeLabelSequence(
                tuple(itertools.chain.from_iterable(p.outcome_labels.labels for p in training))
            ),
        ),
        subject=PreprocessingFitScope.POOLED_TRAINING,
    )


def _fit_batch(
    partition: PreprocessingPartition, feature_names: FeatureNameSequence, feature_names_list: list[str] | None = None
) -> PreprocessingFitBatch:
    require_columns(partition.frame, feature_names.names, subject=ContractSubject.SCHEMA)
    cols = feature_names_list if feature_names_list is not None else feature_names.as_list()
    return PreprocessingFitBatch(
        training_matrix=partition.frame.select(cols).to_numpy(),
        training_row_ids=partition.row_ids,
        training_labels=partition.outcome_labels,
    )


def publish_client_preprocessing(request: ClientPublishRequest) -> ClientPreprocessingResult:
    context = request.context
    cond = context.dirichlet_condition

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
            controlled_partition_kind=cond.kind if cond else None,
            dirichlet_concentration=cond.concentration if cond else None,
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

    roles = frozenset(partition_roles(context.split_protocol_identity))

    def row_count(role: PartitionRole) -> RowCount:
        return RowCount(request.partitions.require(role).frame.height) if role in roles else RowCount(0)

    return ClientPreprocessingResult(
        client_identity=request.client_identity,
        paths=build_preprocessed_partition_paths(publication.coordinate_directory, context.split_protocol_identity),
        fitted_state=state,
        publication_status=publication.publication_status,
        train_row_count=row_count(PartitionRole.TRAIN),
        calibration_row_count=row_count(PartitionRole.CALIBRATION),
        evaluation_row_count=row_count(PartitionRole.EVALUATION),
        future_recalibration_row_count=row_count(PartitionRole.FUTURE_RECALIBRATION),
        static_reference_reserve_row_count=row_count(PartitionRole.STATIC_REFERENCE_RESERVE),
    )

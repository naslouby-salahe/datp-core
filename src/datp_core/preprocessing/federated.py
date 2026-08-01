"""Client-local federated preprocessing fit and transform."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import polars as pl

from datp_core.artifacts.coordinates import ReusableDataCoordinate
from datp_core.artifacts.layout import (
    ProcessedAssetName,
    asset_for_partition,
    client_asset_path,
    federated_client_directory,
    partition_roles,
)
from datp_core.artifacts.serialization import TrustedScaler, construct_trusted_estimator
from datp_core.domain.enums import PartitionRole, PreprocessingFitScope, ProcessedDataBranch
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import ClientPathToken, OutcomeLabelSequence
from datp_core.populations.models import PopulationOutcomeLabel
from datp_core.preprocessing.models import (
    ClientPreprocessingResult,
    FittedPreprocessingState,
    FittedStatePublishSpec,
    PreprocessingFitBatch,
    PreprocessingProtocol,
    PreprocessingPublishContext,
)
from datp_core.preprocessing.validation import (
    fit_trusted_batch,
    fitted_state_after_publish,
    processed_assets,
    publish_preprocessed_partitions,
    validate_branch_isolation,
)

type ClientPartitionBundle = tuple[
    Mapping[PartitionRole, pl.DataFrame],
    Mapping[PartitionRole, tuple[str, ...]],
    OutcomeLabelSequence,
]


@dataclass(frozen=True, slots=True)
class ClientPublishRequest:
    context: PreprocessingPublishContext
    client_identity: ClientPathToken
    fitted_estimator: TrustedScaler
    partitions: Mapping[PartitionRole, pl.DataFrame]
    row_ids: Mapping[PartitionRole, Sequence[str]]


def fit_client_preprocessing(
    protocol: PreprocessingProtocol,
    estimator: TrustedScaler,
    batch: PreprocessingFitBatch,
) -> TrustedScaler:
    if protocol.fit_scope is not PreprocessingFitScope.CLIENT_LOCAL_TRAINING:
        raise ScientificContractError(
            "fit_client_preprocessing requires CLIENT_LOCAL_TRAINING fit scope",
            subject=protocol.fit_scope,
        )
    return fit_trusted_batch(protocol, estimator, batch, subject=PreprocessingFitScope.CLIENT_LOCAL_TRAINING)


def fit_federated_preprocessing(
    protocol: PreprocessingProtocol,
    estimator: TrustedScaler,
    batch: PreprocessingFitBatch,
) -> TrustedScaler:
    return fit_trusted_batch(protocol, estimator, batch, subject=protocol.fit_scope)


def fit_estimators_for_federated_clients(
    protocol: PreprocessingProtocol,
    client_ids: tuple[str, ...],
    client_partitions: Mapping[str, ClientPartitionBundle],
) -> dict[str, TrustedScaler]:
    """Fit client-local or pooled federated estimators from extracted partition bundles."""
    estimator_template = construct_trusted_estimator(protocol.estimator_class_name)
    match protocol.fit_scope:
        case PreprocessingFitScope.CLIENT_LOCAL_TRAINING:
            return _fit_client_local_estimators(protocol, estimator_template, client_ids, client_partitions)
        case PreprocessingFitScope.POOLED_TRAINING:
            return _fit_pooled_estimators(protocol, estimator_template, client_ids, client_partitions)
        case _:
            raise ScientificContractError(
                "unsupported federated preprocessing fit scope",
                subject=protocol.fit_scope,
            )


def _fit_client_local_estimators(
    protocol: PreprocessingProtocol,
    estimator_template: TrustedScaler,
    client_ids: tuple[str, ...],
    client_partitions: Mapping[str, ClientPartitionBundle],
) -> dict[str, TrustedScaler]:
    feature_names = list(protocol.input_feature_names)
    fitted: dict[str, TrustedScaler] = {}
    for client_id in client_ids:
        partitions, row_ids, train_labels = client_partitions[client_id]
        fitted[client_id] = fit_federated_preprocessing(
            protocol,
            estimator_template,
            PreprocessingFitBatch(
                training_matrix=partitions[PartitionRole.TRAIN].select(feature_names).to_numpy(),
                training_row_ids=row_ids[PartitionRole.TRAIN],
                training_labels=train_labels,
                benign_label=PopulationOutcomeLabel.BENIGN,
            ),
        )
    return fitted


def _fit_pooled_estimators(
    protocol: PreprocessingProtocol,
    estimator_template: TrustedScaler,
    client_ids: tuple[str, ...],
    client_partitions: Mapping[str, ClientPartitionBundle],
) -> dict[str, TrustedScaler]:
    feature_names = list(protocol.input_feature_names)
    matrices = [
        client_partitions[client_id][0][PartitionRole.TRAIN].select(feature_names).to_numpy()
        for client_id in client_ids
    ]
    row_ids = tuple(
        row_id for client_id in client_ids for row_id in client_partitions[client_id][1][PartitionRole.TRAIN]
    )
    labels = OutcomeLabelSequence(tuple(label for client_id in client_ids for label in client_partitions[client_id][2]))
    pooled = fit_federated_preprocessing(
        protocol,
        estimator_template,
        PreprocessingFitBatch(
            training_matrix=np.vstack(matrices),
            training_row_ids=row_ids,
            training_labels=labels,
            benign_label=PopulationOutcomeLabel.BENIGN,
        ),
    )
    return {client_id: pooled for client_id in client_ids}


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
    assets = processed_assets(context.split_protocol_identity)
    result = publish_preprocessed_partitions(
        context=context,
        branch=ProcessedDataBranch.FEDERATED,
        coordinate_directory=client_coordinate_directory,
        fitted_estimator=request.fitted_estimator,
        partitions=request.partitions,
        row_ids=request.row_ids,
        fit_scope=context.protocol.fit_scope,
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
    paths = {
        role: client_asset_path(result.coordinate_directory, asset_for_partition(role))
        for role in partition_roles(context.split_protocol_identity)
    }
    return ClientPreprocessingResult(
        client_identity=request.client_identity,
        train_path=paths[PartitionRole.TRAIN],
        calibration_path=paths[PartitionRole.CALIBRATION],
        evaluation_path=paths[PartitionRole.EVALUATION],
        fitted_state=state,
        transformed_schema=context.protocol.transformed_schema,
        publication_status=result.publication_status,
        future_recalibration_path=paths.get(PartitionRole.FUTURE_RECALIBRATION),
    )


def reject_centralized_state_for_client(state: FittedPreprocessingState) -> None:
    if state.branch is not ProcessedDataBranch.FEDERATED:
        raise LeakageError("centralized fitted state cannot be used for federated clients", subject=state.branch)

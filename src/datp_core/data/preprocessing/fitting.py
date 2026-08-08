"""Train-only fitting for client-local and pooled preprocessing protocols."""

import numpy as np
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from datp_core.artifacts.provenance import ordered_text_checksum
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import ContractSubject, PartitionRole
from datp_core.core.numeric import RowCount
from datp_core.data.preprocessing.contracts import (
    CentralizedPreprocessingInput,
    ClientFittedPreprocessing,
    ClientPreprocessingInput,
    FederatedFittedPreprocessing,
    FittedPreprocessingState,
    PreprocessingFitScope,
    PreprocessingProtocol,
    ScalerFamily,
    TrustedScaler,
)
from datp_core.data.preprocessing.validation import validate_fit_partition, validate_fitted_state


def fit_federated_preprocessing(
    inputs: tuple[ClientPreprocessingInput, ...],
    protocol: PreprocessingProtocol,
) -> FederatedFittedPreprocessing:
    if not inputs:
        raise ScientificContractError(
            "federated preprocessing requires at least one client",
            subject=ContractSubject.PREPROCESSING,
        )
    ordered = tuple(sorted(inputs, key=lambda item: item.client))
    identities = tuple(item.client for item in ordered)
    if len(frozenset(identities)) != len(identities):
        raise ScientificContractError(
            "federated preprocessing inputs must be unique by client",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    match protocol.fit_scope:
        case PreprocessingFitScope.CLIENT_LOCAL_TRAINING:
            fitted = tuple(_fit_client(item, protocol) for item in ordered)
            return FederatedFittedPreprocessing(protocol=protocol, clients=fitted, pooled_state=None)
        case PreprocessingFitScope.POOLED_TRAINING:
            state = _fit_pooled(ordered, protocol)
            return FederatedFittedPreprocessing(
                protocol=protocol,
                clients=tuple(ClientFittedPreprocessing(client=item.client, state=state) for item in ordered),
                pooled_state=state,
            )


def fit_centralized_preprocessing(request: CentralizedPreprocessingInput) -> FittedPreprocessingState:
    if request.protocol.fit_scope is not PreprocessingFitScope.POOLED_TRAINING:
        raise ScientificContractError(
            "centralized preprocessing requires a pooled training protocol",
            subject=ContractSubject.PREPROCESSING,
        )
    training = request.partitions.require(PartitionRole.TRAIN)
    validate_fit_partition(training, request.protocol)
    state = FittedPreprocessingState(
        protocol=request.protocol,
        estimator=_fit_scaler(training.frame.to_numpy(), request.protocol.scaler_family),
        fit_row_count=RowCount(training.frame.height),
        fit_row_checksum=ordered_text_checksum(tuple(str(row_id) for row_id in training.row_ids)),
        owner=None,
    )
    validate_fitted_state(state)
    return state


def _fit_client(item: ClientPreprocessingInput, protocol: PreprocessingProtocol) -> ClientFittedPreprocessing:
    training = item.partitions.require(PartitionRole.TRAIN)
    validate_fit_partition(training, protocol)
    state = FittedPreprocessingState(
        protocol=protocol,
        estimator=_fit_scaler(training.frame.to_numpy(), protocol.scaler_family),
        fit_row_count=RowCount(training.frame.height),
        fit_row_checksum=ordered_text_checksum(tuple(str(row_id) for row_id in training.row_ids)),
        owner=item.client,
    )
    validate_fitted_state(state)
    return ClientFittedPreprocessing(client=item.client, state=state)


def _fit_pooled(
    ordered: tuple[ClientPreprocessingInput, ...],
    protocol: PreprocessingProtocol,
) -> FittedPreprocessingState:
    training_partitions = tuple(item.partitions.require(PartitionRole.TRAIN) for item in ordered)
    for partition in training_partitions:
        validate_fit_partition(partition, protocol)
    values = np.concatenate(tuple(partition.frame.to_numpy() for partition in training_partitions), axis=0)
    row_ids = tuple(str(row_id) for partition in training_partitions for row_id in partition.row_ids)
    state = FittedPreprocessingState(
        protocol=protocol,
        estimator=_fit_scaler(values, protocol.scaler_family),
        fit_row_count=RowCount(values.shape[0]),
        fit_row_checksum=ordered_text_checksum(row_ids),
        owner=None,
    )
    validate_fitted_state(state)
    return state


def _fit_scaler(values: np.ndarray, family: ScalerFamily) -> TrustedScaler:
    if values.ndim != 2 or values.shape[0] < 1:
        raise ScientificContractError(
            "preprocessing fit requires a non-empty two-dimensional matrix",
            subject=ContractSubject.PREPROCESSING,
        )
    match family:
        case ScalerFamily.STANDARD:
            estimator: TrustedScaler = StandardScaler(with_mean=True, with_std=True)
        case ScalerFamily.MIN_MAX:
            estimator = MinMaxScaler(clip=False)
        case ScalerFamily.COLUMN_ORDER_PROJECTION:
            raise ScientificContractError(
                "column-order projection does not fit a statistical estimator",
                subject=ContractSubject.PREPROCESSING,
            )
    estimator.fit(values)
    return estimator

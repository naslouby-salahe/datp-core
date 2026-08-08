"""Apply fitted preprocessing state without refitting or clipping."""

import numpy as np
import polars as pl

from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import ContractSubject
from datp_core.data.preprocessing.contracts import (
    CentralizedPreprocessingInput,
    CentralizedPreprocessingResult,
    ClientPreprocessingInput,
    ClientPreprocessingResult,
    FederatedFittedPreprocessing,
    FederatedPreprocessingResult,
    FittedPreprocessingState,
    PreprocessingPartition,
    TransformedPartition,
)
from datp_core.data.preprocessing.validation import (
    validate_fitted_state,
    validate_transform_partition,
)


def transform_federated_preprocessing(
    inputs: tuple[ClientPreprocessingInput, ...],
    fitted: FederatedFittedPreprocessing,
) -> FederatedPreprocessingResult:
    by_client = {item.client: item for item in inputs}
    if frozenset(by_client) != frozenset(item.client for item in fitted.clients):
        raise ScientificContractError(
            "fitted preprocessing and transform inputs must cover the same client inventory",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    results = tuple(_transform_client(by_client[item.client], item.state) for item in fitted.clients)
    return FederatedPreprocessingResult(fitted=fitted, clients=results)


def transform_centralized_preprocessing(
    request: CentralizedPreprocessingInput,
    state: FittedPreprocessingState,
) -> CentralizedPreprocessingResult:
    if state.owner is not None or state.protocol != request.protocol:
        raise ScientificContractError(
            "centralized transform requires its pooled fitted preprocessing state",
            subject=ContractSubject.PREPROCESSING,
        )
    return CentralizedPreprocessingResult(
        state=state,
        partitions=tuple(_transform_partition(partition, state) for partition in request.partitions.partitions),
    )


def _transform_client(
    request: ClientPreprocessingInput,
    state: FittedPreprocessingState,
) -> ClientPreprocessingResult:
    if state.owner is not None and state.owner != request.client:
        raise ScientificContractError(
            "client-local preprocessing state cannot transform another client",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    return ClientPreprocessingResult(
        client=request.client,
        state=state,
        partitions=tuple(_transform_partition(partition, state) for partition in request.partitions.partitions),
    )


def _transform_partition(
    partition: PreprocessingPartition,
    state: FittedPreprocessingState,
) -> TransformedPartition:
    validate_fitted_state(state)
    validate_transform_partition(partition, state.protocol)
    transformed = np.asarray(state.estimator.transform(partition.frame.to_numpy()), dtype=np.float64)
    if transformed.shape != partition.frame.shape or not np.isfinite(transformed).all():
        raise ScientificContractError(
            "preprocessing transform must preserve matrix shape and produce finite values",
            subject=ContractSubject.PREPROCESSING,
        )
    return TransformedPartition(
        role=partition.role,
        frame=pl.DataFrame(transformed, schema=tuple(state.protocol.feature_names), orient="row"),
        row_ids=partition.row_ids,
        outcome_labels=partition.outcome_labels,
    )

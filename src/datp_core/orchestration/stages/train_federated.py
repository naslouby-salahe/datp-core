"""Stage: dispatch federated training across FedAvg, FedProx, and genuine Ditto."""

from dataclasses import dataclass, replace
from pathlib import Path
from shutil import rmtree
from typing import ClassVar, cast

from datp_core.artifacts.store import publish_atomically
from datp_core.domain.contracts import ClientCollection, ClientOwned
from datp_core.domain.enums import ContractSubject, PublicationStatus, StageOperationId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum
from datp_core.learning.federated.checkpointing import (
    CheckpointCandidate,
    FederatedHistoryAssetName,
    ReusedDittoTrainingRequest,
    ReusedFederatedTrainingRequest,
    load_reused_ditto_training,
    load_reused_federated_training,
    rebase_checkpoint_candidates,
)
from datp_core.learning.federated.ditto import DittoTrainingRequest, train_ditto
from datp_core.learning.federated.fedavg import train_fedavg
from datp_core.learning.federated.fedprox import train_fedprox
from datp_core.learning.federated.models import (
    ClientTrainingInput,
    FederatedTrainingResult,
    PreparedClientProvenance,
)
from datp_core.learning.federated.training import FederatedTrainingRequest, preprocessing_state_set_checksum
from datp_core.populations.catalogue import resolve_population
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import FedAvgProtocol, FedProxProtocol

type GlobalFederatedProtocol = FedAvgProtocol | FedProxProtocol


@dataclass(frozen=True, slots=True)
class TrainFederatedRequest:
    request: FederatedTrainingRequest[GlobalFederatedProtocol]
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TrainDittoRequest:
    request: DittoTrainingRequest
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TrainFederatedStageResult:
    stage: ClassVar[StageOperationId] = StageOperationId.TRAIN_FEDERATED
    publication_status: PublicationStatus
    training: FederatedTrainingResult
    candidates: tuple[CheckpointCandidate, ...]


@dataclass(frozen=True, slots=True)
class TrainDittoStageResult:
    stage: ClassVar[StageOperationId] = StageOperationId.TRAIN_FEDERATED
    publication_status: PublicationStatus
    global_training: FederatedTrainingResult
    global_candidates: tuple[CheckpointCandidate, ...]
    personalized_candidates: ClientCollection[ClientIdentity, tuple[CheckpointCandidate, ...]]


def train_federated_stage(stage_request: TrainFederatedRequest) -> TrainFederatedStageResult:
    request = stage_request.request
    _validate_training_inputs(request.clients, request.autoencoder.widths[0])
    preprocessing_checksum = _compute_checksum(request.clients)

    def write(temporary: Path) -> None:
        temporary_request = replace(request, output_directory=temporary)
        match request.training_protocol:
            case FedAvgProtocol():
                train_fedavg(cast(FederatedTrainingRequest[FedAvgProtocol], temporary_request))
            case FedProxProtocol():
                train_fedprox(cast(FederatedTrainingRequest[FedProxProtocol], temporary_request))

    outcome = publish_atomically(
        target=request.output_directory,
        overwrite=stage_request.overwrite,
        is_reusable=_training_is_reusable,
        write=write,
        reusable_value=lambda _directory: None,
        remove_target=rmtree,
    )
    identity_kind = resolve_population(request.coordinate.population).declaration.identity_kind
    loaded = load_reused_federated_training(
        ReusedFederatedTrainingRequest(
            coordinate=request.coordinate,
            directory=request.output_directory,
            clients=tuple(client.client for client in request.clients),
            checkpoint_protocol=request.checkpoint_protocol,
            identity_kind=identity_kind,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
            preprocessing_state_set_checksum=preprocessing_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
        )
    )
    return TrainFederatedStageResult(
        publication_status=outcome.status,
        training=loaded.training_result,
        candidates=rebase_checkpoint_candidates(loaded.candidates, request.output_directory),
    )


def train_ditto_stage(stage_request: TrainDittoRequest) -> TrainDittoStageResult:
    request = stage_request.request
    _validate_training_inputs(request.clients, request.autoencoder.widths[0])
    preprocessing_checksum = _compute_checksum(request.clients)

    def write(temporary: Path) -> None:
        train_ditto(replace(request, global_output_directory=temporary))

    outcome = publish_atomically(
        target=request.global_output_directory,
        overwrite=stage_request.overwrite,
        is_reusable=_training_is_reusable,
        write=write,
        reusable_value=lambda _directory: None,
        remove_target=rmtree,
    )
    identity_kind = resolve_population(request.global_coordinate.population).declaration.identity_kind
    loaded = load_reused_ditto_training(
        ReusedDittoTrainingRequest(
            global_coordinate=request.global_coordinate,
            personalized_coordinate=request.personalized_coordinate,
            global_directory=request.global_output_directory,
            personalized_directory=request.personalized_output_directory,
            clients=tuple(client.client for client in request.clients),
            checkpoint_protocol=request.checkpoint_protocol,
            identity_kind=identity_kind,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
            preprocessing_state_set_checksum=preprocessing_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
        )
    )
    global_candidates = (
        rebase_checkpoint_candidates(loaded.global_candidates, request.global_output_directory)
        if outcome.status is PublicationStatus.PUBLISHED
        else loaded.global_candidates
    )
    personalized = tuple(
        ClientOwned(
            item.client,
            rebase_checkpoint_candidates(item.candidates, request.personalized_output_directory)
            if outcome.status is PublicationStatus.PUBLISHED
            else item.candidates,
        )
        for item in loaded.personalized_candidates
    )
    return TrainDittoStageResult(
        publication_status=outcome.status,
        global_training=loaded.global_training_result,
        global_candidates=global_candidates,
        personalized_candidates=ClientCollection(personalized),
    )


def _training_is_reusable(directory: Path) -> bool:
    return (directory / FederatedHistoryAssetName.COMPLETE.value).is_file()


def _compute_checksum(clients: tuple[ClientTrainingInput, ...]) -> Checksum:
    return preprocessing_state_set_checksum(
        tuple(
            PreparedClientProvenance(
                client=client.client,
                preprocessing_checksum=client.preprocessing_state.estimator_checksum,
            )
            for client in clients
        )
    )


def _validate_training_inputs(clients: tuple[ClientTrainingInput, ...], autoencoder_width: int) -> None:
    if not clients:
        raise ScientificContractError(
            "federated training requires client inputs",
            subject=ContractSubject.TRAINING,
        )
    feature_names = clients[0].feature_names
    if autoencoder_width != len(feature_names):
        raise ScientificContractError(
            "autoencoder input width must match the transformed feature schema",
            subject=ContractSubject.WIDTHS,
        )
    if any(client.feature_names != feature_names for client in clients):
        raise ScientificContractError(
            "federated clients must share one transformed feature schema",
            subject=ContractSubject.SCHEMA,
        )

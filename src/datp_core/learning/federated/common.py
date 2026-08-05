"""Shared federated training adapters for publication, reuse, and validation."""

from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

from datp_core.datasets.registry import resolve_population
from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum
from datp_core.learning.federated.checkpoints.candidates import rebase_checkpoint_candidates
from datp_core.learning.federated.checkpoints.identities import FederatedHistoryAssetName
from datp_core.learning.federated.checkpoints.reuse import (
    ReusedDittoTrainingRequest,
    ReusedFederatedTrainingRequest,
    load_reused_ditto_training,
    load_reused_federated_training,
)
from datp_core.learning.federated.ditto import DittoTrainingRequest, train_ditto
from datp_core.learning.federated.fedavg import train_fedavg
from datp_core.learning.federated.fedprox import train_fedprox
from datp_core.learning.federated.models import (
    CheckpointCandidate,
    ClientTrainingInput,
    FederatedTrainingResult,
    PersonalizedCandidateSet,
    PreparedClientProvenance,
)
from datp_core.learning.federated.training import FederatedTrainingRequest, preprocessing_state_set_checksum
from datp_core.protocols.models import FedAvgProtocol, FedProxProtocol

type GlobalFederatedProtocol = FedAvgProtocol | FedProxProtocol


@dataclass(frozen=True, slots=True)
class FederatedTrainingArtifacts:
    training: FederatedTrainingResult
    candidates: tuple[CheckpointCandidate, ...]


@dataclass(frozen=True, slots=True)
class DittoTrainingArtifacts:
    global_training: FederatedTrainingResult
    global_candidates: tuple[CheckpointCandidate, ...]
    personalized_candidates: tuple[PersonalizedCandidateSet, ...]


def validate_federated_training_inputs(
    clients: tuple[ClientTrainingInput, ...],
    autoencoder_width: int,
) -> None:
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


def write_federated_training(
    request: FederatedTrainingRequest[GlobalFederatedProtocol],
    directory: Path,
) -> FederatedTrainingArtifacts:
    temporary_request = replace(request, output_directory=directory)
    match temporary_request.training_protocol:
        case FedAvgProtocol():
            outcome = train_fedavg(cast(FederatedTrainingRequest[FedAvgProtocol], temporary_request))
        case FedProxProtocol():
            outcome = train_fedprox(cast(FederatedTrainingRequest[FedProxProtocol], temporary_request))
    return FederatedTrainingArtifacts(outcome.training_result, outcome.candidates)


def federated_training_is_reusable(
    request: FederatedTrainingRequest[GlobalFederatedProtocol],
    directory: Path,
) -> bool:
    del request
    return (directory / FederatedHistoryAssetName.COMPLETE.value).is_file()


def load_reused_federated_artifacts(
    request: FederatedTrainingRequest[GlobalFederatedProtocol],
    directory: Path,
) -> FederatedTrainingArtifacts:
    identity_kind = resolve_population(request.coordinate.population).declaration.identity_kind
    loaded = load_reused_federated_training(
        ReusedFederatedTrainingRequest(
            coordinate=request.coordinate,
            directory=directory,
            clients=tuple(client.client for client in request.clients),
            checkpoint_protocol=request.checkpoint_protocol,
            identity_kind=identity_kind,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
            preprocessing_state_set_checksum=training_preprocessing_checksum(request.clients),
            split_manifest_checksum=request.split_manifest_checksum,
        )
    )
    return FederatedTrainingArtifacts(loaded.training_result, loaded.candidates)


def rebase_federated_training(
    result: FederatedTrainingArtifacts,
    directory: Path,
) -> FederatedTrainingArtifacts:
    return FederatedTrainingArtifacts(
        training=result.training,
        candidates=rebase_checkpoint_candidates(result.candidates, directory),
    )


def write_ditto_training(
    request: DittoTrainingRequest,
    directories: tuple[Path, ...],
) -> DittoTrainingArtifacts:
    global_directory, personalized_directory = ditto_directories(directories)
    outcome = train_ditto(
        replace(
            request,
            global_output_directory=global_directory,
            personalized_output_directory=personalized_directory,
        )
    )
    return DittoTrainingArtifacts(
        global_training=outcome.global_training_result,
        global_candidates=outcome.global_candidates,
        personalized_candidates=outcome.personalized_candidates,
    )


def ditto_training_is_reusable(
    request: DittoTrainingRequest,
    directories: tuple[Path, ...],
) -> bool:
    del request
    global_directory, personalized_directory = ditto_directories(directories)
    return (global_directory / FederatedHistoryAssetName.COMPLETE.value).is_file() and (
        personalized_directory / FederatedHistoryAssetName.COMPLETE.value
    ).is_file()


def load_reused_ditto_artifacts(
    request: DittoTrainingRequest,
    directories: tuple[Path, ...],
) -> DittoTrainingArtifacts:
    global_directory, personalized_directory = ditto_directories(directories)
    identity_kind = resolve_population(request.global_coordinate.population).declaration.identity_kind
    loaded = load_reused_ditto_training(
        ReusedDittoTrainingRequest(
            global_coordinate=request.global_coordinate,
            personalized_coordinate=request.personalized_coordinate,
            global_directory=global_directory,
            personalized_directory=personalized_directory,
            clients=tuple(client.client for client in request.clients),
            checkpoint_protocol=request.checkpoint_protocol,
            identity_kind=identity_kind,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
            preprocessing_state_set_checksum=training_preprocessing_checksum(request.clients),
            split_manifest_checksum=request.split_manifest_checksum,
        )
    )
    return DittoTrainingArtifacts(
        global_training=loaded.global_training_result,
        global_candidates=loaded.global_candidates,
        personalized_candidates=loaded.personalized_candidates,
    )


def rebase_ditto_training(
    result: DittoTrainingArtifacts,
    directories: tuple[Path, ...],
) -> DittoTrainingArtifacts:
    global_directory, personalized_directory = ditto_directories(directories)
    return DittoTrainingArtifacts(
        global_training=result.global_training,
        global_candidates=rebase_checkpoint_candidates(result.global_candidates, global_directory),
        personalized_candidates=tuple(
            PersonalizedCandidateSet(
                client=item.client,
                candidates=rebase_checkpoint_candidates(item.candidates, personalized_directory),
            )
            for item in result.personalized_candidates
        ),
    )


def ditto_directories(directories: tuple[Path, ...]) -> tuple[Path, Path]:
    if len(directories) != 2:
        raise ValueError("Ditto publication requires global and personalized directories")
    return directories[0], directories[1]


def training_preprocessing_checksum(clients: tuple[ClientTrainingInput, ...]) -> Checksum:
    return preprocessing_state_set_checksum(
        tuple(
            PreparedClientProvenance(
                client=client.client,
                preprocessing_checksum=client.preprocessing_state.estimator_checksum,
            )
            for client in clients
        )
    )

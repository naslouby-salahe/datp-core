from dataclasses import dataclass, replace
from pathlib import Path

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import ContractSubject
from datp_core.core.numeric import FeatureCount
from datp_core.data.registry import resolve_population
from datp_core.detector.checkpoints.candidates import rebase_checkpoint_candidates
from datp_core.detector.checkpoints.identities import FederatedHistoryAssetName
from datp_core.detector.checkpoints.reuse import (
    ReusedDittoTrainingRequest,
    ReusedFederatedTrainingRequest,
    load_reused_ditto_training,
    load_reused_federated_training,
)
from datp_core.detector.training.ditto import DittoTrainingRequest, train_ditto
from datp_core.detector.training.engine import FederatedTrainingRequest, preprocessing_state_set_checksum
from datp_core.detector.training.federated import GlobalFederatedProtocol, train_global_federated
from datp_core.detector.training.models import (
    CheckpointCandidate,
    ClientTrainingInput,
    FederatedTrainingResult,
    PersonalizedCandidateSet,
    PreparedClientProvenance,
)


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
    autoencoder_width: FeatureCount,
) -> None:
    if not clients:
        raise ScientificContractError(
            ErrorMessage("federated training requires client inputs"),
            subject=ContractSubject.TRAINING,
        )
    feature_names = clients[0].feature_names
    if autoencoder_width.value != len(feature_names):
        raise ScientificContractError(
            ErrorMessage("autoencoder input width must match the transformed feature schema"),
            subject=ContractSubject.WIDTHS,
        )
    for client in clients[1:]:
        if client.feature_names != feature_names:
            raise ScientificContractError(
                ErrorMessage("federated clients must share one transformed feature schema"),
                subject=ContractSubject.SCHEMA,
            )


def materialize_global_federated_training(
    request: FederatedTrainingRequest[GlobalFederatedProtocol],
    directory: Path,
) -> FederatedTrainingArtifacts:
    outcome = train_global_federated(replace(request, output_directory=directory))
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
    filename = FederatedHistoryAssetName.COMPLETE.value
    return (global_directory / filename).is_file() and (personalized_directory / filename).is_file()


def load_reused_ditto_artifacts(
    request: DittoTrainingRequest,
    directories: tuple[Path, ...],
) -> DittoTrainingArtifacts:
    global_directory, personalized_directory = ditto_directories(directories)
    identity_kind = resolve_population(request.coordinates.global_coordinate.population).declaration.identity_kind
    loaded = load_reused_ditto_training(
        ReusedDittoTrainingRequest(
            coordinates=request.coordinates,
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
            [
                PersonalizedCandidateSet(
                    client=item.client,
                    candidates=rebase_checkpoint_candidates(item.candidates, personalized_directory),
                )
                for item in result.personalized_candidates
            ]
        ),
    )


def ditto_directories(directories: tuple[Path, ...]) -> tuple[Path, Path]:
    if len(directories) != 2:
        raise ValueError("Ditto publication requires global and personalized directories")
    return directories[0], directories[1]


def training_preprocessing_checksum(clients: tuple[ClientTrainingInput, ...]) -> Checksum:
    return preprocessing_state_set_checksum(
        tuple(
            [
                PreparedClientProvenance(
                    client=client.client,
                    preprocessing_checksum=client.preprocessing_state.estimator_checksum,
                )
                for client in clients
            ]
        )
    )

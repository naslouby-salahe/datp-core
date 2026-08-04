"""Trusted reload of completed federated and Ditto training publications."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.domain.enums import ContractSubject, PopulationIdentityKind, TrainingModelId
from datp_core.domain.errors import ArtifactIntegrityError
from datp_core.domain.values import BatchSize, Checksum
from datp_core.learning.federated.checkpoints.candidates import (
    ReusedGlobalCandidatesRequest,
    ReusedPersonalizedCandidatesRequest,
    load_reused_global_candidates,
    load_reused_personalized_candidates,
    validated_global_manifest,
    validated_personalized_manifest,
    verify_completion,
)
from datp_core.learning.federated.checkpoints.history import (
    load_federated_training_history,
    load_published_device_name,
)
from datp_core.learning.federated.models import (
    DittoTrainingOutcome,
    FederatedTrainingCoordinate,
    FederatedTrainingOutcome,
    FederatedTrainingResult,
)
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol


@dataclass(frozen=True, slots=True, kw_only=True)
class ReusedFederatedTrainingRequest:
    coordinate: FederatedTrainingCoordinate
    directory: Path
    clients: tuple[ClientIdentity, ...]
    checkpoint_protocol: CheckpointProtocol
    identity_kind: PopulationIdentityKind
    autoencoder: AutoencoderProtocol
    batch_size: BatchSize
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class ReusedDittoTrainingRequest:
    global_coordinate: FederatedTrainingCoordinate
    personalized_coordinate: FederatedTrainingCoordinate
    global_directory: Path
    personalized_directory: Path
    clients: tuple[ClientIdentity, ...]
    checkpoint_protocol: CheckpointProtocol
    identity_kind: PopulationIdentityKind
    autoencoder: AutoencoderProtocol
    batch_size: BatchSize
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum


def load_reused_federated_training(
    request: ReusedFederatedTrainingRequest,
) -> FederatedTrainingOutcome:
    if request.coordinate.model not in {
        TrainingModelId.FEDAVG_AUTOENCODER,
        TrainingModelId.FEDPROX_AUTOENCODER,
    }:
        raise ArtifactIntegrityError(
            "Ditto reuse requires the typed Ditto reuse request",
            subject=ContractSubject.COORDINATE,
        )
    candidates = load_reused_global_candidates(
        ReusedGlobalCandidatesRequest(
            coordinate=request.coordinate,
            directory=request.directory,
            checkpoint_protocol=request.checkpoint_protocol,
            preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
        )
    )
    history = load_federated_training_history(
        request.coordinate,
        request.directory,
        request.identity_kind,
        clients=request.clients,
        checkpoint_protocol=request.checkpoint_protocol,
    )
    return FederatedTrainingOutcome(
        training_result=FederatedTrainingResult(
            coordinate=request.coordinate,
            autoencoder=request.autoencoder,
            checkpoint_protocol=request.checkpoint_protocol,
            history=history,
            preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
            device_name=load_published_device_name(request.directory),
            batch_size_used=request.batch_size,
        ),
        candidates=candidates,
    )


def load_reused_ditto_training(request: ReusedDittoTrainingRequest) -> DittoTrainingOutcome:
    global_request = ReusedGlobalCandidatesRequest(
        coordinate=request.global_coordinate,
        directory=request.global_directory,
        checkpoint_protocol=request.checkpoint_protocol,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        autoencoder=request.autoencoder,
        batch_size=request.batch_size,
    )
    personalized_request = ReusedPersonalizedCandidatesRequest(
        personalized_coordinate=request.personalized_coordinate,
        personalized_output_directory=request.personalized_directory,
        global_history_directory=request.global_directory,
        clients=request.clients,
        checkpoint_protocol=request.checkpoint_protocol,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        autoencoder=request.autoencoder,
        batch_size=request.batch_size,
    )
    global_manifest = validated_global_manifest(global_request)
    personalized_manifest = validated_personalized_manifest(personalized_request)
    personalized_digest = verify_completion(
        request.personalized_directory,
        personalized_manifest,
        include_history=False,
    )
    if global_manifest.linked_personalized_digest != personalized_digest:
        raise ArtifactIntegrityError(
            "Ditto global publication is linked to a different personalized publication",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    global_candidates = load_reused_global_candidates(global_request)
    personalized_candidates = load_reused_personalized_candidates(personalized_request)
    history = load_federated_training_history(
        request.global_coordinate,
        request.global_directory,
        request.identity_kind,
        clients=request.clients,
        checkpoint_protocol=request.checkpoint_protocol,
        personalized_coordinate=request.personalized_coordinate,
    )
    global_training = FederatedTrainingResult(
        coordinate=request.global_coordinate,
        autoencoder=request.autoencoder,
        checkpoint_protocol=request.checkpoint_protocol,
        history=history,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        device_name=load_published_device_name(request.global_directory),
        batch_size_used=request.batch_size,
    )
    return DittoTrainingOutcome(
        global_training_result=global_training,
        global_candidates=global_candidates,
        personalized_candidates=personalized_candidates,
    )

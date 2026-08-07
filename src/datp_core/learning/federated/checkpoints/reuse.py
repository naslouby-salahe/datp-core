"""Trusted reload of completed federated and Ditto training publications."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import (
    CheckpointStatus,
    ContractSubject,
    PopulationIdentityKind,
    TrainingModelId,
)
from datp_core.domain.errors import ArtifactIntegrityError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import BatchSize, RoundNumber
from datp_core.domain.values.paths import ClientPathToken
from datp_core.domain.values.ratios import MetricValue
from datp_core.learning.federated.checkpoints.candidates import (
    candidate_tensor_name,
)
from datp_core.learning.federated.checkpoints.documents import (
    CandidateManifest,
    CandidateManifestEntry,
)
from datp_core.learning.federated.checkpoints.history import (
    history_frames,
    load_federated_training_history,
    load_published_device_name,
    read_parquet,
    validate_personalized_history,
    validate_round_summary,
)
from datp_core.learning.federated.checkpoints.identities import (
    CandidateManifestKind,
    FederatedHistoryAssetName,
    FederatedHistoryColumn,
)
from datp_core.learning.federated.checkpoints.publication import (
    load_manifest,
    validate_manifest,
    verify_completion,
)
from datp_core.learning.federated.models import (
    CheckpointCandidate,
    DittoTrainingCoordinates,
    DittoTrainingOutcome,
    FederatedTrainingCoordinate,
    FederatedTrainingOutcome,
    FederatedTrainingResult,
    PersonalizedCandidateSet,
)
from datp_core.protocols.checkpoints import CheckpointProtocol, validate_persisted_checkpoint_file
from datp_core.protocols.training import AutoencoderProtocol


@dataclass(frozen=True, slots=True, kw_only=True)
class ReusedGlobalCandidatesRequest:
    coordinate: FederatedTrainingCoordinate
    directory: Path
    checkpoint_protocol: CheckpointProtocol
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    autoencoder: AutoencoderProtocol
    batch_size: BatchSize


@dataclass(frozen=True, slots=True, kw_only=True)
class ReusedPersonalizedCandidatesRequest:
    personalized_coordinate: FederatedTrainingCoordinate
    personalized_output_directory: Path
    global_history_directory: Path
    clients: tuple[ClientIdentity, ...]
    checkpoint_protocol: CheckpointProtocol
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    autoencoder: AutoencoderProtocol
    batch_size: BatchSize


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
    coordinates: DittoTrainingCoordinates
    global_directory: Path
    personalized_directory: Path
    clients: tuple[ClientIdentity, ...]
    checkpoint_protocol: CheckpointProtocol
    identity_kind: PopulationIdentityKind
    autoencoder: AutoencoderProtocol
    batch_size: BatchSize
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum


def validated_global_manifest(
    request: ReusedGlobalCandidatesRequest,
) -> CandidateManifest:
    manifest = load_manifest(request.directory)
    validate_manifest(
        manifest,
        kind=CandidateManifestKind.GLOBAL,
        coordinate=request.coordinate,
        checkpoint_protocol=request.checkpoint_protocol,
        autoencoder=request.autoencoder,
        batch_size=request.batch_size,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
    )
    verify_completion(request.directory, manifest, include_history=True)
    expected_entries = tuple(
        (round_number, None, candidate_tensor_name(round_number))
        for round_number in request.checkpoint_protocol.candidates
    )
    observed_entries = tuple((entry.round_number, entry.client_id, entry.tensor_name) for entry in manifest.entries)
    if observed_entries != expected_entries:
        raise ArtifactIntegrityError(
            "global candidate manifest entries are incomplete, duplicated, or out of order",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    return manifest


def load_reused_global_candidates(
    request: ReusedGlobalCandidatesRequest,
) -> tuple[CheckpointCandidate, ...]:
    manifest = validated_global_manifest(request)
    round_frame, _, _ = history_frames(request.directory)
    expected_rounds = tuple(
        RoundNumber(value)
        for value in range(
            1,
            request.checkpoint_protocol.maximum_round.value + 1,
        )
    )
    validate_round_summary(round_frame, expected_rounds)
    losses_by_round: dict[RoundNumber, MetricValue] = {
        RoundNumber(int(round_number)): MetricValue(float(loss))
        for round_number, loss in round_frame.select(
            (
                FederatedHistoryColumn.ROUND_NUMBER.value,
                FederatedHistoryColumn.AGGREGATE_LOSS.value,
            )
        ).iter_rows()
    }
    return tuple(_global_candidate(request, entry, losses_by_round) for entry in manifest.entries)


def _global_candidate(
    request: ReusedGlobalCandidatesRequest,
    entry: CandidateManifestEntry,
    losses_by_round: dict[RoundNumber, MetricValue],
) -> CheckpointCandidate:
    path = request.directory / entry.tensor_name
    validate_persisted_checkpoint_file(path, entry.tensor_checksum)

    if entry.round_number not in losses_by_round:
        raise ArtifactIntegrityError(
            "global checkpoint requires exactly one matching round loss",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )

    return CheckpointCandidate(
        coordinate=request.coordinate,
        round_number=entry.round_number,
        client=None,
        tensor_path=path,
        tensor_checksum=entry.tensor_checksum,
        mean_training_loss=losses_by_round[entry.round_number],
        status=CheckpointStatus.CANDIDATE,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
    )


def validated_personalized_manifest(
    request: ReusedPersonalizedCandidatesRequest,
) -> CandidateManifest:
    manifest = load_manifest(request.personalized_output_directory)
    validate_manifest(
        manifest,
        kind=CandidateManifestKind.PERSONALIZED,
        coordinate=request.personalized_coordinate,
        checkpoint_protocol=request.checkpoint_protocol,
        autoencoder=request.autoencoder,
        batch_size=request.batch_size,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
    )
    verify_completion(
        request.personalized_output_directory,
        manifest,
        include_history=False,
    )
    expected_entries = tuple(
        (
            round_number,
            ClientPathToken(client.client_id),
            candidate_tensor_name(round_number, client),
        )
        for client in request.clients
        for round_number in request.checkpoint_protocol.candidates
    )
    observed_entries = tuple((entry.round_number, entry.client_id, entry.tensor_name) for entry in manifest.entries)
    if observed_entries != expected_entries:
        raise ArtifactIntegrityError(
            "personalized candidate manifest entries do not match the expected clients and rounds",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    return manifest


def load_reused_personalized_candidates(
    request: ReusedPersonalizedCandidatesRequest,
) -> tuple[PersonalizedCandidateSet, ...]:
    manifest = validated_personalized_manifest(request)
    personalized_frame = read_parquet(
        request.global_history_directory / FederatedHistoryAssetName.PERSONALIZED_ROUNDS.value
    )
    training_rounds = tuple(
        RoundNumber(value)
        for value in range(
            1,
            request.checkpoint_protocol.maximum_round.value + 1,
        )
    )
    validate_personalized_history(
        personalized_frame,
        expected_rounds=training_rounds,
        expected_clients=request.clients,
    )

    losses_by_client_round: dict[tuple[str, RoundNumber], MetricValue] = {
        (str(client_id), RoundNumber(int(round_number))): MetricValue(float(loss))
        for round_number, client_id, loss in personalized_frame.select(
            (
                FederatedHistoryColumn.ROUND_NUMBER.value,
                FederatedHistoryColumn.CLIENT_ID.value,
                FederatedHistoryColumn.LOCAL_LOSS.value,
            )
        ).iter_rows()
    }

    entries_by_client: dict[str, list[CandidateManifestEntry]] = {}
    for entry in manifest.entries:
        if entry.client_id is not None:
            entries_by_client.setdefault(str(entry.client_id), []).append(entry)

    return tuple(
        PersonalizedCandidateSet(
            client=client,
            candidates=tuple(
                _personalized_candidate(request, client, entry, losses_by_client_round)
                for entry in entries_by_client.get(client.client_id, [])
            ),
        )
        for client in request.clients
    )


def _personalized_candidate(
    request: ReusedPersonalizedCandidatesRequest,
    client: ClientIdentity,
    entry: CandidateManifestEntry,
    losses_by_client_round: dict[tuple[str, RoundNumber], MetricValue],
) -> CheckpointCandidate:
    path = request.personalized_output_directory / entry.tensor_name
    validate_persisted_checkpoint_file(path, entry.tensor_checksum)

    key = (client.client_id, entry.round_number)
    if key not in losses_by_client_round:
        raise ArtifactIntegrityError(
            "personalized checkpoint requires exactly one matching client-round loss",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )

    return CheckpointCandidate(
        coordinate=request.personalized_coordinate,
        round_number=entry.round_number,
        client=client,
        tensor_path=path,
        tensor_checksum=entry.tensor_checksum,
        mean_training_loss=losses_by_client_round[key],
        status=CheckpointStatus.CANDIDATE,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
    )


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


def load_reused_ditto_training(
    request: ReusedDittoTrainingRequest,
) -> DittoTrainingOutcome:
    global_request = ReusedGlobalCandidatesRequest(
        coordinate=request.coordinates.global_coordinate,
        directory=request.global_directory,
        checkpoint_protocol=request.checkpoint_protocol,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        autoencoder=request.autoencoder,
        batch_size=request.batch_size,
    )
    personalized_request = ReusedPersonalizedCandidatesRequest(
        personalized_coordinate=request.coordinates.personalized_coordinate,
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
        request.coordinates.global_coordinate,
        request.global_directory,
        request.identity_kind,
        clients=request.clients,
        checkpoint_protocol=request.checkpoint_protocol,
        personalized_coordinate=request.coordinates.personalized_coordinate,
    )
    global_training = FederatedTrainingResult(
        coordinate=request.coordinates.global_coordinate,
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

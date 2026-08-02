"""Genuine Ditto: one global FedAvg-trained model plus persistent per-client personalized models.

Personalized states are regularized toward the global state received at the start of each
round and are never aggregated into the global model. Global and personalized checkpoints
and scores are structurally distinct coordinates.
"""

from dataclasses import dataclass
from pathlib import Path

import torch

from datp_core.domain.enums import ContractSubject, TrainingModelId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    ClientCount,
    LearningRate,
    RoundNumber,
    Seed,
)
from datp_core.learning.autoencoder import (
    AutoencoderState,
    build_reconstruction_autoencoder,
    clone_autoencoder_state,
    clone_state,
)
from datp_core.learning.federated.checkpointing import retain_checkpoint_candidates
from datp_core.learning.federated.models import (
    ClientTrainingInput,
    ClientTrainingResult,
    ClientUpdate,
    DittoTrainingOutcome,
    FederatedRoundResult,
    FederatedTrainingCoordinate,
    FederatedTrainingHistory,
    FederatedTrainingResult,
    GlobalModelStateReference,
    PersonalizedCandidateSet,
    PersonalizedModelStateReference,
    RoundSnapshot,
)
from datp_core.learning.federated.training import (
    PreparedFederatedClientData,
    ProximalTerm,
    TrainingStream,
    aggregate_client_updates,
    compute_weighted_aggregate_loss,
    create_communication_record,
    create_round_snapshot,
    derive_client_stream_seed,
    prepare_federated_client_data,
    preprocessing_state_set_checksum,
    serialize_and_checksum_state_dict,
    train_client_update,
    validate_common_request,
)
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol, DittoProtocol
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.runtime.determinism import configure_deterministic_execution


@dataclass(frozen=True, slots=True)
class DittoTrainingRequest:
    global_coordinate: FederatedTrainingCoordinate
    personalized_coordinate: FederatedTrainingCoordinate
    clients: tuple[ClientTrainingInput, ...]
    population_client_count: ClientCount
    autoencoder: AutoencoderProtocol
    training_protocol: DittoProtocol
    checkpoint_protocol: CheckpointProtocol
    training_seed: Seed
    batch_size: BatchSize
    learning_rate: LearningRate
    split_manifest_checksum: Checksum
    global_output_directory: Path
    personalized_output_directory: Path


def train_ditto(request: DittoTrainingRequest) -> DittoTrainingOutcome:
    _validate_request(request)
    configure_deterministic_execution(request.training_seed)
    device = resolve_cuda_device()

    ordered_clients = tuple(sorted(request.clients, key=lambda item: item.client))
    prepared_clients: list[PreparedFederatedClientData] = [
        prepare_federated_client_data(client_input, request.autoencoder) for client_input in ordered_clients
    ]

    regularization = request.training_protocol.regularization
    global_model = build_reconstruction_autoencoder(request.autoencoder, initialization_seed=request.training_seed)
    global_state = clone_autoencoder_state(global_model)
    global_model.to(device)
    del global_model

    personalized_states: dict[ClientIdentity, AutoencoderState] = {
        client_data.client: clone_state(global_state) for client_data in prepared_clients
    }

    candidate_rounds: set[RoundNumber] = set(request.checkpoint_protocol.candidates)
    rounds: list[FederatedRoundResult] = []
    global_snapshots: list[RoundSnapshot] = []
    personalized_snapshots: dict[ClientIdentity, list[RoundSnapshot]] = {
        client_data.client: [] for client_data in prepared_clients
    }

    for round_index in range(1, request.checkpoint_protocol.maximum_round.value + 1):
        round_number = RoundNumber(round_index)
        reference_state = {name: tensor.to(device) for name, tensor in global_state.items()}
        client_updates: list[ClientUpdate] = []
        client_results: list[ClientTrainingResult] = []
        personalized_references: list[PersonalizedModelStateReference] = []

        for client_index, client_data in enumerate(prepared_clients):
            client = client_data.client
            global_seed = derive_client_stream_seed(
                request.training_seed, round_number, client_index, TrainingStream.GLOBAL_CLIENT_UPDATE
            )
            personalized_seed = derive_client_stream_seed(
                request.training_seed, round_number, client_index, TrainingStream.PERSONALIZED_CLIENT_UPDATE
            )

            update, result = train_client_update(
                client_data=client_data,
                initial_state=reference_state,
                autoencoder=request.autoencoder,
                optimizer_protocol=request.training_protocol.optimizer,
                learning_rate=request.learning_rate,
                batch_size=request.batch_size,
                seed=global_seed,
                device=device,
            )
            client_updates.append(update)
            client_results.append(result)

            personalized_state = clone_state(personalized_states[client])
            personalized_update, _ = train_client_update(
                client_data=client_data,
                initial_state=personalized_state,
                autoencoder=request.autoencoder,
                optimizer_protocol=request.training_protocol.optimizer,
                learning_rate=request.learning_rate,
                batch_size=request.batch_size,
                seed=personalized_seed,
                device=device,
                proximal_term=ProximalTerm(reference_state=reference_state, coefficient=regularization),
            )
            personalized_states[client] = personalized_update.state_dict
            if round_number in candidate_rounds:
                personalized_snapshots[client].append(
                    create_round_snapshot(round_number, personalized_update.state_dict, personalized_update.local_loss)
                )
            personalized_state_checksum, _ = serialize_and_checksum_state_dict(personalized_update.state_dict)
            personalized_references.append(
                PersonalizedModelStateReference(
                    coordinate=request.personalized_coordinate,
                    client=client,
                    round_number=round_number,
                    local_loss=personalized_update.local_loss,
                    state_checksum=personalized_state_checksum,
                    tensor_path=None,
                )
            )

        aggregated = aggregate_client_updates(client_updates)
        global_state = aggregated

        aggregate_loss = compute_weighted_aggregate_loss(client_updates)
        global_state_checksum, single_state_bytes = serialize_and_checksum_state_dict(aggregated)
        communication = create_communication_record(
            round_number, single_state_bytes, len(prepared_clients), len(prepared_clients)
        )

        global_reference = GlobalModelStateReference(
            coordinate=request.global_coordinate,
            round_number=round_number,
            state_checksum=global_state_checksum,
            tensor_path=None,
        )
        rounds.append(
            FederatedRoundResult(
                round_number=round_number,
                client_results=tuple(client_results),
                aggregate_loss=aggregate_loss,
                communication=communication,
                global_state_reference=global_reference,
                personalized_state_references=tuple(personalized_references),
            )
        )

        if round_number in candidate_rounds:
            global_snapshots.append(create_round_snapshot(round_number, aggregated, aggregate_loss))

    history = FederatedTrainingHistory(coordinate=request.global_coordinate, rounds=tuple(rounds))
    preprocessing_checksum = preprocessing_state_set_checksum(
        tuple((client.client, client.preprocessing_checksum) for client in prepared_clients)
    )

    global_candidates = retain_checkpoint_candidates(
        request.global_coordinate,
        tuple(global_snapshots),
        checkpoint_protocol=request.checkpoint_protocol,
        autoencoder=request.autoencoder,
        output_directory=request.global_output_directory,
        preprocessing_state_set_checksum=preprocessing_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        client=None,
        device=device,
    )

    personalized_candidate_sets: list[PersonalizedCandidateSet] = []
    for client_data in prepared_clients:
        client = client_data.client
        candidates = retain_checkpoint_candidates(
            request.personalized_coordinate,
            tuple(personalized_snapshots[client]),
            checkpoint_protocol=request.checkpoint_protocol,
            autoencoder=request.autoencoder,
            output_directory=request.personalized_output_directory,
            preprocessing_state_set_checksum=preprocessing_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
            client=client,
            device=device,
        )
        personalized_candidate_sets.append(PersonalizedCandidateSet(client=client, candidates=candidates))

    global_training_result = FederatedTrainingResult(
        coordinate=request.global_coordinate,
        autoencoder=request.autoencoder,
        checkpoint_protocol=request.checkpoint_protocol,
        history=history,
        preprocessing_state_set_checksum=preprocessing_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        device_name=torch.cuda.get_device_name(device),
        batch_size_used=request.batch_size,
    )
    return DittoTrainingOutcome(
        global_training_result=global_training_result,
        global_candidates=global_candidates,
        personalized_candidates=tuple(personalized_candidate_sets),
    )


def _validate_request(request: DittoTrainingRequest) -> None:
    if request.global_coordinate.model is not TrainingModelId.DITTO_GLOBAL_AUTOENCODER:
        raise ScientificContractError(
            "Ditto global training requires the DITTO_GLOBAL_AUTOENCODER coordinate",
            subject=request.global_coordinate.model,
        )
    if request.personalized_coordinate.model is not TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
        raise ScientificContractError(
            "Ditto personalized training requires the DITTO_PERSONALIZED_AUTOENCODER coordinate",
            subject=request.personalized_coordinate.model,
        )
    if request.training_protocol.kind is not TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
        raise ScientificContractError(
            "Ditto training protocol must declare DITTO_PERSONALIZED_AUTOENCODER",
            subject=request.training_protocol.kind,
        )
    if request.global_coordinate.model_coefficient != request.training_protocol.regularization:
        raise ScientificContractError(
            "Ditto global coordinate regularization must match the training protocol",
            subject=ContractSubject.COORDINATE,
        )
    if request.personalized_coordinate.model_coefficient != request.training_protocol.regularization:
        raise ScientificContractError(
            "Ditto personalized coordinate regularization must match the training protocol",
            subject=ContractSubject.COORDINATE,
        )
    validate_common_request(request.clients, request.population_client_count)

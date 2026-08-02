"""Genuine Ditto: one global FedAvg-trained model plus persistent per-client personalized models.

Personalized states are regularized toward the global state received at the start of each
round and are never aggregated into the global model. Global and personalized checkpoints
and scores are structurally distinct coordinates.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from datp_core.domain.enums import ContractSubject, TrainingModelId, WarningCode
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    ByteCount,
    Checksum,
    ClientCount,
    LearningRate,
    MetricValue,
    ProximalCoefficient,
    RoundNumber,
    Seed,
)
from datp_core.learning.autoencoder import ReconstructionAutoencoder, load_autoencoder_state
from datp_core.learning.federated.checkpointing import RoundSnapshot, retain_checkpoint_candidates
from datp_core.learning.federated.fedavg import FedAvgClientDataset
from datp_core.learning.federated.models import (
    CheckpointCandidate,
    ClientTrainingResult,
    ClientUpdate,
    CommunicationRecord,
    FederatedRoundResult,
    FederatedTrainingCoordinate,
    FederatedTrainingHistory,
    FederatedTrainingResult,
    GlobalModelStateReference,
    PersonalizedModelStateReference,
)
from datp_core.learning.federated.training import (
    ProximalTerm,
    aggregate_client_updates,
    build_client_loader,
    build_optimizer,
    checksum_state_dict,
    client_round_seed,
    extract_feature_arrays,
    preprocessing_state_set_checksum,
    reject_attack_rows_in_federated_training,
    reject_centralized_preprocessing_for_federated_training,
    run_local_epoch,
    serialized_state_dict_bytes,
)
from datp_core.populations.models import PopulationOutcomeLabel
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol, DittoProtocol
from datp_core.protocols.training import OPTIMIZER
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.runtime.determinism import configure_deterministic_execution


@dataclass(frozen=True, slots=True)
class DittoTrainingRequest:
    global_coordinate: FederatedTrainingCoordinate
    personalized_coordinate: FederatedTrainingCoordinate
    clients: tuple[FedAvgClientDataset, ...]
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
    benign_label: PopulationOutcomeLabel = PopulationOutcomeLabel.BENIGN


@dataclass(frozen=True, slots=True)
class DittoTrainingOutcome:
    global_training_result: FederatedTrainingResult
    global_candidates: tuple[CheckpointCandidate, ...]
    personalized_candidates_by_client: dict[str, tuple[CheckpointCandidate, ...]]


def train_ditto(request: DittoTrainingRequest) -> DittoTrainingOutcome:
    """Train the global Ditto model and every client's persistent personalized model."""
    _validate_request(request)
    configure_deterministic_execution(request.training_seed)
    device = resolve_cuda_device()

    ordered_clients = tuple(sorted(request.clients, key=lambda item: item.training_input.client))
    for client_dataset in ordered_clients:
        reject_centralized_preprocessing_for_federated_training(client_dataset.preprocessing_state)

    regularization = request.training_protocol.regularization.value
    global_model = ReconstructionAutoencoder(request.autoencoder.widths).to(device)
    global_state = {name: tensor.detach().clone() for name, tensor in global_model.state_dict().items()}
    personalized_states: dict[str, dict[str, torch.Tensor]] = {
        client.training_input.client.client_id: {name: tensor.detach().clone() for name, tensor in global_state.items()}
        for client in ordered_clients
    }

    candidate_rounds = {candidate.value for candidate in request.checkpoint_protocol.candidates}
    rounds: list[FederatedRoundResult] = []
    global_snapshots: list[RoundSnapshot] = []
    personalized_snapshots: dict[str, list[RoundSnapshot]] = {
        client.training_input.client.client_id: [] for client in ordered_clients
    }

    for round_index in range(1, request.checkpoint_protocol.maximum_round.value + 1):
        round_number = RoundNumber(round_index)
        reference_state = {name: tensor.to(device) for name, tensor in global_state.items()}
        client_updates: list[ClientUpdate] = []
        client_results: list[ClientTrainingResult] = []
        personalized_references: list[PersonalizedModelStateReference] = []

        for client_index, client_dataset in enumerate(ordered_clients):
            client = client_dataset.training_input.client
            matrix, labels, _row_ids = extract_feature_arrays(
                client_dataset.training_input.training_features,
                client_dataset.training_input.feature_names,
            )
            reject_attack_rows_in_federated_training(labels, request.benign_label.value)
            client_seed = client_round_seed(request.training_seed, client_index)

            global_local_model = ReconstructionAutoencoder(request.autoencoder.widths).to(device)
            load_autoencoder_state(
                global_local_model, {name: tensor.clone() for name, tensor in reference_state.items()}
            )
            global_optimizer = build_optimizer(global_local_model, OPTIMIZER, request.learning_rate)
            global_loader = build_client_loader(matrix, batch_size=request.batch_size, seed=client_seed, device=device)
            global_local_state, global_local_loss, sample_count = run_local_epoch(
                global_local_model, global_optimizer, global_loader, device
            )
            client_updates.append(
                ClientUpdate(
                    client=client,
                    state_dict=global_local_state,
                    sample_count=sample_count,
                    local_loss=global_local_loss,
                )
            )
            client_results.append(
                ClientTrainingResult(client=client, sample_count=sample_count, local_loss=global_local_loss)
            )

            personalized_model = ReconstructionAutoencoder(request.autoencoder.widths).to(device)
            load_autoencoder_state(
                personalized_model,
                {name: tensor.to(device) for name, tensor in personalized_states[client.client_id].items()},
            )
            personalized_optimizer = build_optimizer(personalized_model, OPTIMIZER, request.learning_rate)
            personalized_loader = build_client_loader(
                matrix, batch_size=request.batch_size, seed=client_seed, device=device
            )
            personalized_state, _personalized_loss, _personalized_sample_count = run_local_epoch(
                personalized_model,
                personalized_optimizer,
                personalized_loader,
                device,
                proximal_term=ProximalTerm(
                    reference_state=reference_state, coefficient=ProximalCoefficient(regularization)
                ),
            )
            personalized_states[client.client_id] = personalized_state
            if round_index in candidate_rounds:
                personalized_snapshots[client.client_id].append(
                    RoundSnapshot(
                        round_number,
                        {name: tensor.clone() for name, tensor in personalized_state.items()},
                        global_local_loss,
                    )
                )
            personalized_references.append(
                PersonalizedModelStateReference(
                    coordinate=request.personalized_coordinate,
                    client=client,
                    round_number=round_number,
                    state_checksum=checksum_state_dict(personalized_state),
                    tensor_path=None,
                )
            )

        if len(client_updates) != request.population_client_count.value:
            raise ScientificContractError(
                "Ditto requires full participation from every declared population client",
                subject=ContractSubject.CLIENT,
            )

        aggregated = aggregate_client_updates(client_updates)
        global_state = aggregated
        load_autoencoder_state(global_model, {name: tensor.to(device) for name, tensor in aggregated.items()})

        aggregate_loss = MetricValue(float(np.mean([item.local_loss.value for item in client_results])))
        upload_bytes = sum(len(serialized_state_dict_bytes(update.state_dict)) for update in client_updates)
        upload_bytes += sum(
            len(serialized_state_dict_bytes(personalized_states[client_id])) for client_id in personalized_states
        )
        download_bytes = len(serialized_state_dict_bytes(aggregated)) * len(ordered_clients)
        communication = CommunicationRecord(
            round_number=round_number,
            estimated_upload_bytes=ByteCount(upload_bytes),
            estimated_download_bytes=ByteCount(download_bytes),
            estimation_basis=WarningCode.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
        )
        global_reference = GlobalModelStateReference(
            coordinate=request.global_coordinate,
            round_number=round_number,
            state_checksum=checksum_state_dict(aggregated),
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

        if round_index in candidate_rounds:
            global_snapshots.append(
                RoundSnapshot(
                    round_number,
                    {name: tensor.clone() for name, tensor in aggregated.items()},
                    aggregate_loss,
                )
            )

    history = FederatedTrainingHistory(coordinate=request.global_coordinate, rounds=tuple(rounds))
    preprocessing_checksum = preprocessing_state_set_checksum(
        tuple(client.preprocessing_state.estimator_checksum for client in ordered_clients)
    )

    request.global_output_directory.mkdir(parents=True, exist_ok=True)
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

    request.personalized_output_directory.mkdir(parents=True, exist_ok=True)
    personalized_candidates_by_client: dict[str, tuple[CheckpointCandidate, ...]] = {}
    for client_dataset in ordered_clients:
        client = client_dataset.training_input.client
        personalized_candidates_by_client[client.client_id] = retain_checkpoint_candidates(
            request.personalized_coordinate,
            tuple(personalized_snapshots[client.client_id]),
            checkpoint_protocol=request.checkpoint_protocol,
            autoencoder=request.autoencoder,
            output_directory=request.personalized_output_directory,
            preprocessing_state_set_checksum=preprocessing_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
            client=client,
            device=device,
        )

    global_training_result = FederatedTrainingResult(
        coordinate=request.global_coordinate,
        autoencoder_widths=tuple(request.autoencoder.widths),
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
        personalized_candidates_by_client=personalized_candidates_by_client,
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
    if not request.clients:
        raise ScientificContractError(
            "Ditto training requires at least one client dataset",
            subject=ContractSubject.CLIENT,
        )
    client_ids = tuple(item.training_input.client.client_id for item in request.clients)
    if len(set(client_ids)) != len(client_ids):
        raise ScientificContractError(
            "Ditto training cannot receive duplicate client identities",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    if len(request.clients) != request.population_client_count.value:
        raise ScientificContractError(
            "Ditto training requires exactly the declared population client count",
            subject=ContractSubject.CLIENT,
        )
    if request.batch_size < 1:
        raise ScientificContractError(
            "Ditto batch size must remain the declared positive value",
            subject=ContractSubject.BATCH_SIZE,
        )

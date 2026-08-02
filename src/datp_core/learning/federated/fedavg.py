from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from datp_core.domain.enums import CommunicationEstimationMethod, ContractSubject, TrainingModelId
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
from datp_core.learning.autoencoder import (
    ReconstructionAutoencoder,
    build_reconstruction_autoencoder,
    load_autoencoder_state,
)
from datp_core.learning.federated.checkpointing import RoundSnapshot, retain_checkpoint_candidates
from datp_core.learning.federated.models import (
    CheckpointCandidate,
    ClientTrainingInput,
    ClientTrainingResult,
    ClientUpdate,
    CommunicationRecord,
    FederatedRoundResult,
    FederatedTrainingCoordinate,
    FederatedTrainingHistory,
    FederatedTrainingResult,
    GlobalModelStateReference,
)
from datp_core.learning.federated.training import (
    PreparedFederatedClientData,
    ProximalTerm,
    aggregate_client_updates,
    build_client_loader,
    build_optimizer,
    checksum_state_dict,
    client_round_seed,
    prepare_federated_client_data,
    preprocessing_state_set_checksum,
    run_local_epoch,
    serialized_state_dict_bytes,
)
from datp_core.preprocessing.models import FittedPreprocessingState
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol, FedAvgProtocol
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.runtime.determinism import configure_deterministic_execution


@dataclass(frozen=True, slots=True)
class FederatedClientDataset:
    training_input: ClientTrainingInput
    preprocessing_state: FittedPreprocessingState


@dataclass(frozen=True, slots=True)
class FedAvgTrainingRequest:
    coordinate: FederatedTrainingCoordinate
    clients: tuple[FederatedClientDataset, ...]
    population_client_count: ClientCount
    autoencoder: AutoencoderProtocol
    training_protocol: FedAvgProtocol
    checkpoint_protocol: CheckpointProtocol
    training_seed: Seed
    batch_size: BatchSize
    learning_rate: LearningRate
    split_manifest_checksum: Checksum
    output_directory: Path


@dataclass(frozen=True, slots=True)
class FederatedTrainingOutcome:
    training_result: FederatedTrainingResult
    candidates: tuple[CheckpointCandidate, ...]


def train_fedavg(request: FedAvgTrainingRequest) -> FederatedTrainingOutcome:
    """Train the FedAvg core detector to the declared maximum round."""
    validate_federated_training_request(request, TrainingModelId.FEDAVG_AUTOENCODER)
    return _run_federated_training(request, proximal_coefficient=None)


def _run_federated_training(
    request: Any,
    *,
    proximal_coefficient: ProximalCoefficient | None,
) -> FederatedTrainingOutcome:
    configure_deterministic_execution(request.training_seed)
    device = resolve_cuda_device()

    ordered_clients = tuple(sorted(request.clients, key=lambda item: item.training_input.client))
    prepared_clients: list[PreparedFederatedClientData] = [
        prepare_federated_client_data(client_dataset.training_input, client_dataset.preprocessing_state)
        for client_dataset in ordered_clients
    ]

    global_model = build_reconstruction_autoencoder(request.autoencoder, initialization_seed=request.training_seed)
    global_model.to(device)
    global_state = {name: tensor.detach().clone() for name, tensor in global_model.state_dict().items()}

    candidate_rounds = {candidate.value for candidate in request.checkpoint_protocol.candidates}
    rounds: list[FederatedRoundResult] = []
    snapshots: list[RoundSnapshot] = []

    for round_index in range(1, request.checkpoint_protocol.maximum_round.value + 1):
        round_number = RoundNumber(round_index)
        client_updates: list[ClientUpdate] = []
        client_results: list[ClientTrainingResult] = []
        reference_state = {name: tensor.to(device) for name, tensor in global_state.items()}

        for client_index, client_data in enumerate(prepared_clients):
            client_seed = client_round_seed(request.training_seed, round_number, client_index)
            local_model = ReconstructionAutoencoder(request.autoencoder.widths).to(device)
            load_autoencoder_state(local_model, {name: tensor.clone() for name, tensor in reference_state.items()})
            optimizer = build_optimizer(local_model, request.training_protocol.optimizer, request.learning_rate)
            loader = build_client_loader(client_data, batch_size=request.batch_size, seed=client_seed)
            proximal_term = (
                ProximalTerm(reference_state=reference_state, coefficient=proximal_coefficient)
                if proximal_coefficient is not None
                else None
            )
            local_state, local_loss, sample_count = run_local_epoch(
                local_model, optimizer, loader, device, proximal_term=proximal_term
            )
            client = client_data.client
            client_updates.append(
                ClientUpdate(client=client, state_dict=local_state, sample_count=sample_count, local_loss=local_loss)
            )
            client_results.append(ClientTrainingResult(client=client, sample_count=sample_count, local_loss=local_loss))

        if len(client_updates) != request.population_client_count.value:
            raise ScientificContractError(
                "federated training requires full participation from every declared population client",
                subject=ContractSubject.CLIENT,
            )

        aggregated = aggregate_client_updates(client_updates)
        global_state = aggregated
        load_autoencoder_state(global_model, {name: tensor.to(device) for name, tensor in aggregated.items()})

        total_samples = sum(u.sample_count.value for u in client_updates)
        aggregate_loss = MetricValue(
            sum(u.local_loss.value * u.sample_count.value for u in client_updates) / total_samples
        )
        single_state_bytes = len(serialized_state_dict_bytes(aggregated))
        upload_bytes = len(client_updates) * single_state_bytes
        download_bytes = len(ordered_clients) * single_state_bytes

        communication = CommunicationRecord(
            round_number=round_number,
            estimated_upload_bytes=ByteCount(upload_bytes),
            estimated_download_bytes=ByteCount(download_bytes),
            estimation_basis=CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
        )
        global_reference = GlobalModelStateReference(
            coordinate=request.coordinate,
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
                personalized_state_references=(),
            )
        )

        if round_index in candidate_rounds:
            snapshots.append(
                RoundSnapshot(
                    round_number,
                    {name: tensor.clone() for name, tensor in aggregated.items()},
                    aggregate_loss,
                )
            )

    history = FederatedTrainingHistory(coordinate=request.coordinate, rounds=tuple(rounds))
    preprocessing_checksum = preprocessing_state_set_checksum(
        tuple(client.preprocessing_state.estimator_checksum for client in prepared_clients)
    )

    request.output_directory.mkdir(parents=True, exist_ok=True)
    candidates = retain_checkpoint_candidates(
        request.coordinate,
        tuple(snapshots),
        checkpoint_protocol=request.checkpoint_protocol,
        autoencoder=request.autoencoder,
        output_directory=request.output_directory,
        preprocessing_state_set_checksum=preprocessing_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        client=None,
        device=device,
    )

    training_result = FederatedTrainingResult(
        coordinate=request.coordinate,
        autoencoder_widths=tuple(request.autoencoder.widths),
        checkpoint_protocol=request.checkpoint_protocol,
        history=history,
        preprocessing_state_set_checksum=preprocessing_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        device_name=torch.cuda.get_device_name(device),
        batch_size_used=request.batch_size,
    )
    return FederatedTrainingOutcome(training_result=training_result, candidates=candidates)


def validate_federated_training_request(
    request: Any,
    expected_model: TrainingModelId,
) -> None:
    if request.coordinate.model != expected_model:
        raise ScientificContractError(
            f"training requires the {expected_model.name} coordinate",
            subject=request.coordinate.model,
        )
    if request.training_protocol.kind is not expected_model:
        raise ScientificContractError(
            f"training protocol must declare {expected_model}",
            subject=request.training_protocol.kind,
        )
    if not request.clients:
        raise ScientificContractError(
            "training requires at least one client dataset",
            subject=ContractSubject.CLIENT,
        )
    client_ids = tuple(item.training_input.client.client_id for item in request.clients)
    if len(set(client_ids)) != len(client_ids):
        raise ScientificContractError(
            "training cannot receive duplicate client identities",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    if len(request.clients) != request.population_client_count.value:
        raise ScientificContractError(
            "training requires exactly the declared population client count",
            subject=ContractSubject.CLIENT,
        )
    if request.batch_size < 1:
        raise ScientificContractError(
            "batch size must remain the declared positive value",
            subject=ContractSubject.BATCH_SIZE,
        )

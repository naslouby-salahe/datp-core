"""FedProx aggregation-side heterogeneity stress test: proximal term toward the global state.

The primary FedProx coefficient selection rule is unresolved. Every declared positive
coefficient is trained independently and reported; no coefficient is promoted to
"primary" without a declared rule.
"""

from dataclasses import dataclass
from enum import StrEnum
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
from datp_core.learning.federated.fedavg import FedAvgClientDataset, FedAvgTrainingOutcome
from datp_core.learning.federated.models import (
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
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol, FedProxProtocol
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.runtime.determinism import configure_deterministic_execution


class FedProxPrimarySelectionStatus(StrEnum):
    UNRESOLVED_NO_SOURCE_BACKED_RULE = "unresolved_no_source_backed_rule"


@dataclass(frozen=True, slots=True)
class FedProxPrimarySelectionOutcome:
    status: FedProxPrimarySelectionStatus
    declared_coefficients: tuple[ProximalCoefficient, ...]
    detail: str


def fedprox_primary_selection_outcome(
    declared_coefficients: tuple[ProximalCoefficient, ...],
) -> FedProxPrimarySelectionOutcome:
    """Report the FedProx primary-coefficient gap rather than inventing a selection rule."""
    return FedProxPrimarySelectionOutcome(
        status=FedProxPrimarySelectionStatus.UNRESOLVED_NO_SOURCE_BACKED_RULE,
        declared_coefficients=declared_coefficients,
        detail=(
            "the pre-registered non-test rule for selecting one primary FedProx coefficient "
            "on Regime A is not declared in the scientific source of truth; the full grid "
            "remains trained and reportable, but no coefficient is promoted to primary"
        ),
    )


@dataclass(frozen=True, slots=True)
class FedProxTrainingRequest:
    coordinate: FederatedTrainingCoordinate
    clients: tuple[FedAvgClientDataset, ...]
    population_client_count: ClientCount
    autoencoder: AutoencoderProtocol
    training_protocol: FedProxProtocol
    checkpoint_protocol: CheckpointProtocol
    training_seed: Seed
    batch_size: BatchSize
    learning_rate: LearningRate
    split_manifest_checksum: Checksum
    output_directory: Path
    benign_label: PopulationOutcomeLabel = PopulationOutcomeLabel.BENIGN


def train_fedprox(request: FedProxTrainingRequest) -> FedAvgTrainingOutcome:
    """Train one FedProx coefficient's model independently from the FedAvg core."""
    _validate_request(request)
    configure_deterministic_execution(request.training_seed)
    device = resolve_cuda_device()

    ordered_clients = tuple(sorted(request.clients, key=lambda item: item.training_input.client.client_id))
    for client_dataset in ordered_clients:
        reject_centralized_preprocessing_for_federated_training(client_dataset.preprocessing_state)

    coefficient = request.training_protocol.coefficient
    global_model = ReconstructionAutoencoder(request.autoencoder.widths).to(device)
    global_state = {name: tensor.detach().clone() for name, tensor in global_model.state_dict().items()}

    candidate_rounds = {candidate.value for candidate in request.checkpoint_protocol.candidates}
    rounds: list[FederatedRoundResult] = []
    snapshots: list[RoundSnapshot] = []

    for round_index in range(1, request.checkpoint_protocol.maximum_round.value + 1):
        round_number = RoundNumber(round_index)
        client_updates: list[ClientUpdate] = []
        client_results: list[ClientTrainingResult] = []
        reference_state = {name: tensor.to(device) for name, tensor in global_state.items()}

        for client_index, client_dataset in enumerate(ordered_clients):
            matrix, labels, _row_ids = extract_feature_arrays(
                client_dataset.training_input.training_features,
                client_dataset.training_input.feature_names,
            )
            reject_attack_rows_in_federated_training(labels, request.benign_label.value)
            client_seed = client_round_seed(request.training_seed, client_index)
            local_model = ReconstructionAutoencoder(request.autoencoder.widths).to(device)
            load_autoencoder_state(local_model, {name: tensor.clone() for name, tensor in reference_state.items()})
            optimizer = build_optimizer(local_model, request.training_protocol.optimizer, request.learning_rate)
            loader = build_client_loader(matrix, batch_size=request.batch_size, seed=client_seed, device=device)
            local_state, local_loss, sample_count = run_local_epoch(
                local_model,
                optimizer,
                loader,
                device,
                proximal_term=ProximalTerm(reference_state=reference_state, coefficient=coefficient),
            )
            client = client_dataset.training_input.client
            client_updates.append(
                ClientUpdate(client=client, state_dict=local_state, sample_count=sample_count, local_loss=local_loss)
            )
            client_results.append(ClientTrainingResult(client=client, sample_count=sample_count, local_loss=local_loss))

        if len(client_updates) != request.population_client_count.value:
            raise ScientificContractError(
                "FedProx requires full participation from every declared population client",
                subject=ContractSubject.CLIENT,
            )

        aggregated = aggregate_client_updates(client_updates)
        global_state = aggregated
        load_autoencoder_state(global_model, {name: tensor.to(device) for name, tensor in aggregated.items()})

        aggregate_loss = MetricValue(float(np.mean([item.local_loss.value for item in client_results])))
        upload_bytes = sum(len(serialized_state_dict_bytes(update.state_dict)) for update in client_updates)
        download_bytes = len(serialized_state_dict_bytes(aggregated)) * len(ordered_clients)
        communication = CommunicationRecord(
            round_number=round_number,
            estimated_upload_bytes=ByteCount(upload_bytes),
            estimated_download_bytes=ByteCount(download_bytes),
            estimation_basis=WarningCode.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
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
        tuple(client.preprocessing_state.estimator_checksum for client in ordered_clients)
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
    return FedAvgTrainingOutcome(training_result=training_result, candidates=candidates)


def _validate_request(request: FedProxTrainingRequest) -> None:
    if request.coordinate.model is not TrainingModelId.FEDPROX_AUTOENCODER:
        raise ScientificContractError(
            "FedProx training requires the FEDPROX_AUTOENCODER coordinate",
            subject=request.coordinate.model,
        )
    if request.training_protocol.kind is not TrainingModelId.FEDPROX_AUTOENCODER:
        raise ScientificContractError(
            "FedProx training protocol must declare FEDPROX_AUTOENCODER",
            subject=request.training_protocol.kind,
        )
    if request.coordinate.model_coefficient != request.training_protocol.coefficient:
        raise ScientificContractError(
            "FedProx coordinate coefficient must match the training protocol coefficient",
            subject=ContractSubject.COORDINATE,
        )
    if not request.clients:
        raise ScientificContractError(
            "FedProx training requires at least one client dataset",
            subject=ContractSubject.CLIENT,
        )
    client_ids = tuple(item.training_input.client.client_id for item in request.clients)
    if len(set(client_ids)) != len(client_ids):
        raise ScientificContractError(
            "FedProx training cannot receive duplicate client identities",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    if len(request.clients) != request.population_client_count.value:
        raise ScientificContractError(
            "FedProx training requires exactly the declared population client count",
            subject=ContractSubject.CLIENT,
        )
    if request.batch_size.value < 1:
        raise ScientificContractError(
            "FedProx batch size must remain the declared positive value",
            subject=ContractSubject.BATCH_SIZE,
        )

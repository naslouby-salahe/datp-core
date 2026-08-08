from dataclasses import dataclass
from pathlib import Path

import torch

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import ContractSubject, CudaDeviceName, TrainingModelId
from datp_core.core.numeric import BatchSize, ClientCount, LearningRate, RoundNumber, Seed
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.autoencoder import (
    build_reconstruction_autoencoder,
    clone_autoencoder_state,
    clone_state,
)
from datp_core.detector.checkpoints.contracts import CheckpointProtocol
from datp_core.detector.checkpoints.publication import write_ditto_training
from datp_core.detector.training.engine import (
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
from datp_core.detector.training.models import (
    ClientTrainingInput,
    ClientTrainingResult,
    ClientUpdate,
    DittoTrainingCoordinates,
    DittoTrainingOutcome,
    FederatedRoundResult,
    FederatedTrainingHistory,
    FederatedTrainingResult,
    GlobalModelStateReference,
    PersonalizedModelStateReference,
    PersonalizedSnapshotSet,
    PreparedClientProvenance,
    RoundSnapshot,
)
from datp_core.protocols.training import AutoencoderProtocol, DittoProtocol
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.runtime.determinism import configure_deterministic_execution


@dataclass(frozen=True, slots=True)
class DittoTrainingRequest:
    coordinates: DittoTrainingCoordinates
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


def _require_client_entry[T](mapping: dict[ClientIdentity, T], client: ClientIdentity) -> T:
    try:
        return mapping[client]
    except KeyError as err:
        raise ScientificContractError(
            "Ditto personalized state must resolve exactly once per client",
            subject=ContractSubject.CLIENT_IDENTITY,
        ) from err


def _validate_request(request: DittoTrainingRequest) -> None:
    if request.training_protocol.kind is not TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
        raise ScientificContractError(
            "Ditto protocol kind must be DITTO_PERSONALIZED_AUTOENCODER",
            subject=request.training_protocol.kind,
        )
    if request.coordinates.global_coordinate.model_coefficient != request.training_protocol.regularization:
        raise ScientificContractError(
            "Ditto coordinate regularization must match the protocol",
            subject=ContractSubject.COORDINATE,
        )
    if request.training_protocol.local_epochs.value != 1:
        raise ScientificContractError(
            "Ditto requires exactly one local epoch",
            subject=ContractSubject.TRAINING,
        )
    validate_common_request(
        request.coordinates.global_coordinate,
        request.training_seed,
        request.clients,
        request.population_client_count,
    )


def train_ditto(request: DittoTrainingRequest) -> DittoTrainingOutcome:
    _validate_request(request)
    configure_deterministic_execution(request.training_seed)
    device = resolve_cuda_device()

    ordered_inputs = tuple(sorted(request.clients, key=lambda item: item.client))
    prepared = tuple(prepare_federated_client_data(item, request.autoencoder) for item in ordered_inputs)

    provenance = tuple(
        [
            PreparedClientProvenance(
                client=item.client,
                preprocessing_checksum=item.preprocessing_checksum,
            )
            for item in prepared
        ]
    )
    preprocessing_checksum = preprocessing_state_set_checksum(provenance)

    initial_model = build_reconstruction_autoencoder(
        request.autoencoder,
        initialization_seed=request.training_seed,
    )
    global_state = clone_autoencoder_state(initial_model)

    personalized_states = {item.client: clone_state(global_state) for item in prepared}
    personalized_snapshots: dict[ClientIdentity, list[RoundSnapshot]] = {item.client: [] for item in prepared}

    candidate_rounds = frozenset(request.checkpoint_protocol.candidates)
    rounds: list[FederatedRoundResult] = []
    global_snapshots: list[RoundSnapshot] = []

    for round_value in range(1, request.checkpoint_protocol.maximum_round.value + 1):
        round_number = RoundNumber(round_value)
        global_updates: list[ClientUpdate] = []
        personalized_references: list[PersonalizedModelStateReference] = []

        for client_data in prepared:
            client_id = client_data.client
            p_state = _require_client_entry(personalized_states, client_id)

            global_update = train_client_update(
                client_data=client_data,
                initial_state=global_state,
                autoencoder=request.autoencoder,
                optimizer_protocol=request.training_protocol.optimizer,
                learning_rate=request.learning_rate,
                batch_size=request.batch_size,
                seed=derive_client_stream_seed(
                    request.training_seed,
                    round_number,
                    client_id,
                    TrainingStream.GLOBAL_CLIENT_UPDATE,
                ),
                device=device,
            )

            personalized_update = train_client_update(
                client_data=client_data,
                initial_state=p_state,
                autoencoder=request.autoencoder,
                optimizer_protocol=request.training_protocol.optimizer,
                learning_rate=request.learning_rate,
                batch_size=request.batch_size,
                seed=derive_client_stream_seed(
                    request.training_seed,
                    round_number,
                    client_id,
                    TrainingStream.PERSONALIZED_CLIENT_UPDATE,
                ),
                device=device,
                proximal_term=ProximalTerm(
                    reference_state=global_state,
                    coefficient=request.training_protocol.regularization,
                ),
            )

            if personalized_update.sample_count != global_update.sample_count:
                raise ScientificContractError(
                    "Ditto global and personalized updates must process the same client rows",
                    subject=ContractSubject.ROWS,
                )

            global_updates.append(global_update)
            personalized_states[client_id] = personalized_update.state_dict

            personalized_checksum, _, _ = serialize_and_checksum_state_dict(personalized_update.state_dict)
            personalized_references.append(
                PersonalizedModelStateReference(
                    coordinate=request.coordinates.personalized_coordinate,
                    client=client_id,
                    round_number=round_number,
                    local_loss=personalized_update.local_loss,
                    state_checksum=personalized_checksum,
                    tensor_path=None,
                )
            )

            if round_number in candidate_rounds:
                _require_client_entry(personalized_snapshots, client_id).append(
                    create_round_snapshot(
                        round_number,
                        personalized_update.state_dict,
                        personalized_update.local_loss,
                    )
                )

        aggregated = aggregate_client_updates(global_updates)
        aggregate_loss = compute_weighted_aggregate_loss(global_updates)
        global_checksum, state_size, logical_elements = serialize_and_checksum_state_dict(aggregated)

        rounds.append(
            FederatedRoundResult(
                round_number=round_number,
                client_results=tuple(ClientTrainingResult.from_update(update) for update in global_updates),
                aggregate_loss=aggregate_loss,
                communication=create_communication_record(
                    round_number,
                    state_size,
                    logical_elements,
                    upload_count=request.population_client_count,
                    download_count=request.population_client_count,
                ),
                global_state_reference=GlobalModelStateReference(
                    coordinate=request.coordinates.global_coordinate,
                    round_number=round_number,
                    state_checksum=global_checksum,
                    tensor_path=None,
                ),
                personalized_state_references=tuple(personalized_references),
            )
        )
        global_state = aggregated

        if round_number in candidate_rounds:
            global_snapshots.append(create_round_snapshot(round_number, global_state, aggregate_loss))

    global_result = FederatedTrainingResult(
        coordinate=request.coordinates.global_coordinate,
        autoencoder=request.autoencoder,
        checkpoint_protocol=request.checkpoint_protocol,
        history=FederatedTrainingHistory(
            coordinate=request.coordinates.global_coordinate,
            rounds=tuple(rounds),
        ),
        preprocessing_state_set_checksum=preprocessing_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        device_name=CudaDeviceName(torch.cuda.get_device_name(device).strip()),
        batch_size_used=request.batch_size,
    )

    return write_ditto_training(
        global_result=global_result,
        global_snapshots=tuple(global_snapshots),
        personalized_coordinate=request.coordinates.personalized_coordinate,
        personalized_snapshot_sets=tuple(
            [
                PersonalizedSnapshotSet(client=client, snapshots=tuple(snapshots))
                for client, snapshots in personalized_snapshots.items()
            ]
        ),
        global_output_directory=request.global_output_directory,
        personalized_output_directory=request.personalized_output_directory,
    )

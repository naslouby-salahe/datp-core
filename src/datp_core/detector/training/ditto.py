from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from platform import platform
from sys import version
from time import monotonic

import torch

from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import ContractSubject, DeviceName, NonEmptyString, TrainingModelId
from datp_core.core.numeric import BatchSize, ClientCount, ElapsedSeconds, LearningRate, RoundNumber, Seed
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.autoencoder import (
    AutoencoderModelState,
    build_reconstruction_autoencoder,
)
from datp_core.detector.checkpoints.contracts import DiagnosticSnapshotProtocol
from datp_core.detector.checkpoints.publication import write_ditto_training
from datp_core.detector.training.contracts import AutoencoderProtocol, DittoProtocol
from datp_core.detector.training.convergence import ConvergenceMonitor
from datp_core.detector.training.engine import (
    ProximalTerm,
    TrainingStream,
    aggregate_client_updates,
    compute_weighted_aggregate_loss,
    compute_weighted_validation_loss,
    create_communication_record,
    derive_client_stream_seed,
    prepare_federated_client_data,
    serialize_model_state,
    train_client_update,
    validate_common_request,
)
from datp_core.detector.training.models import (
    ClientTrainingInput,
    ClientTrainingResult,
    ClientUpdate,
    DittoRuntimeEnvironment,
    DittoTrainingCoordinates,
    DittoTrainingOutcome,
    FederatedRoundResult,
    FederatedTrainingHistory,
    FederatedTrainingResult,
    GlobalModelStateReference,
    PersonalizedModelStateReference,
    PersonalizedTerminalModel,
    TrainingTerminationReason,
)
from datp_core.runtime.compute import LEARNING_DEVICE
from datp_core.runtime.determinism import configure_deterministic_execution


@dataclass(frozen=True, slots=True)
class DittoTrainingRequest:
    coordinates: DittoTrainingCoordinates
    clients: tuple[ClientTrainingInput, ...]
    population_client_count: ClientCount
    autoencoder: AutoencoderProtocol
    training_protocol: DittoProtocol
    diagnostic_snapshot_protocol: DiagnosticSnapshotProtocol
    training_seed: Seed
    batch_size: BatchSize
    learning_rate: LearningRate
    global_output_directory: Path
    personalized_output_directory: Path
    progress_callback: Callable[[RoundNumber, RoundNumber], None] | None = field(
        default=None,
        compare=False,
        repr=False,
    )


def _require_client_entry[T](mapping: dict[ClientIdentity, T], client: ClientIdentity) -> T:
    try:
        return mapping[client]
    except KeyError as err:
        raise ScientificContractError(
            ErrorMessage("Ditto personalized state must resolve exactly once per client"),
            subject=ContractSubject.CLIENT_IDENTITY,
        ) from err


def _validate_request(request: DittoTrainingRequest) -> None:
    if request.training_protocol.kind is not TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
        raise ScientificContractError(
            ErrorMessage("Ditto protocol kind must be DITTO_PERSONALIZED_AUTOENCODER"),
            subject=request.training_protocol.kind,
        )
    if request.coordinates.global_coordinate.model_coefficient != request.training_protocol.regularization:
        raise ScientificContractError(
            ErrorMessage("Ditto coordinate regularization must match the protocol"),
            subject=ContractSubject.COORDINATE,
        )
    if request.training_protocol.local_epochs.value != 1:
        raise ScientificContractError(
            ErrorMessage("Ditto requires exactly one local epoch"),
            subject=ContractSubject.TRAINING,
        )
    validate_common_request(
        request.coordinates.global_coordinate,
        request.training_seed,
        request.clients,
        request.population_client_count,
    )


def _ditto_runtime_environment() -> DittoRuntimeEnvironment:
    hostname = __import__("socket").gethostname().strip()
    return DittoRuntimeEnvironment(
        host=NonEmptyString(hostname),
        operating_system=NonEmptyString(platform()),
        python_runtime=NonEmptyString(version.replace("\n", " ")),
        torch_runtime=NonEmptyString(torch.__version__),
    )


def train_ditto(request: DittoTrainingRequest) -> DittoTrainingOutcome:
    _validate_request(request)
    configure_deterministic_execution(request.training_seed)
    device = LEARNING_DEVICE
    runtime_environment = _ditto_runtime_environment()

    ordered_inputs = tuple(sorted(request.clients, key=lambda item: item.client))
    prepared = tuple(prepare_federated_client_data(item, request.autoencoder) for item in ordered_inputs)

    initial_model = build_reconstruction_autoencoder(
        request.autoencoder,
        initialization_seed=request.training_seed,
    )
    global_model_state = AutoencoderModelState.from_model(initial_model)
    serialized_global_state_evidence = serialize_model_state(global_model_state)

    personalized_model_states = {item.client: global_model_state for item in prepared}
    convergence = request.diagnostic_snapshot_protocol.convergence
    monitor = ConvergenceMonitor(request.diagnostic_snapshot_protocol) if convergence is not None else None
    rounds: list[FederatedRoundResult] = []

    for round_value in range(1, request.diagnostic_snapshot_protocol.maximum_round.value + 1):
        round_number = RoundNumber(round_value)
        if request.progress_callback is not None:
            request.progress_callback(round_number, request.diagnostic_snapshot_protocol.maximum_round)
        global_updates: list[ClientUpdate] = []
        personalized_references: list[PersonalizedModelStateReference] = []

        for client_data in prepared:
            client_id = client_data.client
            personalized_model_state = _require_client_entry(personalized_model_states, client_id)

            global_update = train_client_update(
                client_data=client_data,
                initial_model_state=global_model_state,
                autoencoder=request.autoencoder,
                optimizer_protocol=request.training_protocol.optimizer,
                learning_rate=request.learning_rate,
                batch_size=request.batch_size,
                local_epochs=request.training_protocol.local_epochs,
                seed=derive_client_stream_seed(
                    request.training_seed,
                    round_number,
                    client_id,
                    TrainingStream.GLOBAL_CLIENT_UPDATE,
                ),
                device=device,
            )

            personalized_started = monotonic()
            personalized_update = train_client_update(
                client_data=client_data,
                initial_model_state=personalized_model_state,
                autoencoder=request.autoencoder,
                optimizer_protocol=request.training_protocol.optimizer,
                learning_rate=request.learning_rate,
                batch_size=request.batch_size,
                local_epochs=request.training_protocol.local_epochs,
                seed=derive_client_stream_seed(
                    request.training_seed,
                    round_number,
                    client_id,
                    TrainingStream.PERSONALIZED_CLIENT_UPDATE,
                ),
                device=device,
                proximal_term=ProximalTerm(
                    reference_model_state=global_model_state,
                    coefficient=request.training_protocol.regularization,
                ),
            )
            personalized_wall_time = ElapsedSeconds(monotonic() - personalized_started)

            if personalized_update.sample_count != global_update.sample_count:
                raise ScientificContractError(
                    ErrorMessage("Ditto global and personalized updates must process the same client rows"),
                    subject=ContractSubject.ROWS,
                )

            global_updates.append(global_update)
            personalized_model_states[client_id] = personalized_update.model_state

            personalized_references.append(
                PersonalizedModelStateReference(
                    coordinate=request.coordinates.personalized_coordinate,
                    client=client_id,
                    round_number=round_number,
                    local_loss=personalized_update.local_loss,
                    personalized_training_wall_time=personalized_wall_time,
                    tensor_path=None,
                )
            )

        aggregated = aggregate_client_updates(global_updates)
        aggregate_loss = compute_weighted_aggregate_loss(global_updates)
        aggregate_validation_loss = (
            compute_weighted_validation_loss(
                model_state=aggregated,
                prepared=prepared,
                autoencoder=request.autoencoder,
                device=device,
            )
            if monitor is not None
            else None
        )
        rounds.append(
            FederatedRoundResult(
                round_number=round_number,
                client_results=tuple(ClientTrainingResult.from_update(update) for update in global_updates),
                aggregate_loss=aggregate_loss,
                communication=create_communication_record(
                    round_number,
                    serialized_global_state_evidence.byte_count,
                    serialized_global_state_evidence.logical_element_count,
                    upload_count=request.population_client_count,
                    download_count=request.population_client_count,
                ),
                global_state_reference=GlobalModelStateReference(
                    coordinate=request.coordinates.global_coordinate,
                    round_number=round_number,
                    tensor_path=None,
                ),
                personalized_state_references=tuple(personalized_references),
                aggregate_validation_loss=aggregate_validation_loss,
            )
        )
        global_model_state = aggregated
        if monitor is not None:
            if aggregate_validation_loss is None:
                raise ScientificContractError(
                    ErrorMessage("convergence requires an aggregate benign validation loss"),
                    subject=ContractSubject.TRAINING,
                )
            monitor.record(aggregate_validation_loss)
            if monitor.should_stop(round_number):
                break

    global_result = FederatedTrainingResult(
        coordinate=request.coordinates.global_coordinate,
        autoencoder=request.autoencoder,
        diagnostic_snapshot_protocol=request.diagnostic_snapshot_protocol,
        history=FederatedTrainingHistory(
            coordinate=request.coordinates.global_coordinate,
            rounds=tuple(rounds),
        ),
        termination_reason=(
            TrainingTerminationReason.CONVERGED
            if monitor is not None and monitor.converged_round is not None
            else (
                TrainingTerminationReason.MAXIMUM_ROUNDS_WITHOUT_CONVERGENCE
                if monitor is not None
                else TrainingTerminationReason.FIXED_ROUND_BUDGET_COMPLETED
            )
        ),
        terminal_model_state=global_model_state.on_cpu_with_contiguous_tensors(),
        device_name=DeviceName("cpu"),
        batch_size_used=request.batch_size,
    )

    return write_ditto_training(
        global_result=global_result,
        personalized_terminal_models=tuple(
            PersonalizedTerminalModel(
                coordinate=request.coordinates.personalized_coordinate,
                client=client,
                model_state=model_state.on_cpu_with_contiguous_tensors(),
                final_round=rounds[-1].round_number,
            )
            for client, model_state in personalized_model_states.items()
        ),
        global_output_directory=request.global_output_directory,
        personalized_output_directory=request.personalized_output_directory,
        runtime_environment=runtime_environment,
    )

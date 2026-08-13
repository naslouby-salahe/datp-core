from pathlib import Path

from datp_core.artifacts.serializers.safetensors import load_state_dict_tensors, save_state_dict_tensors
from datp_core.core.errors import ArtifactIntegrityError, ErrorMessage
from datp_core.core.identifiers import ContractSubject
from datp_core.core.numeric import BatchSize
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.autoencoder import AutoencoderModelState, ReconstructionAutoencoder
from datp_core.detector.checkpoints.contracts import DiagnosticSnapshotProtocol
from datp_core.detector.checkpoints.history import (
    load_federated_training_history,
    load_published_device_name,
    persist_federated_training_history,
)
from datp_core.detector.checkpoints.identities import FederatedHistoryAssetName
from datp_core.detector.training.contracts import AutoencoderProtocol
from datp_core.detector.training.models import (
    DittoRuntimeEnvironment,
    DittoTrainingOutcome,
    FederatedTrainingCoordinate,
    FederatedTrainingExecution,
    FederatedTrainingResult,
    PersonalizedTerminalModel,
    TrainingTerminationReason,
)


def load_federated_training(
    coordinate: FederatedTrainingCoordinate,
    output_directory: Path,
    *,
    clients: tuple[ClientIdentity, ...],
    diagnostic_snapshot_protocol: DiagnosticSnapshotProtocol,
    autoencoder: AutoencoderProtocol,
    batch_size: BatchSize,
) -> FederatedTrainingResult | None:
    if output_directory.is_symlink():
        raise ArtifactIntegrityError(
            ErrorMessage("training publication directory cannot be a symbolic link"),
            subject=ContractSubject.ARTIFACT_PATH,
        )
    terminal_path = output_directory / FederatedHistoryAssetName.TERMINAL_MODEL.value
    if terminal_path.is_symlink():
        raise ArtifactIntegrityError(
            ErrorMessage("persisted terminal model cannot be a symbolic link"),
            subject=ContractSubject.ARTIFACT_PATH,
        )
    if not terminal_path.is_file():
        if output_directory.is_dir() and next(output_directory.iterdir(), None) is not None:
            raise ArtifactIntegrityError(
                ErrorMessage("training publication is incomplete because its terminal model is missing"),
                subject=ContractSubject.ARTIFACT_PATH,
            )
        return None
    ordered_clients = tuple(sorted(clients))
    history = load_federated_training_history(
        coordinate,
        output_directory,
        ordered_clients[0].identity_kind,
        clients=ordered_clients,
        diagnostic_snapshot_protocol=diagnostic_snapshot_protocol,
    )
    device_name = load_published_device_name(output_directory)
    terminal_model_state = AutoencoderModelState.from_torch_state_dict(load_state_dict_tensors(terminal_path, "cpu"))
    _require_matching_architecture(terminal_model_state, autoencoder)
    terminal_round = history.rounds[-1].round_number
    monitor_enabled = diagnostic_snapshot_protocol.convergence is not None
    if not monitor_enabled:
        termination_reason = TrainingTerminationReason.FIXED_ROUND_BUDGET_COMPLETED
    elif terminal_round != diagnostic_snapshot_protocol.maximum_round:
        termination_reason = TrainingTerminationReason.CONVERGED
    else:
        termination_reason = TrainingTerminationReason.MAXIMUM_ROUNDS_WITHOUT_CONVERGENCE
    return FederatedTrainingResult(
        coordinate=coordinate,
        autoencoder=autoencoder,
        diagnostic_snapshot_protocol=diagnostic_snapshot_protocol,
        history=history,
        termination_reason=termination_reason,
        terminal_model_state=terminal_model_state,
        device_name=device_name,
        batch_size_used=batch_size,
    )


def _require_matching_architecture(model_state: AutoencoderModelState, autoencoder: AutoencoderProtocol) -> None:
    probe = ReconstructionAutoencoder(autoencoder.widths)
    try:
        model_state.apply_to(probe)
    except RuntimeError as error:
        raise ArtifactIntegrityError(
            ErrorMessage("persisted terminal model state does not match the declared autoencoder architecture"),
            subject=ContractSubject.ARTIFACT_PATH,
        ) from error


def write_federated_training(
    execution: FederatedTrainingExecution,
    output_directory: Path,
) -> FederatedTrainingResult:
    require_empty_directory(output_directory)
    result = execution.training_result
    persist_federated_training_history(result.history, output_directory, device_name=result.device_name)
    save_state_dict_tensors(
        result.terminal_model_state.to_torch_state_dict(),
        output_directory / FederatedHistoryAssetName.TERMINAL_MODEL.value,
    )
    return result


def write_ditto_training(
    *,
    global_result: FederatedTrainingResult,
    personalized_terminal_models: tuple[PersonalizedTerminalModel, ...],
    global_output_directory: Path,
    personalized_output_directory: Path,
    runtime_environment: DittoRuntimeEnvironment,
) -> DittoTrainingOutcome:
    outcome = DittoTrainingOutcome(
        global_training_result=global_result,
        personalized_terminal_models=personalized_terminal_models,
        runtime_environment=runtime_environment,
    )
    require_separate_directories(global_output_directory, personalized_output_directory)
    require_empty_directory(global_output_directory)
    require_empty_directory(personalized_output_directory)
    persist_federated_training_history(
        global_result.history,
        global_output_directory,
        device_name=global_result.device_name,
    )
    save_state_dict_tensors(
        global_result.terminal_model_state.to_torch_state_dict(),
        global_output_directory / FederatedHistoryAssetName.TERMINAL_MODEL.value,
    )
    for terminal_model in personalized_terminal_models:
        save_state_dict_tensors(
            terminal_model.model_state.to_torch_state_dict(),
            personalized_output_directory / f"terminal_model_{terminal_model.client.client_id.value}.safetensors",
        )
    return outcome


def require_empty_directory(directory: Path) -> None:
    if directory.is_symlink():
        raise ArtifactIntegrityError(
            ErrorMessage("training publication directory cannot be a symbolic link"),
            subject=ContractSubject.ARTIFACT_PATH,
        )
    if directory.exists() and not directory.is_dir():
        raise ArtifactIntegrityError(
            ErrorMessage("training publication destination must be a directory"),
            subject=ContractSubject.ARTIFACT_PATH,
        )
    directory.mkdir(parents=True, exist_ok=True)
    if next(directory.iterdir(), None) is not None:
        raise ArtifactIntegrityError(
            ErrorMessage("training publication directory must be empty"),
            subject=ContractSubject.ARTIFACT_PATH,
        )


def require_separate_directories(left: Path, right: Path) -> None:
    if left.resolve(strict=False) == right.resolve(strict=False):
        raise ArtifactIntegrityError(
            ErrorMessage("Ditto terminal-model publications require separate directories"),
            subject=ContractSubject.ARTIFACT_PATH,
        )

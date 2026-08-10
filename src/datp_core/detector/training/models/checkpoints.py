from dataclasses import dataclass

from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import ContractSubject, CudaDeviceName, TrainingModelId
from datp_core.core.numeric import BatchSize, RoundNumber
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.autoencoder import AutoencoderModelState
from datp_core.detector.checkpoints.contracts import DiagnosticSnapshotProtocol
from datp_core.detector.training.contracts import AutoencoderProtocol, FederatedTrainingCoordinate
from datp_core.detector.training.models.records import FederatedTrainingHistory


@dataclass(frozen=True, slots=True)
class FederatedTrainingResult:
    coordinate: FederatedTrainingCoordinate
    autoencoder: AutoencoderProtocol
    diagnostic_snapshot_protocol: DiagnosticSnapshotProtocol
    history: FederatedTrainingHistory
    terminal_model_state: AutoencoderModelState
    device_name: CudaDeviceName
    batch_size_used: BatchSize

    def __post_init__(self) -> None:
        if self.history.coordinate != self.coordinate:
            raise ScientificContractError(
                ErrorMessage("training result coordinate must match its history"),
                subject=ContractSubject.COORDINATE,
            )
        if not self.device_name.strip():
            raise ScientificContractError(
                ErrorMessage("training result requires a non-empty CUDA device name"),
                subject=ContractSubject.CUDA,
            )
        if self.history.rounds[-1].round_number.value > self.diagnostic_snapshot_protocol.maximum_round.value:
            raise ScientificContractError(
                ErrorMessage("training terminal round cannot exceed the declared maximum"),
                subject=ContractSubject.TRAINING,
            )


@dataclass(frozen=True, slots=True)
class FederatedTrainingExecution:
    training_result: FederatedTrainingResult


@dataclass(frozen=True, slots=True)
class PersonalizedTerminalModel:
    coordinate: FederatedTrainingCoordinate
    client: ClientIdentity
    model_state: AutoencoderModelState
    final_round: RoundNumber

    def __post_init__(self) -> None:
        if self.coordinate.model is not TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            raise ScientificContractError(
                ErrorMessage("personalized terminal models require the Ditto personalized coordinate"),
                subject=ContractSubject.COORDINATE,
            )
        if self.client.population != self.coordinate.population:
            raise ScientificContractError(
                ErrorMessage("personalized terminal model client population must match its coordinate"),
                subject=ContractSubject.CLIENT_IDENTITY,
            )


@dataclass(frozen=True, slots=True)
class DittoTrainingOutcome:
    global_training_result: FederatedTrainingResult
    personalized_terminal_models: tuple[PersonalizedTerminalModel, ...]

    def __post_init__(self) -> None:
        if self.global_training_result.coordinate.model is not TrainingModelId.DITTO_GLOBAL_AUTOENCODER:
            raise ScientificContractError(
                ErrorMessage("Ditto outcome requires a Ditto global training result"),
                subject=ContractSubject.COORDINATE,
            )
        history_clients = tuple(
            result.client for result in self.global_training_result.history.rounds[0].client_results
        )
        terminal_clients = tuple(item.client for item in self.personalized_terminal_models)
        if terminal_clients != history_clients:
            raise ScientificContractError(
                ErrorMessage("Ditto personalized terminal models must match deterministic history client order"),
                subject=ContractSubject.CLIENT,
            )
        final_round = self.global_training_result.history.rounds[-1].round_number
        for terminal_model in self.personalized_terminal_models:
            if not self.global_training_result.coordinate.matches_ditto_peer(terminal_model.coordinate):
                raise ScientificContractError(
                    ErrorMessage("global and personalized terminal models must share one experiment identity"),
                    subject=ContractSubject.COORDINATE,
                )
            if terminal_model.final_round != final_round:
                raise ScientificContractError(
                    ErrorMessage("Ditto terminal models must finish in the same round"),
                    subject=ContractSubject.TRAINING,
                )

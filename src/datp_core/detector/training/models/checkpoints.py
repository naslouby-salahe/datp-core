from dataclasses import dataclass
from pathlib import Path

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import CheckpointStatus, ContractSubject, CudaDeviceName, TrainingModelId
from datp_core.core.numeric import BatchSize, MetricValue, RoundNumber
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.checkpoints.contracts import CheckpointProtocol
from datp_core.detector.training.contracts import AutoencoderProtocol, FederatedTrainingCoordinate
from datp_core.detector.training.models.records import FederatedTrainingHistory
from datp_core.detector.training.models.snapshots import RoundSnapshot


@dataclass(frozen=True, slots=True)
class CheckpointCandidate:
    coordinate: FederatedTrainingCoordinate
    round_number: RoundNumber
    client: ClientIdentity | None
    tensor_path: Path
    tensor_checksum: Checksum
    mean_training_loss: MetricValue
    status: CheckpointStatus
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum

    def __post_init__(self) -> None:
        if self.status not in {
            CheckpointStatus.CANDIDATE,
            CheckpointStatus.STABILITY_EVIDENCE,
            CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
        }:
            raise ScientificContractError(
                ErrorMessage("federated checkpoint candidate has an invalid status"),
                subject=self.status,
            )
        if self.coordinate.model is TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            if self.client is None:
                raise ScientificContractError(
                    ErrorMessage("Ditto personalized checkpoints require a client"),
                    subject=ContractSubject.CLIENT_IDENTITY,
                )
            if self.client.population != self.coordinate.population:
                raise ScientificContractError(
                    ErrorMessage("checkpoint client population must match its coordinate"),
                    subject=ContractSubject.CLIENT_IDENTITY,
                )
        elif self.client is not None:
            raise ScientificContractError(
                ErrorMessage("global checkpoints cannot carry a client identity"),
                subject=ContractSubject.CLIENT_IDENTITY,
            )


@dataclass(frozen=True, slots=True)
class CheckpointDecision:
    coordinate: FederatedTrainingCoordinate
    client: ClientIdentity | None
    selected: CheckpointCandidate
    candidates: tuple[CheckpointCandidate, ...]
    checkpoint_protocol: CheckpointProtocol
    status: CheckpointStatus

    def __post_init__(self) -> None:
        if not self.candidates:
            raise ScientificContractError(
                ErrorMessage("a checkpoint decision requires retained candidates"),
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        if self.status is not CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
            raise ScientificContractError(
                ErrorMessage("checkpoint decision status must be SELECTED_BY_NON_TEST_RULE"),
                subject=self.status,
            )
        if tuple(candidate.round_number for candidate in self.candidates) != tuple(self.checkpoint_protocol.candidates):
            raise ScientificContractError(
                ErrorMessage("checkpoint decision candidates must equal the declared ordered rounds"),
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        if self.selected.round_number != self.checkpoint_protocol.maximum_round:
            raise ScientificContractError(
                ErrorMessage("the selected checkpoint must be the declared maximum round"),
                subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
            )

        reference = self.candidates[0]
        selected_count = 0

        for candidate in self.candidates:
            if candidate.coordinate != self.coordinate:
                raise ScientificContractError(
                    ErrorMessage("every decision candidate must match the decision coordinate"),
                    subject=ContractSubject.COORDINATE,
                )
            if candidate.client != self.client:
                raise ScientificContractError(
                    ErrorMessage("every decision candidate must match the decision client"),
                    subject=ContractSubject.CLIENT_IDENTITY,
                )
            if candidate.preprocessing_state_set_checksum != reference.preprocessing_state_set_checksum:
                raise ScientificContractError(
                    ErrorMessage("decision candidates must share preprocessing provenance"),
                    subject=ContractSubject.PREPROCESSING,
                )
            if candidate.split_manifest_checksum != reference.split_manifest_checksum:
                raise ScientificContractError(
                    ErrorMessage("decision candidates must share split provenance"),
                    subject=ContractSubject.SPLIT,
                )

            if candidate == self.selected:
                if candidate.status is not CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
                    raise ScientificContractError(
                        ErrorMessage("checkpoint decision candidates have inconsistent terminal statuses"),
                        subject=ContractSubject.CHECKPOINT_CANDIDATES,
                    )
                selected_count += 1
            elif candidate.status is not CheckpointStatus.STABILITY_EVIDENCE:
                raise ScientificContractError(
                    ErrorMessage("checkpoint decision candidates have inconsistent terminal statuses"),
                    subject=ContractSubject.CHECKPOINT_CANDIDATES,
                )

        if selected_count != 1:
            raise ScientificContractError(
                ErrorMessage("the selected checkpoint must be the unique selected-status candidate"),
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )


@dataclass(frozen=True, slots=True)
class FederatedTrainingResult:
    coordinate: FederatedTrainingCoordinate
    autoencoder: AutoencoderProtocol
    checkpoint_protocol: CheckpointProtocol
    history: FederatedTrainingHistory
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
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
        final_round = self.history.rounds[-1].round_number
        if final_round != self.checkpoint_protocol.maximum_round:
            raise ScientificContractError(
                ErrorMessage("history terminal round must equal the checkpoint maximum round"),
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        if any(candidate.value > final_round.value for candidate in self.checkpoint_protocol.candidates):
            raise ScientificContractError(
                ErrorMessage("checkpoint candidates cannot exceed the training history"),
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )


@dataclass(frozen=True, slots=True)
class FederatedTrainingExecution:
    training_result: FederatedTrainingResult
    snapshots: tuple[RoundSnapshot, ...]

    def __post_init__(self) -> None:
        if tuple(snapshot.round_number for snapshot in self.snapshots) != tuple(
            self.training_result.checkpoint_protocol.candidates
        ):
            raise ScientificContractError(
                ErrorMessage("training execution snapshots must equal the declared checkpoint rounds"),
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )


@dataclass(frozen=True, slots=True)
class FederatedTrainingOutcome:
    training_result: FederatedTrainingResult
    candidates: tuple[CheckpointCandidate, ...]

    def __post_init__(self) -> None:
        if not self.candidates:
            raise ScientificContractError(
                ErrorMessage("federated training outcome requires candidates"),
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        expected_rounds = tuple(self.training_result.checkpoint_protocol.candidates)
        if tuple(candidate.round_number for candidate in self.candidates) != expected_rounds:
            raise ScientificContractError(
                ErrorMessage("outcome candidate rounds must equal the checkpoint protocol"),
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        if len({candidate.tensor_path for candidate in self.candidates}) != len(self.candidates):
            raise ScientificContractError(
                ErrorMessage("outcome checkpoint paths must be unique"),
                subject=ContractSubject.ARTIFACT_PATH,
            )
        for candidate in self.candidates:
            if candidate.coordinate != self.training_result.coordinate:
                raise ScientificContractError(
                    ErrorMessage("outcome candidates must match the training coordinate"),
                    subject=ContractSubject.COORDINATE,
                )
            if candidate.status is not CheckpointStatus.CANDIDATE:
                raise ScientificContractError(
                    ErrorMessage("training outcomes contain unselected checkpoint candidates"),
                    subject=ContractSubject.CHECKPOINT_CANDIDATES,
                )
            if candidate.preprocessing_state_set_checksum != self.training_result.preprocessing_state_set_checksum:
                raise ScientificContractError(
                    ErrorMessage("candidate preprocessing provenance must match the training result"),
                    subject=ContractSubject.PREPROCESSING,
                )
            if candidate.split_manifest_checksum != self.training_result.split_manifest_checksum:
                raise ScientificContractError(
                    ErrorMessage("candidate split provenance must match the training result"),
                    subject=ContractSubject.SPLIT,
                )


@dataclass(frozen=True, slots=True)
class PersonalizedCandidateSet:
    client: ClientIdentity
    candidates: tuple[CheckpointCandidate, ...]

    def __post_init__(self) -> None:
        if not self.candidates:
            raise ScientificContractError(
                ErrorMessage("a personalized candidate set requires candidates"),
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )

        rounds = [candidate.round_number for candidate in self.candidates]
        if any(rounds[i] >= rounds[i + 1] for i in range(len(rounds) - 1)):
            raise ScientificContractError(
                ErrorMessage("personalized candidate rounds must be unique and ordered"),
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )

        reference = self.candidates[0]
        if reference.coordinate.model is not TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            raise ScientificContractError(
                ErrorMessage("personalized candidate sets require the Ditto personalized coordinate"),
                subject=ContractSubject.COORDINATE,
            )
        for candidate in self.candidates:
            if candidate.coordinate != reference.coordinate:
                raise ScientificContractError(
                    ErrorMessage("personalized candidates must share one coordinate"),
                    subject=ContractSubject.COORDINATE,
                )
            if candidate.client != self.client:
                raise ScientificContractError(
                    ErrorMessage("personalized candidates must belong to the set client"),
                    subject=ContractSubject.CLIENT_IDENTITY,
                )
            if candidate.status is not CheckpointStatus.CANDIDATE:
                raise ScientificContractError(
                    ErrorMessage("personalized training outcomes contain unselected candidates"),
                    subject=ContractSubject.CHECKPOINT_CANDIDATES,
                )
            if candidate.preprocessing_state_set_checksum != reference.preprocessing_state_set_checksum:
                raise ScientificContractError(
                    ErrorMessage("personalized candidates must share preprocessing provenance"),
                    subject=ContractSubject.PREPROCESSING,
                )
            if candidate.split_manifest_checksum != reference.split_manifest_checksum:
                raise ScientificContractError(
                    ErrorMessage("personalized candidates must share split provenance"),
                    subject=ContractSubject.SPLIT,
                )


@dataclass(frozen=True, slots=True)
class DittoTrainingOutcome:
    global_training_result: FederatedTrainingResult
    global_candidates: tuple[CheckpointCandidate, ...]
    personalized_candidates: tuple[PersonalizedCandidateSet, ...]

    def __post_init__(self) -> None:
        if self.global_training_result.coordinate.model is not TrainingModelId.DITTO_GLOBAL_AUTOENCODER:
            raise ScientificContractError(
                ErrorMessage("Ditto outcome requires a Ditto global training result"),
                subject=ContractSubject.COORDINATE,
            )

        FederatedTrainingOutcome(
            training_result=self.global_training_result,
            candidates=self.global_candidates,
        )

        expected_rounds = tuple(self.global_training_result.checkpoint_protocol.candidates)
        history_clients = tuple(
            result.client for result in self.global_training_result.history.rounds[0].client_results
        )
        personalized_clients = tuple(item.client for item in self.personalized_candidates)

        if personalized_clients != history_clients:
            raise ScientificContractError(
                ErrorMessage("Ditto personalized candidate sets must match deterministic history client order"),
                subject=ContractSubject.CLIENT,
            )

        for candidate_set in self.personalized_candidates:
            if tuple(candidate.round_number for candidate in candidate_set.candidates) != expected_rounds:
                raise ScientificContractError(
                    ErrorMessage("global and personalized Ditto candidate rounds must match"),
                    subject=ContractSubject.CHECKPOINT_CANDIDATES,
                )

            ref = candidate_set.candidates[0]
            if not self.global_training_result.coordinate.matches_ditto_peer(ref.coordinate):
                raise ScientificContractError(
                    ErrorMessage("global and personalized Ditto candidates must share one experiment identity"),
                    subject=ContractSubject.COORDINATE,
                )
            if ref.preprocessing_state_set_checksum != self.global_training_result.preprocessing_state_set_checksum:
                raise ScientificContractError(
                    ErrorMessage("global and personalized preprocessing provenance must match"),
                    subject=ContractSubject.PREPROCESSING,
                )
            if ref.split_manifest_checksum != self.global_training_result.split_manifest_checksum:
                raise ScientificContractError(
                    ErrorMessage("global and personalized split provenance must match"),
                    subject=ContractSubject.SPLIT,
                )

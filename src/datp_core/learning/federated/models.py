"""Typed immutable contracts for federated autoencoder training."""

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.domain.enums import (
    CheckpointStatus,
    CommunicationEstimationMethod,
    ContractSubject,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    ByteCount,
    Checksum,
    CudaDeviceName,
    DittoRegularization,
    FeatureNameSequence,
    MetricValue,
    ProximalCoefficient,
    RoundNumber,
    RowCount,
    Seed,
)
from datp_core.learning.autoencoder import AutoencoderState
from datp_core.populations.models import ClientIdentity
from datp_core.preprocessing.models import FederatedFittedPreprocessingState
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol


def validate_client_preprocessing_match(
    client: ClientIdentity,
    preprocessing_state: FederatedFittedPreprocessingState,
    feature_names: FeatureNameSequence,
) -> None:
    state_identity = preprocessing_state.client_identity
    if state_identity.value != client.client_id:
        raise ScientificContractError(
            "preprocessing state client identity token must match the client training input",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    if preprocessing_state.protocol.input_feature_names != feature_names:
        raise ScientificContractError(
            "preprocessing transformed feature schema must match the declared training feature names",
            subject=ContractSubject.SCHEMA,
        )


@dataclass(frozen=True, slots=True, eq=False)
class ClientTrainingInput:
    client: ClientIdentity
    training_features: pl.DataFrame
    feature_names: FeatureNameSequence
    preprocessing_state: FederatedFittedPreprocessingState

    def __post_init__(self) -> None:
        if self.training_features.height < 1:
            raise ScientificContractError(
                "client training input requires at least one benign training row",
                subject=ContractSubject.ROWS,
            )
        validate_client_preprocessing_match(
            self.client,
            self.preprocessing_state,
            self.feature_names,
        )


_GLOBAL_MODELS = frozenset(
    {
        TrainingModelId.FEDAVG_AUTOENCODER,
        TrainingModelId.FEDPROX_AUTOENCODER,
        TrainingModelId.DITTO_GLOBAL_AUTOENCODER,
    }
)


def _require_model_coefficient(
    model: TrainingModelId,
    coefficient: ProximalCoefficient | DittoRegularization | None,
) -> None:
    match model:
        case TrainingModelId.FEDAVG_AUTOENCODER:
            valid = coefficient is None
            message = "FedAvg coordinates carry no model coefficient"
        case TrainingModelId.FEDPROX_AUTOENCODER:
            valid = isinstance(coefficient, ProximalCoefficient)
            message = "FedProx coordinates require a proximal coefficient"
        case TrainingModelId.DITTO_GLOBAL_AUTOENCODER | TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            valid = isinstance(coefficient, DittoRegularization)
            message = "Ditto coordinates require a personalization regularization value"
        case _:
            raise ScientificContractError(
                f"unsupported federated training model {model}",
                subject=ContractSubject.TRAINING,
            )
    if not valid:
        raise ScientificContractError(message, subject=ContractSubject.TRAINING)


@dataclass(frozen=True, slots=True)
class FederatedTrainingCoordinate:
    population: PopulationId
    training_seed: Seed
    split_protocol: SplitProtocolId
    preprocessing_identity: PreprocessingProtocolId
    model: TrainingModelId
    model_coefficient: ProximalCoefficient | DittoRegularization | None

    def __post_init__(self) -> None:
        _require_model_coefficient(self.model, self.model_coefficient)

    def matches_ditto_peer(self, other: "FederatedTrainingCoordinate") -> bool:
        return (
            self.population == other.population
            and self.training_seed == other.training_seed
            and self.split_protocol == other.split_protocol
            and self.preprocessing_identity == other.preprocessing_identity
            and self.model_coefficient == other.model_coefficient
            and {self.model, other.model}
            == {
                TrainingModelId.DITTO_GLOBAL_AUTOENCODER,
                TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
            }
        )


@dataclass(frozen=True, slots=True)
class PreparedClientProvenance:
    client: ClientIdentity
    preprocessing_checksum: Checksum


@dataclass(frozen=True, slots=True)
class ClientUpdate:
    client: ClientIdentity
    state_dict: AutoencoderState
    sample_count: RowCount
    local_loss: MetricValue

    def __post_init__(self) -> None:
        if self.sample_count.value < 1:
            raise ScientificContractError(
                "a client update requires at least one training sample",
                subject=ContractSubject.ROWS,
            )


@dataclass(frozen=True, slots=True)
class ClientTrainingResult:
    client: ClientIdentity
    sample_count: RowCount
    local_loss: MetricValue

    @classmethod
    def from_update(cls, update: ClientUpdate) -> "ClientTrainingResult":
        return cls(
            client=update.client,
            sample_count=update.sample_count,
            local_loss=update.local_loss,
        )


@dataclass(frozen=True, slots=True)
class CommunicationRecord:
    round_number: RoundNumber
    estimated_upload_bytes: ByteCount
    estimated_download_bytes: ByteCount
    estimation_basis: CommunicationEstimationMethod

    def __post_init__(self) -> None:
        if self.estimation_basis is not CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE:
            raise ScientificContractError(
                "communication bytes must remain tagged as serialized-message-size estimates",
                subject=ContractSubject.RUNTIME,
            )


@dataclass(frozen=True, slots=True)
class GlobalModelStateReference:
    coordinate: FederatedTrainingCoordinate
    round_number: RoundNumber
    state_checksum: Checksum
    tensor_path: Path | None

    def __post_init__(self) -> None:
        if self.coordinate.model not in _GLOBAL_MODELS:
            raise ScientificContractError(
                "a global state reference requires a global federated model coordinate",
                subject=ContractSubject.COORDINATE,
            )


@dataclass(frozen=True, slots=True)
class PersonalizedModelStateReference:
    coordinate: FederatedTrainingCoordinate
    client: ClientIdentity
    round_number: RoundNumber
    local_loss: MetricValue
    state_checksum: Checksum
    tensor_path: Path | None

    def __post_init__(self) -> None:
        if self.coordinate.model is not TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            raise ScientificContractError(
                "personalized state references require the Ditto personalized coordinate",
                subject=ContractSubject.COORDINATE,
            )
        if self.client.population != self.coordinate.population:
            raise ScientificContractError(
                "personalized state client population must match its coordinate",
                subject=ContractSubject.CLIENT_IDENTITY,
            )


@dataclass(frozen=True, slots=True)
class FederatedRoundResult:
    round_number: RoundNumber
    client_results: tuple[ClientTrainingResult, ...]
    aggregate_loss: MetricValue
    communication: CommunicationRecord
    global_state_reference: GlobalModelStateReference
    personalized_state_references: tuple[PersonalizedModelStateReference, ...]

    def __post_init__(self) -> None:
        if not self.client_results:
            raise ScientificContractError(
                "a federated round requires at least one client result",
                subject=ContractSubject.CLIENT,
            )
        clients = tuple(result.client for result in self.client_results)
        if len(set(clients)) != len(clients):
            raise ScientificContractError(
                "a federated round cannot contain duplicate client results",
                subject=ContractSubject.CLIENT_IDENTITY,
            )
        if self.communication.round_number != self.round_number:
            raise ScientificContractError(
                "communication round must match the training round",
                subject=ContractSubject.COORDINATE,
            )
        if self.global_state_reference.round_number != self.round_number:
            raise ScientificContractError(
                "global state round must match the training round",
                subject=ContractSubject.COORDINATE,
            )

        coordinate = self.global_state_reference.coordinate
        personalized = self.personalized_state_references
        personalized_clients = tuple(reference.client for reference in personalized)
        if len(set(personalized_clients)) != len(personalized_clients):
            raise ScientificContractError(
                "a federated round cannot contain duplicate personalized references",
                subject=ContractSubject.CLIENT_IDENTITY,
            )

        match coordinate.model:
            case TrainingModelId.DITTO_GLOBAL_AUTOENCODER:
                if set(personalized_clients) != set(clients):
                    raise ScientificContractError(
                        "every Ditto global round requires exactly one personalized reference per client",
                        subject=ContractSubject.CLIENT,
                    )
                for reference in personalized:
                    if reference.round_number != self.round_number:
                        raise ScientificContractError(
                            "personalized state round must match the containing training round",
                            subject=ContractSubject.COORDINATE,
                        )
                    if not coordinate.matches_ditto_peer(reference.coordinate):
                        raise ScientificContractError(
                            "Ditto global and personalized references must share one experiment identity",
                            subject=ContractSubject.COORDINATE,
                        )
            case TrainingModelId.FEDAVG_AUTOENCODER | TrainingModelId.FEDPROX_AUTOENCODER:
                if personalized:
                    raise ScientificContractError(
                        "FedAvg and FedProx rounds cannot carry personalized references",
                        subject=ContractSubject.COORDINATE,
                    )
            case _:
                raise ScientificContractError(
                    "unsupported global model in a federated round",
                    subject=ContractSubject.COORDINATE,
                )


@dataclass(frozen=True, slots=True)
class FederatedTrainingHistory:
    coordinate: FederatedTrainingCoordinate
    rounds: tuple[FederatedRoundResult, ...]

    def __post_init__(self) -> None:
        if not self.rounds:
            raise ScientificContractError(
                "federated training history must contain at least one round",
                subject=ContractSubject.TRAINING,
            )
        observed_rounds = tuple(item.round_number.value for item in self.rounds)
        if observed_rounds != tuple(range(1, len(self.rounds) + 1)):
            raise ScientificContractError(
                "federated history rounds must be consecutive from one",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )

        reference_clients = tuple(item.client for item in self.rounds[0].client_results)
        for item in self.rounds:
            if item.global_state_reference.coordinate != self.coordinate:
                raise ScientificContractError(
                    "every training-history round must use the history coordinate",
                    subject=ContractSubject.COORDINATE,
                )
            current_clients = tuple(result.client for result in item.client_results)
            if current_clients != reference_clients:
                raise ScientificContractError(
                    "every training-history round must preserve deterministic client ordering",
                    subject=ContractSubject.CLIENT,
                )


@dataclass(frozen=True, slots=True)
class RoundSnapshot:
    round_number: RoundNumber
    state_dict: AutoencoderState
    mean_training_loss: MetricValue


@dataclass(frozen=True, slots=True)
class PersonalizedSnapshotSet:
    client: ClientIdentity
    snapshots: tuple[RoundSnapshot, ...]


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
                "federated checkpoint candidate has an invalid status",
                subject=self.status,
            )
        if self.coordinate.model is TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            if self.client is None:
                raise ScientificContractError(
                    "Ditto personalized checkpoints require a client",
                    subject=ContractSubject.CLIENT_IDENTITY,
                )
            if self.client.population != self.coordinate.population:
                raise ScientificContractError(
                    "checkpoint client population must match its coordinate",
                    subject=ContractSubject.CLIENT_IDENTITY,
                )
        elif self.client is not None:
            raise ScientificContractError(
                "global checkpoints cannot carry a client identity",
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
                "a checkpoint decision requires retained candidates",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        if self.status is not CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
            raise ScientificContractError(
                "checkpoint decision status must be SELECTED_BY_NON_TEST_RULE",
                subject=self.status,
            )
        if tuple(candidate.round_number for candidate in self.candidates) != tuple(self.checkpoint_protocol.candidates):
            raise ScientificContractError(
                "checkpoint decision candidates must equal the declared ordered rounds",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )

        reference = self.candidates[0]
        selected_candidates = tuple(
            candidate for candidate in self.candidates if candidate.status is CheckpointStatus.SELECTED_BY_NON_TEST_RULE
        )
        if selected_candidates != (self.selected,):
            raise ScientificContractError(
                "the selected checkpoint must be the unique selected-status candidate",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        if self.selected.round_number != self.checkpoint_protocol.maximum_round:
            raise ScientificContractError(
                "the selected checkpoint must be the declared maximum round",
                subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
            )

        for candidate in self.candidates:
            if candidate.coordinate != self.coordinate:
                raise ScientificContractError(
                    "every decision candidate must match the decision coordinate",
                    subject=ContractSubject.COORDINATE,
                )
            if candidate.client != self.client:
                raise ScientificContractError(
                    "every decision candidate must match the decision client",
                    subject=ContractSubject.CLIENT_IDENTITY,
                )
            if candidate.preprocessing_state_set_checksum != reference.preprocessing_state_set_checksum:
                raise ScientificContractError(
                    "decision candidates must share preprocessing provenance",
                    subject=ContractSubject.PREPROCESSING,
                )
            if candidate.split_manifest_checksum != reference.split_manifest_checksum:
                raise ScientificContractError(
                    "decision candidates must share split provenance",
                    subject=ContractSubject.SPLIT,
                )
            expected_status = (
                CheckpointStatus.SELECTED_BY_NON_TEST_RULE
                if candidate == self.selected
                else CheckpointStatus.STABILITY_EVIDENCE
            )
            if candidate.status is not expected_status:
                raise ScientificContractError(
                    "checkpoint decision candidates have inconsistent terminal statuses",
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
                "training result coordinate must match its history",
                subject=ContractSubject.COORDINATE,
            )
        if not self.device_name.strip():
            raise ScientificContractError(
                "training result requires a non-empty CUDA device name",
                subject=ContractSubject.CUDA,
            )
        final_round = self.history.rounds[-1].round_number
        if final_round != self.checkpoint_protocol.maximum_round:
            raise ScientificContractError(
                "history terminal round must equal the checkpoint maximum round",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        if any(candidate.value > final_round.value for candidate in self.checkpoint_protocol.candidates):
            raise ScientificContractError(
                "checkpoint candidates cannot exceed the training history",
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
                "training execution snapshots must equal the declared checkpoint rounds",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )


@dataclass(frozen=True, slots=True)
class FederatedTrainingOutcome:
    training_result: FederatedTrainingResult
    candidates: tuple[CheckpointCandidate, ...]

    def __post_init__(self) -> None:
        if not self.candidates:
            raise ScientificContractError(
                "federated training outcome requires candidates",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        expected_rounds = tuple(self.training_result.checkpoint_protocol.candidates)
        if tuple(candidate.round_number for candidate in self.candidates) != expected_rounds:
            raise ScientificContractError(
                "outcome candidate rounds must equal the checkpoint protocol",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        paths = tuple(candidate.tensor_path for candidate in self.candidates)
        if len(set(paths)) != len(paths):
            raise ScientificContractError(
                "outcome checkpoint paths must be unique",
                subject=ContractSubject.ARTIFACT_PATH,
            )
        for candidate in self.candidates:
            if candidate.coordinate != self.training_result.coordinate:
                raise ScientificContractError(
                    "outcome candidates must match the training coordinate",
                    subject=ContractSubject.COORDINATE,
                )
            if candidate.status is not CheckpointStatus.CANDIDATE:
                raise ScientificContractError(
                    "training outcomes contain unselected checkpoint candidates",
                    subject=ContractSubject.CHECKPOINT_CANDIDATES,
                )
            if candidate.preprocessing_state_set_checksum != self.training_result.preprocessing_state_set_checksum:
                raise ScientificContractError(
                    "candidate preprocessing provenance must match the training result",
                    subject=ContractSubject.PREPROCESSING,
                )
            if candidate.split_manifest_checksum != self.training_result.split_manifest_checksum:
                raise ScientificContractError(
                    "candidate split provenance must match the training result",
                    subject=ContractSubject.SPLIT,
                )


@dataclass(frozen=True, slots=True)
class PersonalizedCandidateSet:
    client: ClientIdentity
    candidates: tuple[CheckpointCandidate, ...]

    def __post_init__(self) -> None:
        if not self.candidates:
            raise ScientificContractError(
                "a personalized candidate set requires candidates",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        rounds = tuple(candidate.round_number for candidate in self.candidates)
        if rounds != tuple(sorted(set(rounds))):
            raise ScientificContractError(
                "personalized candidate rounds must be unique and ordered",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )

        reference = self.candidates[0]
        if reference.coordinate.model is not TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            raise ScientificContractError(
                "personalized candidate sets require the Ditto personalized coordinate",
                subject=ContractSubject.COORDINATE,
            )
        for candidate in self.candidates:
            if candidate.coordinate != reference.coordinate:
                raise ScientificContractError(
                    "personalized candidates must share one coordinate",
                    subject=ContractSubject.COORDINATE,
                )
            if candidate.client != self.client:
                raise ScientificContractError(
                    "personalized candidates must belong to the set client",
                    subject=ContractSubject.CLIENT_IDENTITY,
                )
            if candidate.status is not CheckpointStatus.CANDIDATE:
                raise ScientificContractError(
                    "personalized training outcomes contain unselected candidates",
                    subject=ContractSubject.CHECKPOINT_CANDIDATES,
                )
            if candidate.preprocessing_state_set_checksum != reference.preprocessing_state_set_checksum:
                raise ScientificContractError(
                    "personalized candidates must share preprocessing provenance",
                    subject=ContractSubject.PREPROCESSING,
                )
            if candidate.split_manifest_checksum != reference.split_manifest_checksum:
                raise ScientificContractError(
                    "personalized candidates must share split provenance",
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
                "Ditto outcome requires a Ditto global training result",
                subject=ContractSubject.COORDINATE,
            )
        global_outcome = FederatedTrainingOutcome(
            training_result=self.global_training_result,
            candidates=self.global_candidates,
        )
        del global_outcome

        expected_rounds = tuple(self.global_training_result.checkpoint_protocol.candidates)
        history_clients = tuple(
            result.client for result in self.global_training_result.history.rounds[0].client_results
        )
        personalized_clients = tuple(item.client for item in self.personalized_candidates)
        if personalized_clients != history_clients:
            raise ScientificContractError(
                "Ditto personalized candidate sets must match deterministic history client order",
                subject=ContractSubject.CLIENT,
            )

        for candidate_set in self.personalized_candidates:
            if tuple(candidate.round_number for candidate in candidate_set.candidates) != expected_rounds:
                raise ScientificContractError(
                    "global and personalized Ditto candidate rounds must match",
                    subject=ContractSubject.CHECKPOINT_CANDIDATES,
                )
            for candidate in candidate_set.candidates:
                if not self.global_training_result.coordinate.matches_ditto_peer(candidate.coordinate):
                    raise ScientificContractError(
                        "global and personalized Ditto candidates must share one experiment identity",
                        subject=ContractSubject.COORDINATE,
                    )
                if (
                    candidate.preprocessing_state_set_checksum
                    != self.global_training_result.preprocessing_state_set_checksum
                ):
                    raise ScientificContractError(
                        "global and personalized preprocessing provenance must match",
                        subject=ContractSubject.PREPROCESSING,
                    )
                if candidate.split_manifest_checksum != self.global_training_result.split_manifest_checksum:
                    raise ScientificContractError(
                        "global and personalized split provenance must match",
                        subject=ContractSubject.SPLIT,
                    )

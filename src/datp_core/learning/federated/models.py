"""Typed, immutable federated learning model contracts."""

from enum import StrEnum
from dataclasses import dataclass
from pathlib import Path

import polars as pl
import torch

from datp_core.domain.enums import (
    CheckpointStatus,
    CommunicationEstimationMethod,
    ContractSubject,
    PopulationId,
    PopulationIdentityKind,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    ByteCount,
    Checksum,
    DittoRegularization,
    FeatureNameSequence,
    MetricValue,
    ProximalCoefficient,
    RoundNumber,
    RowCount,
    Seed,
)
from datp_core.learning.autoencoder import ModelStateMap
from datp_core.populations.models import ClientIdentity
from datp_core.preprocessing.models import FittedPreprocessingState
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol

CANDIDATE_PREFIX: str = "checkpoint_round_"
CANDIDATE_SUFFIX: str = ".safetensors"
PERSONALIZED_INFIX: str = "_client_"


@dataclass(frozen=True, slots=True)
class RoundSnapshot:
    """In-memory candidate-round state prior to persistence."""

    round_number: RoundNumber
    state_dict: ModelStateMap
    mean_training_loss: MetricValue


class FederatedHistoryAssetName(StrEnum):
    ROUND_SUMMARY = "round_summary.parquet"
    CLIENT_ROUNDS = "client_rounds.parquet"
    PERSONALIZED_ROUNDS = "personalized_rounds.parquet"
    DEVICE_NAME = "device_name.txt"
    COMPLETE = "COMPLETE"


class FederatedHistoryColumn(StrEnum):
    ROUND_NUMBER = "round_number"
    AGGREGATE_LOSS = "aggregate_loss"
    UPLOAD_BYTES = "upload_bytes"
    DOWNLOAD_BYTES = "download_bytes"
    GLOBAL_STATE_CHECKSUM = "global_state_checksum"
    CLIENT_ID = "client_id"
    SAMPLE_COUNT = "sample_count"
    LOCAL_LOSS = "local_loss"
    STATE_CHECKSUM = "state_checksum"


def candidate_tensor_name(round_number: RoundNumber, client: ClientIdentity | None = None) -> str:
    base = f"{CANDIDATE_PREFIX}{round_number.value}"
    if client is not None:
        base = f"{base}{PERSONALIZED_INFIX}{client.client_id}"
    return f"{base}{CANDIDATE_SUFFIX}"


def _require_model_coefficient_matches_kind(
    model: TrainingModelId,
    coefficient: ProximalCoefficient | DittoRegularization | None,
) -> None:
    match model:
        case TrainingModelId.FEDAVG_AUTOENCODER:
            if coefficient is not None:
                raise ScientificContractError(
                    "FedAvg coordinates carry no model coefficient",
                    subject=ContractSubject.TRAINING,
                )
        case TrainingModelId.FEDPROX_AUTOENCODER:
            if not isinstance(coefficient, ProximalCoefficient):
                raise ScientificContractError(
                    "FedProx coordinates require a proximal coefficient",
                    subject=ContractSubject.TRAINING,
                )
        case TrainingModelId.DITTO_GLOBAL_AUTOENCODER | TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            if not isinstance(coefficient, DittoRegularization):
                raise ScientificContractError(
                    "Ditto coordinates require a personalization regularization value",
                    subject=ContractSubject.TRAINING,
                )


@dataclass(frozen=True, slots=True)
class FederatedTrainingCoordinate:
    population: PopulationId
    training_seed: Seed
    split_protocol: SplitProtocolId
    preprocessing_identity: PreprocessingProtocolId
    model: TrainingModelId
    model_coefficient: ProximalCoefficient | DittoRegularization | None

    def __post_init__(self) -> None:
        _require_model_coefficient_matches_kind(self.model, self.model_coefficient)


@dataclass(frozen=True, slots=True)
class ClientTrainingInput:
    client: ClientIdentity
    training_features: pl.DataFrame
    feature_names: FeatureNameSequence
    preprocessing_state: FittedPreprocessingState

    def __post_init__(self) -> None:
        if self.training_features.height < 1:
            raise ScientificContractError(
                "client training input requires at least one benign training row",
                subject=ContractSubject.ROWS,
            )
        if self.preprocessing_state.branch is not ProcessedDataBranch.FEDERATED:
            raise ScientificContractError(
                "federated training requires federated preprocessing branch",
                subject=self.preprocessing_state.branch,
            )
        if (
            self.preprocessing_state.client_identity is None
            or self.preprocessing_state.client_identity.value != self.client.client_id
        ):
            raise ScientificContractError(
                "preprocessing state client identity must match client training input",
                subject=ContractSubject.CLIENT_IDENTITY,
            )


@dataclass(frozen=True, slots=True)
class ClientUpdate:
    client: ClientIdentity
    state_dict: dict[str, torch.Tensor]
    sample_count: RowCount
    local_loss: MetricValue

    def __post_init__(self) -> None:
        if self.sample_count < 1:
            raise ScientificContractError(
                "a client update requires at least one training sample",
                subject=ContractSubject.ROWS,
            )


@dataclass(frozen=True, slots=True)
class ClientTrainingResult:
    client: ClientIdentity
    sample_count: RowCount
    local_loss: MetricValue


@dataclass(frozen=True, slots=True)
class CommunicationRecord:
    round_number: RoundNumber
    estimated_upload_bytes: ByteCount
    estimated_download_bytes: ByteCount
    estimation_basis: CommunicationEstimationMethod

    def __post_init__(self) -> None:
        if self.estimation_basis is not CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE:
            raise ScientificContractError(
                "communication bytes must be tagged as a serialized-message-size estimate, "
                "never a measured network cost",
                subject=ContractSubject.RUNTIME,
            )


@dataclass(frozen=True, slots=True)
class GlobalModelStateReference:
    coordinate: FederatedTrainingCoordinate
    round_number: RoundNumber
    state_checksum: Checksum
    tensor_path: Path | None

    def __post_init__(self) -> None:
        if self.coordinate.model is TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            raise ScientificContractError(
                "a personalized-model coordinate cannot be referenced as a global state",
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
                "personalized-model state references require the Ditto personalized coordinate",
                subject=ContractSubject.COORDINATE,
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
        client_ids = tuple(item.client.client_id for item in self.client_results)
        if len(set(client_ids)) != len(client_ids):
            raise ScientificContractError(
                "a federated round cannot report duplicate client results",
                subject=ContractSubject.CLIENT,
            )
        if self.communication.round_number != self.round_number:
            raise ScientificContractError(
                "communication record round number must match the training round",
                subject=ContractSubject.COORDINATE,
            )
        if self.global_state_reference.round_number != self.round_number:
            raise ScientificContractError(
                "global state reference round number must match the training round",
                subject=ContractSubject.COORDINATE,
            )
        personalized_clients = tuple(item.client.client_id for item in self.personalized_state_references)
        if len(set(personalized_clients)) != len(personalized_clients):
            raise ScientificContractError(
                "a federated round cannot report duplicate personalized state references",
                subject=ContractSubject.CLIENT,
            )


@dataclass(frozen=True, slots=True)
class FederatedTrainingHistory:
    coordinate: FederatedTrainingCoordinate
    rounds: tuple[FederatedRoundResult, ...]

    def __post_init__(self) -> None:
        observed = tuple(item.round_number.value for item in self.rounds)
        expected = tuple(range(1, len(observed) + 1))
        if observed != expected:
            raise ScientificContractError(
                "federated training history must record consecutive rounds starting at one",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        for round_result in self.rounds:
            if round_result.global_state_reference.coordinate != self.coordinate:
                raise ScientificContractError(
                    "every round in a training history must share the training coordinate",
                    subject=ContractSubject.COORDINATE,
                )


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
        if self.client is not None and self.coordinate.model is not TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            raise ScientificContractError(
                "only Ditto personalized checkpoints carry a client identity",
                subject=ContractSubject.CLIENT_IDENTITY,
            )
        if self.client is None and self.coordinate.model is TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            raise ScientificContractError(
                "Ditto personalized checkpoints require a client identity",
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
        selected_rounds = {item.round_number for item in self.candidates}
        if self.selected.round_number not in selected_rounds:
            raise ScientificContractError(
                "the selected checkpoint must be one of the retained candidates",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        if self.status is not CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
            raise ScientificContractError(
                "a federated checkpoint decision status must be SELECTED_BY_NON_TEST_RULE",
                subject=self.status,
            )
        if self.selected.round_number != self.checkpoint_protocol.maximum_round:
            raise ScientificContractError(
                "the selected checkpoint must equal the declared maximum round",
                subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
            )
        if self.selected.client != self.client:
            raise ScientificContractError(
                "the selected checkpoint client identity must match the decision client identity",
                subject=ContractSubject.CLIENT_IDENTITY,
            )


@dataclass(frozen=True, slots=True)
class FederatedTrainingResult:
    coordinate: FederatedTrainingCoordinate
    autoencoder: AutoencoderProtocol
    checkpoint_protocol: CheckpointProtocol
    history: FederatedTrainingHistory
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    device_name: str
    batch_size_used: BatchSize

    def __post_init__(self) -> None:
        if self.history.coordinate != self.coordinate:
            raise ScientificContractError(
                "training result coordinate must match its own history coordinate",
                subject=ContractSubject.COORDINATE,
            )


@dataclass(frozen=True, slots=True)
class FederatedTrainingOutcome:
    training_result: FederatedTrainingResult
    candidates: tuple[CheckpointCandidate, ...]


@dataclass(frozen=True, slots=True)
class PersonalizedCandidateSet:
    client: ClientIdentity
    candidates: tuple[CheckpointCandidate, ...]


@dataclass(frozen=True, slots=True)
class DittoTrainingOutcome:
    global_training_result: FederatedTrainingResult
    global_candidates: tuple[CheckpointCandidate, ...]
    personalized_candidates: tuple[PersonalizedCandidateSet, ...]

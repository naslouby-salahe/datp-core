"""Typed, immutable federated learning model contracts."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl
import torch

from datp_core.domain.enums import (
    CheckpointStatus,
    CommunicationEstimationMethod,
    ContractSubject,
    PopulationId,
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
from datp_core.learning.autoencoder import AutoencoderState
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
    state_dict: AutoencoderState
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


_ROUND_SUMMARY_DTYPE: Mapping[str, type[pl.DataType]] = {
    FederatedHistoryColumn.ROUND_NUMBER.value: pl.Int64,
    FederatedHistoryColumn.AGGREGATE_LOSS.value: pl.Float64,
    FederatedHistoryColumn.UPLOAD_BYTES.value: pl.Int64,
    FederatedHistoryColumn.DOWNLOAD_BYTES.value: pl.Int64,
    FederatedHistoryColumn.GLOBAL_STATE_CHECKSUM.value: pl.String,
}

_CLIENT_ROUNDS_DTYPE: Mapping[str, type[pl.DataType]] = {
    FederatedHistoryColumn.ROUND_NUMBER.value: pl.Int64,
    FederatedHistoryColumn.CLIENT_ID.value: pl.String,
    FederatedHistoryColumn.SAMPLE_COUNT.value: pl.Int64,
    FederatedHistoryColumn.LOCAL_LOSS.value: pl.Float64,
}

_PERSONALIZED_ROUNDS_DTYPE: Mapping[str, type[pl.DataType]] = {
    FederatedHistoryColumn.ROUND_NUMBER.value: pl.Int64,
    FederatedHistoryColumn.CLIENT_ID.value: pl.String,
    FederatedHistoryColumn.LOCAL_LOSS.value: pl.Float64,
    FederatedHistoryColumn.STATE_CHECKSUM.value: pl.String,
}


ROUND_SUMMARY_SCHEMA: Mapping[str, type[pl.DataType]] = _ROUND_SUMMARY_DTYPE
CLIENT_ROUNDS_SCHEMA: Mapping[str, type[pl.DataType]] = _CLIENT_ROUNDS_DTYPE
PERSONALIZED_ROUNDS_SCHEMA: Mapping[str, type[pl.DataType]] = _PERSONALIZED_ROUNDS_DTYPE


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
        personalized_client_ids = tuple(item.client.client_id for item in self.personalized_state_references)
        if len(set(personalized_client_ids)) != len(personalized_client_ids):
            raise ScientificContractError(
                "a federated round cannot report duplicate personalized state references",
                subject=ContractSubject.CLIENT,
            )
        if self.personalized_state_references:
            if self.global_state_reference.coordinate.model is TrainingModelId.DITTO_GLOBAL_AUTOENCODER:
                if set(personalized_client_ids) != set(client_ids):
                    raise ScientificContractError(
                        "Ditto personalized references must cover exactly the round client set",
                        subject=ContractSubject.CLIENT,
                    )
            elif self.global_state_reference.coordinate.model is not TrainingModelId.DITTO_GLOBAL_AUTOENCODER:
                raise ScientificContractError(
                    "non-Ditto rounds must not carry personalized state references",
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
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        observed = tuple(item.round_number.value for item in self.rounds)
        expected = tuple(range(1, len(observed) + 1))
        if observed != expected:
            raise ScientificContractError(
                "federated training history must record consecutive rounds starting at one",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        reference_client_ids = frozenset(
            item.client.client_id for item in self.rounds[0].client_results
        )
        for round_result in self.rounds:
            if round_result.global_state_reference.coordinate != self.coordinate:
                raise ScientificContractError(
                    "every round in a training history must share the training coordinate",
                    subject=ContractSubject.COORDINATE,
                )
            current_client_ids = frozenset(
                item.client.client_id for item in round_result.client_results
            )
            if current_client_ids != reference_client_ids:
                raise ScientificContractError(
                    "every round must contain the same client identity set",
                    subject=ContractSubject.CLIENT,
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
        if self.selected not in self.candidates:
            raise ScientificContractError(
                "the selected checkpoint must be exactly one of the retained candidates",
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
        self._validate_candidate_set_invariants()

    def _validate_candidate_set_invariants(self) -> None:
        reference = self.candidates[0]
        selected_count = 0
        for candidate in self.candidates:
            if candidate.coordinate != reference.coordinate:
                raise ScientificContractError(
                    "all checkpoint candidates must share the same coordinate",
                    subject=ContractSubject.COORDINATE,
                )
            if candidate.client != self.client:
                raise ScientificContractError(
                    "all checkpoint candidates must share the same client identity",
                    subject=ContractSubject.CLIENT_IDENTITY,
                )
            if candidate.preprocessing_state_set_checksum != reference.preprocessing_state_set_checksum:
                raise ScientificContractError(
                    "all checkpoint candidates must share the same preprocessing checksum",
                    subject=ContractSubject.PREPROCESSING,
                )
            if candidate.split_manifest_checksum != reference.split_manifest_checksum:
                raise ScientificContractError(
                    "all checkpoint candidates must share the same split manifest checksum",
                    subject=ContractSubject.SPLIT,
                )
            if candidate.status is CheckpointStatus.CANDIDATE:
                raise ScientificContractError(
                    "retained checkpoint candidates must have their terminal status assigned",
                    subject=ContractSubject.CHECKPOINT_CANDIDATES,
                )
            if candidate.status is CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
                selected_count += 1
        if selected_count != 1:
            raise ScientificContractError(
                "exactly one candidate must have SELECTED_BY_NON_TEST_RULE status",
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

    def __post_init__(self) -> None:
        if not self.candidates:
            raise ScientificContractError(
                "a personalized candidate set requires at least one candidate",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        rounds = tuple(c.round_number for c in self.candidates)
        if len(set(rounds)) != len(rounds):
            raise ScientificContractError(
                "personalized candidate rounds must be unique",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        if rounds != tuple(sorted(rounds)):
            raise ScientificContractError(
                "personalized candidate rounds must be strictly ordered",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        reference = self.candidates[0]
        for candidate in self.candidates:
            if candidate.client != self.client:
                raise ScientificContractError(
                    "every personalized candidate must belong to the declared client",
                    subject=ContractSubject.CLIENT_IDENTITY,
                )
            if candidate.preprocessing_state_set_checksum != reference.preprocessing_state_set_checksum:
                raise ScientificContractError(
                    "personalized candidates must share preprocessing checksums",
                    subject=ContractSubject.PREPROCESSING,
                )
            if candidate.split_manifest_checksum != reference.split_manifest_checksum:
                raise ScientificContractError(
                    "personalized candidates must share split manifest checksums",
                    subject=ContractSubject.SPLIT,
                )


@dataclass(frozen=True, slots=True)
class DittoTrainingOutcome:
    global_training_result: FederatedTrainingResult
    global_candidates: tuple[CheckpointCandidate, ...]
    personalized_candidates: tuple[PersonalizedCandidateSet, ...]

    def __post_init__(self) -> None:
        if not self.personalized_candidates:
            raise ScientificContractError(
                "Ditto training requires at least one personalized candidate set",
                subject=ContractSubject.CLIENT,
            )
        client_ids = tuple(pcs.client.client_id for pcs in self.personalized_candidates)
        if len(set(client_ids)) != len(client_ids):
            raise ScientificContractError(
                "Ditto personalized client identities must be unique",
                subject=ContractSubject.CLIENT_IDENTITY,
            )
        self._validate_ditto_candidate_coordinates()

    def _validate_ditto_candidate_coordinates(self) -> None:
        for candidate in self.global_candidates:
            if candidate.coordinate.model is not TrainingModelId.DITTO_GLOBAL_AUTOENCODER:
                raise ScientificContractError(
                    "global Ditto candidates must use the DITTO_GLOBAL_AUTOENCODER coordinate",
                    subject=ContractSubject.COORDINATE,
                )
        if not self.global_candidates:
            return
        global_ref = self.global_candidates[0]
        for pcs in self.personalized_candidates:
            for candidate in pcs.candidates:
                self._validate_single_personalized_candidate(candidate, global_ref)

    @staticmethod
    def _validate_single_personalized_candidate(
        candidate: "CheckpointCandidate", global_ref: "CheckpointCandidate"
    ) -> None:
        if candidate.coordinate.model is not TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            raise ScientificContractError(
                "personalized Ditto candidates must use DITTO_PERSONALIZED_AUTOENCODER",
                subject=ContractSubject.COORDINATE,
            )
        if candidate.preprocessing_state_set_checksum != global_ref.preprocessing_state_set_checksum:
            raise ScientificContractError(
                "global and personalized preprocessing checksums must match",
                subject=ContractSubject.PREPROCESSING,
            )
        if candidate.split_manifest_checksum != global_ref.split_manifest_checksum:
            raise ScientificContractError(
                "global and personalized split manifest checksums must match",
                subject=ContractSubject.SPLIT,
            )

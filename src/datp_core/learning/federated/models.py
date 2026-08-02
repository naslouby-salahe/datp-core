from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
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
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
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
    checksum_file,
    checksum_text,
)
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import CheckpointProtocol


ROUND_SUMMARY_SCHEMA: Mapping[str, type[pl.DataType]] = {
    "round_number": pl.Int64,
    "aggregate_loss": pl.Float64,
    "upload_bytes": pl.Int64,
    "download_bytes": pl.Int64,
    "global_state_checksum": pl.String,
}

CLIENT_ROUNDS_SCHEMA: Mapping[str, type[pl.DataType]] = {
    "round_number": pl.Int64,
    "client_id": pl.String,
    "sample_count": pl.Int64,
    "local_loss": pl.Float64,
}

PERSONALIZED_ROUNDS_SCHEMA: Mapping[str, type[pl.DataType]] = {
    "round_number": pl.Int64,
    "client_id": pl.String,
    "local_loss": pl.Float64,
    "state_checksum": pl.String,
}


def _validate_schema(frame: pl.DataFrame, expected_schema: Mapping[str, type[pl.DataType]]) -> None:
    for col, dtype in expected_schema.items():
        if col not in frame.columns:
            raise ArtifactIntegrityError(
                f"Parquet table missing required column '{col}'",
                subject=ContractSubject.SCHEMA,
            )
        if frame.schema[col] != dtype:
            raise ArtifactIntegrityError(
                f"Parquet column '{col}' has type {frame.schema[col]}, expected {dtype}",
                subject=ContractSubject.SCHEMA,
            )


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

    def __post_init__(self) -> None:
        if self.training_features.height < 1:
            raise ScientificContractError(
                "client training input requires at least one benign training row",
                subject=ContractSubject.ROWS,
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
        selected_rounds = {item.round_number.value for item in self.candidates}
        if self.selected.round_number.value not in selected_rounds:
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
    autoencoder_widths: tuple[int, ...]
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


class FederatedCheckpointAssetName(StrEnum):
    CANDIDATE_PREFIX = "checkpoint_round_"
    CANDIDATE_SUFFIX = ".safetensors"
    PERSONALIZED_INFIX = "_client_"


class FederatedHistoryAssetName(StrEnum):
    ROUND_SUMMARY = "round_summary.parquet"
    CLIENT_ROUNDS = "client_rounds.parquet"
    PERSONALIZED_ROUNDS = "personalized_rounds.parquet"
    DEVICE_NAME = "device_name.txt"
    COMPLETE = "COMPLETE"


def candidate_tensor_name(round_number: RoundNumber, client: ClientIdentity | None = None) -> str:
    base = f"{FederatedCheckpointAssetName.CANDIDATE_PREFIX}{round_number.value}"
    if client is not None:
        base = f"{base}{FederatedCheckpointAssetName.PERSONALIZED_INFIX}{client.client_id}"
    return f"{base}{FederatedCheckpointAssetName.CANDIDATE_SUFFIX}"


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


def persist_federated_training_history(
    history: FederatedTrainingHistory,
    directory: Path,
    *,
    device_name: str,
) -> None:
    if not device_name:
        raise ArtifactIntegrityError(
            "training publication requires a non-empty device name",
            subject=ContractSubject.CUDA,
        )
    directory.mkdir(parents=True, exist_ok=True)
    (directory / FederatedHistoryAssetName.DEVICE_NAME).write_text(device_name, encoding="utf-8")
    
    round_rows = [
        {
            "round_number": r.round_number.value,
            "aggregate_loss": r.aggregate_loss.value,
            "upload_bytes": r.communication.estimated_upload_bytes.value,
            "download_bytes": r.communication.estimated_download_bytes.value,
            "global_state_checksum": r.global_state_reference.state_checksum.value,
        }
        for r in history.rounds
    ]
    client_rows = [
        {
            "round_number": r.round_number.value,
            "client_id": cr.client.client_id,
            "sample_count": cr.sample_count.value,
            "local_loss": cr.local_loss.value,
        }
        for r in history.rounds
        for cr in r.client_results
    ]
    personalized_rows = [
        {
            "round_number": r.round_number.value,
            "client_id": pr.client.client_id,
            "local_loss": pr.local_loss.value,
            "state_checksum": pr.state_checksum.value,
        }
        for r in history.rounds
        for pr in r.personalized_state_references
    ]

    pl.DataFrame(round_rows, schema=ROUND_SUMMARY_SCHEMA).write_parquet(
        directory / FederatedHistoryAssetName.ROUND_SUMMARY
    )
    pl.DataFrame(client_rows, schema=CLIENT_ROUNDS_SCHEMA).write_parquet(
        directory / FederatedHistoryAssetName.CLIENT_ROUNDS
    )
    if personalized_rows:
        pl.DataFrame(personalized_rows, schema=PERSONALIZED_ROUNDS_SCHEMA).write_parquet(
            directory / FederatedHistoryAssetName.PERSONALIZED_ROUNDS
        )


def load_federated_training_history(
    coordinate: FederatedTrainingCoordinate,
    directory: Path,
    identity_kind: PopulationIdentityKind,
) -> FederatedTrainingHistory:
    column = FederatedHistoryColumn
    round_summary_path = directory / FederatedHistoryAssetName.ROUND_SUMMARY
    client_rounds_path = directory / FederatedHistoryAssetName.CLIENT_ROUNDS
    if not round_summary_path.is_file() or not client_rounds_path.is_file():
        raise ArtifactIntegrityError("history parquet file missing", subject=ContractSubject.ARTIFACT_PATH)
    
    round_frame = pl.read_parquet(round_summary_path).sort(column.ROUND_NUMBER.value)
    _validate_schema(round_frame, ROUND_SUMMARY_SCHEMA)
    client_frame = pl.read_parquet(client_rounds_path)
    _validate_schema(client_frame, CLIENT_ROUNDS_SCHEMA)
    
    personalized_path = directory / FederatedHistoryAssetName.PERSONALIZED_ROUNDS
    personalized_frame = None
    if personalized_path.is_file():
        personalized_frame = pl.read_parquet(personalized_path)
        _validate_schema(personalized_frame, PERSONALIZED_ROUNDS_SCHEMA)

    rounds: list[FederatedRoundResult] = []
    for round_row in round_frame.iter_rows(named=True):
        round_number = RoundNumber(int(round_row[column.ROUND_NUMBER.value]))
        client_rows = client_frame.filter(pl.col(column.ROUND_NUMBER.value) == round_row[column.ROUND_NUMBER.value])
        client_results = tuple(
            ClientTrainingResult(
                client=ClientIdentity(coordinate.population, str(row[column.CLIENT_ID.value]), identity_kind),
                sample_count=RowCount(int(row[column.SAMPLE_COUNT.value])),
                local_loss=MetricValue(float(row[column.LOCAL_LOSS.value])),
            )
            for row in client_rows.iter_rows(named=True)
        )
        personalized_references: tuple[PersonalizedModelStateReference, ...] = ()
        if personalized_frame is not None:
            rows = personalized_frame.filter(pl.col(column.ROUND_NUMBER.value) == round_row[column.ROUND_NUMBER.value])
            personalized_references = tuple(
                PersonalizedModelStateReference(
                    coordinate=coordinate,
                    client=ClientIdentity(coordinate.population, str(row[column.CLIENT_ID.value]), identity_kind),
                    round_number=round_number,
                    local_loss=MetricValue(float(row[column.LOCAL_LOSS.value])),
                    state_checksum=Checksum(str(row[column.STATE_CHECKSUM.value])),
                    tensor_path=None,
                )
                for row in rows.iter_rows(named=True)
            )
        communication = CommunicationRecord(
            round_number=round_number,
            estimated_upload_bytes=ByteCount(int(round_row[column.UPLOAD_BYTES.value])),
            estimated_download_bytes=ByteCount(int(round_row[column.DOWNLOAD_BYTES.value])),
            estimation_basis=CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
        )
        global_reference = GlobalModelStateReference(
            coordinate=coordinate,
            round_number=round_number,
            state_checksum=Checksum(str(round_row[column.GLOBAL_STATE_CHECKSUM.value])),
            tensor_path=None,
        )
        rounds.append(
            FederatedRoundResult(
                round_number=round_number,
                client_results=client_results,
                aggregate_loss=MetricValue(float(round_row[column.AGGREGATE_LOSS.value])),
                communication=communication,
                global_state_reference=global_reference,
                personalized_state_references=personalized_references,
            )
        )
    return FederatedTrainingHistory(coordinate=coordinate, rounds=tuple(rounds))


def training_complete_digest(candidates: tuple[CheckpointCandidate, ...]) -> Checksum:
    set_payload = "|".join(
        f"{item.round_number.value}:{item.tensor_checksum.value}:{item.status.value}" for item in candidates
    )
    return checksum_text(f"{checksum_text(set_payload).value}|{len(candidates)}")


def federated_training_directory_is_reusable(directory: Path, candidate_rounds: tuple[RoundNumber, ...]) -> bool:
    complete = directory / FederatedHistoryAssetName.COMPLETE
    round_summary = directory / FederatedHistoryAssetName.ROUND_SUMMARY
    client_rounds = directory / FederatedHistoryAssetName.CLIENT_ROUNDS
    device_name = directory / FederatedHistoryAssetName.DEVICE_NAME
    if not all(path.is_file() for path in (complete, round_summary, client_rounds, device_name)):
        return False
    if not device_name.read_text(encoding="utf-8").strip():
        return False
    try:
        round_frame = pl.read_parquet(round_summary)
        _validate_schema(round_frame, ROUND_SUMMARY_SCHEMA)
        client_frame = pl.read_parquet(client_rounds)
        _validate_schema(client_frame, CLIENT_ROUNDS_SCHEMA)
    except Exception:
        return False
    return all((directory / candidate_tensor_name(round_number)).is_file() for round_number in candidate_rounds)


def load_published_device_name(directory: Path) -> str:
    device_path = directory / FederatedHistoryAssetName.DEVICE_NAME
    if not device_path.is_file():
        raise ArtifactIntegrityError(
            "reused federated training is missing the published device name",
            subject=ContractSubject.CUDA,
        )
    device_name = device_path.read_text(encoding="utf-8").strip()
    if not device_name:
        raise ArtifactIntegrityError(
            "reused federated training device name is empty",
            subject=ContractSubject.CUDA,
        )
    return device_name


@dataclass(frozen=True, slots=True)
class ReusedGlobalCandidatesRequest:
    coordinate: FederatedTrainingCoordinate
    directory: Path
    checkpoint_protocol: CheckpointProtocol
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum


@dataclass(frozen=True, slots=True)
class ReusedPersonalizedCandidatesRequest:
    personalized_coordinate: FederatedTrainingCoordinate
    personalized_output_directory: Path
    global_history_directory: Path
    clients: tuple[ClientIdentity, ...]
    checkpoint_protocol: CheckpointProtocol
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum


@dataclass(frozen=True, slots=True)
class ReusedFederatedTrainingRequest:
    coordinate: FederatedTrainingCoordinate
    directory: Path
    checkpoint_protocol: CheckpointProtocol
    identity_kind: PopulationIdentityKind
    autoencoder_widths: tuple[int, ...]
    batch_size: BatchSize
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum


def load_reused_global_candidates(request: ReusedGlobalCandidatesRequest) -> tuple[CheckpointCandidate, ...]:
    column = FederatedHistoryColumn
    round_summary_path = request.directory / FederatedHistoryAssetName.ROUND_SUMMARY
    if not round_summary_path.is_file():
        raise ArtifactIntegrityError(
            "reused global candidates missing history summary",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    round_frame = pl.read_parquet(round_summary_path)
    _validate_schema(round_frame, ROUND_SUMMARY_SCHEMA)
    loss_by_round = {
        int(row[column.ROUND_NUMBER.value]): MetricValue(float(row[column.AGGREGATE_LOSS.value]))
        for row in round_frame.iter_rows(named=True)
    }
    candidates: list[CheckpointCandidate] = []
    for candidate_round in request.checkpoint_protocol.candidates:
        path = request.directory / candidate_tensor_name(candidate_round)
        if not path.is_file():
            raise ArtifactIntegrityError("reused checkpoint candidate missing", subject=ContractSubject.ARTIFACT_PATH)
        candidates.append(
            CheckpointCandidate(
                coordinate=request.coordinate,
                round_number=candidate_round,
                client=None,
                tensor_path=path,
                tensor_checksum=checksum_file(path),
                mean_training_loss=loss_by_round[candidate_round.value],
                status=CheckpointStatus.CANDIDATE,
                preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
                split_manifest_checksum=request.split_manifest_checksum,
            )
        )
    return tuple(candidates)


def load_reused_personalized_candidates(
    request: ReusedPersonalizedCandidatesRequest,
) -> dict[ClientIdentity, tuple[CheckpointCandidate, ...]]:
    personalized_rounds_path = request.global_history_directory / FederatedHistoryAssetName.PERSONALIZED_ROUNDS
    if not personalized_rounds_path.is_file():
        raise ArtifactIntegrityError(
            "reused personalized candidates require published personalized round losses",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    personalized_frame = pl.read_parquet(personalized_rounds_path)
    _validate_schema(personalized_frame, PERSONALIZED_ROUNDS_SCHEMA)
    result: dict[ClientIdentity, tuple[CheckpointCandidate, ...]] = {}
    for client in request.clients:
        candidates: list[CheckpointCandidate] = []
        for candidate_round in request.checkpoint_protocol.candidates:
            path = request.personalized_output_directory / candidate_tensor_name(candidate_round, client)
            if not path.is_file():
                raise ArtifactIntegrityError(
                    "reused personalized checkpoint candidate missing",
                    subject=ContractSubject.ARTIFACT_PATH,
                )
            loss_rows = personalized_frame.filter(
                (pl.col("round_number") == candidate_round.value) & (pl.col("client_id") == client.client_id)
            )
            if loss_rows.height != 1:
                raise ArtifactIntegrityError(
                    "reused personalized candidate is missing its published local loss",
                    subject=ContractSubject.TRAINING,
                )
            local_loss = MetricValue(float(loss_rows.item(0, "local_loss")))
            candidates.append(
                CheckpointCandidate(
                    coordinate=request.personalized_coordinate,
                    round_number=candidate_round,
                    client=client,
                    tensor_path=path,
                    tensor_checksum=checksum_file(path),
                    mean_training_loss=local_loss,
                    status=CheckpointStatus.CANDIDATE,
                    preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
                    split_manifest_checksum=request.split_manifest_checksum,
                )
            )
        result[client] = tuple(candidates)
    return result


def rebase_checkpoint_candidates(
    candidates: tuple[CheckpointCandidate, ...],
    directory: Path,
    *,
    client: ClientIdentity | None,
) -> tuple[CheckpointCandidate, ...]:
    rebased: list[CheckpointCandidate] = []
    for candidate in candidates:
        path = directory / candidate_tensor_name(candidate.round_number, client)
        rebased.append(
            replace(
                candidate,
                tensor_path=path,
                tensor_checksum=checksum_file(path),
            )
        )
    return tuple(rebased)


def load_reused_federated_training(
    request: ReusedFederatedTrainingRequest,
) -> tuple[FederatedTrainingResult, tuple[CheckpointCandidate, ...]]:
    history = load_federated_training_history(request.coordinate, request.directory, request.identity_kind)
    candidates = load_reused_global_candidates(
        ReusedGlobalCandidatesRequest(
            coordinate=request.coordinate,
            directory=request.directory,
            checkpoint_protocol=request.checkpoint_protocol,
            preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
        )
    )
    training_result = FederatedTrainingResult(
        coordinate=request.coordinate,
        autoencoder_widths=request.autoencoder_widths,
        checkpoint_protocol=request.checkpoint_protocol,
        history=history,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        device_name=load_published_device_name(request.directory),
        batch_size_used=request.batch_size,
    )
    return training_result, candidates

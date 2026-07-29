"""Stage: dispatch federated training across FedAvg, FedProx, and genuine Ditto."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from shutil import rmtree

import polars as pl

from datp_core.artifacts.store import AtomicPublication, publish_atomically
from datp_core.domain.enums import ContractSubject, PublicationStatus, StageOperationId
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    ClientCount,
    LearningRate,
    MetricValue,
    RoundNumber,
    RowCount,
    Seed,
    checksum_file,
    checksum_text,
)
from datp_core.learning.federated.checkpointing import (
    CheckpointCandidate,
    candidate_set_checksum,
    candidate_tensor_name,
)
from datp_core.learning.federated.ditto import DittoTrainingOutcome, DittoTrainingRequest, train_ditto
from datp_core.learning.federated.fedavg import (
    FedAvgClientDataset,
    FedAvgTrainingOutcome,
    FedAvgTrainingRequest,
    train_fedavg,
)
from datp_core.learning.federated.fedprox import FedProxTrainingRequest, train_fedprox
from datp_core.learning.federated.models import (
    ClientTrainingInput,
    ClientTrainingResult,
    CommunicationRecord,
    FederatedRoundResult,
    FederatedTrainingCoordinate,
    FederatedTrainingHistory,
    FederatedTrainingResult,
    GlobalModelStateReference,
    PersonalizedModelStateReference,
)
from datp_core.learning.federated.training import preprocessing_state_set_checksum
from datp_core.orchestration.stages.preprocess_federated import ClientPreprocessPublication
from datp_core.populations.catalogue import resolve_population
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import (
    AutoencoderProtocol,
    CheckpointProtocol,
    DittoProtocol,
    FedAvgProtocol,
    FedProxProtocol,
)


class FederatedHistoryAssetName(StrEnum):
    ROUND_SUMMARY = "round_summary.parquet"
    CLIENT_ROUNDS = "client_rounds.parquet"
    PERSONALIZED_ROUNDS = "personalized_rounds.parquet"
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


@dataclass
class _OutcomeBox[OutcomeT]:
    """A single-slot mutable box for an `AtomicPublication.write` closure to populate."""

    outcome: OutcomeT | None = None


@dataclass(frozen=True, slots=True)
class TrainFedAvgRequest:
    coordinate: FederatedTrainingCoordinate
    client_publications: tuple[ClientPreprocessPublication, ...]
    population_client_count: ClientCount
    autoencoder: AutoencoderProtocol
    training_protocol: FedAvgProtocol
    checkpoint_protocol: CheckpointProtocol
    training_seed: Seed
    batch_size: BatchSize
    learning_rate: LearningRate
    split_manifest_checksum: Checksum
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TrainFedProxRequest:
    coordinate: FederatedTrainingCoordinate
    client_publications: tuple[ClientPreprocessPublication, ...]
    population_client_count: ClientCount
    autoencoder: AutoencoderProtocol
    training_protocol: FedProxProtocol
    checkpoint_protocol: CheckpointProtocol
    training_seed: Seed
    batch_size: BatchSize
    learning_rate: LearningRate
    split_manifest_checksum: Checksum
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TrainDittoRequest:
    global_coordinate: FederatedTrainingCoordinate
    personalized_coordinate: FederatedTrainingCoordinate
    client_publications: tuple[ClientPreprocessPublication, ...]
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
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TrainFederatedStageResult:
    stage: StageOperationId
    publication_status: PublicationStatus
    training: FederatedTrainingResult
    candidates: tuple[CheckpointCandidate, ...]


@dataclass(frozen=True, slots=True)
class TrainDittoStageResult:
    stage: StageOperationId
    publication_status: PublicationStatus
    global_training: FederatedTrainingResult
    global_candidates: tuple[CheckpointCandidate, ...]
    personalized_candidates_by_client: dict[str, tuple[CheckpointCandidate, ...]]


def train_fedavg_stage(request: TrainFedAvgRequest) -> TrainFederatedStageResult:
    clients = _build_client_datasets(request.coordinate, request.client_publications)
    preprocessing_checksum = preprocessing_state_set_checksum(
        tuple(client.preprocessing_state.estimator_checksum for client in clients)
    )
    box: _OutcomeBox[FedAvgTrainingOutcome] = _OutcomeBox()

    def write(temporary: Path) -> None:
        outcome = train_fedavg(
            FedAvgTrainingRequest(
                coordinate=request.coordinate,
                clients=clients,
                population_client_count=request.population_client_count,
                autoencoder=request.autoencoder,
                training_protocol=request.training_protocol,
                checkpoint_protocol=request.checkpoint_protocol,
                training_seed=request.training_seed,
                batch_size=request.batch_size,
                learning_rate=request.learning_rate,
                split_manifest_checksum=request.split_manifest_checksum,
                output_directory=temporary,
            )
        )
        _persist_history(outcome.training_result.history, temporary)
        digest = _training_complete_digest(outcome.candidates)
        (temporary / FederatedHistoryAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")
        box.outcome = outcome

    reused = publish_atomically(
        AtomicPublication(
            target=request.output_directory,
            overwrite=request.overwrite,
            is_reusable=lambda directory: _is_reusable(directory, request.checkpoint_protocol),
            write=write,
            remove_target=rmtree,
        )
    )
    if reused:
        training, candidates = _load_reused_training(
            request.coordinate,
            request.output_directory,
            request.checkpoint_protocol,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
            preprocessing_state_set_checksum=preprocessing_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
        )
        status = PublicationStatus.REUSED
    else:
        if box.outcome is None:
            raise ArtifactIntegrityError(
                "federated training write did not populate an outcome", subject=ContractSubject.TRAINING
            )
        training = box.outcome.training_result
        candidates = _rebase_candidates(box.outcome.candidates, request.output_directory, client=None)
        status = PublicationStatus.PUBLISHED
    return TrainFederatedStageResult(
        stage=StageOperationId.TRAIN_FEDERATED,
        publication_status=status,
        training=training,
        candidates=candidates,
    )


def train_fedprox_stage(request: TrainFedProxRequest) -> TrainFederatedStageResult:
    clients = _build_client_datasets(request.coordinate, request.client_publications)
    preprocessing_checksum = preprocessing_state_set_checksum(
        tuple(client.preprocessing_state.estimator_checksum for client in clients)
    )
    box: _OutcomeBox[FedAvgTrainingOutcome] = _OutcomeBox()

    def write(temporary: Path) -> None:
        outcome = train_fedprox(
            FedProxTrainingRequest(
                coordinate=request.coordinate,
                clients=clients,
                population_client_count=request.population_client_count,
                autoencoder=request.autoencoder,
                training_protocol=request.training_protocol,
                checkpoint_protocol=request.checkpoint_protocol,
                training_seed=request.training_seed,
                batch_size=request.batch_size,
                learning_rate=request.learning_rate,
                split_manifest_checksum=request.split_manifest_checksum,
                output_directory=temporary,
            )
        )
        _persist_history(outcome.training_result.history, temporary)
        digest = _training_complete_digest(outcome.candidates)
        (temporary / FederatedHistoryAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")
        box.outcome = outcome

    reused = publish_atomically(
        AtomicPublication(
            target=request.output_directory,
            overwrite=request.overwrite,
            is_reusable=lambda directory: _is_reusable(directory, request.checkpoint_protocol),
            write=write,
            remove_target=rmtree,
        )
    )
    if reused:
        training, candidates = _load_reused_training(
            request.coordinate,
            request.output_directory,
            request.checkpoint_protocol,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
            preprocessing_state_set_checksum=preprocessing_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
        )
        status = PublicationStatus.REUSED
    else:
        if box.outcome is None:
            raise ArtifactIntegrityError(
                "federated training write did not populate an outcome", subject=ContractSubject.TRAINING
            )
        training = box.outcome.training_result
        candidates = _rebase_candidates(box.outcome.candidates, request.output_directory, client=None)
        status = PublicationStatus.PUBLISHED
    return TrainFederatedStageResult(
        stage=StageOperationId.TRAIN_FEDERATED,
        publication_status=status,
        training=training,
        candidates=candidates,
    )


def train_ditto_stage(request: TrainDittoRequest) -> TrainDittoStageResult:
    clients = _build_client_datasets(request.global_coordinate, request.client_publications)
    preprocessing_checksum = preprocessing_state_set_checksum(
        tuple(client.preprocessing_state.estimator_checksum for client in clients)
    )
    box: _OutcomeBox[DittoTrainingOutcome] = _OutcomeBox()

    def write_global(temporary: Path) -> None:
        if box.outcome is None:
            box.outcome = train_ditto(
                DittoTrainingRequest(
                    global_coordinate=request.global_coordinate,
                    personalized_coordinate=request.personalized_coordinate,
                    clients=clients,
                    population_client_count=request.population_client_count,
                    autoencoder=request.autoencoder,
                    training_protocol=request.training_protocol,
                    checkpoint_protocol=request.checkpoint_protocol,
                    training_seed=request.training_seed,
                    batch_size=request.batch_size,
                    learning_rate=request.learning_rate,
                    split_manifest_checksum=request.split_manifest_checksum,
                    global_output_directory=temporary,
                    personalized_output_directory=request.personalized_output_directory,
                )
            )
        _persist_history(box.outcome.global_training_result.history, temporary)
        digest = _training_complete_digest(box.outcome.global_candidates)
        (temporary / FederatedHistoryAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")

    reused = publish_atomically(
        AtomicPublication(
            target=request.global_output_directory,
            overwrite=request.overwrite,
            is_reusable=lambda directory: _is_reusable(directory, request.checkpoint_protocol),
            write=write_global,
            remove_target=rmtree,
        )
    )
    if reused:
        global_training, global_candidates = _load_reused_training(
            request.global_coordinate,
            request.global_output_directory,
            request.checkpoint_protocol,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
            preprocessing_state_set_checksum=preprocessing_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
        )
        personalized_candidates = _load_reused_personalized_candidates(
            request, clients, preprocessing_state_set_checksum=preprocessing_checksum
        )
        status = PublicationStatus.REUSED
    else:
        if box.outcome is None:
            raise ArtifactIntegrityError(
                "Ditto training write did not populate an outcome", subject=ContractSubject.TRAINING
            )
        global_training = box.outcome.global_training_result
        global_candidates = _rebase_candidates(
            box.outcome.global_candidates, request.global_output_directory, client=None
        )
        personalized_candidates = {
            client_id: _rebase_candidates(
                candidates, request.personalized_output_directory, client=_client_by_id(clients, client_id)
            )
            for client_id, candidates in box.outcome.personalized_candidates_by_client.items()
        }
        status = PublicationStatus.PUBLISHED
    return TrainDittoStageResult(
        stage=StageOperationId.TRAIN_FEDERATED,
        publication_status=status,
        global_training=global_training,
        global_candidates=global_candidates,
        personalized_candidates_by_client=personalized_candidates,
    )


def _client_by_id(clients: tuple[FedAvgClientDataset, ...], client_id: str) -> ClientIdentity:
    for client in clients:
        if client.training_input.client.client_id == client_id:
            return client.training_input.client
    raise ScientificContractError(
        f"no client dataset found for personalized checkpoint client {client_id}",
        subject=ContractSubject.CLIENT_IDENTITY,
    )


def _build_client_datasets(
    coordinate: FederatedTrainingCoordinate,
    client_publications: tuple[ClientPreprocessPublication, ...],
) -> tuple[FedAvgClientDataset, ...]:
    binding = resolve_population(coordinate.population)
    identity_kind = binding.declaration.identity_kind
    datasets: list[FedAvgClientDataset] = []
    for publication in client_publications:
        client = ClientIdentity(coordinate.population, publication.client_identity.value, identity_kind)
        frame = pl.read_parquet(publication.result.train_path)
        feature_names = publication.result.transformed_schema.feature_names
        training_input = ClientTrainingInput(
            client=client,
            training_features=frame,
            feature_names=_as_feature_name_sequence(feature_names),
        )
        datasets.append(
            FedAvgClientDataset(training_input=training_input, preprocessing_state=publication.result.fitted_state)
        )
    return tuple(datasets)


def _as_feature_name_sequence(names: tuple[str, ...]):
    from datp_core.domain.values import FeatureNameSequence

    return FeatureNameSequence(names)


def _persist_history(history: FederatedTrainingHistory, directory: Path) -> None:
    column = FederatedHistoryColumn
    round_rows = []
    client_rows = []
    personalized_rows = []
    for round_result in history.rounds:
        round_rows.append(
            {
                column.ROUND_NUMBER.value: round_result.round_number.value,
                column.AGGREGATE_LOSS.value: round_result.aggregate_loss.value,
                column.UPLOAD_BYTES.value: round_result.communication.estimated_upload_bytes.value,
                column.DOWNLOAD_BYTES.value: round_result.communication.estimated_download_bytes.value,
                column.GLOBAL_STATE_CHECKSUM.value: round_result.global_state_reference.state_checksum.value,
            }
        )
        for client_result in round_result.client_results:
            client_rows.append(
                {
                    column.ROUND_NUMBER.value: round_result.round_number.value,
                    column.CLIENT_ID.value: client_result.client.client_id,
                    column.SAMPLE_COUNT.value: client_result.sample_count.value,
                    column.LOCAL_LOSS.value: client_result.local_loss.value,
                }
            )
        for personalized_reference in round_result.personalized_state_references:
            personalized_rows.append(
                {
                    column.ROUND_NUMBER.value: round_result.round_number.value,
                    column.CLIENT_ID.value: personalized_reference.client.client_id,
                    column.STATE_CHECKSUM.value: personalized_reference.state_checksum.value,
                }
            )
    pl.DataFrame(round_rows).write_parquet(directory / FederatedHistoryAssetName.ROUND_SUMMARY)
    pl.DataFrame(client_rows).write_parquet(directory / FederatedHistoryAssetName.CLIENT_ROUNDS)
    if personalized_rows:
        pl.DataFrame(personalized_rows).write_parquet(directory / FederatedHistoryAssetName.PERSONALIZED_ROUNDS)


def _load_history(
    coordinate: FederatedTrainingCoordinate,
    directory: Path,
    identity_kind,
) -> FederatedTrainingHistory:
    from datp_core.domain.values import ByteCount
    from datp_core.domain.values import Checksum as ChecksumType

    column = FederatedHistoryColumn
    round_frame = pl.read_parquet(directory / FederatedHistoryAssetName.ROUND_SUMMARY).sort(column.ROUND_NUMBER.value)
    client_frame = pl.read_parquet(directory / FederatedHistoryAssetName.CLIENT_ROUNDS)
    personalized_path = directory / FederatedHistoryAssetName.PERSONALIZED_ROUNDS
    personalized_frame = pl.read_parquet(personalized_path) if personalized_path.is_file() else None

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
                    state_checksum=ChecksumType(str(row[column.STATE_CHECKSUM.value])),
                    tensor_path=None,
                )
                for row in rows.iter_rows(named=True)
            )
        communication = CommunicationRecord(
            round_number=round_number,
            estimated_upload_bytes=ByteCount(int(round_row[column.UPLOAD_BYTES.value])),
            estimated_download_bytes=ByteCount(int(round_row[column.DOWNLOAD_BYTES.value])),
            estimation_basis=_estimation_basis(),
        )
        global_reference = GlobalModelStateReference(
            coordinate=coordinate,
            round_number=round_number,
            state_checksum=ChecksumType(str(round_row[column.GLOBAL_STATE_CHECKSUM.value])),
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


def _estimation_basis():
    from datp_core.domain.enums import WarningCode

    return WarningCode.SERIALIZED_MESSAGE_SIZE_ESTIMATE


def _training_complete_digest(candidates: tuple[CheckpointCandidate, ...]) -> Checksum:
    return checksum_text(f"{candidate_set_checksum(candidates).value}|{len(candidates)}")


def _is_reusable(directory: Path, checkpoint_protocol: CheckpointProtocol) -> bool:
    complete = directory / FederatedHistoryAssetName.COMPLETE
    round_summary = directory / FederatedHistoryAssetName.ROUND_SUMMARY
    client_rounds = directory / FederatedHistoryAssetName.CLIENT_ROUNDS
    if not (complete.is_file() and round_summary.is_file() and client_rounds.is_file()):
        return False
    for candidate_round in checkpoint_protocol.candidates:
        if not (directory / candidate_tensor_name(candidate_round)).is_file():
            return False
    return True


def _load_reused_training(
    coordinate: FederatedTrainingCoordinate,
    directory: Path,
    checkpoint_protocol: CheckpointProtocol,
    *,
    autoencoder: AutoencoderProtocol,
    batch_size: BatchSize,
    preprocessing_state_set_checksum: Checksum,
    split_manifest_checksum: Checksum,
) -> tuple[FederatedTrainingResult, tuple[CheckpointCandidate, ...]]:
    from datp_core.domain.enums import CheckpointStatus
    from datp_core.domain.values import MetricValue as MetricValueType

    binding = resolve_population(coordinate.population)
    identity_kind = binding.declaration.identity_kind
    history = _load_history(coordinate, directory, identity_kind)

    round_frame = pl.read_parquet(directory / FederatedHistoryAssetName.ROUND_SUMMARY)
    loss_by_round = {
        int(row[FederatedHistoryColumn.ROUND_NUMBER.value]): MetricValueType(
            float(row[FederatedHistoryColumn.AGGREGATE_LOSS.value])
        )
        for row in round_frame.iter_rows(named=True)
    }
    candidates: list[CheckpointCandidate] = []
    for candidate_round in checkpoint_protocol.candidates:
        path = directory / candidate_tensor_name(candidate_round)
        if not path.is_file():
            raise ArtifactIntegrityError("reused checkpoint candidate missing", subject=ContractSubject.ARTIFACT_PATH)
        candidates.append(
            CheckpointCandidate(
                coordinate=coordinate,
                round_number=candidate_round,
                client=None,
                tensor_path=path,
                tensor_checksum=checksum_file(path),
                mean_training_loss=loss_by_round[candidate_round.value],
                status=CheckpointStatus.CANDIDATE,
                preprocessing_state_set_checksum=preprocessing_state_set_checksum,
                split_manifest_checksum=split_manifest_checksum,
            )
        )
    training_result = FederatedTrainingResult(
        coordinate=coordinate,
        autoencoder_widths=tuple(autoencoder.widths),
        checkpoint_protocol=checkpoint_protocol,
        history=history,
        preprocessing_state_set_checksum=preprocessing_state_set_checksum,
        split_manifest_checksum=split_manifest_checksum,
        device_name="reused",
        batch_size_used=batch_size,
    )
    return training_result, tuple(candidates)


def _rebase_candidates(
    candidates: tuple[CheckpointCandidate, ...],
    directory: Path,
    *,
    client: ClientIdentity | None,
) -> tuple[CheckpointCandidate, ...]:
    rebased: list[CheckpointCandidate] = []
    for candidate in candidates:
        path = directory / candidate_tensor_name(candidate.round_number, client)
        rebased.append(
            CheckpointCandidate(
                coordinate=candidate.coordinate,
                round_number=candidate.round_number,
                client=candidate.client,
                tensor_path=path,
                tensor_checksum=checksum_file(path),
                mean_training_loss=candidate.mean_training_loss,
                status=candidate.status,
                preprocessing_state_set_checksum=candidate.preprocessing_state_set_checksum,
                split_manifest_checksum=candidate.split_manifest_checksum,
            )
        )
    return tuple(rebased)


def _load_reused_personalized_candidates(
    request: TrainDittoRequest,
    clients: tuple[FedAvgClientDataset, ...],
    *,
    preprocessing_state_set_checksum: Checksum,
) -> dict[str, tuple[CheckpointCandidate, ...]]:
    from datp_core.domain.enums import CheckpointStatus

    result: dict[str, tuple[CheckpointCandidate, ...]] = {}
    for client_dataset in clients:
        client = client_dataset.training_input.client
        candidates: list[CheckpointCandidate] = []
        for candidate_round in request.checkpoint_protocol.candidates:
            path = request.personalized_output_directory / candidate_tensor_name(candidate_round, client)
            if not path.is_file():
                raise ArtifactIntegrityError(
                    "reused personalized checkpoint candidate missing",
                    subject=ContractSubject.ARTIFACT_PATH,
                )
            candidates.append(
                CheckpointCandidate(
                    coordinate=request.personalized_coordinate,
                    round_number=candidate_round,
                    client=client,
                    tensor_path=path,
                    tensor_checksum=checksum_file(path),
                    mean_training_loss=MetricValue(0.0),
                    status=CheckpointStatus.CANDIDATE,
                    preprocessing_state_set_checksum=preprocessing_state_set_checksum,
                    split_manifest_checksum=request.split_manifest_checksum,
                )
            )
        result[client.client_id] = tuple(candidates)
    return result

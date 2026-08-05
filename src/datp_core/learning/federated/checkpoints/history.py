"""Federated training-history persistence and trusted reload."""

from dataclasses import dataclass
from os import replace as atomic_replace
from pathlib import Path

import polars as pl
from polars.exceptions import PolarsError

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import (
    CommunicationEstimationMethod,
    ContractSubject,
    PopulationIdentityKind,
    TrainingModelId,
)
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.values import ByteCount, Checksum, CudaDeviceName, MetricValue, RoundNumber, RowCount
from datp_core.learning.federated.checkpoints.identities import (
    CLIENT_ROUNDS_SCHEMA,
    PERSONALIZED_ROUNDS_SCHEMA,
    ROUND_SUMMARY_SCHEMA,
    FederatedHistoryAssetName,
    FederatedHistoryColumn,
    ParquetColumnSpec,
)
from datp_core.learning.federated.models import (
    ClientTrainingResult,
    CommunicationRecord,
    FederatedRoundResult,
    FederatedTrainingCoordinate,
    FederatedTrainingHistory,
    GlobalModelStateReference,
    PersonalizedModelStateReference,
)
from datp_core.protocols.models import CheckpointProtocol


@dataclass(frozen=True, slots=True, kw_only=True)
class RoundSummaryRecord:
    round_number: RoundNumber
    aggregate_loss: MetricValue
    upload_bytes: ByteCount
    download_bytes: ByteCount
    global_state_checksum: Checksum


def read_parquet(path: Path) -> pl.DataFrame:
    if not path.is_file():
        raise ArtifactIntegrityError(
            f"required Parquet artifact is missing: {path.name}",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    try:
        return pl.read_parquet(path)
    except (OSError, PolarsError) as error:
        raise ArtifactIntegrityError(
            f"Parquet artifact is unreadable or invalid: {path.name}",
            subject=ContractSubject.ARTIFACT_PATH,
        ) from error


def schema_pairs(schema: tuple[ParquetColumnSpec, ...]) -> tuple[tuple[str, type[pl.DataType]], ...]:
    return tuple((column.identity.value, column.dtype) for column in schema)


def validate_parquet_schema(frame: pl.DataFrame, expected_schema: tuple[ParquetColumnSpec, ...]) -> None:
    expected_columns = tuple(column.identity.value for column in expected_schema)
    if tuple(frame.columns) != expected_columns:
        raise ArtifactIntegrityError(
            "Parquet columns do not match the exact declared schema order",
            subject=ContractSubject.SCHEMA,
        )
    for column in expected_schema:
        observed = frame.schema[column.identity.value]
        if observed != column.dtype:
            raise ArtifactIntegrityError(
                f"Parquet column {column.identity.value!r} has type {observed}, expected {column.dtype}",
                subject=ContractSubject.SCHEMA,
            )


def validate_round_summary(frame: pl.DataFrame, expected_rounds: tuple[RoundNumber, ...]) -> None:
    validate_parquet_schema(frame, ROUND_SUMMARY_SCHEMA)
    observed = tuple(
        RoundNumber(value) for value in frame.get_column(FederatedHistoryColumn.ROUND_NUMBER.value).to_list()
    )
    if observed != expected_rounds:
        raise ArtifactIntegrityError(
            "round summary rows must equal the exact ordered training rounds",
            subject=ContractSubject.SCHEMA,
        )


def _validate_client_rows(
    frame: pl.DataFrame,
    schema: tuple[ParquetColumnSpec, ...],
    *,
    expected_rounds: tuple[RoundNumber, ...],
    expected_clients: tuple[ClientIdentity, ...],
    table_name: str,
) -> None:
    validate_parquet_schema(frame, schema)
    if frame.height < 1:
        raise ArtifactIntegrityError(f"{table_name} must contain rows", subject=ContractSubject.SCHEMA)
    round_column = FederatedHistoryColumn.ROUND_NUMBER.value
    client_column = FederatedHistoryColumn.CLIENT_ID.value
    observed_pairs = tuple(
        (RoundNumber(int(round_value)), str(client_id))
        for round_value, client_id in frame.select((round_column, client_column)).iter_rows()
    )
    expected_pairs = tuple(
        (round_number, client.client_id) for round_number in expected_rounds for client in expected_clients
    )
    if observed_pairs != expected_pairs:
        raise ArtifactIntegrityError(
            f"{table_name} must contain one ordered row for every declared round and client",
            subject=ContractSubject.SCHEMA,
        )


def validate_client_history(
    frame: pl.DataFrame,
    *,
    expected_rounds: tuple[RoundNumber, ...],
    expected_clients: tuple[ClientIdentity, ...],
) -> None:
    _validate_client_rows(
        frame,
        CLIENT_ROUNDS_SCHEMA,
        expected_rounds=expected_rounds,
        expected_clients=expected_clients,
        table_name="client history",
    )


def validate_personalized_history(
    frame: pl.DataFrame,
    *,
    expected_rounds: tuple[RoundNumber, ...],
    expected_clients: tuple[ClientIdentity, ...],
) -> None:
    _validate_client_rows(
        frame,
        PERSONALIZED_ROUNDS_SCHEMA,
        expected_rounds=expected_rounds,
        expected_clients=expected_clients,
        table_name="personalized history",
    )


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(f".{path.name}.tmp")
    staging.write_text(text, encoding="utf-8")
    atomic_replace(staging, path)


def persist_federated_training_history(
    history: FederatedTrainingHistory,
    directory: Path,
    *,
    device_name: CudaDeviceName,
) -> None:
    normalized_device = device_name.strip()
    if not normalized_device:
        raise ScientificContractError(
            "training publication requires a non-empty CUDA device name",
            subject=ContractSubject.CUDA,
        )
    round_rows = tuple(
        (
            item.round_number.value,
            item.aggregate_loss.value,
            item.communication.estimated_upload_bytes.value,
            item.communication.estimated_download_bytes.value,
            item.global_state_reference.state_checksum.value,
        )
        for item in history.rounds
    )
    client_rows = tuple(
        (
            item.round_number.value,
            result.client.client_id,
            result.sample_count.value,
            result.local_loss.value,
        )
        for item in history.rounds
        for result in item.client_results
    )
    personalized_rows = tuple(
        (
            item.round_number.value,
            reference.client.client_id,
            reference.local_loss.value,
            reference.state_checksum.value,
        )
        for item in history.rounds
        for reference in item.personalized_state_references
    )
    directory.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(round_rows, schema=schema_pairs(ROUND_SUMMARY_SCHEMA), orient="row").write_parquet(
        directory / FederatedHistoryAssetName.ROUND_SUMMARY.value
    )
    pl.DataFrame(client_rows, schema=schema_pairs(CLIENT_ROUNDS_SCHEMA), orient="row").write_parquet(
        directory / FederatedHistoryAssetName.CLIENT_ROUNDS.value
    )
    if personalized_rows:
        pl.DataFrame(
            personalized_rows,
            schema=schema_pairs(PERSONALIZED_ROUNDS_SCHEMA),
            orient="row",
        ).write_parquet(directory / FederatedHistoryAssetName.PERSONALIZED_ROUNDS.value)
    atomic_write_text(directory / FederatedHistoryAssetName.DEVICE_NAME.value, normalized_device)


def history_frames(directory: Path) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame | None]:
    round_frame = read_parquet(directory / FederatedHistoryAssetName.ROUND_SUMMARY.value)
    client_frame = read_parquet(directory / FederatedHistoryAssetName.CLIENT_ROUNDS.value)
    personalized_path = directory / FederatedHistoryAssetName.PERSONALIZED_ROUNDS.value
    personalized_frame = read_parquet(personalized_path) if personalized_path.is_file() else None
    return round_frame, client_frame, personalized_frame


def load_published_device_name(directory: Path) -> CudaDeviceName:
    path = directory / FederatedHistoryAssetName.DEVICE_NAME.value
    try:
        value = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as error:
        raise ArtifactIntegrityError(
            "published CUDA device name is unreadable",
            subject=ContractSubject.CUDA,
        ) from error
    if not value:
        raise ArtifactIntegrityError("published CUDA device name is empty", subject=ContractSubject.CUDA)
    return CudaDeviceName(value)


def load_federated_training_history(
    coordinate: FederatedTrainingCoordinate,
    directory: Path,
    identity_kind: PopulationIdentityKind,
    *,
    clients: tuple[ClientIdentity, ...],
    checkpoint_protocol: CheckpointProtocol,
    personalized_coordinate: FederatedTrainingCoordinate | None = None,
) -> FederatedTrainingHistory:
    round_frame, client_frame, personalized_frame = history_frames(directory)
    training_rounds = tuple(RoundNumber(value) for value in range(1, checkpoint_protocol.maximum_round.value + 1))
    validate_round_summary(round_frame, training_rounds)
    validate_client_history(client_frame, expected_rounds=training_rounds, expected_clients=clients)
    match coordinate.model:
        case TrainingModelId.DITTO_GLOBAL_AUTOENCODER:
            if personalized_coordinate is None or personalized_frame is None:
                raise ArtifactIntegrityError(
                    "Ditto global history requires its personalized coordinate and history",
                    subject=ContractSubject.COORDINATE,
                )
            if not coordinate.matches_ditto_peer(personalized_coordinate):
                raise ArtifactIntegrityError(
                    "Ditto global and personalized coordinates do not match",
                    subject=ContractSubject.COORDINATE,
                )
            validate_personalized_history(
                personalized_frame,
                expected_rounds=training_rounds,
                expected_clients=clients,
            )
        case TrainingModelId.FEDAVG_AUTOENCODER | TrainingModelId.FEDPROX_AUTOENCODER:
            if personalized_coordinate is not None or personalized_frame is not None:
                raise ArtifactIntegrityError(
                    "FedAvg and FedProx publications cannot contain personalized history",
                    subject=ContractSubject.ARTIFACT_PATH,
                )
        case _:
            raise ArtifactIntegrityError(
                "unsupported model in federated history publication",
                subject=ContractSubject.COORDINATE,
            )
    rounds = tuple(
        _round_result(
            coordinate=coordinate,
            personalized_coordinate=personalized_coordinate,
            identity_kind=identity_kind,
            summary=summary,
            client_frame=client_frame,
            personalized_frame=personalized_frame,
        )
        for summary in _round_summaries(round_frame)
    )
    return FederatedTrainingHistory(coordinate=coordinate, rounds=rounds)


def _round_summaries(frame: pl.DataFrame) -> tuple[RoundSummaryRecord, ...]:
    column = FederatedHistoryColumn
    return tuple(
        RoundSummaryRecord(
            round_number=RoundNumber(int(round_number)),
            aggregate_loss=MetricValue(float(aggregate_loss)),
            upload_bytes=ByteCount(int(upload_bytes)),
            download_bytes=ByteCount(int(download_bytes)),
            global_state_checksum=Checksum(str(global_state_checksum)),
        )
        for round_number, aggregate_loss, upload_bytes, download_bytes, global_state_checksum in frame.select(
            (
                column.ROUND_NUMBER.value,
                column.AGGREGATE_LOSS.value,
                column.UPLOAD_BYTES.value,
                column.DOWNLOAD_BYTES.value,
                column.GLOBAL_STATE_CHECKSUM.value,
            )
        ).iter_rows()
    )


def _round_result(
    *,
    coordinate: FederatedTrainingCoordinate,
    personalized_coordinate: FederatedTrainingCoordinate | None,
    identity_kind: PopulationIdentityKind,
    summary: RoundSummaryRecord,
    client_frame: pl.DataFrame,
    personalized_frame: pl.DataFrame | None,
) -> FederatedRoundResult:
    column = FederatedHistoryColumn
    client_rows = client_frame.filter(pl.col(column.ROUND_NUMBER.value) == summary.round_number.value)
    client_results = tuple(
        ClientTrainingResult(
            client=ClientIdentity(coordinate.population, str(client_id), identity_kind),
            sample_count=RowCount(int(sample_count)),
            local_loss=MetricValue(float(local_loss)),
        )
        for client_id, sample_count, local_loss in client_rows.select(
            (column.CLIENT_ID.value, column.SAMPLE_COUNT.value, column.LOCAL_LOSS.value)
        ).iter_rows()
    )
    personalized_references = _personalized_references(
        coordinate=coordinate,
        personalized_coordinate=personalized_coordinate,
        identity_kind=identity_kind,
        round_number=summary.round_number,
        personalized_frame=personalized_frame,
    )
    return FederatedRoundResult(
        round_number=summary.round_number,
        client_results=client_results,
        aggregate_loss=summary.aggregate_loss,
        communication=CommunicationRecord(
            round_number=summary.round_number,
            estimated_upload_bytes=summary.upload_bytes,
            estimated_download_bytes=summary.download_bytes,
            estimation_basis=CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
        ),
        global_state_reference=GlobalModelStateReference(
            coordinate=coordinate,
            round_number=summary.round_number,
            state_checksum=summary.global_state_checksum,
            tensor_path=None,
        ),
        personalized_state_references=personalized_references,
    )


def _personalized_references(
    *,
    coordinate: FederatedTrainingCoordinate,
    personalized_coordinate: FederatedTrainingCoordinate | None,
    identity_kind: PopulationIdentityKind,
    round_number: RoundNumber,
    personalized_frame: pl.DataFrame | None,
) -> tuple[PersonalizedModelStateReference, ...]:
    if personalized_coordinate is None:
        return ()
    if personalized_frame is None:
        raise ArtifactIntegrityError(
            "personalized coordinate requires personalized history",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    column = FederatedHistoryColumn
    rows = personalized_frame.filter(pl.col(column.ROUND_NUMBER.value) == round_number.value)
    return tuple(
        PersonalizedModelStateReference(
            coordinate=personalized_coordinate,
            client=ClientIdentity(coordinate.population, str(client_id), identity_kind),
            round_number=round_number,
            local_loss=MetricValue(float(local_loss)),
            state_checksum=Checksum(str(state_checksum)),
            tensor_path=None,
        )
        for client_id, local_loss, state_checksum in rows.select(
            (column.CLIENT_ID.value, column.LOCAL_LOSS.value, column.STATE_CHECKSUM.value)
        ).iter_rows()
    )

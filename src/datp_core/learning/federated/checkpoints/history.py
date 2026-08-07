"""Federated training-history persistence and trusted reload."""

from dataclasses import dataclass
from enum import StrEnum
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
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import ByteCount, RoundNumber, RowCount
from datp_core.domain.values.identifiers import CudaDeviceName
from datp_core.domain.values.ratios import MetricValue
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
from datp_core.protocols.checkpoints import CheckpointProtocol


class _ClientHistoryTable(StrEnum):
    CLIENT = "client history"
    PERSONALIZED = "personalized history"


@dataclass(frozen=True, slots=True)
class _ClientRoundRow:
    client: ClientIdentity
    sample_count: RowCount
    local_loss: MetricValue


@dataclass(frozen=True, slots=True)
class _PersonalizedRoundRow:
    client: ClientIdentity
    local_loss: MetricValue
    state_checksum: Checksum


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


def schema_pairs(schema: tuple[ParquetColumnSpec, ...]) -> dict[str, type[pl.DataType]]:
    return {column.identity.value: column.dtype for column in schema}


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
    table_name: _ClientHistoryTable,
) -> None:
    validate_parquet_schema(frame, schema)
    if frame.height < 1:
        raise ArtifactIntegrityError(f"{table_name} must contain rows", subject=ContractSubject.SCHEMA)

    round_column = FederatedHistoryColumn.ROUND_NUMBER.value
    client_column = FederatedHistoryColumn.CLIENT_ID.value

    observed_rounds = frame.get_column(round_column).to_list()
    observed_clients_list = frame.get_column(client_column).to_list()

    observed_pairs = tuple(
        (RoundNumber(int(r)), str(c)) for r, c in zip(observed_rounds, observed_clients_list, strict=True)
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
        table_name=_ClientHistoryTable.CLIENT,
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
        table_name=_ClientHistoryTable.PERSONALIZED,
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

    r_nums, a_losses, u_bytes, d_bytes, g_sums = [], [], [], [], []
    c_rounds, c_ids, c_samples, c_losses = [], [], [], []
    p_rounds, p_ids, p_losses, p_sums = [], [], [], []

    for item in history.rounds:
        r_nums.append(item.round_number.value)
        a_losses.append(item.aggregate_loss.value)
        u_bytes.append(item.communication.estimated_upload_bytes.value)
        d_bytes.append(item.communication.estimated_download_bytes.value)
        g_sums.append(item.global_state_reference.state_checksum.value)

        for result in item.client_results:
            c_rounds.append(item.round_number.value)
            c_ids.append(result.client.client_id)
            c_samples.append(result.sample_count.value)
            c_losses.append(result.local_loss.value)

        for reference in item.personalized_state_references:
            p_rounds.append(item.round_number.value)
            p_ids.append(reference.client.client_id)
            p_losses.append(reference.local_loss.value)
            p_sums.append(reference.state_checksum.value)

    directory.mkdir(parents=True, exist_ok=True)

    pl.DataFrame(
        {
            FederatedHistoryColumn.ROUND_NUMBER.value: r_nums,
            FederatedHistoryColumn.AGGREGATE_LOSS.value: a_losses,
            FederatedHistoryColumn.UPLOAD_BYTES.value: u_bytes,
            FederatedHistoryColumn.DOWNLOAD_BYTES.value: d_bytes,
            FederatedHistoryColumn.GLOBAL_STATE_CHECKSUM.value: g_sums,
        },
        schema=schema_pairs(ROUND_SUMMARY_SCHEMA),
    ).write_parquet(directory / FederatedHistoryAssetName.ROUND_SUMMARY.value)

    pl.DataFrame(
        {
            FederatedHistoryColumn.ROUND_NUMBER.value: c_rounds,
            FederatedHistoryColumn.CLIENT_ID.value: c_ids,
            FederatedHistoryColumn.SAMPLE_COUNT.value: c_samples,
            FederatedHistoryColumn.LOCAL_LOSS.value: c_losses,
        },
        schema=schema_pairs(CLIENT_ROUNDS_SCHEMA),
    ).write_parquet(directory / FederatedHistoryAssetName.CLIENT_ROUNDS.value)

    if p_rounds:
        pl.DataFrame(
            {
                FederatedHistoryColumn.ROUND_NUMBER.value: p_rounds,
                FederatedHistoryColumn.CLIENT_ID.value: p_ids,
                FederatedHistoryColumn.LOCAL_LOSS.value: p_losses,
                FederatedHistoryColumn.STATE_CHECKSUM.value: p_sums,
            },
            schema=schema_pairs(PERSONALIZED_ROUNDS_SCHEMA),
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

    column = FederatedHistoryColumn
    client_dict_by_round: dict[RoundNumber, list[_ClientRoundRow]] = {}
    for round_val, client_val, sample_val, loss_val in client_frame.select(
        (column.ROUND_NUMBER.value, column.CLIENT_ID.value, column.SAMPLE_COUNT.value, column.LOCAL_LOSS.value)
    ).iter_rows():
        client_dict_by_round.setdefault(RoundNumber(int(round_val)), []).append(
            _ClientRoundRow(
                client=ClientIdentity(coordinate.population, str(client_val), identity_kind),
                sample_count=RowCount(int(sample_val)),
                local_loss=MetricValue(float(loss_val)),
            )
        )

    personalized_dict_by_round: dict[RoundNumber, list[_PersonalizedRoundRow]] = {}
    if personalized_frame is not None:
        for round_val, client_val, loss_val, checksum_val in personalized_frame.select(
            (column.ROUND_NUMBER.value, column.CLIENT_ID.value, column.LOCAL_LOSS.value, column.STATE_CHECKSUM.value)
        ).iter_rows():
            personalized_dict_by_round.setdefault(RoundNumber(int(round_val)), []).append(
                _PersonalizedRoundRow(
                    client=ClientIdentity(coordinate.population, str(client_val), identity_kind),
                    local_loss=MetricValue(float(loss_val)),
                    state_checksum=Checksum(str(checksum_val)),
                )
            )

    rounds = tuple(
        _round_result(
            coordinate=coordinate,
            personalized_coordinate=personalized_coordinate,
            summary=summary,
            client_data=client_dict_by_round.get(summary.round_number, []),
            personalized_data=personalized_dict_by_round.get(summary.round_number, []),
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
    summary: RoundSummaryRecord,
    client_data: list[_ClientRoundRow],
    personalized_data: list[_PersonalizedRoundRow],
) -> FederatedRoundResult:
    client_results = tuple(
        ClientTrainingResult(
            client=row.client,
            sample_count=row.sample_count,
            local_loss=row.local_loss,
        )
        for row in client_data
    )
    personalized_references = _personalized_references(
        personalized_coordinate=personalized_coordinate,
        round_number=summary.round_number,
        personalized_data=personalized_data,
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
    personalized_coordinate: FederatedTrainingCoordinate | None,
    round_number: RoundNumber,
    personalized_data: list[_PersonalizedRoundRow],
) -> tuple[PersonalizedModelStateReference, ...]:
    if personalized_coordinate is None:
        return ()
    if not personalized_data:
        raise ArtifactIntegrityError(
            "personalized coordinate requires personalized history",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    return tuple(
        PersonalizedModelStateReference(
            coordinate=personalized_coordinate,
            client=row.client,
            round_number=round_number,
            local_loss=row.local_loss,
            state_checksum=row.state_checksum,
            tensor_path=None,
        )
        for row in personalized_data
    )

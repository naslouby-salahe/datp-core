from dataclasses import dataclass
from pathlib import Path

import polars as pl
import torch

from datp_core.core.errors import ArtifactIntegrityError, ErrorMessage, ScientificContractError
from datp_core.core.identifiers import (
    ContractSubject,
    PartitionRole,
    PopulationId,
    SerializationFormat,
    SplitProtocolId,
)
from datp_core.core.numeric import FeatureCount, RowCount
from datp_core.data.populations.contracts import STABLE_ROW_ID_COLUMN, ClientIdentity
from datp_core.data.preprocessing.artifacts import scored_partition_roles
from datp_core.detector.scoring.contracts import ScoreArtifactManifest, ScoreGenerationResult, ScoreRecord
from datp_core.detector.scoring.frames import (
    SCORE_FRAME_COLUMNS,
    model_from_terminal_state,
    score_and_persist_autoencoder_frame,
    validate_persisted_score_frame,
)
from datp_core.detector.scoring.models import (
    ClientScoringInput,
    FederatedScoreAssetName,
    FederatedScoreGenerationResult,
    FederatedScoreRecord,
    GenerateFederatedScoresRequest,
    ScoreGenerationRequest,
)
from datp_core.runtime.compute import resolve_cuda_device


@dataclass(slots=True)
class _ScoreRecordInventory:
    calibration: list[FederatedScoreRecord]
    evaluation: list[FederatedScoreRecord]
    future_recalibration: list[FederatedScoreRecord]

    @classmethod
    def empty(cls) -> "_ScoreRecordInventory":
        return cls(calibration=[], evaluation=[], future_recalibration=[])

    def append(self, role: PartitionRole, record: FederatedScoreRecord) -> None:
        match role:
            case PartitionRole.CALIBRATION:
                self.calibration.append(record)
            case PartitionRole.EVALUATION:
                self.evaluation.append(record)
            case PartitionRole.FUTURE_RECALIBRATION:
                self.future_recalibration.append(record)
            case _:
                raise ScientificContractError(ErrorMessage("training rows are never score artifacts"), subject=role)

    def records_for(self, role: PartitionRole) -> tuple[FederatedScoreRecord, ...]:
        match role:
            case PartitionRole.CALIBRATION:
                return tuple(self.calibration)
            case PartitionRole.EVALUATION:
                return tuple(self.evaluation)
            case PartitionRole.FUTURE_RECALIBRATION:
                return tuple(self.future_recalibration)
            case _:
                raise ScientificContractError(ErrorMessage("training rows are never score artifacts"), subject=role)


def publish_federated_scores(request: GenerateFederatedScoresRequest) -> FederatedScoreGenerationResult:
    if not request.overwrite:
        reused = load_federated_scores(request)
        if reused is not None:
            return reused
    if request.output_directory.exists() and not request.overwrite:
        raise FileExistsError(f"score output already exists: {request.output_directory}")
    return _generate_federated_scores(
        ScoreGenerationRequest(
            training=request.training,
            scored_split_protocol=request.scored_split_protocol,
            autoencoder=request.autoencoder,
            feature_names=request.feature_names,
            clients=request.clients,
            batch_size=request.batch_size,
            output_directory=request.output_directory,
        ),
        resolve_cuda_device(),
    )


def load_federated_scores(request: GenerateFederatedScoresRequest) -> FederatedScoreGenerationResult | None:
    roles = scored_partition_roles(request.scored_split_protocol)
    ordered_clients = tuple(sorted(request.clients, key=lambda item: item.client))
    expected_paths = tuple(
        _score_path(request.output_directory, client_input, role) for client_input in ordered_clients for role in roles
    )
    if not any(path.is_file() for path in expected_paths):
        return None
    records = _ScoreRecordInventory.empty()
    for client_input in ordered_clients:
        for role in roles:
            path = _score_path(request.output_directory, client_input, role)
            expected_frame = client_input.features_for(role)
            persisted_frame = validate_persisted_score_frame(path, RowCount(expected_frame.height))
            _require_matching_row_identity(persisted_frame, expected_frame, client_input.client, role)
            records.append(
                role,
                ScoreRecord(
                    coordinate=request.training.coordinate,
                    partition_role=role,
                    path=path,
                    row_count=RowCount(persisted_frame.height),
                    feature_count=FeatureCount(len(request.feature_names)),
                    serialization_format=SerializationFormat.PARQUET,
                    scored_client=client_input.client,
                ),
            )
    return ScoreGenerationResult(
        manifest=ScoreArtifactManifest(
            coordinate=request.training.coordinate,
            scored_split_protocol=request.scored_split_protocol,
            calibration_records=records.records_for(PartitionRole.CALIBRATION),
            evaluation_records=records.records_for(PartitionRole.EVALUATION),
            future_recalibration_records=records.records_for(PartitionRole.FUTURE_RECALIBRATION),
        )
    )


def _score_path(output_directory: Path, client_input: ClientScoringInput, role: PartitionRole) -> Path:
    return output_directory / client_input.client.client_id.value / _asset_name_for_partition(role).value


def _require_matching_row_identity(
    persisted_frame: pl.DataFrame,
    expected_frame: pl.DataFrame,
    client: ClientIdentity,
    role: PartitionRole,
) -> None:
    persisted_ids = tuple(persisted_frame.get_column(SCORE_FRAME_COLUMNS[0]).to_list())
    expected_ids = tuple(str(value) for value in expected_frame.get_column(STABLE_ROW_ID_COLUMN).to_list())
    if persisted_ids != expected_ids:
        raise ArtifactIntegrityError(
            ErrorMessage(
                f"persisted {role.value} score artifact row identities do not match the current "
                f"partition for client {client.client_id.value}"
            ),
            subject=ContractSubject.ARTIFACT_PATH,
        )


def _generate_federated_scores(request: ScoreGenerationRequest, device: torch.device) -> FederatedScoreGenerationResult:
    _validate_request(request)
    model = model_from_terminal_state(request.training.terminal_model_state, request.autoencoder, device)
    records = _ScoreRecordInventory.empty()
    for client_input in sorted(request.clients, key=lambda item: item.client):
        directory = request.output_directory / client_input.client.client_id.value
        for role in scored_partition_roles(request.scored_split_protocol):
            persisted = score_and_persist_autoencoder_frame(
                frame=client_input.features_for(role),
                partition_role=role,
                feature_names=request.feature_names,
                model=model,
                batch_size=request.batch_size,
                device=device,
                destination=directory / _asset_name_for_partition(role).value,
            )
            records.append(
                role,
                ScoreRecord(
                    coordinate=request.training.coordinate,
                    partition_role=role,
                    path=persisted.path,
                    row_count=persisted.row_count,
                    feature_count=persisted.feature_count,
                    serialization_format=SerializationFormat.PARQUET,
                    scored_client=client_input.client,
                ),
            )
    return ScoreGenerationResult(
        manifest=ScoreArtifactManifest(
            coordinate=request.training.coordinate,
            scored_split_protocol=request.scored_split_protocol,
            calibration_records=records.records_for(PartitionRole.CALIBRATION),
            evaluation_records=records.records_for(PartitionRole.EVALUATION),
            future_recalibration_records=records.records_for(PartitionRole.FUTURE_RECALIBRATION),
        )
    )


def _validate_request(request: ScoreGenerationRequest) -> None:
    if not _split_binding_is_valid(request):
        raise ScientificContractError(
            ErrorMessage(
                "scored split must match training split except for the matched Edge temporal static reference"
            ),
            subject=ContractSubject.SPLIT,
        )
    if not request.clients:
        raise ScientificContractError(ErrorMessage("score generation requires at least one client scoring input"))
    client_ids = tuple(item.client.client_id for item in request.clients)
    if len(frozenset(client_ids)) != len(client_ids):
        raise ScientificContractError(
            ErrorMessage("score generation cannot receive duplicate client identities"),
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    for client in request.clients:
        for role in scored_partition_roles(request.scored_split_protocol):
            client.features_for(role)


def _split_binding_is_valid(request: ScoreGenerationRequest) -> bool:
    coordinate = request.training.coordinate
    return request.scored_split_protocol is coordinate.split_protocol or (
        coordinate.population is PopulationId.EDGE_TEMPORAL_GROUPS
        and coordinate.split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
        and request.scored_split_protocol is SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE
    )


def _asset_name_for_partition(role: PartitionRole) -> FederatedScoreAssetName:
    match role:
        case PartitionRole.CALIBRATION:
            return FederatedScoreAssetName.CALIBRATION
        case PartitionRole.FUTURE_RECALIBRATION:
            return FederatedScoreAssetName.FUTURE_RECALIBRATION
        case PartitionRole.EVALUATION:
            return FederatedScoreAssetName.EVALUATION
        case _:
            raise ScientificContractError(ErrorMessage("training rows are never scored"), subject=role)

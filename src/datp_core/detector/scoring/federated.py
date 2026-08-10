from dataclasses import dataclass

import torch

from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import (
    ContractSubject,
    PartitionRole,
    PopulationId,
    SerializationFormat,
    SplitProtocolId,
)
from datp_core.data.preprocessing.artifacts import scored_partition_roles
from datp_core.detector.scoring.contracts import ScoreArtifactManifest, ScoreGenerationResult, ScoreRecord
from datp_core.detector.scoring.frames import model_from_terminal_state, score_and_persist_autoencoder_frame
from datp_core.detector.scoring.models import (
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

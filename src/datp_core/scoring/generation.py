"""Immutable, reusable-across-thresholds federated score generation."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np
import polars as pl
import torch
from safetensors.torch import load_file

from datp_core.artifacts.layout import scored_partition_roles
from datp_core.artifacts.serialization import canonical_checksum
from datp_core.domain.enums import (
    CheckpointStatus,
    ContractSubject,
    PartitionRole,
    SerializationFormat,
)
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    FeatureCount,
    FeatureNameSequence,
    RowCount,
    checksum_file,
)
from datp_core.learning.autoencoder import ReconstructionAutoencoder, reconstruction_errors
from datp_core.learning.federated.models import CheckpointCandidate
from datp_core.pipeline.checkpoints.service import validate_persisted_checkpoint_file
from datp_core.pipeline.scoring.frames import (
    extract_score_arrays,
    score_frame,
    validate_persisted_score_frame,
    validate_score_input_frame,
)
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import AutoencoderProtocol
from datp_core.scoring.models import (
    FixedScoreInvariant,
    ScoreArtifactManifest,
    ScoreGenerationResult,
    ScoreRecord,
    record_set_checksum,
)


class FederatedScoreAssetName(StrEnum):
    CALIBRATION = "calibration.parquet"
    EVALUATION = "evaluation.parquet"
    FUTURE_RECALIBRATION = "future_recalibration.parquet"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True, eq=False)
class ClientScoringInput:
    client: ClientIdentity
    calibration_features: pl.DataFrame
    evaluation_features: pl.DataFrame
    future_recalibration_features: pl.DataFrame | None = None

    def features_for(self, role: PartitionRole) -> pl.DataFrame:
        match role:
            case PartitionRole.CALIBRATION:
                return self.calibration_features
            case PartitionRole.FUTURE_RECALIBRATION:
                if self.future_recalibration_features is None:
                    raise ScientificContractError(
                        "temporal score input is missing future recalibration features",
                        subject=role,
                    )
                return self.future_recalibration_features
            case PartitionRole.EVALUATION:
                return self.evaluation_features
            case PartitionRole.TRAIN:
                raise ScientificContractError("training rows are never scored", subject=role)
            case PartitionRole.STATIC_REFERENCE_RESERVE:
                raise ScientificContractError("static-reference reserve rows are never scored", subject=role)


@dataclass(frozen=True, slots=True)
class ScoreGenerationRequest:
    checkpoint: CheckpointCandidate
    autoencoder: AutoencoderProtocol
    feature_names: FeatureNameSequence
    clients: tuple[ClientScoringInput, ...]
    batch_size: BatchSize
    output_directory: Path
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum


@dataclass(slots=True)
class _ScoreRecordInventory:
    calibration: list[ScoreRecord]
    evaluation: list[ScoreRecord]
    future_recalibration: list[ScoreRecord]

    @classmethod
    def empty(cls) -> "_ScoreRecordInventory":
        return cls(calibration=[], evaluation=[], future_recalibration=[])

    def records_for(self, role: PartitionRole) -> list[ScoreRecord]:
        match role:
            case PartitionRole.CALIBRATION:
                return self.calibration
            case PartitionRole.EVALUATION:
                return self.evaluation
            case PartitionRole.FUTURE_RECALIBRATION:
                return self.future_recalibration
            case PartitionRole.TRAIN:
                raise ScientificContractError("training rows are never score artifacts", subject=role)
            case PartitionRole.STATIC_REFERENCE_RESERVE:
                raise ScientificContractError("static-reference reserve rows are never score artifacts", subject=role)

    def append(self, role: PartitionRole, record: ScoreRecord) -> None:
        self.records_for(role).append(record)

    def immutable_records_for(self, role: PartitionRole) -> tuple[ScoreRecord, ...]:
        return tuple(self.records_for(role))


def load_checkpoint_model(
    checkpoint: CheckpointCandidate,
    autoencoder: AutoencoderProtocol,
    device: torch.device,
) -> ReconstructionAutoencoder:
    if device.type != "cuda":
        raise ScientificContractError(
            "scoring requires a CUDA device",
            subject=ContractSubject.CUDA,
        )
    validate_persisted_checkpoint_file(checkpoint.tensor_path, checkpoint.tensor_checksum)
    model = ReconstructionAutoencoder(autoencoder.widths).to(device)
    state = load_file(str(checkpoint.tensor_path), device=str(device))
    model.load_state_dict(state, strict=True)
    model.eval()
    return model


def generate_federated_scores(request: ScoreGenerationRequest, device: torch.device) -> ScoreGenerationResult:
    """Write one complete score artifact inventory to an empty caller-owned directory."""
    _validate_request(request)
    _require_empty_output_directory(request.output_directory)
    model = load_checkpoint_model(request.checkpoint, request.autoencoder, device)
    scored_roles = scored_partition_roles(request.checkpoint.coordinate.split_protocol)
    records = _ScoreRecordInventory.empty()

    for client_input in sorted(request.clients, key=lambda item: item.client):
        client_directory = request.output_directory / client_input.client.client_id
        for role in scored_roles:
            frame = client_input.features_for(role)
            validate_score_input_frame(frame, role, request.feature_names)
            record = _score_partition(
                frame=frame,
                client=client_input.client,
                partition_role=role,
                request=request,
                model=model,
                device=device,
                destination=client_directory / _asset_name_for_partition(role).value,
            )
            records.append(role, record)

    for role in scored_roles:
        for record in records.records_for(role):
            validate_persisted_score_frame(record.path, record.checksum, record.row_count)

    invariant = _fixed_score_invariant(request, records)
    _write_complete_marker(request.output_directory, invariant)
    manifest = ScoreArtifactManifest(
        coordinate=request.checkpoint.coordinate,
        checkpoint_round=request.checkpoint.round_number,
        checkpoint_checksum=request.checkpoint.tensor_checksum,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        calibration_records=records.immutable_records_for(PartitionRole.CALIBRATION),
        evaluation_records=records.immutable_records_for(PartitionRole.EVALUATION),
        future_recalibration_records=records.immutable_records_for(PartitionRole.FUTURE_RECALIBRATION),
    )
    return ScoreGenerationResult(manifest=manifest)


def _require_empty_output_directory(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise ArtifactIntegrityError(
            "score generation output directory must be empty",
            subject=ContractSubject.ARTIFACT_PATH,
        )


def _fixed_score_invariant(
    request: ScoreGenerationRequest,
    records: _ScoreRecordInventory,
) -> FixedScoreInvariant:
    future_records = records.immutable_records_for(PartitionRole.FUTURE_RECALIBRATION)
    return FixedScoreInvariant(
        model_checksum=request.checkpoint.tensor_checksum,
        calibration_score_set_checksum=record_set_checksum(
            records.immutable_records_for(PartitionRole.CALIBRATION)
        ),
        evaluation_score_set_checksum=record_set_checksum(
            records.immutable_records_for(PartitionRole.EVALUATION)
        ),
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        future_recalibration_score_set_checksum=(
            record_set_checksum(future_records) if future_records else None
        ),
    )


def _validate_request(request: ScoreGenerationRequest) -> None:
    if request.checkpoint.status is not CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
        raise ScientificContractError(
            "scoring requires the non-test-selected checkpoint, never a raw candidate",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    if request.checkpoint.preprocessing_state_set_checksum != request.preprocessing_state_set_checksum:
        raise ScientificContractError(
            "checkpoint preprocessing checksum mismatch during scoring",
            subject=ContractSubject.PREPROCESSING,
        )
    if request.checkpoint.split_manifest_checksum != request.split_manifest_checksum:
        raise ScientificContractError(
            "checkpoint split manifest checksum mismatch during scoring",
            subject=ContractSubject.SPLIT,
        )
    if not request.clients:
        raise ScientificContractError(
            "score generation requires at least one client scoring input",
            subject=ContractSubject.CLIENT,
        )
    client_ids = tuple(item.client.client_id for item in request.clients)
    if len(frozenset(client_ids)) != len(client_ids):
        raise ScientificContractError(
            "score generation cannot receive duplicate client identities",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    expected_roles = scored_partition_roles(request.checkpoint.coordinate.split_protocol)
    for client in request.clients:
        for role in expected_roles:
            client.features_for(role)


def _score_partition(
    *,
    frame: pl.DataFrame,
    client: ClientIdentity,
    partition_role: PartitionRole,
    request: ScoreGenerationRequest,
    model: ReconstructionAutoencoder,
    device: torch.device,
    destination: Path,
) -> ScoreRecord:
    matrix, labels, row_ids = extract_score_arrays(frame, request.feature_names)
    scores = reconstruction_errors(model, matrix, batch_size=request.batch_size, device=device)
    if scores.shape[0] != matrix.shape[0]:
        raise ScientificContractError("score count must equal partition row count", subject=partition_role)
    if not np.isfinite(scores).all():
        raise ScientificContractError(
            f"generated scores must be finite in {partition_role.value} partition",
            subject=ContractSubject.SCORES,
        )
    output = score_frame(row_ids, labels, scores)
    destination.parent.mkdir(parents=True, exist_ok=True)
    output.write_parquet(destination)
    return ScoreRecord(
        coordinate=request.checkpoint.coordinate,
        partition_role=partition_role,
        checkpoint_round=request.checkpoint.round_number,
        checkpoint_checksum=request.checkpoint.tensor_checksum,
        path=destination,
        checksum=checksum_file(destination),
        row_count=RowCount(output.height),
        feature_count=FeatureCount(len(request.feature_names)),
        serialization_format=SerializationFormat.PARQUET,
        scored_client=client,
    )


def _asset_name_for_partition(role: PartitionRole) -> FederatedScoreAssetName:
    match role:
        case PartitionRole.CALIBRATION:
            return FederatedScoreAssetName.CALIBRATION
        case PartitionRole.FUTURE_RECALIBRATION:
            return FederatedScoreAssetName.FUTURE_RECALIBRATION
        case PartitionRole.EVALUATION:
            return FederatedScoreAssetName.EVALUATION
        case PartitionRole.TRAIN:
            raise ScientificContractError("training rows are never scored", subject=role)
        case PartitionRole.STATIC_REFERENCE_RESERVE:
            raise ScientificContractError("static-reference reserve rows are never scored", subject=role)


def _write_complete_marker(directory: Path, invariant: FixedScoreInvariant) -> None:
    digest = canonical_checksum(invariant)
    (directory / FederatedScoreAssetName.COMPLETE.value).write_text(digest.value, encoding="utf-8")

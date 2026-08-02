"""Immutable, reusable-across-thresholds federated score generation."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np
import polars as pl
import torch
from safetensors.torch import load_file

from datp_core.artifacts.layout import scored_partition_roles
from datp_core.domain.enums import (
    CheckpointStatus,
    ContractSubject,
    PartitionRole,
    ScoreFrameColumn,
    SerializationFormat,
)
from datp_core.domain.errors import ArtifactIntegrityError, LeakageError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    FeatureCount,
    FeatureNameSequence,
    OutcomeLabelSequence,
    RowCount,
    checksum_file,
)
from datp_core.learning.autoencoder import LEARNING_DTYPE, ReconstructionAutoencoder, reconstruction_errors
from datp_core.learning.federated.checkpointing import CheckpointCandidate
from datp_core.populations.models import (
    OUTCOME_LABEL_COLUMN,
    STABLE_ROW_ID_COLUMN,
    ClientIdentity,
)
from datp_core.protocols.models import AutoencoderProtocol
from datp_core.runtime.compute import require_cuda_available
from datp_core.scoring.models import (
    FixedScoreInvariant,
    ScoreArtifactManifest,
    ScoreGenerationResult,
    ScoreRecord,
)
from datp_core.scoring.reconstruction import assert_higher_score_is_anomaly_evidence


class FederatedScoreAssetName(StrEnum):
    CALIBRATION = "calibration.parquet"
    EVALUATION = "evaluation.parquet"
    FUTURE_RECALIBRATION = "future_recalibration.parquet"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True)
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


def load_checkpoint_model(
    checkpoint: CheckpointCandidate,
    autoencoder: AutoencoderProtocol,
    device: torch.device,
) -> ReconstructionAutoencoder:
    require_cuda_available()
    model = ReconstructionAutoencoder(autoencoder.widths).to(device)
    state = load_file(str(checkpoint.tensor_path), device=str(device))
    model.load_state_dict(state, strict=True)
    model.eval()
    return model


def generate_federated_scores(request: ScoreGenerationRequest, device: torch.device) -> ScoreGenerationResult:
    """Generate calibration and evaluation reconstruction scores exactly once per checkpoint."""
    _validate_request(request)
    model = load_checkpoint_model(request.checkpoint, request.autoencoder, device)
    request.output_directory.mkdir(parents=True, exist_ok=True)

    scored_roles = scored_partition_roles(request.checkpoint.coordinate.split_protocol)
    records_by_role: dict[PartitionRole, list[ScoreRecord]] = {role: [] for role in scored_roles}
    for client_input in sorted(request.clients, key=lambda item: item.client):
        client_directory = request.output_directory / client_input.client.client_id
        for role in records_by_role:
            records_by_role[role].append(
                _score_partition(
                    frame=client_input.features_for(role),
                    client=client_input.client,
                    partition_role=role,
                    request=request,
                    model=model,
                    device=device,
                    destination=client_directory / _asset_name_for_partition(role),
                )
            )

    _assert_polarity(model, request, device)
    for records in records_by_role.values():
        for record in records:
            _assert_reload_equality(record)

    manifest = ScoreArtifactManifest(
        coordinate=request.checkpoint.coordinate,
        checkpoint_round=request.checkpoint.round_number,
        checkpoint_checksum=request.checkpoint.tensor_checksum,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        calibration_records=tuple(records_by_role[PartitionRole.CALIBRATION]),
        evaluation_records=tuple(records_by_role[PartitionRole.EVALUATION]),
        higher_score_means_greater_anomaly=True,
        future_recalibration_records=tuple(records_by_role.get(PartitionRole.FUTURE_RECALIBRATION, ())),
    )
    return ScoreGenerationResult(manifest=manifest, invariant=FixedScoreInvariant.from_manifest(manifest))


def reject_score_regeneration_per_threshold() -> None:
    raise LeakageError(
        "federated scores are frozen detector outputs and must not be regenerated per threshold method",
        subject=ContractSubject.THRESHOLD_METHOD,
    )


def reject_threshold_identity_in_score_coordinate(threshold_identity: str | None) -> None:
    if threshold_identity is not None:
        raise ScientificContractError(
            "federated score coordinates must not include threshold identity",
            subject=ContractSubject.THRESHOLD_IDENTITY,
        )


def reject_attack_calibration_rows(labels: OutcomeLabelSequence, benign_label: str) -> None:
    """Structural guard reused by downstream calibration construction: benign-only calibration."""
    if any(label != benign_label for label in labels):
        raise LeakageError(
            "attack-labelled rows cannot enter benign calibration construction",
            subject=ContractSubject.CALIBRATION,
        )


def _extract_feature_arrays(
    frame: pl.DataFrame,
    feature_names: FeatureNameSequence,
) -> tuple["np.ndarray[tuple[int, int], np.dtype[np.float32]]", tuple[str, ...], tuple[str, ...]]:
    matrix = frame.select(feature_names.as_list()).to_numpy().astype(LEARNING_DTYPE, copy=False)
    labels = tuple(str(v) for v in frame.get_column(OUTCOME_LABEL_COLUMN).to_list())
    row_ids = tuple(str(v) for v in frame.get_column(STABLE_ROW_ID_COLUMN).to_list())
    return matrix, labels, row_ids


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
    if len(set(client_ids)) != len(client_ids):
        raise ScientificContractError(
            "score generation cannot receive duplicate client identities",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    expected_roles = set(scored_partition_roles(request.checkpoint.coordinate.split_protocol))
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
    matrix, labels, row_ids = _extract_feature_arrays(frame, request.feature_names)
    scores = reconstruction_errors(model, matrix, batch_size=request.batch_size, device=device)
    if scores.shape[0] != matrix.shape[0]:
        raise ScientificContractError("score count must equal partition row count", subject=partition_role)
    output = pl.DataFrame(
        {
            ScoreFrameColumn.STABLE_ROW_ID.value: list(row_ids),
            ScoreFrameColumn.OUTCOME_LABEL.value: list(labels),
            ScoreFrameColumn.RECONSTRUCTION_ERROR.value: scores.tolist(),
        }
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    output.write_parquet(destination)
    return ScoreRecord(
        coordinate=request.checkpoint.coordinate,
        scored_client=client,
        partition_role=partition_role,
        checkpoint_round=request.checkpoint.round_number,
        checkpoint_checksum=request.checkpoint.tensor_checksum,
        path=destination,
        checksum=checksum_file(destination),
        row_count=RowCount(output.height),
        feature_count=FeatureCount(len(request.feature_names)),
        serialization_format=SerializationFormat.PARQUET,
    )


def _assert_polarity(model: ReconstructionAutoencoder, request: ScoreGenerationRequest, device: torch.device) -> None:
    for client_input in request.clients:
        matrix, _labels, _row_ids = _extract_feature_arrays(client_input.calibration_features, request.feature_names)
        if matrix.shape[0] == 0:
            continue
        assert_higher_score_is_anomaly_evidence(model, matrix, batch_size=request.batch_size, device=device)
        return
    raise ScientificContractError(
        "cannot verify anomaly-score polarity: no client provided calibration rows",
        subject=ContractSubject.SCORES,
    )


def _assert_reload_equality(record: ScoreRecord) -> None:
    if not record.path.is_file():
        raise ArtifactIntegrityError("score artifact is missing", subject=ContractSubject.ARTIFACT_PATH)
    original = pl.read_parquet(record.path)
    reloaded = pl.read_parquet(record.path)
    if original.shape != reloaded.shape or not original.equals(reloaded):
        raise ArtifactIntegrityError("score reload equality failed", subject=ContractSubject.ARTIFACT_PATH)
    if checksum_file(record.path) != record.checksum:
        raise ArtifactIntegrityError("score checksum changed after write", subject=ContractSubject.ARTIFACT_PATH)
    if original.height != record.row_count.value:
        raise ArtifactIntegrityError("score artifact row count mismatch", subject=ContractSubject.ARTIFACT_PATH)


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

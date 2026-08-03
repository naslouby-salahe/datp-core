"""Immutable, reusable-across-thresholds federated score generation."""

from dataclasses import dataclass
from enum import StrEnum
from os import replace as atomic_replace
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

import numpy as np
import numpy.typing as npt
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
    RowCount,
    checksum_file,
    checksum_text,
)
from datp_core.learning.autoencoder import LEARNING_DTYPE, ReconstructionAutoencoder, reconstruction_errors
from datp_core.learning.federated.checkpointing import CheckpointCandidate
from datp_core.populations.models import (
    OUTCOME_LABEL_COLUMN,
    STABLE_ROW_ID_COLUMN,
    ClientIdentity,
    PopulationOutcomeLabel,
)
from datp_core.protocols.models import AutoencoderProtocol
from datp_core.scoring.models import (
    FixedScoreInvariant,
    ScoreArtifactManifest,
    ScoreGenerationResult,
    ScoreRecord,
    _record_set_checksum,
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
    if not checkpoint.tensor_path.is_file():
        raise ArtifactIntegrityError(
            "checkpoint tensor file is missing",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    if checksum_file(checkpoint.tensor_path) != checkpoint.tensor_checksum:
        raise ArtifactIntegrityError(
            "checkpoint tensor checksum mismatch before loading",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    model = ReconstructionAutoencoder(autoencoder.widths).to(device)
    state = load_file(str(checkpoint.tensor_path), device=str(device))
    model.load_state_dict(state, strict=True)
    model.eval()
    return model


def generate_federated_scores(request: ScoreGenerationRequest, device: torch.device) -> ScoreGenerationResult:
    _validate_request(request)
    model = load_checkpoint_model(request.checkpoint, request.autoencoder, device)

    staging = _new_staging_directory(request.output_directory)
    try:
        scored_roles = scored_partition_roles(request.checkpoint.coordinate.split_protocol)
        records_by_role: dict[PartitionRole, list[ScoreRecord]] = {role: [] for role in scored_roles}
        for client_input in sorted(request.clients, key=lambda item: item.client):
            client_directory = staging / client_input.client.client_id
            for role in records_by_role:
                frame = client_input.features_for(role)
                _validate_frame(frame, role, request.feature_names)
                result = _score_partition(
                    frame=frame,
                    client=client_input.client,
                    partition_role=role,
                    request=request,
                    model=model,
                    device=device,
                    destination=client_directory / _asset_name_for_partition(role).value,
                )
                records_by_role[role].append(result)

        for records in records_by_role.values():
            for record in records:
                _assert_reload_equality(record)

        invariant = FixedScoreInvariant(
            model_checksum=request.checkpoint.tensor_checksum,
            calibration_score_set_checksum=_record_set_checksum(tuple(records_by_role[PartitionRole.CALIBRATION])),
            evaluation_score_set_checksum=_record_set_checksum(tuple(records_by_role[PartitionRole.EVALUATION])),
            preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
            future_recalibration_score_set_checksum=(
                _record_set_checksum(tuple(records_by_role.get(PartitionRole.FUTURE_RECALIBRATION, [])))
                if PartitionRole.FUTURE_RECALIBRATION in records_by_role
                and records_by_role[PartitionRole.FUTURE_RECALIBRATION]
                else None
            ),
        )
        _write_complete_marker(staging, invariant)
        _replace_directory(staging, request.output_directory)
    except Exception:
        _cleanup_staging(staging)
        raise

    rebased_by_role: dict[PartitionRole, tuple[ScoreRecord, ...]] = {}
    for role, records in records_by_role.items():
        rebased: list[ScoreRecord] = []
        for record in records:
            path = (
                request.output_directory
                / record.scored_client.client_id
                / _asset_name_for_partition(record.partition_role).value
            )
            if not path.is_file():
                raise ArtifactIntegrityError(
                    "published score partition missing after atomic replace",
                    subject=ContractSubject.SCORES,
                )
            rebased.append(
                ScoreRecord(
                    coordinate=record.coordinate,
                    scored_client=record.scored_client,
                    partition_role=record.partition_role,
                    checkpoint_round=record.checkpoint_round,
                    checkpoint_checksum=record.checkpoint_checksum,
                    path=path,
                    checksum=checksum_file(path),
                    row_count=record.row_count,
                    feature_count=record.feature_count,
                    serialization_format=record.serialization_format,
                )
            )
        rebased_by_role[role] = tuple(rebased)
    manifest = ScoreArtifactManifest(
        coordinate=request.checkpoint.coordinate,
        checkpoint_round=request.checkpoint.round_number,
        checkpoint_checksum=request.checkpoint.tensor_checksum,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        calibration_records=rebased_by_role[PartitionRole.CALIBRATION],
        evaluation_records=rebased_by_role[PartitionRole.EVALUATION],
        future_recalibration_records=rebased_by_role.get(PartitionRole.FUTURE_RECALIBRATION, ()),
    )
    return ScoreGenerationResult(manifest=manifest, invariant=invariant)


def _validate_frame(
    frame: pl.DataFrame,
    role: PartitionRole,
    feature_names: FeatureNameSequence,
) -> None:
    if frame.height == 0 and role in {PartitionRole.CALIBRATION, PartitionRole.FUTURE_RECALIBRATION}:
        raise ScientificContractError(
            f"{role.value} partition must not be empty",
            subject=ContractSubject.ROWS,
        )
    if STABLE_ROW_ID_COLUMN not in frame.columns:
        raise ScientificContractError(
            f"frame missing stable row ID column '{STABLE_ROW_ID_COLUMN}'",
            subject=ContractSubject.SCHEMA,
        )
    if OUTCOME_LABEL_COLUMN not in frame.columns:
        raise ScientificContractError(
            f"frame missing outcome label column '{OUTCOME_LABEL_COLUMN}'",
            subject=ContractSubject.SCHEMA,
        )
    row_ids = tuple(str(v) for v in frame.get_column(STABLE_ROW_ID_COLUMN).to_list())
    if any(v is None for v in frame.get_column(STABLE_ROW_ID_COLUMN).to_list()):
        raise ScientificContractError(
            f"stable row IDs must not be null in {role.value} partition",
            subject=ContractSubject.ROWS,
        )
    if len(set(row_ids)) != len(row_ids):
        raise ScientificContractError(
            f"stable row IDs must be unique within {role.value} partition",
            subject=ContractSubject.ROWS,
        )
    labels = tuple(str(v) for v in frame.get_column(OUTCOME_LABEL_COLUMN).to_list())
    if any(v is None for v in frame.get_column(OUTCOME_LABEL_COLUMN).to_list()):
        raise ScientificContractError(
            f"outcome labels must not be null in {role.value} partition",
            subject=ContractSubject.LABEL,
        )
    if role in {PartitionRole.CALIBRATION, PartitionRole.FUTURE_RECALIBRATION}:
        if any(label != PopulationOutcomeLabel.BENIGN.value for label in labels):
            raise LeakageError(
                "attack-labelled rows cannot enter benign calibration construction",
                subject=ContractSubject.CALIBRATION,
            )
    missing = [name for name in feature_names if name not in frame.columns]
    if missing:
        raise ScientificContractError(
            f"{role.value} frame missing declared features: {', '.join(missing)}",
            subject=ContractSubject.FEATURES,
        )
    for name in feature_names:
        dtype = frame.schema[name]
        if not dtype.is_numeric():
            raise ScientificContractError(
                f"feature column '{name}' in {role.value} partition must be numeric, got {dtype}",
                subject=ContractSubject.FEATURES,
            )
        col = frame.get_column(name)
        if any(not np.isfinite(v) for v in col.to_list() if v is not None):
            raise ScientificContractError(
                f"feature column '{name}' in {role.value} partition contains non-finite values",
                subject=ContractSubject.FEATURES,
            )


def _extract_feature_arrays(
    frame: pl.DataFrame,
    feature_names: FeatureNameSequence,
) -> tuple[npt.NDArray[np.float32], tuple[str, ...], tuple[str, ...]]:
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
    if not np.isfinite(scores).all():
        raise ScientificContractError(
            f"generated scores must be finite in {partition_role.value} partition",
            subject=ContractSubject.SCORES,
        )
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


def _assert_reload_equality(record: ScoreRecord) -> None:
    if not record.path.is_file():
        raise ArtifactIntegrityError("score artifact is missing", subject=ContractSubject.ARTIFACT_PATH)
    reloaded = pl.read_parquet(record.path)
    if checksum_file(record.path) != record.checksum:
        raise ArtifactIntegrityError("score checksum changed after write", subject=ContractSubject.ARTIFACT_PATH)
    if reloaded.height != record.row_count.value:
        raise ArtifactIntegrityError("score artifact row count mismatch", subject=ContractSubject.ARTIFACT_PATH)
    expected_columns = (
        ScoreFrameColumn.STABLE_ROW_ID.value,
        ScoreFrameColumn.OUTCOME_LABEL.value,
        ScoreFrameColumn.RECONSTRUCTION_ERROR.value,
    )
    if tuple(reloaded.columns) != expected_columns:
        raise ArtifactIntegrityError("score artifact schema mismatch", subject=ContractSubject.SCHEMA)
    expected_dtypes = (pl.Utf8, pl.Utf8, pl.Float64)
    observed_dtypes = tuple(reloaded.schema[col] for col in expected_columns)
    if observed_dtypes != expected_dtypes:
        raise ArtifactIntegrityError("score artifact column dtype mismatch", subject=ContractSubject.SCHEMA)


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


def _new_staging_directory(target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    return Path(mkdtemp(prefix=f".{target.name}.", dir=target.parent))


def _replace_directory(staging: Path, target: Path) -> None:
    if target.exists():
        rmtree(target)
    atomic_replace(staging, target)


def _cleanup_staging(staging: Path) -> None:
    if staging.exists():
        rmtree(staging, ignore_errors=True)


def _write_complete_marker(directory: Path, invariant: FixedScoreInvariant) -> None:
    import json

    payload = json.dumps(
        {
            "model_checksum": invariant.model_checksum.value,
            "calibration_score_set_checksum": invariant.calibration_score_set_checksum.value,
            "evaluation_score_set_checksum": invariant.evaluation_score_set_checksum.value,
            "preprocessing_state_set_checksum": invariant.preprocessing_state_set_checksum.value,
            "split_manifest_checksum": invariant.split_manifest_checksum.value,
            "future_recalibration_score_set_checksum": (
                invariant.future_recalibration_score_set_checksum.value
                if invariant.future_recalibration_score_set_checksum is not None
                else None
            ),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = checksum_text(payload)
    (directory / FederatedScoreAssetName.COMPLETE.value).write_text(digest.value, encoding="utf-8")

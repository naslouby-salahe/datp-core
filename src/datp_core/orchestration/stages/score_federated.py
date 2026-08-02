"""Stage: score federated calibration and evaluation partitions with the selected checkpoint."""

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

import polars as pl

from datp_core.artifacts.layout import scored_partition_roles
from datp_core.artifacts.store import AtomicPublication, publish_atomically
from datp_core.domain.enums import (
    ContractSubject,
    PartitionRole,
    PublicationStatus,
    SerializationFormat,
    SplitProtocolId,
    StageOperationId,
)
from datp_core.domain.errors import ArtifactIntegrityError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    FeatureCount,
    FeatureNameSequence,
    RowCount,
    checksum_file,
    checksum_text,
)
from datp_core.learning.federated.checkpointing import CheckpointCandidate
from datp_core.protocols.models import AutoencoderProtocol
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.scoring.generation import (
    ClientScoringInput,
    FederatedScoreAssetName,
    ScoreGenerationRequest,
    generate_federated_scores,
)
from datp_core.scoring.models import FixedScoreInvariant, ScoreArtifactManifest, ScoreGenerationResult, ScoreRecord


@dataclass(frozen=True, slots=True)
class ScoreFederatedRequest:
    checkpoint: CheckpointCandidate
    autoencoder: AutoencoderProtocol
    feature_names: FeatureNameSequence
    clients: tuple[ClientScoringInput, ...]
    batch_size: BatchSize
    output_directory: Path
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    overwrite: bool


@dataclass(frozen=True, slots=True)
class ScoreFederatedStageResult:
    stage: StageOperationId
    publication_status: PublicationStatus
    result: ScoreGenerationResult


def score_federated_stage(request: ScoreFederatedRequest) -> ScoreFederatedStageResult:
    device = resolve_cuda_device()
    holder: dict[str, ScoreGenerationResult] = {}

    def write(temporary: Path) -> None:
        result = generate_federated_scores(
            ScoreGenerationRequest(
                checkpoint=request.checkpoint,
                autoencoder=request.autoencoder,
                feature_names=request.feature_names,
                clients=request.clients,
                batch_size=request.batch_size,
                output_directory=temporary,
                preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
                split_manifest_checksum=request.split_manifest_checksum,
            ),
            device,
        )
        digest = _score_complete_digest(result)
        (temporary / FederatedScoreAssetName.COMPLETE.value).write_text(digest.value, encoding="utf-8")
        holder["result"] = result

    reused = publish_atomically(
        AtomicPublication(
            target=request.output_directory,
            overwrite=request.overwrite,
            is_reusable=lambda directory: _is_reusable(directory, request),
            write=write,
            remove_target=rmtree,
        )
    )
    if reused:
        result = _load_reused_scores(request)
        status = PublicationStatus.REUSED
    else:
        result = _rebase_scoring(holder["result"], request.output_directory)
        status = PublicationStatus.PUBLISHED
    return ScoreFederatedStageResult(stage=StageOperationId.SCORE_FEDERATED, publication_status=status, result=result)


def _score_complete_digest(result: ScoreGenerationResult) -> Checksum:
    records = tuple(
        record
        for role in scored_partition_roles(result.manifest.coordinate.split_protocol)
        for record in result.manifest.records_for(role)
    )
    values = (result.invariant.model_checksum.value, *(record.checksum.value for record in records))
    return checksum_text("|".join(values))


def _client_paths(output_directory: Path, request: ScoreFederatedRequest) -> list[tuple[str, tuple[Path, ...]]]:
    return [
        (
            client_input.client.client_id,
            tuple(
                output_directory / client_input.client.client_id / _asset_name_for_partition(role).value
                for role in scored_partition_roles(request.checkpoint.coordinate.split_protocol)
            ),
        )
        for client_input in sorted(request.clients, key=lambda item: item.client.client_id)
    ]


def _is_reusable(directory: Path, request: ScoreFederatedRequest) -> bool:
    complete = directory / FederatedScoreAssetName.COMPLETE.value
    if not complete.is_file():
        return False
    for _, paths in _client_paths(directory, request):
        if any(not path.is_file() for path in paths):
            return False
    return True


def _build_records(
    output_directory: Path,
    request: ScoreFederatedRequest,
    partition_role: PartitionRole,
) -> tuple[ScoreRecord, ...]:
    records: list[ScoreRecord] = []
    for client_input in sorted(request.clients, key=lambda item: item.client.client_id):
        client_directory = output_directory / client_input.client.client_id
        path = client_directory / _asset_name_for_partition(partition_role).value
        if not path.is_file():
            raise ArtifactIntegrityError(
                f"expected federated score partition is missing: {path}",
                subject=ContractSubject.ARTIFACT_PATH,
            )
        frame = pl.read_parquet(path)
        records.append(
            ScoreRecord(
                coordinate=request.checkpoint.coordinate,
                scored_client=client_input.client,
                partition_role=partition_role,
                checkpoint_round=request.checkpoint.round_number,
                checkpoint_checksum=request.checkpoint.tensor_checksum,
                path=path,
                checksum=checksum_file(path),
                row_count=RowCount(frame.height),
                feature_count=FeatureCount(len(request.feature_names)),
                serialization_format=SerializationFormat.PARQUET,
            )
        )
    return tuple(records)


def _load_reused_scores(request: ScoreFederatedRequest) -> ScoreGenerationResult:
    calibration_records = _build_records(request.output_directory, request, PartitionRole.CALIBRATION)
    evaluation_records = _build_records(request.output_directory, request, PartitionRole.EVALUATION)
    future_records = (
        _build_records(request.output_directory, request, PartitionRole.FUTURE_RECALIBRATION)
        if request.checkpoint.coordinate.split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
        else ()
    )
    manifest = ScoreArtifactManifest(
        coordinate=request.checkpoint.coordinate,
        checkpoint_round=request.checkpoint.round_number,
        checkpoint_checksum=request.checkpoint.tensor_checksum,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        calibration_records=calibration_records,
        evaluation_records=evaluation_records,
        higher_score_means_greater_anomaly=True,
        future_recalibration_records=future_records,
    )
    return ScoreGenerationResult(manifest=manifest, invariant=FixedScoreInvariant.from_manifest(manifest))


def _rebase_scoring(result: ScoreGenerationResult, output_directory: Path) -> ScoreGenerationResult:
    calibration_records = tuple(
        _rebased_record(record, output_directory) for record in result.manifest.calibration_records
    )
    evaluation_records = tuple(
        _rebased_record(record, output_directory) for record in result.manifest.evaluation_records
    )
    future_records = tuple(
        _rebased_record(record, output_directory) for record in result.manifest.future_recalibration_records
    )
    manifest = ScoreArtifactManifest(
        coordinate=result.manifest.coordinate,
        checkpoint_round=result.manifest.checkpoint_round,
        checkpoint_checksum=result.manifest.checkpoint_checksum,
        preprocessing_state_set_checksum=result.manifest.preprocessing_state_set_checksum,
        split_manifest_checksum=result.manifest.split_manifest_checksum,
        calibration_records=calibration_records,
        evaluation_records=evaluation_records,
        higher_score_means_greater_anomaly=result.manifest.higher_score_means_greater_anomaly,
        future_recalibration_records=future_records,
    )
    return ScoreGenerationResult(manifest=manifest, invariant=FixedScoreInvariant.from_manifest(manifest))


def _rebased_record(record: ScoreRecord, output_directory: Path) -> ScoreRecord:
    path = output_directory / record.scored_client.client_id / _asset_name_for_partition(record.partition_role).value
    if not path.is_file():
        raise ArtifactIntegrityError(
            "published score partition missing after atomic replace",
            subject=ContractSubject.SCORES,
        )
    return ScoreRecord(
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


def _asset_name_for_partition(role: PartitionRole) -> FederatedScoreAssetName:
    match role:
        case PartitionRole.CALIBRATION:
            return FederatedScoreAssetName.CALIBRATION
        case PartitionRole.FUTURE_RECALIBRATION:
            return FederatedScoreAssetName.FUTURE_RECALIBRATION
        case PartitionRole.EVALUATION:
            return FederatedScoreAssetName.EVALUATION
        case PartitionRole.TRAIN:
            raise ArtifactIntegrityError("training rows are never score assets", subject=ContractSubject.SCORES)
        case PartitionRole.STATIC_REFERENCE_RESERVE:
            raise ArtifactIntegrityError(
                "static-reference reserve rows are never score assets",
                subject=ContractSubject.SCORES,
            )

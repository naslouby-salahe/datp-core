"""Stage: score federated calibration and evaluation partitions with the selected checkpoint."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import polars as pl

from datp_core.artifacts.layout import scored_partition_roles
from datp_core.domain.enums import (
    ContractSubject,
    PartitionRole,
    PublicationStatus,
    SerializationFormat,
    SplitProtocolId,
    StageOperationId,
)
from datp_core.domain.errors import ArtifactIntegrityError
from datp_core.domain.values import BatchSize, Checksum, FeatureCount, FeatureNameSequence, RowCount, checksum_file
from datp_core.learning.federated.models import CheckpointCandidate
from datp_core.pipeline.publication.codec import ArtifactPublication, publish_artifact
from datp_core.protocols.models import AutoencoderProtocol
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.scoring.generation import (
    ClientScoringInput,
    FederatedScoreAssetName,
    ScoreGenerationRequest,
    generate_federated_scores,
)
from datp_core.scoring.models import ScoreArtifactManifest, ScoreGenerationResult, ScoreRecord


@dataclass(slots=True, eq=False)
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
    stage: ClassVar[StageOperationId] = StageOperationId.SCORE_FEDERATED
    publication_status: PublicationStatus
    result: ScoreGenerationResult


@dataclass(frozen=True, slots=True)
class _FederatedScoringCodec:
    def write(self, request: ScoreFederatedRequest, directory: Path) -> ScoreGenerationResult:
        return generate_federated_scores(
            ScoreGenerationRequest(
                checkpoint=request.checkpoint,
                autoencoder=request.autoencoder,
                feature_names=request.feature_names,
                clients=request.clients,
                batch_size=request.batch_size,
                output_directory=directory,
                preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
                split_manifest_checksum=request.split_manifest_checksum,
            ),
            resolve_cuda_device(),
        )

    def validate(self, request: ScoreFederatedRequest, directory: Path) -> bool:
        return _is_reusable(directory, request)

    def load(self, request: ScoreFederatedRequest, directory: Path) -> ScoreGenerationResult:
        return _load_reused_scores(request, directory)

    def rebase(self, result: ScoreGenerationResult, directory: Path) -> ScoreGenerationResult:
        return _rebase_scoring(result, directory)


def score_federated_stage(request: ScoreFederatedRequest) -> ScoreFederatedStageResult:
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=request,
            codec=_FederatedScoringCodec(),
            overwrite=request.overwrite,
            complete_marker=FederatedScoreAssetName.COMPLETE.value,
        )
    )
    return ScoreFederatedStageResult(
        publication_status=publication.status,
        result=publication.value,
    )


def _client_paths(
    output_directory: Path,
    request: ScoreFederatedRequest,
) -> tuple[tuple[Path, ...], ...]:
    return tuple(
        tuple(
            output_directory / client_input.client.client_id / _asset_name_for_partition(role).value
            for role in scored_partition_roles(request.checkpoint.coordinate.split_protocol)
        )
        for client_input in sorted(request.clients, key=lambda item: item.client)
    )


def _is_reusable(directory: Path, request: ScoreFederatedRequest) -> bool:
    complete = directory / FederatedScoreAssetName.COMPLETE.value
    return complete.is_file() and all(path.is_file() for paths in _client_paths(directory, request) for path in paths)


def _build_records(
    output_directory: Path,
    request: ScoreFederatedRequest,
    partition_role: PartitionRole,
) -> tuple[ScoreRecord, ...]:
    records: list[ScoreRecord] = []
    for client_input in sorted(request.clients, key=lambda item: item.client):
        path = output_directory / client_input.client.client_id / _asset_name_for_partition(partition_role).value
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


def _load_reused_scores(
    request: ScoreFederatedRequest,
    output_directory: Path,
) -> ScoreGenerationResult:
    calibration_records = _build_records(output_directory, request, PartitionRole.CALIBRATION)
    evaluation_records = _build_records(output_directory, request, PartitionRole.EVALUATION)
    future_records = (
        _build_records(output_directory, request, PartitionRole.FUTURE_RECALIBRATION)
        if request.checkpoint.coordinate.split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
        else ()
    )
    return ScoreGenerationResult(
        manifest=ScoreArtifactManifest(
            coordinate=request.checkpoint.coordinate,
            checkpoint_round=request.checkpoint.round_number,
            checkpoint_checksum=request.checkpoint.tensor_checksum,
            preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
            calibration_records=calibration_records,
            evaluation_records=evaluation_records,
            future_recalibration_records=future_records,
        )
    )


def _rebase_scoring(result: ScoreGenerationResult, output_directory: Path) -> ScoreGenerationResult:
    manifest = result.manifest
    return ScoreGenerationResult(
        manifest=ScoreArtifactManifest(
            coordinate=manifest.coordinate,
            checkpoint_round=manifest.checkpoint_round,
            checkpoint_checksum=manifest.checkpoint_checksum,
            preprocessing_state_set_checksum=manifest.preprocessing_state_set_checksum,
            split_manifest_checksum=manifest.split_manifest_checksum,
            calibration_records=tuple(
                _rebased_record(record, output_directory) for record in manifest.calibration_records
            ),
            evaluation_records=tuple(
                _rebased_record(record, output_directory) for record in manifest.evaluation_records
            ),
            future_recalibration_records=tuple(
                _rebased_record(record, output_directory) for record in manifest.future_recalibration_records
            ),
        )
    )


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

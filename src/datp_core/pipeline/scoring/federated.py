"""Federated reconstruction-score generation, persistence, and reuse."""

from dataclasses import dataclass, replace
from pathlib import Path
from shutil import rmtree

import polars as pl
import torch

from datp_core.domain.enums import (
    CheckpointStatus,
    ContractSubject,
    PartitionRole,
    PopulationId,
    SerializationFormat,
    SplitProtocolId,
)
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values import FeatureCount, RowCount, checksum_file
from datp_core.pipeline.publication.service import ArtifactPublication, FunctionalArtifactCodec, publish_artifact
from datp_core.pipeline.scoring.frames import (
    load_checkpoint_model,
    score_and_persist_autoencoder_frame,
    validate_persisted_score_frame,
)
from datp_core.pipeline.scoring.models import (
    FederatedScoreArtifactManifest,
    FederatedScoreAssetName,
    FederatedScoreGenerationResult,
    FederatedScoreRecord,
    GenerateFederatedScoresRequest,
    ScoreGenerationRequest,
)
from datp_core.preprocessing.contracts import scored_partition_roles
from datp_core.protocols.inference import (
    FixedScoreInvariant,
    ScoreArtifactManifest,
    ScoreGenerationResult,
    ScoreRecord,
    record_set_checksum,
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

    def records_for(self, role: PartitionRole) -> list[FederatedScoreRecord]:
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

    def append(self, role: PartitionRole, record: FederatedScoreRecord) -> None:
        self.records_for(role).append(record)

    def extend(self, role: PartitionRole, records: tuple[FederatedScoreRecord, ...]) -> None:
        self.records_for(role).extend(records)

    def immutable_records_for(self, role: PartitionRole) -> tuple[FederatedScoreRecord, ...]:
        return tuple(self.records_for(role))


def generate_federated_scores(request: ScoreGenerationRequest, device: torch.device) -> FederatedScoreGenerationResult:
    _validate_request(request)
    _require_empty_output_directory(request.output_directory)
    model = load_checkpoint_model(request.checkpoint, request.autoencoder, device)
    scored_roles = scored_partition_roles(request.scored_split_protocol)
    records = _ScoreRecordInventory.empty()
    for client_input in sorted(request.clients, key=lambda item: item.client):
        client_directory = request.output_directory / client_input.client.client_id
        for role in scored_roles:
            persisted = score_and_persist_autoencoder_frame(
                frame=client_input.features_for(role),
                partition_role=role,
                feature_names=request.feature_names,
                model=model,
                batch_size=request.batch_size,
                device=device,
                destination=client_directory / _asset_name_for_partition(role).value,
            )
            records.append(
                role,
                ScoreRecord(
                    coordinate=request.checkpoint.coordinate,
                    partition_role=role,
                    checkpoint_round=request.checkpoint.round_number,
                    checkpoint_checksum=request.checkpoint.tensor_checksum,
                    path=persisted.path,
                    checksum=persisted.checksum,
                    row_count=persisted.row_count,
                    feature_count=persisted.feature_count,
                    serialization_format=SerializationFormat.PARQUET,
                    scored_client=client_input.client,
                ),
            )
    invariant = _fixed_score_invariant(request, records)
    _write_complete_marker(request.output_directory, invariant)
    return _result_from_inventory(request, records)


def write_federated_scores(
    request: ScoreGenerationRequest,
    directory: Path,
    device: torch.device,
) -> FederatedScoreGenerationResult:
    return generate_federated_scores(replace(request, output_directory=directory), device)


def materialize_federated_scores(
    request: ScoreGenerationRequest,
    device: torch.device,
) -> FederatedScoreGenerationResult:
    directory = request.output_directory
    if federated_scoring_is_reusable(request, directory):
        return load_reused_federated_scores(request, directory)
    _remove_incomplete_output(directory)
    return generate_federated_scores(request, device)


def federated_scoring_is_reusable(request: ScoreGenerationRequest, directory: Path) -> bool:
    complete = directory / FederatedScoreAssetName.COMPLETE.value
    if not complete.is_file() or not all(path.is_file() for path in _client_paths(directory, request)):
        return False
    try:
        loaded = load_reused_federated_scores(request, directory)
        expected = canonical_checksum(_invariant_from_manifest(loaded.manifest))
        return complete.read_text(encoding="utf-8").strip() == expected.value
    except (ArtifactIntegrityError, OSError, ScientificContractError, ValueError):
        return False


def load_reused_federated_scores(
    request: ScoreGenerationRequest,
    directory: Path,
) -> FederatedScoreGenerationResult:
    records = _ScoreRecordInventory.empty()
    for role in scored_partition_roles(request.scored_split_protocol):
        records.extend(role, _build_records(directory, request, role))
    return _result_from_inventory(request, records)


def rebase_federated_scores(result: FederatedScoreGenerationResult, directory: Path) -> FederatedScoreGenerationResult:
    manifest = result.manifest
    return ScoreGenerationResult(
        manifest=ScoreArtifactManifest(
            coordinate=manifest.coordinate,
            scored_split_protocol=manifest.scored_split_protocol,
            checkpoint_round=manifest.checkpoint_round,
            checkpoint_checksum=manifest.checkpoint_checksum,
            preprocessing_state_set_checksum=manifest.preprocessing_state_set_checksum,
            split_manifest_checksum=manifest.split_manifest_checksum,
            calibration_records=tuple(_rebased_record(record, directory) for record in manifest.calibration_records),
            evaluation_records=tuple(_rebased_record(record, directory) for record in manifest.evaluation_records),
            future_recalibration_records=tuple(
                _rebased_record(record, directory) for record in manifest.future_recalibration_records
            ),
        )
    )


def publish_federated_scores(request: GenerateFederatedScoresRequest) -> FederatedScoreGenerationResult:
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=request,
            codec=FunctionalArtifactCodec(
                writer=lambda item, directory: write_federated_scores(
                    _federated_request(item, directory), directory, resolve_cuda_device()
                ),
                validator=lambda item, directory: federated_scoring_is_reusable(
                    _federated_request(item, directory), directory
                ),
                loader=lambda item, directory: load_reused_federated_scores(
                    _federated_request(item, directory), directory
                ),
                rebaser=rebase_federated_scores,
            ),
            overwrite=request.overwrite,
            complete_marker=FederatedScoreAssetName.COMPLETE.value,
        )
    )
    return publication.value


def _federated_request(request: GenerateFederatedScoresRequest, directory: Path) -> ScoreGenerationRequest:
    return ScoreGenerationRequest(
        checkpoint=request.checkpoint,
        scored_split_protocol=request.checkpoint.coordinate.split_protocol,
        autoencoder=request.autoencoder,
        feature_names=request.feature_names,
        clients=request.clients,
        batch_size=request.batch_size,
        output_directory=directory,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
    )


def _result_from_inventory(
    request: ScoreGenerationRequest,
    records: _ScoreRecordInventory,
) -> FederatedScoreGenerationResult:
    return ScoreGenerationResult(
        manifest=ScoreArtifactManifest(
            coordinate=request.checkpoint.coordinate,
            scored_split_protocol=request.scored_split_protocol,
            checkpoint_round=request.checkpoint.round_number,
            checkpoint_checksum=request.checkpoint.tensor_checksum,
            preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
            calibration_records=records.immutable_records_for(PartitionRole.CALIBRATION),
            evaluation_records=records.immutable_records_for(PartitionRole.EVALUATION),
            future_recalibration_records=records.immutable_records_for(PartitionRole.FUTURE_RECALIBRATION),
        )
    )


def _client_paths(output_directory: Path, request: ScoreGenerationRequest) -> tuple[Path, ...]:
    return tuple(
        output_directory / client_input.client.client_id / _asset_name_for_partition(role).value
        for client_input in sorted(request.clients, key=lambda item: item.client)
        for role in scored_partition_roles(request.scored_split_protocol)
    )


def _build_records(
    output_directory: Path,
    request: ScoreGenerationRequest,
    partition_role: PartitionRole,
) -> tuple[FederatedScoreRecord, ...]:
    records: list[FederatedScoreRecord] = []
    for client_input in sorted(request.clients, key=lambda item: item.client):
        path = output_directory / client_input.client.client_id / _asset_name_for_partition(partition_role).value
        if not path.is_file():
            raise ArtifactIntegrityError(
                f"expected federated score partition is missing: {path}",
                subject=ContractSubject.ARTIFACT_PATH,
            )
        frame = pl.read_parquet(path)
        record = ScoreRecord(
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
        validate_persisted_score_frame(record.path, record.checksum, record.row_count)
        records.append(record)
    return tuple(records)


def _rebased_record(record: FederatedScoreRecord, output_directory: Path) -> FederatedScoreRecord:
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


def _remove_incomplete_output(directory: Path) -> None:
    if directory.is_dir():
        rmtree(directory)
    elif directory.exists():
        directory.unlink()


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
        calibration_score_set_checksum=record_set_checksum(records.immutable_records_for(PartitionRole.CALIBRATION)),
        evaluation_score_set_checksum=record_set_checksum(records.immutable_records_for(PartitionRole.EVALUATION)),
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        future_recalibration_score_set_checksum=(record_set_checksum(future_records) if future_records else None),
    )


def _invariant_from_manifest(manifest: FederatedScoreArtifactManifest) -> FixedScoreInvariant:
    return FixedScoreInvariant(
        model_checksum=manifest.checkpoint_checksum,
        calibration_score_set_checksum=record_set_checksum(manifest.calibration_records),
        evaluation_score_set_checksum=record_set_checksum(manifest.evaluation_records),
        preprocessing_state_set_checksum=manifest.preprocessing_state_set_checksum,
        split_manifest_checksum=manifest.split_manifest_checksum,
        future_recalibration_score_set_checksum=(
            record_set_checksum(manifest.future_recalibration_records)
            if manifest.future_recalibration_records
            else None
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
    if not _split_binding_is_valid(request):
        raise ScientificContractError(
            "scored split must match checkpoint training split except for the matched Edge temporal static reference",
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
    expected_roles = scored_partition_roles(request.scored_split_protocol)
    for client in request.clients:
        for role in expected_roles:
            client.features_for(role)


def _split_binding_is_valid(request: ScoreGenerationRequest) -> bool:
    coordinate = request.checkpoint.coordinate
    if request.scored_split_protocol is coordinate.split_protocol:
        return request.checkpoint.split_manifest_checksum == request.split_manifest_checksum
    return (
        coordinate.population is PopulationId.EDGE_TEMPORAL_GROUPS
        and coordinate.split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
        and request.scored_split_protocol is SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE
        and request.checkpoint.split_manifest_checksum != request.split_manifest_checksum
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

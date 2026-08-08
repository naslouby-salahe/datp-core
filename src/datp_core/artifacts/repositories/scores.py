"""Persist and reload centralized and federated reconstruction-score results."""

from enum import StrEnum
from pathlib import Path
from shutil import rmtree

from datp_core.artifacts.provenance import Checksum, checksum_file
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.artifacts.serializers.parquet import read_frame, write_frame
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ArtifactIntegrityError
from datp_core.core.identifiers import PartitionRole
from datp_core.core.numeric import FeatureCount, RowCount
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.scoring.contracts import (
    CentralizedScoringResult,
    ClientScoredPartition,
    FederatedScoringResult,
    ScoredPartition,
)
from datp_core.detector.training.contracts import CentralizedTrainingCoordinate, FederatedTrainingCoordinate


class ScoreRepositoryAsset(StrEnum):
    MANIFEST = "manifest.json"
    COMPLETE = "COMPLETE"


class ScorePartitionAsset(StrEnum):
    CALIBRATION = "calibration.parquet"
    EVALUATION = "evaluation.parquet"
    FUTURE_RECALIBRATION = "future_recalibration.parquet"

    @classmethod
    def for_role(cls, role: PartitionRole) -> "ScorePartitionAsset":
        return cls(role.value + ".parquet")


class PersistedScorePartition(StrictModel):
    role: PartitionRole
    relative_path: str
    checksum: Checksum
    row_count: RowCount
    feature_count: FeatureCount
    client: ClientIdentity | None


class FederatedScoreManifest(StrictModel):
    coordinate: FederatedTrainingCoordinate
    scored_split_protocol: object
    checkpoint_round: object
    checkpoint_checksum: Checksum
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    partitions: tuple[PersistedScorePartition, ...]


class CentralizedScoreManifest(StrictModel):
    coordinate: CentralizedTrainingCoordinate
    checkpoint_round: object
    checkpoint_checksum: Checksum
    preprocessing_state_checksum: Checksum
    split_manifest_checksum: Checksum
    partitions: tuple[PersistedScorePartition, ...]


class FederatedScorePublication(StrictModel):
    directory: Path
    manifest: FederatedScoreManifest
    complete_digest: Checksum


class CentralizedScorePublication(StrictModel):
    directory: Path
    manifest: CentralizedScoreManifest
    complete_digest: Checksum


def publish_federated_scores(
    result: FederatedScoringResult,
    directory: Path,
    *,
    overwrite: bool,
) -> FederatedScorePublication:
    if directory.exists() and not overwrite:
        return load_federated_score_publication(directory)
    _prepare_directory(directory)
    partitions = tuple(
        _persist_client_partition(item, directory)
        for group in (result.calibration, result.evaluation, result.future_recalibration)
        for item in group
    )
    manifest = FederatedScoreManifest(
        coordinate=result.coordinate,
        scored_split_protocol=result.scored_split_protocol,
        checkpoint_round=result.checkpoint_round,
        checkpoint_checksum=result.checkpoint_checksum,
        preprocessing_state_set_checksum=result.preprocessing_state_set_checksum,
        split_manifest_checksum=result.split_manifest_checksum,
        partitions=partitions,
    )
    digest = _write_manifest(directory, manifest)
    return FederatedScorePublication(directory=directory, manifest=manifest, complete_digest=digest)


def publish_centralized_scores(
    result: CentralizedScoringResult,
    directory: Path,
    *,
    overwrite: bool,
) -> CentralizedScorePublication:
    if directory.exists() and not overwrite:
        return load_centralized_score_publication(directory)
    _prepare_directory(directory)
    partitions = (
        _persist_scored_partition(result.calibration, directory / ScorePartitionAsset.CALIBRATION.value, client=None),
        _persist_scored_partition(result.evaluation, directory / ScorePartitionAsset.EVALUATION.value, client=None),
    )
    manifest = CentralizedScoreManifest(
        coordinate=result.coordinate,
        checkpoint_round=result.checkpoint_round,
        checkpoint_checksum=result.checkpoint_checksum,
        preprocessing_state_checksum=result.preprocessing_state_checksum,
        split_manifest_checksum=result.split_manifest_checksum,
        partitions=partitions,
    )
    digest = _write_manifest(directory, manifest)
    return CentralizedScorePublication(directory=directory, manifest=manifest, complete_digest=digest)


def load_federated_score_publication(directory: Path) -> FederatedScorePublication:
    manifest = _load_manifest(directory, FederatedScoreManifest)
    _validate_partitions(directory, manifest.partitions)
    return FederatedScorePublication(
        directory=directory,
        manifest=manifest,
        complete_digest=checksum_file(directory / ScoreRepositoryAsset.MANIFEST.value),
    )


def load_centralized_score_publication(directory: Path) -> CentralizedScorePublication:
    manifest = _load_manifest(directory, CentralizedScoreManifest)
    _validate_partitions(directory, manifest.partitions)
    return CentralizedScorePublication(
        directory=directory,
        manifest=manifest,
        complete_digest=checksum_file(directory / ScoreRepositoryAsset.MANIFEST.value),
    )


def reload_federated_scores(publication: FederatedScorePublication) -> FederatedScoringResult:
    manifest = publication.manifest
    calibration = _reload_client_group(publication.directory, manifest.partitions, PartitionRole.CALIBRATION)
    evaluation = _reload_client_group(publication.directory, manifest.partitions, PartitionRole.EVALUATION)
    future = _reload_client_group(publication.directory, manifest.partitions, PartitionRole.FUTURE_RECALIBRATION)
    return FederatedScoringResult(
        coordinate=manifest.coordinate,
        scored_split_protocol=manifest.scored_split_protocol,
        checkpoint_round=manifest.checkpoint_round,
        checkpoint_checksum=manifest.checkpoint_checksum,
        preprocessing_state_set_checksum=manifest.preprocessing_state_set_checksum,
        split_manifest_checksum=manifest.split_manifest_checksum,
        calibration=calibration,
        evaluation=evaluation,
        future_recalibration=future,
    )


def reload_centralized_scores(publication: CentralizedScorePublication) -> CentralizedScoringResult:
    manifest = publication.manifest
    calibration = _require_single_partition(publication.directory, manifest.partitions, PartitionRole.CALIBRATION)
    evaluation = _require_single_partition(publication.directory, manifest.partitions, PartitionRole.EVALUATION)
    return CentralizedScoringResult(
        coordinate=manifest.coordinate,
        checkpoint_round=manifest.checkpoint_round,
        checkpoint_checksum=manifest.checkpoint_checksum,
        preprocessing_state_checksum=manifest.preprocessing_state_checksum,
        split_manifest_checksum=manifest.split_manifest_checksum,
        calibration=calibration,
        evaluation=evaluation,
    )


def _persist_client_partition(item: ClientScoredPartition, directory: Path) -> PersistedScorePartition:
    path = directory / item.client.client_id / ScorePartitionAsset.for_role(item.scored.role).value
    return _persist_scored_partition(item.scored, path, client=item.client, root=directory)


def _persist_scored_partition(
    scored: ScoredPartition,
    path: Path,
    *,
    client: ClientIdentity | None,
    root: Path | None = None,
) -> PersistedScorePartition:
    checksum, row_count = write_frame(scored.frame, path)
    base = root or path.parent
    return PersistedScorePartition(
        role=scored.role,
        relative_path=path.relative_to(base).as_posix(),
        checksum=checksum,
        row_count=row_count,
        feature_count=scored.feature_count,
        client=client,
    )


def _reload_client_group(
    directory: Path,
    partitions: tuple[PersistedScorePartition, ...],
    role: PartitionRole,
) -> tuple[ClientScoredPartition, ...]:
    selected = tuple(item for item in partitions if item.role is role)
    return tuple(
        ClientScoredPartition(client=_require_client(item), scored=_reload_scored_partition(directory, item))
        for item in sorted(selected, key=lambda value: _require_client(value))
    )


def _require_single_partition(
    directory: Path,
    partitions: tuple[PersistedScorePartition, ...],
    role: PartitionRole,
) -> ScoredPartition:
    selected = tuple(item for item in partitions if item.role is role)
    if len(selected) != 1 or selected[0].client is not None:
        raise ArtifactIntegrityError(f"centralized score publication requires exactly one {role.value} partition")
    return _reload_scored_partition(directory, selected[0])


def _reload_scored_partition(directory: Path, persisted: PersistedScorePartition) -> ScoredPartition:
    frame = read_frame(
        directory / persisted.relative_path,
        expected_checksum=persisted.checksum,
        expected_row_count=persisted.row_count,
    )
    return ScoredPartition(role=persisted.role, frame=frame, feature_count=persisted.feature_count)


def _require_client(persisted: PersistedScorePartition) -> ClientIdentity:
    if persisted.client is None:
        raise ArtifactIntegrityError("federated score partition is missing its client identity")
    return persisted.client


def _prepare_directory(directory: Path) -> None:
    if directory.exists():
        rmtree(directory)
    directory.mkdir(parents=True, exist_ok=False)


def _write_manifest(directory: Path, manifest: StrictModel) -> Checksum:
    path = directory / ScoreRepositoryAsset.MANIFEST.value
    path.write_text(canonical_json_text(manifest), encoding="utf-8")
    digest = checksum_file(path)
    (directory / ScoreRepositoryAsset.COMPLETE.value).write_text(digest.value, encoding="utf-8")
    return digest


def _load_manifest[ManifestT: StrictModel](directory: Path, model: type[ManifestT]) -> ManifestT:
    path = directory / ScoreRepositoryAsset.MANIFEST.value
    complete = directory / ScoreRepositoryAsset.COMPLETE.value
    if not path.is_file() or not complete.is_file():
        raise ArtifactIntegrityError(f"score publication is incomplete: {directory}")
    digest = checksum_file(path)
    if complete.read_text(encoding="utf-8").strip() != digest.value:
        raise ArtifactIntegrityError(f"score completion digest mismatch: {directory}")
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def _validate_partitions(directory: Path, partitions: tuple[PersistedScorePartition, ...]) -> None:
    for item in partitions:
        read_frame(directory / item.relative_path, expected_checksum=item.checksum, expected_row_count=item.row_count)

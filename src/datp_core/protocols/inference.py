"""Layer-neutral inference and score-artifact contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from datp_core.domain.enums import (
    ContractSubject,
    PartitionRole,
    PopulationId,
    SerializationFormat,
    SplitProtocolId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import Checksum, checksum_text
from datp_core.domain.values.counts import FeatureCount, RoundNumber, RowCount


class TrainingCoordinateContract(Protocol):
    @property
    def population(self) -> PopulationId: ...

    @property
    def split_protocol(self) -> SplitProtocolId: ...


class ClientIdentityContract(Protocol):
    @property
    def client_id(self) -> str: ...

    @property
    def population(self) -> PopulationId: ...


POST_TRAINING_SCORE_PARTITIONS = frozenset(
    {
        PartitionRole.CALIBRATION,
        PartitionRole.FUTURE_RECALIBRATION,
        PartitionRole.EVALUATION,
    }
)


@dataclass(frozen=True, slots=True)
class ScoreArtifact[CoordinateT: TrainingCoordinateContract]:
    coordinate: CoordinateT
    partition_role: PartitionRole
    checkpoint_round: RoundNumber
    checkpoint_checksum: Checksum
    path: Path
    checksum: Checksum
    row_count: RowCount
    feature_count: FeatureCount
    serialization_format: SerializationFormat

    def __post_init__(self) -> None:
        if self.partition_role not in POST_TRAINING_SCORE_PARTITIONS:
            raise ScientificContractError(
                "score artifacts are only defined for post-training partitions",
                subject=self.partition_role,
            )
        if self.serialization_format is not SerializationFormat.PARQUET:
            raise ScientificContractError(
                "score artifacts must use Parquet serialization",
                subject=ContractSubject.SCHEMA,
            )


@dataclass(frozen=True, slots=True)
class ScoreRecord[
    CoordinateT: TrainingCoordinateContract,
    ClientT: ClientIdentityContract,
](ScoreArtifact[CoordinateT]):
    scored_client: ClientT

    def __post_init__(self) -> None:
        if self.partition_role not in POST_TRAINING_SCORE_PARTITIONS:
            raise ScientificContractError(
                "score artifacts are only defined for post-training partitions",
                subject=self.partition_role,
            )
        if self.serialization_format is not SerializationFormat.PARQUET:
            raise ScientificContractError(
                "score artifacts must use Parquet serialization",
                subject=ContractSubject.SCHEMA,
            )
        if self.scored_client.population is not self.coordinate.population:
            raise ScientificContractError(
                "scored client population must match the training coordinate",
                subject=ContractSubject.CLIENT_IDENTITY,
            )


@dataclass(frozen=True, slots=True)
class ScoreArtifactManifest[
    CoordinateT: TrainingCoordinateContract,
    ClientT: ClientIdentityContract,
]:
    coordinate: CoordinateT
    scored_split_protocol: SplitProtocolId
    checkpoint_round: RoundNumber
    checkpoint_checksum: Checksum
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    calibration_records: tuple[ScoreRecord[CoordinateT, ClientT], ...]
    evaluation_records: tuple[ScoreRecord[CoordinateT, ClientT], ...]
    future_recalibration_records: tuple[ScoreRecord[CoordinateT, ClientT], ...] = ()

    def __post_init__(self) -> None:
        if not self.calibration_records or not self.evaluation_records:
            raise ScientificContractError(
                "a score artifact manifest requires calibration and evaluation records",
                subject=ContractSubject.SCORES,
            )
        _require_consistent_partition_records(self, self.calibration_records, PartitionRole.CALIBRATION)
        _require_consistent_partition_records(self, self.evaluation_records, PartitionRole.EVALUATION)
        expected_future = self.scored_split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
        if expected_future != bool(self.future_recalibration_records):
            raise ScientificContractError(
                "score manifest future-recalibration inventory must match its scored split protocol",
                subject=ContractSubject.SCORES,
            )
        if expected_future:
            _require_consistent_partition_records(
                self,
                self.future_recalibration_records,
                PartitionRole.FUTURE_RECALIBRATION,
            )
            _require_matching_client_inventory(self.calibration_records, self.future_recalibration_records)
        _require_matching_client_inventory(self.calibration_records, self.evaluation_records)
        _require_consistent_feature_count(self)

    def records_for(self, role: PartitionRole) -> tuple[ScoreRecord[CoordinateT, ClientT], ...]:
        match role:
            case PartitionRole.CALIBRATION:
                return self.calibration_records
            case PartitionRole.FUTURE_RECALIBRATION:
                return self.future_recalibration_records
            case PartitionRole.EVALUATION:
                return self.evaluation_records
            case PartitionRole.TRAIN:
                raise ScientificContractError("training records are not score artifacts", subject=role)
            case PartitionRole.STATIC_REFERENCE_RESERVE:
                raise ScientificContractError("static-reference reserve is not a score artifact", subject=role)

    def score_set_checksum(self, role: PartitionRole) -> Checksum:
        return record_set_checksum(self.records_for(role))


@dataclass(frozen=True, slots=True)
class FixedScoreInvariant:
    model_checksum: Checksum
    calibration_score_set_checksum: Checksum
    evaluation_score_set_checksum: Checksum
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    future_recalibration_score_set_checksum: Checksum | None = None

    @staticmethod
    def from_manifest[
        CoordinateT: TrainingCoordinateContract,
        ClientT: ClientIdentityContract,
    ](
        manifest: ScoreArtifactManifest[CoordinateT, ClientT],
    ) -> FixedScoreInvariant:
        return FixedScoreInvariant(
            model_checksum=manifest.checkpoint_checksum,
            calibration_score_set_checksum=manifest.score_set_checksum(PartitionRole.CALIBRATION),
            evaluation_score_set_checksum=manifest.score_set_checksum(PartitionRole.EVALUATION),
            preprocessing_state_set_checksum=manifest.preprocessing_state_set_checksum,
            split_manifest_checksum=manifest.split_manifest_checksum,
            future_recalibration_score_set_checksum=(
                manifest.score_set_checksum(PartitionRole.FUTURE_RECALIBRATION)
                if manifest.future_recalibration_records
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class ScoreGenerationResult[
    CoordinateT: TrainingCoordinateContract,
    ClientT: ClientIdentityContract,
]:
    manifest: ScoreArtifactManifest[CoordinateT, ClientT]

    @property
    def invariant(self) -> FixedScoreInvariant:
        return FixedScoreInvariant.from_manifest(self.manifest)


def record_set_checksum[
    CoordinateT: TrainingCoordinateContract,
    ClientT: ClientIdentityContract,
](
    records: tuple[ScoreRecord[CoordinateT, ClientT], ...],
) -> Checksum:
    payload = "\n".join(
        f"{record.scored_client.population.value}|{record.scored_client.client_id}|{record.checksum.value}"
        for record in sorted(records, key=lambda item: item.scored_client.client_id)
    )
    return checksum_text(payload)


def _require_consistent_partition_records[
    CoordinateT: TrainingCoordinateContract,
    ClientT: ClientIdentityContract,
](
    manifest: ScoreArtifactManifest[CoordinateT, ClientT],
    records: tuple[ScoreRecord[CoordinateT, ClientT], ...],
    role: PartitionRole,
) -> None:
    client_ids = tuple(record.scored_client.client_id for record in records)
    if len(frozenset(client_ids)) != len(client_ids):
        raise ScientificContractError(
            f"duplicate scored-client records in {role.value} partition",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    for record in records:
        if record.partition_role is not role:
            raise ScientificContractError(
                f"score record partition role {record.partition_role.value} "
                f"does not match expected collection role {role.value}",
                subject=ContractSubject.SCORES,
            )
        _require_record_matches_manifest(manifest, record)


def _require_record_matches_manifest[
    CoordinateT: TrainingCoordinateContract,
    ClientT: ClientIdentityContract,
](
    manifest: ScoreArtifactManifest[CoordinateT, ClientT],
    record: ScoreRecord[CoordinateT, ClientT],
) -> None:
    if record.coordinate != manifest.coordinate:
        raise ScientificContractError(
            "score record coordinate must match the manifest coordinate",
            subject=ContractSubject.COORDINATE,
        )
    if record.checkpoint_checksum != manifest.checkpoint_checksum:
        raise ScientificContractError(
            "score record checkpoint checksum must match the manifest checkpoint",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    if record.checkpoint_round != manifest.checkpoint_round:
        raise ScientificContractError(
            "score record checkpoint round must match the manifest checkpoint round",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )


def _require_matching_client_inventory[
    CoordinateT: TrainingCoordinateContract,
    ClientT: ClientIdentityContract,
](
    left: tuple[ScoreRecord[CoordinateT, ClientT], ...],
    right: tuple[ScoreRecord[CoordinateT, ClientT], ...],
) -> None:
    left_ids = frozenset((record.scored_client.population, record.scored_client.client_id) for record in left)
    right_ids = frozenset((record.scored_client.population, record.scored_client.client_id) for record in right)
    if left_ids != right_ids:
        raise ScientificContractError(
            "every scored partition must cover the same client inventory",
            subject=ContractSubject.CLIENT_IDENTITY,
        )


def _require_consistent_feature_count[
    CoordinateT: TrainingCoordinateContract,
    ClientT: ClientIdentityContract,
](
    manifest: ScoreArtifactManifest[CoordinateT, ClientT],
) -> None:
    all_records = (
        *manifest.calibration_records,
        *manifest.evaluation_records,
        *manifest.future_recalibration_records,
    )
    if len(frozenset(record.feature_count for record in all_records)) != 1:
        raise ScientificContractError(
            "all score records must share the same feature count",
            subject=ContractSubject.FEATURES,
        )

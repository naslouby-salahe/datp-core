"""Typed, immutable federated score-artifact records."""

from dataclasses import dataclass
from functools import total_ordering
from pathlib import Path

from datp_core.domain.enums import ContractSubject, PartitionRole, SerializationFormat, SplitProtocolId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, FeatureCount, RoundNumber, RowCount, checksum_text
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity


@total_ordering
@dataclass(frozen=True, slots=True)
class ScoreRecord:
    coordinate: FederatedTrainingCoordinate
    scored_client: ClientIdentity
    partition_role: PartitionRole
    checkpoint_round: RoundNumber
    checkpoint_checksum: Checksum
    path: Path
    checksum: Checksum
    row_count: RowCount
    feature_count: FeatureCount
    serialization_format: SerializationFormat

    def __post_init__(self) -> None:
        if self.partition_role not in {
            PartitionRole.CALIBRATION,
            PartitionRole.FUTURE_RECALIBRATION,
            PartitionRole.EVALUATION,
        }:
            raise ScientificContractError(
                "federated score records are only defined for post-training partitions",
                subject=self.partition_role,
            )
        if self.serialization_format is not SerializationFormat.PARQUET:
            raise ScientificContractError(
                "federated scores must use Parquet serialization",
                subject=self.serialization_format,
            )

    def __lt__(self, other: "ScoreRecord") -> bool:
        return self.scored_client < other.scored_client


@dataclass(frozen=True, slots=True)
class ScoreArtifactManifest:
    coordinate: FederatedTrainingCoordinate
    checkpoint_round: RoundNumber
    checkpoint_checksum: Checksum
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    calibration_records: tuple[ScoreRecord, ...]
    evaluation_records: tuple[ScoreRecord, ...]
    higher_score_means_greater_anomaly: bool
    future_recalibration_records: tuple[ScoreRecord, ...] = ()

    def __post_init__(self) -> None:
        if not self.calibration_records or not self.evaluation_records:
            raise ScientificContractError(
                "a score artifact manifest requires calibration and evaluation records",
                subject=ContractSubject.SCORES,
            )
        if not self.higher_score_means_greater_anomaly:
            raise ScientificContractError(
                "federated reconstruction scores must satisfy the anomaly-polarity invariant",
                subject=ContractSubject.RECONSTRUCTION_ERROR,
            )
        _require_consistent_partition_records(self, self.calibration_records, PartitionRole.CALIBRATION)
        _require_consistent_partition_records(self, self.evaluation_records, PartitionRole.EVALUATION)
        expected_future = self.coordinate.split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
        if expected_future != bool(self.future_recalibration_records):
            raise ScientificContractError(
                "score manifest future-recalibration inventory must match its split protocol",
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

    def records_for(self, role: PartitionRole) -> tuple[ScoreRecord, ...]:
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


@dataclass(frozen=True, slots=True)
class FixedScoreInvariant:
    """The reusable-across-threshold-methods fingerprint of one frozen detector."""

    model_checksum: Checksum
    calibration_score_set_checksum: Checksum
    evaluation_score_set_checksum: Checksum
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    future_recalibration_score_set_checksum: Checksum | None = None

    @staticmethod
    def from_manifest(manifest: ScoreArtifactManifest) -> "FixedScoreInvariant":
        return FixedScoreInvariant(
            model_checksum=manifest.checkpoint_checksum,
            calibration_score_set_checksum=_record_set_checksum(manifest.calibration_records),
            evaluation_score_set_checksum=_record_set_checksum(manifest.evaluation_records),
            preprocessing_state_set_checksum=manifest.preprocessing_state_set_checksum,
            split_manifest_checksum=manifest.split_manifest_checksum,
            future_recalibration_score_set_checksum=(
                _record_set_checksum(manifest.future_recalibration_records)
                if manifest.future_recalibration_records
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class ScoreGenerationResult:
    manifest: ScoreArtifactManifest
    invariant: FixedScoreInvariant

    def __post_init__(self) -> None:
        if self.invariant != FixedScoreInvariant.from_manifest(self.manifest):
            raise ScientificContractError(
                "the fixed-score invariant must be derived from its own manifest",
                subject=ContractSubject.SCORES,
            )


def _require_consistent_partition_records(
    manifest: "ScoreArtifactManifest",
    records: tuple[ScoreRecord, ...],
    role: PartitionRole,
) -> None:
    client_ids = tuple(record.scored_client.client_id for record in records)
    if len(set(client_ids)) != len(client_ids):
        raise ScientificContractError(
            f"duplicate scored-client records in {role.value} partition",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    for record in records:
        _require_record_matches_manifest(manifest, record)


def _require_record_matches_manifest(manifest: "ScoreArtifactManifest", record: ScoreRecord) -> None:
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


def _require_matching_client_inventory(left: tuple[ScoreRecord, ...], right: tuple[ScoreRecord, ...]) -> None:
    if {record.scored_client for record in left} != {record.scored_client for record in right}:
        raise ScientificContractError(
            "every scored partition must cover the same client inventory",
            subject=ContractSubject.CLIENT_IDENTITY,
        )


def _record_set_checksum(records: tuple[ScoreRecord, ...]) -> Checksum:
    ordered = sorted(records)
    payload = "|".join(f"{record.scored_client.client_id}:{record.checksum.value}" for record in ordered)
    return checksum_text(payload)

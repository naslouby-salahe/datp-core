"""Branch-neutral score artifact contracts."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.domain.enums import ContractSubject, PartitionRole, SerializationFormat
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, FeatureCount, RoundNumber, RowCount

POST_TRAINING_SCORE_PARTITIONS = frozenset(
    {
        PartitionRole.CALIBRATION,
        PartitionRole.FUTURE_RECALIBRATION,
        PartitionRole.EVALUATION,
    }
)


@dataclass(frozen=True, slots=True)
class ScoreArtifact[CoordinateT]:
    """Persisted reconstruction-score artifact shared by both detector branches."""

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

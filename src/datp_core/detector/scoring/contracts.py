from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol, cast

from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import (
    ClientIdentityToken,
    ContractSubject,
    PartitionRole,
    PopulationId,
    SerializationFormat,
    SplitProtocolId,
)
from datp_core.core.numeric import FeatureCount, RowCount
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedTrainingCoordinate


class TrainingCoordinateContract(Protocol):
    @property
    def population(self) -> PopulationId: ...

    @property
    def split_protocol(self) -> SplitProtocolId: ...


class ClientIdentityContract(Protocol):
    @property
    def client_id(self) -> ClientIdentityToken: ...

    @property
    def population(self) -> PopulationId: ...


def _validate_score_artifact(partition_role: PartitionRole, serialization_format: SerializationFormat) -> None:
    if partition_role not in {
        PartitionRole.CALIBRATION,
        PartitionRole.FUTURE_RECALIBRATION,
        PartitionRole.EVALUATION,
    }:
        raise ScientificContractError(ErrorMessage("score artifacts are only defined for post-training partitions"))
    if serialization_format is not SerializationFormat.PARQUET:
        raise ScientificContractError(ErrorMessage("score artifacts must use Parquet serialization"))


@dataclass(frozen=True, slots=True)
class ScoreArtifact[CoordinateT]:
    coordinate: CoordinateT
    partition_role: PartitionRole
    path: Path
    row_count: RowCount
    feature_count: FeatureCount
    serialization_format: SerializationFormat

    def __post_init__(self) -> None:
        _validate_score_artifact(self.partition_role, self.serialization_format)


@dataclass(frozen=True, slots=True)
class ScoreRecord[CoordinateT, ClientT](ScoreArtifact[CoordinateT]):
    scored_client: ClientT

    def __post_init__(self) -> None:
        _validate_score_artifact(self.partition_role, self.serialization_format)
        coordinate = cast(TrainingCoordinateContract, self.coordinate)
        client = cast(ClientIdentityContract, self.scored_client)
        if client.population is not coordinate.population:
            raise ScientificContractError(
                ErrorMessage("scored client population must match the training coordinate"),
                subject=ContractSubject.CLIENT_IDENTITY,
            )


@dataclass(frozen=True, slots=True)
class ScoreArtifactManifest[CoordinateT, ClientT]:
    coordinate: CoordinateT
    scored_split_protocol: SplitProtocolId
    calibration_records: tuple[ScoreRecord[CoordinateT, ClientT], ...]
    evaluation_records: tuple[ScoreRecord[CoordinateT, ClientT], ...]
    future_recalibration_records: tuple[ScoreRecord[CoordinateT, ClientT], ...] = ()

    def __post_init__(self) -> None:
        if not self.calibration_records or not self.evaluation_records:
            raise ScientificContractError(
                ErrorMessage("a score artifact manifest requires calibration and evaluation records")
            )
        for records, role in (
            (self.calibration_records, PartitionRole.CALIBRATION),
            (self.evaluation_records, PartitionRole.EVALUATION),
            (self.future_recalibration_records, PartitionRole.FUTURE_RECALIBRATION),
        ):
            if records and any(
                record.coordinate != self.coordinate or record.partition_role is not role for record in records
            ):
                raise ScientificContractError(ErrorMessage("score records must match their manifest"))
        expected_future = self.scored_split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
        if expected_future != bool(self.future_recalibration_records):
            raise ScientificContractError(
                ErrorMessage("score manifest future-recalibration inventory must match its scored split")
            )
        inventories = tuple(
            frozenset(record.scored_client for record in records)
            for records in (
                self.calibration_records,
                self.evaluation_records,
                self.future_recalibration_records,
            )
            if records
        )
        if len(set(inventories)) != 1:
            raise ScientificContractError(ErrorMessage("every scored partition must cover the same clients"))

    def records_for(self, role: PartitionRole) -> tuple[ScoreRecord[CoordinateT, ClientT], ...]:
        match role:
            case PartitionRole.CALIBRATION:
                return self.calibration_records
            case PartitionRole.FUTURE_RECALIBRATION:
                return self.future_recalibration_records
            case PartitionRole.EVALUATION:
                return self.evaluation_records
            case _:
                raise ScientificContractError(ErrorMessage("training rows are not score artifacts"), subject=role)


@dataclass(frozen=True, slots=True)
class ScoreGenerationResult[CoordinateT, ClientT]:
    manifest: ScoreArtifactManifest[CoordinateT, ClientT]


class FederatedScoreAssetName(StrEnum):
    CALIBRATION = "calibration.parquet"
    EVALUATION = "evaluation.parquet"
    FUTURE_RECALIBRATION = "future_recalibration.parquet"


type FederatedScoreRecord = ScoreRecord[FederatedTrainingCoordinate, ClientIdentity]
type FederatedScoreArtifactManifest = ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]
type FederatedScoreGenerationResult = ScoreGenerationResult[FederatedTrainingCoordinate, ClientIdentity]

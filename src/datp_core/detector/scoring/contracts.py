from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Protocol, cast

from pydantic import TypeAdapter

from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import (
    ClientIdentityToken,
    ContractSubject,
    PartitionRole,
    PopulationId,
    SerializationFormat,
    Sha256Digest,
    SplitProtocolId,
)
from datp_core.core.numeric import FeatureCount, RowCount
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.autoencoder import AutoencoderModelState
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


def _normalize_serialized_mapping(mapping: Mapping[str, object]) -> dict[str, object]:
    return {key: _normalize_serialized_value(value) for key, value in mapping.items()}


def _normalize_serialized_value(value: object) -> object:
    normalized_value = value
    if isinstance(normalized_value, Mapping):
        serialized_value = cast(Mapping[str, object], normalized_value)
        if tuple(serialized_value) == ("value",):
            return serialized_value["value"]
    return cast(object, normalized_value)


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
        coordinate_value = cast(object, self.coordinate)
        if isinstance(coordinate_value, Mapping):
            coordinate_value = TypeAdapter(FederatedTrainingCoordinate).validate_python(
                _normalize_serialized_mapping(cast(Mapping[str, object], coordinate_value))
            )
            object.__setattr__(
                self,
                "coordinate",
                coordinate_value,
            )
        client_value = cast(object, self.scored_client)
        if isinstance(client_value, Mapping):
            client_value = TypeAdapter(ClientIdentity).validate_python(
                _normalize_serialized_mapping(cast(Mapping[str, object], client_value))
            )
            object.__setattr__(
                self,
                "scored_client",
                client_value,
            )
        coordinate = cast(TrainingCoordinateContract, coordinate_value)
        client = cast(ClientIdentityContract, client_value)
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
    terminal_detector_identity: Sha256Digest | None = None

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
        for records in (
            self.calibration_records,
            self.evaluation_records,
            self.future_recalibration_records,
        ):
            if records and len({record.scored_client for record in records}) != len(records):
                raise ScientificContractError(
                    ErrorMessage("score manifests cannot contain duplicate client records"),
                    subject=ContractSubject.CLIENT_IDENTITY,
                )

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


def score_artifact_content_identity[CoordinateT, ClientT](
    manifest: ScoreArtifactManifest[CoordinateT, ClientT],
) -> Sha256Digest:
    """Return an ordered, byte-level identity for immutable score artifacts."""
    digest = sha256()
    if manifest.terminal_detector_identity is not None:
        digest.update(b"terminal_detector\0")
        digest.update(str(manifest.terminal_detector_identity).encode("ascii"))
        digest.update(b"\0")
    for role in (PartitionRole.CALIBRATION, PartitionRole.FUTURE_RECALIBRATION, PartitionRole.EVALUATION):
        for record in manifest.records_for(role):
            if not record.path.is_file():
                raise ScientificContractError(
                    ErrorMessage("score artifact is unavailable for content-identity validation"),
                    subject=ContractSubject.ARTIFACT_PATH,
                )
            digest.update(role.value.encode("utf-8"))
            digest.update(b"\0")
            client = cast(ClientIdentityContract, record.scored_client)
            digest.update(client.client_id.value.encode("utf-8"))
            digest.update(b"\0")
            digest.update(record.path.read_bytes())
    return Sha256Digest(digest.hexdigest())


def terminal_detector_content_identity(model_state: AutoencoderModelState) -> Sha256Digest:
    """Return a stable byte-level identity for the one terminal scoring source."""
    digest = sha256()
    for name, tensor in sorted(model_state.to_torch_state_dict().items()):
        normalized = tensor.detach().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(normalized.dtype).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(tuple(normalized.shape)).encode("ascii"))
        digest.update(b"\0")
        digest.update(normalized.numpy().tobytes())
    return Sha256Digest(digest.hexdigest())


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

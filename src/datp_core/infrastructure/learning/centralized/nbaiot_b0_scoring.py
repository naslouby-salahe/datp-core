from collections.abc import Mapping
from dataclasses import dataclass

import msgspec
import torch
from torch import Tensor

from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.lineage import (
    CentralizedCalibrationScoringIdentity,
    CentralizedCheckpointIdentity,
    CentralizedTestScoringIdentity,
    SplitIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.errors import ScoringError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import (
    CentralizedClientCalibrationScoreArtifact,
    CentralizedClientTestScoreArtifact,
    ScoreSampleCount,
)
from datp_core.infrastructure.persistence.hashing import blake3_bytes_content_hash
from datp_core.infrastructure.scoring.anchor import score_client_batch

_SCORE_SCHEMA_VERSION = ArtifactSchemaVersion(value="v1")


def _content_and_hash(scores: Tensor) -> tuple[bytes, str]:
    values: list[float] = scores.tolist()  # type: ignore[reportUnknownMemberType]  # PyTorch's stub omits the element type.
    content = msgspec.json.encode(tuple(values))
    return content, blake3_bytes_content_hash(content)


def _row_order_checksum(sample_count: int) -> str:
    return blake3_bytes_content_hash(msgspec.json.encode(tuple(range(sample_count))))


def _derived_identity(*parts: str) -> str:
    return blake3_bytes_content_hash(msgspec.json.encode(parts))


def _ordered_clients(batches: Mapping[ClientId, Tensor]) -> tuple[ClientId, ...]:
    return tuple(sorted(batches.keys(), key=lambda client_id: client_id.value))


@dataclass(frozen=True, slots=True, kw_only=True)
class B0CalibrationScoreGenerationWorkflow:
    model: torch.nn.Module
    device: torch.device
    centralized_checkpoint_identity: CentralizedCheckpointIdentity
    centralized_checkpoint_content_hash: str
    calibration_split_identity: SplitIdentity
    calibration_batches: Mapping[ClientId, Tensor]

    def generate(self, *, batch_size: int) -> tuple[CentralizedClientCalibrationScoreArtifact, ...]:
        if not self.calibration_batches:
            raise ScoringError(
                detail="B0 calibration scoring requires at least one client batch",
                checkpoint_id=self.centralized_checkpoint_identity.value.value,
                split="calibration",
            )
        split_manifest_hash = self.calibration_split_identity.value.value
        scoring_identity = CentralizedCalibrationScoringIdentity(
            value=StageFingerprint(
                value=_derived_identity("b0-calibration", self.centralized_checkpoint_content_hash, split_manifest_hash)
            )
        )
        return tuple(
            self._client_artifact(
                client_id=client_id,
                batch_size=batch_size,
                scoring_identity=scoring_identity,
                split_manifest_hash=split_manifest_hash,
            )
            for client_id in _ordered_clients(self.calibration_batches)
        )

    def _client_artifact(
        self,
        *,
        client_id: ClientId,
        batch_size: int,
        scoring_identity: CentralizedCalibrationScoringIdentity,
        split_manifest_hash: str,
    ) -> CentralizedClientCalibrationScoreArtifact:
        scores = score_client_batch(
            model=self.model, device=self.device, batch=self.calibration_batches[client_id], batch_size=batch_size
        )
        content_hash = _content_and_hash(scores)[1]
        artifact_ref = ArtifactRef(
            artifact_id=ArtifactId(value="artifact-" + content_hash),
            artifact_type=ArtifactType.CALIBRATION_SCORE_SET,
            content_hash=content_hash,
            schema_version=_SCORE_SCHEMA_VERSION,
            serialization_format=SerializationFormat.JSON,
        )
        return CentralizedClientCalibrationScoreArtifact(
            client_id=client_id,
            calibration_split_identity=self.calibration_split_identity,
            split_manifest_hash=split_manifest_hash,
            scoring_identity=scoring_identity,
            centralized_checkpoint_identity=self.centralized_checkpoint_identity,
            centralized_checkpoint_content_hash=self.centralized_checkpoint_content_hash,
            sample_count=ScoreSampleCount(value=scores.shape[0]),
            schema_version=_SCORE_SCHEMA_VERSION,
            content_hash=content_hash,
            row_order_checksum=_row_order_checksum(scores.shape[0]),
            artifact_ref=artifact_ref,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class B0TestScoreGenerationWorkflow:
    model: torch.nn.Module
    device: torch.device
    centralized_checkpoint_identity: CentralizedCheckpointIdentity
    centralized_checkpoint_content_hash: str
    test_split_identity: SplitIdentity
    benign_batches: Mapping[ClientId, Tensor]
    attack_batches: Mapping[ClientId, Tensor]

    def __post_init__(self) -> None:
        if set(self.benign_batches.keys()) != set(self.attack_batches.keys()):
            raise ScoringError(
                detail="B0 test scoring requires a matching benign and attack client roster",
                checkpoint_id=self.centralized_checkpoint_identity.value.value,
                split="test",
            )
        if not self.benign_batches:
            raise ScoringError(
                detail="B0 test scoring requires at least one client batch",
                checkpoint_id=self.centralized_checkpoint_identity.value.value,
                split="test",
            )

    def generate(self, *, batch_size: int) -> tuple[CentralizedClientTestScoreArtifact, ...]:
        split_manifest_hash = self.test_split_identity.value.value
        scoring_identity = CentralizedTestScoringIdentity(
            value=StageFingerprint(
                value=_derived_identity("b0-test", self.centralized_checkpoint_content_hash, split_manifest_hash)
            )
        )
        return tuple(
            self._client_artifact(
                client_id=client_id,
                batch_size=batch_size,
                scoring_identity=scoring_identity,
                split_manifest_hash=split_manifest_hash,
            )
            for client_id in _ordered_clients(self.benign_batches)
        )

    def _client_artifact(
        self,
        *,
        client_id: ClientId,
        batch_size: int,
        scoring_identity: CentralizedTestScoringIdentity,
        split_manifest_hash: str,
    ) -> CentralizedClientTestScoreArtifact:
        benign_scores = score_client_batch(
            model=self.model, device=self.device, batch=self.benign_batches[client_id], batch_size=batch_size
        )
        attack_scores = score_client_batch(
            model=self.model, device=self.device, batch=self.attack_batches[client_id], batch_size=batch_size
        )
        benign_hash = _content_and_hash(benign_scores)[1]
        attack_hash = _content_and_hash(attack_scores)[1]
        benign_ref = ArtifactRef(
            artifact_id=ArtifactId(value="artifact-" + benign_hash),
            artifact_type=ArtifactType.TEST_SCORE_SET,
            content_hash=benign_hash,
            schema_version=_SCORE_SCHEMA_VERSION,
            serialization_format=SerializationFormat.JSON,
        )
        attack_ref = ArtifactRef(
            artifact_id=ArtifactId(value="artifact-" + attack_hash),
            artifact_type=ArtifactType.TEST_SCORE_SET,
            content_hash=attack_hash,
            schema_version=_SCORE_SCHEMA_VERSION,
            serialization_format=SerializationFormat.JSON,
        )
        return CentralizedClientTestScoreArtifact(
            client_id=client_id,
            test_split_identity=self.test_split_identity,
            split_manifest_hash=split_manifest_hash,
            test_scoring_identity=scoring_identity,
            centralized_checkpoint_identity=self.centralized_checkpoint_identity,
            centralized_checkpoint_content_hash=self.centralized_checkpoint_content_hash,
            benign_scores_ref=benign_ref,
            benign_sample_count=ScoreSampleCount(value=benign_scores.shape[0]),
            benign_content_hash=benign_hash,
            benign_row_order_checksum=_row_order_checksum(benign_scores.shape[0]),
            attack_scores_ref=attack_ref,
            attack_sample_count=ScoreSampleCount(value=attack_scores.shape[0]),
            attack_content_hash=attack_hash,
            attack_row_order_checksum=_row_order_checksum(attack_scores.shape[0]),
            aggregate_manifest_hash=_derived_identity("b0-aggregate", benign_hash, attack_hash),
            score_schema_version=_SCORE_SCHEMA_VERSION,
        )

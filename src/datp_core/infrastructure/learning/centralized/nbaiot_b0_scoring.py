from collections.abc import Mapping
from dataclasses import dataclass

import msgspec
import torch
from torch import Tensor

from datp_core.application.ports.scoring import (
    CentralizedCalibrationScoreGenerationResult,
    CentralizedTestScoreGenerationResult,
    GenerateCentralizedCalibrationScoresRequest,
    GenerateCentralizedTestScoresRequest,
)
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.lineage import (
    CentralizedCalibrationScoringIdentity,
    CentralizedCheckpointIdentity,
    CentralizedTestScoringIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.data.splitting import SplitIdentity
from datp_core.domain.errors import ScoringError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import (
    CentralizedClientCalibrationScoreArtifact,
    CentralizedClientTestScoreArtifact,
    ScoreSampleCount,
)
from datp_core.domain.runtime.admissibility import BatchSize
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
    calibration_batches: Mapping[ClientId, Tensor]

    def generate_calibration_scores(
        self, request: GenerateCentralizedCalibrationScoresRequest
    ) -> CentralizedCalibrationScoreGenerationResult:
        checkpoint_identity = request.checkpoint.checkpoint_identity
        if not self.calibration_batches:
            raise ScoringError(
                detail="B0 calibration scoring requires at least one client batch",
                checkpoint_id=checkpoint_identity.value.value,
                split="calibration",
            )
        checkpoint_content_hash = request.checkpoint.checkpoint_artifact.content_hash
        split_identity = request.processed_splits.split_manifest_identity
        split_manifest_hash = split_identity.value.value
        batch_size = request.scoring.calibration_batch_size.value
        scoring_identity = CentralizedCalibrationScoringIdentity(
            value=StageFingerprint(
                value=_derived_identity("b0-calibration", checkpoint_content_hash, split_manifest_hash, str(batch_size))
            )
        )
        artifacts = tuple(
            self._client_artifact(
                client_id=client_id,
                batch_size=batch_size,
                scoring_identity=scoring_identity,
                split_identity=split_identity,
                split_manifest_hash=split_manifest_hash,
                checkpoint_identity=checkpoint_identity,
                checkpoint_content_hash=checkpoint_content_hash,
            )
            for client_id in _ordered_clients(self.calibration_batches)
        )
        return CentralizedCalibrationScoreGenerationResult(scores=artifacts)

    def _client_artifact(
        self,
        *,
        client_id: ClientId,
        batch_size: int,
        scoring_identity: CentralizedCalibrationScoringIdentity,
        split_identity: SplitIdentity,
        split_manifest_hash: str,
        checkpoint_identity: CentralizedCheckpointIdentity,
        checkpoint_content_hash: str,
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
            calibration_split_identity=split_identity,
            split_manifest_hash=split_manifest_hash,
            scoring_identity=scoring_identity,
            centralized_checkpoint_identity=checkpoint_identity,
            centralized_checkpoint_content_hash=checkpoint_content_hash,
            scoring_batch_size=BatchSize(value=batch_size),
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
    benign_batches: Mapping[ClientId, Tensor]
    attack_batches: Mapping[ClientId, Tensor]

    def __post_init__(self) -> None:
        if set(self.benign_batches.keys()) != set(self.attack_batches.keys()):
            raise ScoringError(
                detail="B0 test scoring requires a matching benign and attack client roster",
                checkpoint_id="unresolved",
                split="test",
            )
        if not self.benign_batches:
            raise ScoringError(
                detail="B0 test scoring requires at least one client batch",
                checkpoint_id="unresolved",
                split="test",
            )

    def generate_test_scores(
        self, request: GenerateCentralizedTestScoresRequest
    ) -> CentralizedTestScoreGenerationResult:
        checkpoint_identity = request.checkpoint.checkpoint_identity
        checkpoint_content_hash = request.checkpoint.checkpoint_artifact.content_hash
        split_identity = request.processed_splits.split_manifest_identity
        split_manifest_hash = split_identity.value.value
        batch_size = request.scoring.test_batch_size.value
        scoring_identity = CentralizedTestScoringIdentity(
            value=StageFingerprint(
                value=_derived_identity("b0-test", checkpoint_content_hash, split_manifest_hash, str(batch_size))
            )
        )
        artifacts = tuple(
            self._client_artifact(
                client_id=client_id,
                batch_size=batch_size,
                scoring_identity=scoring_identity,
                split_identity=split_identity,
                split_manifest_hash=split_manifest_hash,
                checkpoint_identity=checkpoint_identity,
                checkpoint_content_hash=checkpoint_content_hash,
            )
            for client_id in _ordered_clients(self.benign_batches)
        )
        return CentralizedTestScoreGenerationResult(scores=artifacts)

    def _client_artifact(
        self,
        *,
        client_id: ClientId,
        batch_size: int,
        scoring_identity: CentralizedTestScoringIdentity,
        split_identity: SplitIdentity,
        split_manifest_hash: str,
        checkpoint_identity: CentralizedCheckpointIdentity,
        checkpoint_content_hash: str,
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
            test_split_identity=split_identity,
            split_manifest_hash=split_manifest_hash,
            test_scoring_identity=scoring_identity,
            centralized_checkpoint_identity=checkpoint_identity,
            centralized_checkpoint_content_hash=checkpoint_content_hash,
            scoring_batch_size=BatchSize(value=batch_size),
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

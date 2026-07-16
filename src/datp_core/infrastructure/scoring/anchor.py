from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

import msgspec
import torch
from torch import Tensor

from datp_core.application.ports.persistence import (
    ArtifactBundleCommitResult,
    ArtifactBundleMemberWrite,
    CommitArtifactBundleRequest,
)
from datp_core.application.ports.scoring import (
    CalibrationScoreGenerationResult,
    GenerateCalibrationScoresRequest,
    GenerateTestScoresRequest,
    TestScoreGenerationResult,
)
from datp_core.domain.artifacts.bundles import DeclaredTestScoreMember
from datp_core.domain.artifacts.keys import ArtifactNamespace, RunArtifactKey, SerializationFormat
from datp_core.domain.artifacts.lineage import (
    CalibrationScoringIdentity,
    CheckpointIdentity,
    DatasetSourceIdentity,
    FeatureSchemaIdentity,
    PartitionIdentity,
    TestScoringIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import (
    ArtifactId,
    ArtifactRef,
    ArtifactSchemaVersion,
    CalibrationScoreArtifactId,
    StageFingerprint,
    TestScoreArtifactId,
)
from datp_core.domain.errors import ScoringError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import (
    CalibrationScoreArtifactSet,
    CalibrationScoringLineage,
    ClientCalibrationScoreArtifact,
    ClientCalibrationScoreMap,
    ClientMap,
    ClientMapEntry,
    ClientRoster,
    ClientTestScoreArtifact,
    ClientTestScoreMap,
    ScoreLineageContext,
    ScoreSampleCount,
    TestScoreArtifactSet,
    TestScoringLineage,
)
from datp_core.infrastructure.persistence.hashing import blake3_bytes_content_hash

_SCORE_SCHEMA_VERSION = ArtifactSchemaVersion(value="v1")


class ArtifactBundleCommitter(Protocol):
    def commit_bundle(self, request: CommitArtifactBundleRequest) -> ArtifactBundleCommitResult: ...


def _ordered_clients(batches: Mapping[ClientId, Tensor]) -> tuple[ClientId, ...]:
    return tuple(sorted(batches.keys(), key=lambda client_id: client_id.value))


def score_client_batch(*, model: torch.nn.Module, device: torch.device, batch: Tensor, batch_size: int) -> Tensor:
    model.eval()
    collected: list[Tensor] = []
    with torch.no_grad():
        for start in range(0, batch.shape[0], batch_size):
            device_batch = batch[start : start + batch_size].to(device, non_blocking=True)
            reconstruction = model(device_batch)
            if reconstruction.shape != device_batch.shape:
                raise ScoringError(
                    detail="anchor reconstruction shape must match the input feature batch",
                    checkpoint_id="unresolved",
                    split="score-batch",
                )
            collected.append(torch.mean(torch.square(reconstruction - device_batch), dim=1).detach().cpu())
    if not collected:
        return torch.empty(0, dtype=torch.float32)
    return torch.cat(collected)


def _content_and_hash(scores: Tensor) -> tuple[bytes, str]:
    values: list[float] = scores.tolist()  # type: ignore[reportUnknownMemberType]  # PyTorch's stub omits the element type.
    content = msgspec.json.encode(tuple(values))
    return content, blake3_bytes_content_hash(content)


def _row_order_checksum(sample_count: int) -> str:
    return blake3_bytes_content_hash(msgspec.json.encode(tuple(range(sample_count))))


def _client_ordering_checksum(roster: ClientRoster) -> str:
    return blake3_bytes_content_hash(msgspec.json.encode(tuple(client_id.value for client_id in roster.client_ids)))


def _checkpoint_identity(*, content_hash: str) -> CheckpointIdentity:
    return CheckpointIdentity(value=StageFingerprint(value=content_hash))


def _derived_identity(*parts: str) -> str:
    return blake3_bytes_content_hash(msgspec.json.encode(parts))


@dataclass(frozen=True, slots=True, kw_only=True)
class AnchorCalibrationScoreGenerationWorkflow:
    model: torch.nn.Module
    device: torch.device
    dataset_source_identity: DatasetSourceIdentity
    partition_identity: PartitionIdentity
    feature_schema_identity: FeatureSchemaIdentity
    calibration_batches: Mapping[ClientId, Tensor]

    def generate(self, request: GenerateCalibrationScoresRequest) -> CalibrationScoreGenerationResult:
        if not self.calibration_batches:
            raise ScoringError(
                detail="anchor calibration scoring requires at least one client batch",
                checkpoint_id=request.checkpoint.checkpoint_id.value,
                split="calibration",
            )
        batch_size = request.scoring.scoring_batch.calibration_batch_size.value
        ordered_clients = _ordered_clients(self.calibration_batches)
        roster = ClientRoster(client_ids=ordered_clients)
        checkpoint_identity = _checkpoint_identity(content_hash=request.checkpoint.content_hash)
        scoring_identity = CalibrationScoringIdentity(
            value=StageFingerprint(
                value=_derived_identity(
                    "calibration",
                    request.checkpoint.content_hash,
                    request.processed_splits.split_manifest_identity.value.value,
                )
            )
        )
        split_manifest_hash = request.processed_splits.split_manifest_identity.value.value
        entries = tuple(
            ClientMapEntry(
                client_id=client_id,
                value=_calibration_artifact(
                    client_id=client_id,
                    scores=score_client_batch(
                        model=self.model,
                        device=self.device,
                        batch=self.calibration_batches[client_id],
                        batch_size=batch_size,
                    ),
                    request=request,
                    scoring_identity=scoring_identity,
                    checkpoint_identity=checkpoint_identity,
                    split_manifest_hash=split_manifest_hash,
                    feature_schema_identity=self.feature_schema_identity,
                ),
            )
            for client_id in ordered_clients
        )
        context = ScoreLineageContext(
            dataset_source_identity=self.dataset_source_identity,
            partition_identity=self.partition_identity,
            split_identity=request.processed_splits.split_manifest_identity,
            scientific_checkpoint_identity=checkpoint_identity,
            scientific_checkpoint_content_hash=request.checkpoint.content_hash,
            fitted_preprocessor_identity=request.processed_splits.preprocessor_identity,
            feature_schema_identity=self.feature_schema_identity,
            training_identity=request.checkpoint.training_identity,
            score_schema_version=_SCORE_SCHEMA_VERSION,
            roster=roster,
            row_order_checksum=_client_ordering_checksum(roster),
            precision=request.scoring.precision,
            scoring_batch_size=request.scoring.scoring_batch.calibration_batch_size,
        )
        score_set = CalibrationScoreArtifactSet(
            artifact_id=CalibrationScoreArtifactId(
                value="artifact-" + _derived_identity("calibration-set", scoring_identity.value.value)
            ),
            lineage=CalibrationScoringLineage(scoring_identity=scoring_identity, context=context),
            per_client=ClientCalibrationScoreMap(values=ClientMap(roster=roster, entries=entries)),
        )
        return CalibrationScoreGenerationResult(scores=score_set)


def _calibration_artifact(
    *,
    client_id: ClientId,
    scores: Tensor,
    request: GenerateCalibrationScoresRequest,
    scoring_identity: CalibrationScoringIdentity,
    checkpoint_identity: CheckpointIdentity,
    split_manifest_hash: str,
    feature_schema_identity: FeatureSchemaIdentity,
) -> ClientCalibrationScoreArtifact:
    _, content_hash = _content_and_hash(scores)
    artifact_ref = ArtifactRef(
        artifact_id=ArtifactId(value="artifact-" + content_hash),
        artifact_type=ArtifactType.CALIBRATION_SCORE_SET,
        content_hash=content_hash,
        schema_version=_SCORE_SCHEMA_VERSION,
        serialization_format=SerializationFormat.JSON,
    )
    return ClientCalibrationScoreArtifact(
        client_id=client_id,
        calibration_split_identity=request.processed_splits.split_manifest_identity,
        split_manifest_hash=split_manifest_hash,
        scoring_identity=scoring_identity,
        scientific_checkpoint_identity=checkpoint_identity,
        scientific_checkpoint_content_hash=request.checkpoint.content_hash,
        fitted_preprocessor_identity=request.processed_splits.preprocessor_identity,
        feature_schema_identity=feature_schema_identity,
        sample_count=ScoreSampleCount(value=scores.shape[0]),
        schema_version=_SCORE_SCHEMA_VERSION,
        content_hash=content_hash,
        row_order_checksum=_row_order_checksum(scores.shape[0]),
        artifact_ref=artifact_ref,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class AnchorTestScoreGenerationWorkflow:
    model: torch.nn.Module
    device: torch.device
    dataset_source_identity: DatasetSourceIdentity
    partition_identity: PartitionIdentity
    feature_schema_identity: FeatureSchemaIdentity
    benign_batches: Mapping[ClientId, Tensor]
    attack_batches: Mapping[ClientId, Tensor]
    bundle_committer: ArtifactBundleCommitter
    stage_identity: StageFingerprint

    def __post_init__(self) -> None:
        if set(self.benign_batches.keys()) != set(self.attack_batches.keys()):
            raise ScoringError(
                detail="anchor test scoring requires a matching benign and attack client roster",
                checkpoint_id="unresolved",
                split="test",
            )
        if not self.benign_batches:
            raise ScoringError(
                detail="anchor test scoring requires at least one client batch",
                checkpoint_id="unresolved",
                split="test",
            )

    def generate(self, request: GenerateTestScoresRequest) -> TestScoreGenerationResult:
        batch_size = request.scoring.scoring_batch.test_batch_size.value
        ordered_clients = _ordered_clients(self.benign_batches)
        roster = ClientRoster(client_ids=ordered_clients)
        checkpoint_identity = _checkpoint_identity(content_hash=request.checkpoint.content_hash)
        split_manifest_hash = request.processed_splits.split_manifest_identity.value.value
        scoring_identity = TestScoringIdentity(
            value=StageFingerprint(
                value=_derived_identity("test", request.checkpoint.content_hash, split_manifest_hash)
            )
        )
        entries = tuple(
            ClientMapEntry(
                client_id=client_id,
                value=self._commit_client_pair(
                    client_id=client_id,
                    batch_size=batch_size,
                    request=request,
                    scoring_identity=scoring_identity,
                    checkpoint_identity=checkpoint_identity,
                    split_manifest_hash=split_manifest_hash,
                ),
            )
            for client_id in ordered_clients
        )
        context = ScoreLineageContext(
            dataset_source_identity=self.dataset_source_identity,
            partition_identity=self.partition_identity,
            split_identity=request.processed_splits.split_manifest_identity,
            scientific_checkpoint_identity=checkpoint_identity,
            scientific_checkpoint_content_hash=request.checkpoint.content_hash,
            fitted_preprocessor_identity=request.processed_splits.preprocessor_identity,
            feature_schema_identity=self.feature_schema_identity,
            training_identity=request.checkpoint.training_identity,
            score_schema_version=_SCORE_SCHEMA_VERSION,
            roster=roster,
            row_order_checksum=_client_ordering_checksum(roster),
            precision=request.scoring.precision,
            scoring_batch_size=request.scoring.scoring_batch.test_batch_size,
        )
        score_set = TestScoreArtifactSet(
            artifact_id=TestScoreArtifactId(
                value="artifact-" + _derived_identity("test-set", scoring_identity.value.value)
            ),
            lineage=TestScoringLineage(scoring_identity=scoring_identity, context=context),
            per_client=ClientTestScoreMap(values=ClientMap(roster=roster, entries=entries)),
        )
        return TestScoreGenerationResult(scores=score_set)

    def _commit_client_pair(
        self,
        *,
        client_id: ClientId,
        batch_size: int,
        request: GenerateTestScoresRequest,
        scoring_identity: TestScoringIdentity,
        checkpoint_identity: CheckpointIdentity,
        split_manifest_hash: str,
    ) -> ClientTestScoreArtifact:
        benign_scores = score_client_batch(
            model=self.model, device=self.device, batch=self.benign_batches[client_id], batch_size=batch_size
        )
        attack_scores = score_client_batch(
            model=self.model, device=self.device, batch=self.attack_batches[client_id], batch_size=batch_size
        )
        benign_content, benign_hash = _content_and_hash(benign_scores)
        attack_content, attack_hash = _content_and_hash(attack_scores)
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
        aggregate_manifest_hash = _derived_identity("aggregate", benign_hash, attack_hash)
        aggregate = ClientTestScoreArtifact(
            client_id=client_id,
            test_split_identity=request.processed_splits.split_manifest_identity,
            split_manifest_hash=split_manifest_hash,
            test_scoring_identity=scoring_identity,
            scientific_checkpoint_identity=checkpoint_identity,
            scientific_checkpoint_content_hash=request.checkpoint.content_hash,
            fitted_preprocessor_identity=request.processed_splits.preprocessor_identity,
            feature_schema_identity=self.feature_schema_identity,
            benign_scores_ref=benign_ref,
            benign_sample_count=ScoreSampleCount(value=benign_scores.shape[0]),
            benign_content_hash=benign_hash,
            benign_row_order_checksum=_row_order_checksum(benign_scores.shape[0]),
            attack_scores_ref=attack_ref,
            attack_sample_count=ScoreSampleCount(value=attack_scores.shape[0]),
            attack_content_hash=attack_hash,
            attack_row_order_checksum=_row_order_checksum(attack_scores.shape[0]),
            aggregate_manifest_hash=aggregate_manifest_hash,
            score_schema_version=_SCORE_SCHEMA_VERSION,
        )
        self.bundle_committer.commit_bundle(
            CommitArtifactBundleRequest(
                aggregate=aggregate,
                members=(
                    ArtifactBundleMemberWrite(
                        key=self._key(),
                        declared_member=_declared_member(aggregate, attack=False),
                        content=benign_content,
                    ),
                    ArtifactBundleMemberWrite(
                        key=self._key(),
                        declared_member=_declared_member(aggregate, attack=True),
                        content=attack_content,
                    ),
                ),
            )
        )
        return aggregate

    def _key(self) -> RunArtifactKey:
        return RunArtifactKey(
            artifact_type=ArtifactType.TEST_SCORE_SET,
            stage_identity=self.stage_identity,
            namespace=ArtifactNamespace.DATP_ANCHOR,
        )


def _declared_member(aggregate: ClientTestScoreArtifact, *, attack: bool) -> DeclaredTestScoreMember:
    return DeclaredTestScoreMember(
        artifact=aggregate.attack_scores_ref if attack else aggregate.benign_scores_ref,
        client_id=aggregate.client_id,
        test_split_identity=aggregate.test_split_identity,
        split_manifest_hash=aggregate.split_manifest_hash,
        test_scoring_identity=aggregate.test_scoring_identity,
        scientific_checkpoint_identity=aggregate.scientific_checkpoint_identity,
        scientific_checkpoint_content_hash=aggregate.scientific_checkpoint_content_hash,
        fitted_preprocessor_identity=aggregate.fitted_preprocessor_identity,
        feature_schema_identity=aggregate.feature_schema_identity,
        sample_count=aggregate.attack_sample_count if attack else aggregate.benign_sample_count,
        content_hash=aggregate.attack_content_hash if attack else aggregate.benign_content_hash,
        row_order_checksum=aggregate.attack_row_order_checksum if attack else aggregate.benign_row_order_checksum,
    )

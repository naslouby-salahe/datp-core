from pathlib import Path

from datp_core.application.ports.persistence import ArtifactBundleMemberWrite, CommitArtifactBundleRequest
from datp_core.domain.artifacts.bundles import DeclaredTestScoreMember
from datp_core.domain.artifacts.keys import (
    ArtifactNamespace,
    RunArtifactKey,
    SerializationFormat,
    StorageRootKind,
    StorageRootSpec,
    StorageVisibility,
)
from datp_core.domain.artifacts.lineage import (
    CheckpointIdentity,
    FeatureSchemaIdentity,
    FittedPreprocessorIdentity,
    SplitIdentity,
    TestScoringIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import ClientTestScoreArtifact, ScoreSampleCount
from datp_core.infrastructure.persistence.bundles import FileArtifactBundleStore
from datp_core.infrastructure.persistence.hashing import blake3_bytes_content_hash
from datp_core.infrastructure.persistence.roots import bind_storage_root


def bundle_store(path: Path) -> FileArtifactBundleStore:
    return FileArtifactBundleStore(
        root=bind_storage_root(
            spec=StorageRootSpec(kind=StorageRootKind.TEST_SANDBOX, visibility=StorageVisibility.TEST_ISOLATED),
            absolute_path=path,
        )
    )


def bundle_request() -> CommitArtifactBundleRequest:
    content = (b"synthetic benign scores", b"synthetic attack scores")
    aggregate = _aggregate(content)
    return CommitArtifactBundleRequest(
        aggregate=aggregate,
        members=tuple(
            ArtifactBundleMemberWrite(
                key=_key(),
                declared_member=_declared_member(aggregate, attack=attack),
                content=value,
            )
            for attack, value in ((False, content[0]), (True, content[1]))
        ),
    )


def _aggregate(content: tuple[bytes, bytes]) -> ClientTestScoreArtifact:
    client_id = ClientId(value="client-a")
    split_identity = SplitIdentity(value=StageFingerprint(value="a" * 64))
    checkpoint_identity = CheckpointIdentity(value=StageFingerprint(value="b" * 64))
    preprocessor_identity = FittedPreprocessorIdentity(value=StageFingerprint(value="c" * 64))
    schema_identity = FeatureSchemaIdentity(value=StageFingerprint(value="d" * 64))
    scoring_identity = TestScoringIdentity(value=StageFingerprint(value="e" * 64))
    schema_version = ArtifactSchemaVersion(value="test-score-v1")
    benign_reference = _artifact_reference("1", content[0], schema_version)
    attack_reference = _artifact_reference("2", content[1], schema_version)
    return ClientTestScoreArtifact(
        client_id=client_id,
        test_split_identity=split_identity,
        split_manifest_hash="3" * 64,
        test_scoring_identity=scoring_identity,
        scientific_checkpoint_identity=checkpoint_identity,
        scientific_checkpoint_content_hash="4" * 64,
        fitted_preprocessor_identity=preprocessor_identity,
        feature_schema_identity=schema_identity,
        benign_scores_ref=benign_reference,
        benign_sample_count=ScoreSampleCount(value=10),
        benign_content_hash=benign_reference.content_hash,
        benign_row_order_checksum="benign-order",
        attack_scores_ref=attack_reference,
        attack_sample_count=ScoreSampleCount(value=5),
        attack_content_hash=attack_reference.content_hash,
        attack_row_order_checksum="attack-order",
        aggregate_manifest_hash="5" * 64,
        score_schema_version=schema_version,
    )


def _artifact_reference(character: str, content: bytes, schema_version: ArtifactSchemaVersion) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value="artifact-" + character * 64),
        artifact_type=ArtifactType.TEST_SCORE_SET,
        content_hash=blake3_bytes_content_hash(content),
        schema_version=schema_version,
        serialization_format=SerializationFormat.JSON,
    )


def _key() -> RunArtifactKey:
    return RunArtifactKey(
        artifact_type=ArtifactType.TEST_SCORE_SET,
        stage_identity=StageFingerprint(value="f" * 64),
        namespace=ArtifactNamespace.TEST_SANDBOX,
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

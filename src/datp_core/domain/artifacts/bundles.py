from dataclasses import dataclass
from re import fullmatch

from datp_core.domain.artifacts.lineage import (
    CheckpointIdentity,
    FeatureSchemaIdentity,
    FittedPreprocessorIdentity,
    SplitIdentity,
    TestScoringIdentity,
)
from datp_core.domain.artifacts.references import (
    CONTENT_HASH_PATTERN,
    ArtifactId,
    ArtifactRef,
    ArtifactReferenceCollection,
)
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import ClientTestScoreArtifact, ScoreSampleCount

_BUNDLE_ID_PATTERN = r"bundle-[0-9a-f]{64}"


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactBundleId:
    value: str

    def __post_init__(self) -> None:
        if fullmatch(_BUNDLE_ID_PATTERN, self.value) is None:
            raise DomainValidationError(
                detail="artifact bundle id has an invalid canonical format",
                value=self.value,
                constraint=_BUNDLE_ID_PATTERN,
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class DeclaredTestScoreMember:
    artifact: ArtifactRef
    client_id: ClientId
    test_split_identity: SplitIdentity
    split_manifest_hash: str
    test_scoring_identity: TestScoringIdentity
    scientific_checkpoint_identity: CheckpointIdentity
    scientific_checkpoint_content_hash: str
    fitted_preprocessor_identity: FittedPreprocessorIdentity
    feature_schema_identity: FeatureSchemaIdentity
    sample_count: ScoreSampleCount
    content_hash: str
    row_order_checksum: str

    def __post_init__(self) -> None:
        if not all(
            (
                type(self.artifact) is ArtifactRef,
                type(self.client_id) is ClientId,
                type(self.test_split_identity) is SplitIdentity,
                type(self.test_scoring_identity) is TestScoringIdentity,
                type(self.scientific_checkpoint_identity) is CheckpointIdentity,
                type(self.fitted_preprocessor_identity) is FittedPreprocessorIdentity,
                type(self.feature_schema_identity) is FeatureSchemaIdentity,
                type(self.sample_count) is ScoreSampleCount,
                fullmatch(CONTENT_HASH_PATTERN, self.split_manifest_hash) is not None,
                fullmatch(CONTENT_HASH_PATTERN, self.scientific_checkpoint_content_hash) is not None,
                fullmatch(CONTENT_HASH_PATTERN, self.content_hash) is not None,
                bool(self.row_order_checksum),
                self.artifact.content_hash == self.content_hash,
            )
        ):
            raise DomainValidationError(
                detail="declared test-score member requires complete typed integrity-bound lineage",
                value=repr(self),
                constraint="typed test-score lineage with matching artifact content hash",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactBundleManifest:
    bundle_id: ArtifactBundleId
    aggregate: ClientTestScoreArtifact
    members: ArtifactReferenceCollection
    commit_marker_id: ArtifactId

    def __post_init__(self) -> None:
        expected_members = (self.aggregate.benign_scores_ref, self.aggregate.attack_scores_ref)
        if type(self.bundle_id) is not ArtifactBundleId or type(self.aggregate) is not ClientTestScoreArtifact:
            raise DomainValidationError(
                detail="artifact bundle manifest requires typed bundle and test-score aggregate identities",
                value=repr(self),
                constraint="ArtifactBundleId and ClientTestScoreArtifact",
            )
        if self.members.references != expected_members:
            raise DomainValidationError(
                detail="artifact bundle manifest members must exactly match the committed score aggregate",
                value=repr(self.members.references),
                constraint="ordered benign and attack references from ClientTestScoreArtifact",
            )

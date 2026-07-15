from collections.abc import Callable
from dataclasses import replace
from inspect import signature
from pathlib import Path

import msgspec
import pytest
from tests.support.bundles import bundle_request, bundle_store

from datp_core.application.ports.persistence import ArtifactStore
from datp_core.domain.artifacts.bundles import ArtifactBundleManifest, DeclaredTestScoreMember
from datp_core.domain.artifacts.lineage import (
    CheckpointIdentity,
    FeatureSchemaIdentity,
    FittedPreprocessorIdentity,
    SplitIdentity,
    StageFingerprint,
)
from datp_core.domain.artifacts.lineage import (
    TestScoringIdentity as ScoringIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactSchemaVersion
from datp_core.domain.errors import IncompleteArtifactBundleError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import ScoreSampleCount
from datp_core.infrastructure.persistence.bundles import FileArtifactBundleStore


def test_bundle_adapter_matches_the_commit_bundle_port_signature() -> None:
    assert signature(FileArtifactBundleStore.commit_bundle) == signature(ArtifactStore.commit_bundle)


def test_missing_benign_or_attack_member_is_rejected(tmp_path: Path) -> None:
    store = bundle_store(tmp_path)
    request = bundle_request()

    for members in ((request.members[0],), (request.members[1],)):
        invalid_request = replace(request, members=members)

        with pytest.raises(IncompleteArtifactBundleError):
            store.commit_bundle(invalid_request)


def _different_artifact(member: DeclaredTestScoreMember) -> DeclaredTestScoreMember:
    return replace(member, artifact=replace(member.artifact, artifact_id=ArtifactId(value="artifact-" + "3" * 64)))


def _different_client(member: DeclaredTestScoreMember) -> DeclaredTestScoreMember:
    return replace(member, client_id=ClientId(value="client-b"))


def _different_split(member: DeclaredTestScoreMember) -> DeclaredTestScoreMember:
    return replace(member, test_split_identity=SplitIdentity(value=StageFingerprint(value="b" * 64)))


def _different_split_manifest_hash(member: DeclaredTestScoreMember) -> DeclaredTestScoreMember:
    return replace(member, split_manifest_hash="c" * 64)


def _different_scoring_identity(member: DeclaredTestScoreMember) -> DeclaredTestScoreMember:
    return replace(member, test_scoring_identity=ScoringIdentity(value=StageFingerprint(value="d" * 64)))


def _different_checkpoint_identity(member: DeclaredTestScoreMember) -> DeclaredTestScoreMember:
    return replace(member, scientific_checkpoint_identity=CheckpointIdentity(value=StageFingerprint(value="e" * 64)))


def _different_checkpoint_hash(member: DeclaredTestScoreMember) -> DeclaredTestScoreMember:
    return replace(member, scientific_checkpoint_content_hash="f" * 64)


def _different_preprocessor_identity(member: DeclaredTestScoreMember) -> DeclaredTestScoreMember:
    return replace(
        member,
        fitted_preprocessor_identity=FittedPreprocessorIdentity(value=StageFingerprint(value="0" * 64)),
    )


def _different_feature_schema_identity(member: DeclaredTestScoreMember) -> DeclaredTestScoreMember:
    return replace(member, feature_schema_identity=FeatureSchemaIdentity(value=StageFingerprint(value="1" * 64)))


def _different_sample_count(member: DeclaredTestScoreMember) -> DeclaredTestScoreMember:
    return replace(member, sample_count=ScoreSampleCount(value=99))


def _different_schema_version(member: DeclaredTestScoreMember) -> DeclaredTestScoreMember:
    return replace(
        member,
        artifact=replace(member.artifact, schema_version=ArtifactSchemaVersion(value="test-score-v2")),
    )


def _different_content_hash(member: DeclaredTestScoreMember) -> DeclaredTestScoreMember:
    return replace(
        member,
        artifact=replace(member.artifact, content_hash="2" * 64),
        content_hash="2" * 64,
    )


def _different_row_order(member: DeclaredTestScoreMember) -> DeclaredTestScoreMember:
    return replace(member, row_order_checksum="different-order")


_MEMBER_MUTATIONS: tuple[Callable[[DeclaredTestScoreMember], DeclaredTestScoreMember], ...] = (
    _different_artifact,
    _different_client,
    _different_split,
    _different_split_manifest_hash,
    _different_scoring_identity,
    _different_checkpoint_identity,
    _different_checkpoint_hash,
    _different_preprocessor_identity,
    _different_feature_schema_identity,
    _different_sample_count,
    _different_schema_version,
    _different_content_hash,
    _different_row_order,
)


@pytest.mark.parametrize(
    "mutate",
    _MEMBER_MUTATIONS,
)
def test_each_declared_member_field_must_match_the_aggregate(
    tmp_path: Path, mutate: Callable[[DeclaredTestScoreMember], DeclaredTestScoreMember]
) -> None:
    store = bundle_store(tmp_path)
    request = bundle_request()
    mismatched = mutate(request.members[1].declared_member)
    changed_member = replace(request.members[1], declared_member=mismatched)
    invalid_request = replace(request, members=(request.members[0], changed_member))

    with pytest.raises(IncompleteArtifactBundleError):
        store.commit_bundle(invalid_request)


def test_member_logical_key_must_match_its_declared_artifact(tmp_path: Path) -> None:
    store = bundle_store(tmp_path)
    request = bundle_request()
    changed_member = replace(
        request.members[0],
        key=replace(request.members[0].key, artifact_type=ArtifactType.METRIC_OUTPUT),
    )
    invalid_request = replace(request, members=(changed_member, request.members[1]))

    with pytest.raises(IncompleteArtifactBundleError):
        store.commit_bundle(invalid_request)


def test_absent_or_invalid_commit_marker_makes_a_bundle_unreadable(tmp_path: Path) -> None:
    store = bundle_store(tmp_path)
    committed = store.commit_bundle(bundle_request())
    marker = tmp_path / ".artifact-bundles" / committed.manifest.bundle_id.value / "commit-marker.json"

    marker.unlink()
    with pytest.raises(IncompleteArtifactBundleError):
        store.read_bundle(committed.manifest.bundle_id)

    marker.write_bytes(b"not a bundle manifest")
    with pytest.raises(IncompleteArtifactBundleError):
        store.read_bundle(committed.manifest.bundle_id)


def test_child_content_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    store = bundle_store(tmp_path)
    committed = store.commit_bundle(bundle_request())
    child = tmp_path / ".artifact-bundles" / committed.manifest.bundle_id.value / "benign"
    child.write_bytes(b"tampered synthetic benign scores")

    with pytest.raises(IncompleteArtifactBundleError):
        store.read_bundle(committed.manifest.bundle_id)


def test_missing_or_unexpected_member_makes_a_bundle_unreadable(tmp_path: Path) -> None:
    store = bundle_store(tmp_path)
    committed = store.commit_bundle(bundle_request())
    directory = tmp_path / ".artifact-bundles" / committed.manifest.bundle_id.value

    (directory / "attack").unlink()
    with pytest.raises(IncompleteArtifactBundleError):
        store.read_bundle(committed.manifest.bundle_id)

    (directory / "unexpected").write_bytes(b"synthetic extra member")
    with pytest.raises(IncompleteArtifactBundleError):
        store.read_bundle(committed.manifest.bundle_id)


def test_marker_is_written_only_after_both_members_are_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = bundle_store(tmp_path)
    observed_members: list[bool] = []

    def verify_marker_order(*, path: Path, manifest: ArtifactBundleManifest) -> None:
        observed_members.append(all((path.parent / name).is_file() for name in ("benign", "attack")))
        path.write_bytes(msgspec.json.encode(manifest))

    monkeypatch.setattr("datp_core.infrastructure.persistence.bundles._write_marker", verify_marker_order)
    store.commit_bundle(bundle_request())

    assert observed_members == [True]

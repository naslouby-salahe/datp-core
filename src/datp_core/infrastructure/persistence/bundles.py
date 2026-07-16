from dataclasses import dataclass
from os import O_DIRECTORY, O_RDONLY, close, fsync
from os import open as open_file
from pathlib import Path

import msgspec

from datp_core.application.ports.persistence import (
    ArtifactBundleCommitResult,
    ArtifactBundleMemberWrite,
    CommitArtifactBundleRequest,
)
from datp_core.domain.artifacts.bundles import (
    ArtifactBundleId,
    ArtifactBundleManifest,
    DeclaredTestScoreMember,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactReferenceCollection
from datp_core.domain.errors import ArtifactError, IncompleteArtifactBundleError, PartialArtifactError
from datp_core.domain.learning.scores import ClientTestScoreArtifact
from datp_core.infrastructure.persistence.hashing import blake3_bytes_content_hash, blake3_file_content_hash
from datp_core.infrastructure.persistence.roots import BoundStorageRoot

_MARKER_NAME = "commit-marker.json"
_MEMBER_NAMES = ("benign", "attack")


@dataclass(frozen=True, slots=True, kw_only=True)
class FileArtifactBundleStore:
    root: BoundStorageRoot

    def commit_bundle(self, request: CommitArtifactBundleRequest) -> ArtifactBundleCommitResult:
        _verify_declared_members(request)
        bundle_id = _bundle_id(request)
        directory = self.root.absolute_path / ".artifact-bundles" / bundle_id.value
        marker_path = directory / _MARKER_NAME
        if directory.exists():
            if marker_path.exists():
                return self.read_bundle(bundle_id)
            raise _incomplete(bundle_id, "existing bundle directory has no commit marker")
        try:
            directory.mkdir(parents=True)
            for member, name in zip(request.members, _MEMBER_NAMES, strict=True):
                _write_member(path=directory / name, member=member)
            manifest = _manifest(bundle_id=bundle_id, request=request)
            _write_marker(path=marker_path, manifest=manifest)
            _fsync_directory(directory)
        except OSError as error:
            raise PartialArtifactError(
                detail="bundle commit did not complete before its commit marker",
                artifact_id=bundle_id.value,
                stage="commit",
            ) from error
        return self.read_bundle(bundle_id)

    def read_bundle(self, bundle_id: ArtifactBundleId) -> ArtifactBundleCommitResult:
        directory = self.root.absolute_path / ".artifact-bundles" / bundle_id.value
        marker_path = directory / _MARKER_NAME
        manifest = _read_manifest(bundle_id, marker_path)
        _verify_manifest_identity(bundle_id, manifest)
        _verify_manifest_members(directory=directory, manifest=manifest)
        return ArtifactBundleCommitResult(manifest=manifest, commit_marker=_read_marker(marker_path, manifest))


def _verify_declared_members(request: CommitArtifactBundleRequest) -> None:
    _verify_member_order(request)
    for member, expected_member in zip(request.members, _declared_members(request.aggregate), strict=True):
        _verify_member_declaration(member, expected_member)
        _verify_member_content(member)


def _verify_member_order(request: CommitArtifactBundleRequest) -> None:
    expected = (request.aggregate.benign_scores_ref, request.aggregate.attack_scores_ref)
    actual = tuple(member.declared_member.artifact for member in request.members)
    if len(request.members) != len(_MEMBER_NAMES) or actual != expected:
        raise IncompleteArtifactBundleError(
            detail="bundle members must be the aggregate's ordered benign and attack score artifacts",
            artifact_id=request.aggregate.benign_scores_ref.artifact_id.value,
            stage="verify",
        )


def _verify_member_declaration(member: ArtifactBundleMemberWrite, expected: DeclaredTestScoreMember) -> None:
    if member.key.artifact_type is not member.declared_member.artifact.artifact_type:
        raise IncompleteArtifactBundleError(
            detail="bundle member logical key does not match its declared artifact type",
            artifact_id=member.declared_member.artifact.artifact_id.value,
            stage="verify",
        )
    if member.declared_member != expected:
        raise IncompleteArtifactBundleError(
            detail="bundle member lineage does not match the committed test-score aggregate",
            artifact_id=member.declared_member.artifact.artifact_id.value,
            stage="verify",
        )


def _verify_member_content(member: ArtifactBundleMemberWrite) -> None:
    if blake3_bytes_content_hash(member.content) != member.declared_member.artifact.content_hash:
        raise ArtifactError(
            detail="declared bundle member content hash does not match its artifact reference",
            artifact_id=member.declared_member.artifact.artifact_id.value,
            stage="verify",
        )


def _bundle_id_from_parts(
    *, aggregate: ClientTestScoreArtifact, member_references: tuple[ArtifactRef, ...]
) -> ArtifactBundleId:
    descriptor = msgspec.json.encode((aggregate, member_references))
    return ArtifactBundleId(value="bundle-" + blake3_bytes_content_hash(descriptor))


def _bundle_id(request: CommitArtifactBundleRequest) -> ArtifactBundleId:
    member_references = tuple(member.declared_member.artifact for member in request.members)
    return _bundle_id_from_parts(aggregate=request.aggregate, member_references=member_references)


def _bundle_id_from_manifest(manifest: ArtifactBundleManifest) -> ArtifactBundleId:
    return _bundle_id_from_parts(aggregate=manifest.aggregate, member_references=manifest.members.references)


def _manifest(*, bundle_id: ArtifactBundleId, request: CommitArtifactBundleRequest) -> ArtifactBundleManifest:
    member_references = tuple(member.declared_member.artifact for member in request.members)
    return ArtifactBundleManifest(
        bundle_id=bundle_id,
        aggregate=request.aggregate,
        members=ArtifactReferenceCollection(references=member_references),
        commit_marker_id=_marker_id(bundle_id),
    )


def _marker_for(manifest: ArtifactBundleManifest) -> ArtifactRef:
    content = msgspec.json.encode(manifest)
    return ArtifactRef(
        artifact_id=manifest.commit_marker_id,
        artifact_type=ArtifactType.ARTIFACT_BUNDLE,
        content_hash=blake3_bytes_content_hash(content),
        schema_version=manifest.aggregate.score_schema_version,
        serialization_format=manifest.aggregate.benign_scores_ref.serialization_format,
    )


def _read_manifest(bundle_id: ArtifactBundleId, marker_path: Path) -> ArtifactBundleManifest:
    if not marker_path.exists():
        raise _incomplete(bundle_id, "bundle has no verified final commit marker")
    try:
        return msgspec.json.decode(marker_path.read_bytes(), type=ArtifactBundleManifest)
    except (OSError, msgspec.DecodeError, msgspec.ValidationError) as error:
        raise _incomplete(bundle_id, "bundle commit marker is invalid") from error


def _verify_manifest_identity(bundle_id: ArtifactBundleId, manifest: ArtifactBundleManifest) -> None:
    if manifest.bundle_id != bundle_id:
        raise _incomplete(bundle_id, "bundle commit marker identity does not match its directory")
    if manifest.bundle_id != _bundle_id_from_manifest(manifest):
        raise _incomplete(bundle_id, "bundle manifest identity does not match its declared members")
    if manifest.commit_marker_id != _marker_id(bundle_id):
        raise _incomplete(bundle_id, "bundle commit marker identity is invalid")


def _read_marker(marker_path: Path, manifest: ArtifactBundleManifest) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=manifest.commit_marker_id,
        artifact_type=ArtifactType.ARTIFACT_BUNDLE,
        content_hash=blake3_bytes_content_hash(marker_path.read_bytes()),
        schema_version=manifest.aggregate.score_schema_version,
        serialization_format=manifest.aggregate.benign_scores_ref.serialization_format,
    )


def _marker_id(bundle_id: ArtifactBundleId) -> ArtifactId:
    return ArtifactId(value="artifact-" + blake3_bytes_content_hash(bundle_id.value.encode()))


def _write_member(*, path: Path, member: ArtifactBundleMemberWrite) -> None:
    with path.open("xb") as member_file:
        member_file.write(member.content)
        member_file.flush()
        fsync(member_file.fileno())
    if blake3_file_content_hash(path) != member.declared_member.artifact.content_hash:
        raise ArtifactError(
            detail="persisted bundle member content hash does not match its artifact reference",
            artifact_id=member.declared_member.artifact.artifact_id.value,
            stage="verify",
        )


def _write_marker(*, path: Path, manifest: ArtifactBundleManifest) -> None:
    content = msgspec.json.encode(manifest)
    with path.open("xb") as marker_file:
        marker_file.write(content)
        marker_file.flush()
        fsync(marker_file.fileno())
    if blake3_bytes_content_hash(path.read_bytes()) != _marker_for(manifest).content_hash:
        raise _incomplete(manifest.bundle_id, "bundle commit marker failed verification")


def _verify_manifest_members(*, directory: Path, manifest: ArtifactBundleManifest) -> None:
    member_paths = tuple(directory / name for name in _MEMBER_NAMES)
    _verify_member_paths(member_paths, manifest.bundle_id)
    _verify_directory_members(directory, manifest.bundle_id)
    for path, artifact in zip(member_paths, manifest.members.references, strict=True):
        _verify_member_file(path, artifact, manifest.bundle_id)


def _verify_member_paths(member_paths: tuple[Path, ...], bundle_id: ArtifactBundleId) -> None:
    if any(not path.is_file() for path in member_paths):
        raise _incomplete(bundle_id, "bundle is missing a declared member")


def _verify_directory_members(directory: Path, bundle_id: ArtifactBundleId) -> None:
    if {path.name for path in directory.iterdir()} != {*_MEMBER_NAMES, _MARKER_NAME}:
        raise _incomplete(bundle_id, "bundle contains an unexpected member")


def _verify_member_file(path: Path, artifact: ArtifactRef, bundle_id: ArtifactBundleId) -> None:
    if blake3_file_content_hash(path) != artifact.content_hash:
        raise _incomplete(bundle_id, "bundle member hash does not match the committed manifest")


def _declared_members(aggregate: ClientTestScoreArtifact) -> tuple[DeclaredTestScoreMember, DeclaredTestScoreMember]:
    return (
        DeclaredTestScoreMember(
            artifact=aggregate.benign_scores_ref,
            client_id=aggregate.client_id,
            test_split_identity=aggregate.test_split_identity,
            split_manifest_hash=aggregate.split_manifest_hash,
            test_scoring_identity=aggregate.test_scoring_identity,
            scientific_checkpoint_identity=aggregate.scientific_checkpoint_identity,
            scientific_checkpoint_content_hash=aggregate.scientific_checkpoint_content_hash,
            fitted_preprocessor_identity=aggregate.fitted_preprocessor_identity,
            feature_schema_identity=aggregate.feature_schema_identity,
            sample_count=aggregate.benign_sample_count,
            content_hash=aggregate.benign_content_hash,
            row_order_checksum=aggregate.benign_row_order_checksum,
        ),
        DeclaredTestScoreMember(
            artifact=aggregate.attack_scores_ref,
            client_id=aggregate.client_id,
            test_split_identity=aggregate.test_split_identity,
            split_manifest_hash=aggregate.split_manifest_hash,
            test_scoring_identity=aggregate.test_scoring_identity,
            scientific_checkpoint_identity=aggregate.scientific_checkpoint_identity,
            scientific_checkpoint_content_hash=aggregate.scientific_checkpoint_content_hash,
            fitted_preprocessor_identity=aggregate.fitted_preprocessor_identity,
            feature_schema_identity=aggregate.feature_schema_identity,
            sample_count=aggregate.attack_sample_count,
            content_hash=aggregate.attack_content_hash,
            row_order_checksum=aggregate.attack_row_order_checksum,
        ),
    )


def _fsync_directory(path: Path) -> None:
    descriptor = open_file(path, O_RDONLY | O_DIRECTORY)
    try:
        fsync(descriptor)
    finally:
        close(descriptor)


def _incomplete(bundle_id: ArtifactBundleId, detail: str) -> IncompleteArtifactBundleError:
    return IncompleteArtifactBundleError(detail=detail, artifact_id=bundle_id.value, stage="verify")

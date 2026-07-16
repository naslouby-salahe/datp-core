from dataclasses import dataclass
from pathlib import Path
from typing import assert_never

from datp_core.domain.artifacts.keys import (
    ArtifactKey,
    ArtifactNamespace,
    CrossSeedArtifactKey,
    DatasetArtifactKey,
    RegimeArtifactKey,
    RelativeArtifactPath,
    ReportArtifactKey,
    RunArtifactKey,
    SeedScopedArtifactKey,
    StorageRootKind,
)
from datp_core.domain.artifacts.references import ArtifactRef
from datp_core.domain.errors import PathResolutionError
from datp_core.infrastructure.persistence.roots import BoundStorageRoot


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolveArtifactLocationRequest:
    key: ArtifactKey
    root: BoundStorageRoot
    artifact: ArtifactRef


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedArtifactLocation:
    root: BoundStorageRoot
    relative_path: RelativeArtifactPath
    absolute_path: Path


class ArtifactPathResolver:
    def resolve(self, request: ResolveArtifactLocationRequest) -> ResolvedArtifactLocation:
        _validate_namespace_root_pair(key=request.key, root=request.root)
        relative_path = RelativeArtifactPath(value=_relative_path_value(key=request.key, artifact=request.artifact))
        absolute_path = _contained_path(root=request.root, relative_path=relative_path, key=request.key)
        return ResolvedArtifactLocation(
            root=request.root,
            relative_path=relative_path,
            absolute_path=absolute_path,
        )

# TODO - Move these constants to a configuration file 
_ROOT_NAMESPACE_REQUIREMENTS: dict[StorageRootKind, ArtifactNamespace] = {
    StorageRootKind.RECOVERY_STATE: ArtifactNamespace.RECOVERY,
    StorageRootKind.TEST_SANDBOX: ArtifactNamespace.TEST_SANDBOX,
}
_NAMESPACE_ROOT_REQUIREMENTS: dict[ArtifactNamespace, StorageRootKind] = {
    namespace: kind for kind, namespace in _ROOT_NAMESPACE_REQUIREMENTS.items()
}


def _validate_namespace_root_pair(*, key: ArtifactKey, root: BoundStorageRoot) -> None:
    expected_namespace = _ROOT_NAMESPACE_REQUIREMENTS.get(root.spec.kind)
    if expected_namespace is not None and key.namespace is not expected_namespace:
        raise _path_error(key=key, root=root)
    expected_root_kind = _NAMESPACE_ROOT_REQUIREMENTS.get(key.namespace)
    if expected_root_kind is not None and root.spec.kind is not expected_root_kind:
        raise _path_error(key=key, root=root)


def _relative_path_value(*, key: ArtifactKey, artifact: ArtifactRef) -> str:
    if artifact.artifact_type is not key.artifact_type:
        raise PathResolutionError(
            detail="artifact reference type must match its logical key",
            key=repr(key),
            root="artifact type mismatch",
        )
    key_segments = _key_segments(key)
    return "/".join((*key_segments, artifact.content_hash[:2], artifact.content_hash))


def _key_segments(key: ArtifactKey) -> tuple[str, ...]:
    match key:
        case DatasetArtifactKey():
            scope_segments = (
                "dataset",
                key.artifact_type.value,
                key.dataset.value,
                key.stage_identity.value,
            )
        case RegimeArtifactKey():
            scope_segments = (
                "regime",
                key.artifact_type.value,
                key.dataset.value,
                key.regime.value,
                key.stage_identity.value,
            )
        case SeedScopedArtifactKey():
            scope_segments = (
                "seed",
                key.artifact_type.value,
                key.dataset.value,
                key.regime.value,
                str(key.seed.value),
                key.stage_identity.value,
            )
        case CrossSeedArtifactKey():
            scope_segments = (
                "cross_seed",
                key.artifact_type.value,
                key.dataset.value,
                key.regime.value,
                key.seed_cohort_identity.value,
                key.stage_identity.value,
            )
        case RunArtifactKey():
            scope_segments = ("run", key.artifact_type.value, key.stage_identity.value)
        case ReportArtifactKey():
            scope_segments = ("report", key.artifact_type.value, key.stage_identity.value)
        case _ as unreachable:
            assert_never(unreachable)
    return (key.namespace.value, *scope_segments)


def _contained_path(*, root: BoundStorageRoot, relative_path: RelativeArtifactPath, key: ArtifactKey) -> Path:
    resolved_root = root.absolute_path.resolve(strict=False)
    resolved_path = (resolved_root / relative_path.value).resolve(strict=False)
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as error:
        raise _path_error(key=key, root=root) from error
    return resolved_path


def _path_error(*, key: ArtifactKey, root: BoundStorageRoot) -> PathResolutionError:
    return PathResolutionError(
        detail="resolved artifact path escapes or conflicts with its semantic storage root",
        key=repr(key),
        root=str(root.absolute_path),
    )

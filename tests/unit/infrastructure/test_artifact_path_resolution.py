from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import pytest
from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.artifacts.keys import (
    ArtifactNamespace,
    CrossSeedArtifactKey,
    DatasetArtifactKey,
    RegimeArtifactKey,
    ReportArtifactKey,
    RunArtifactKey,
    SeedScopedArtifactKey,
    SerializationFormat,
    StorageRootKind,
    StorageRootSpec,
    StorageVisibility,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.data.datasets import Dataset, Regime
from datp_core.domain.errors import PathResolutionError
from datp_core.domain.runtime.seeds import Seed
from datp_core.infrastructure.persistence.paths import ArtifactPathResolver, ResolveArtifactLocationRequest
from datp_core.infrastructure.persistence.roots import bind_storage_root

_HASH = "a" * 64
_STAGE = StageFingerprint(value="b" * 64)
_ARTIFACT = ArtifactRef(
    artifact_id=ArtifactId(value=f"artifact-{_HASH}"),
    artifact_type=ArtifactType.RESULT_FREEZE,
    content_hash=_HASH,
    schema_version=ArtifactSchemaVersion(value="v1"),
    serialization_format=SerializationFormat.JSON,
)


def _root(path: Path):
    return bind_storage_root(
        spec=StorageRootSpec(kind=StorageRootKind.REPORTS, visibility=StorageVisibility.SCIENTIFIC_OUTPUT),
        absolute_path=path,
    )


def _visibility(kind: StorageRootKind) -> StorageVisibility:
    if kind is StorageRootKind.RAW_DATA:
        return StorageVisibility.EXTERNAL_READONLY
    if kind in {
        StorageRootKind.PROCESSED_DATA,
        StorageRootKind.SCIENTIFIC_CHECKPOINTS,
        StorageRootKind.SCORES,
        StorageRootKind.METRICS,
        StorageRootKind.STATISTICS,
        StorageRootKind.REPORTS,
    }:
        return StorageVisibility.SCIENTIFIC_OUTPUT
    if kind is StorageRootKind.TEST_SANDBOX:
        return StorageVisibility.TEST_ISOLATED
    return StorageVisibility.EPHEMERAL


def _keys(namespace: ArtifactNamespace = ArtifactNamespace.JOURNAL_EXTENSION):
    return (
        DatasetArtifactKey(
            artifact_type=ArtifactType.RESULT_FREEZE,
            dataset=Dataset.N_BAIOT,
            stage_identity=_STAGE,
            namespace=namespace,
        ),
        RegimeArtifactKey(
            artifact_type=ArtifactType.RESULT_FREEZE,
            dataset=Dataset.N_BAIOT,
            regime=Regime.A,
            stage_identity=_STAGE,
            namespace=namespace,
        ),
        SeedScopedArtifactKey(
            artifact_type=ArtifactType.RESULT_FREEZE,
            dataset=Dataset.N_BAIOT,
            regime=Regime.A,
            seed=Seed(value=7),
            stage_identity=_STAGE,
            namespace=namespace,
        ),
        CrossSeedArtifactKey(
            artifact_type=ArtifactType.RESULT_FREEZE,
            dataset=Dataset.N_BAIOT,
            regime=Regime.A,
            seed_cohort_identity=_STAGE,
            stage_identity=_STAGE,
            namespace=namespace,
        ),
        RunArtifactKey(
            artifact_type=ArtifactType.RESULT_FREEZE,
            stage_identity=_STAGE,
            namespace=namespace,
        ),
        ReportArtifactKey(
            artifact_type=ArtifactType.RESULT_FREEZE,
            stage_identity=_STAGE,
            namespace=namespace,
        ),
    )


@pytest.mark.parametrize("kind", tuple(StorageRootKind))
def test_every_semantic_root_can_be_bound(kind: StorageRootKind, tmp_path: Path) -> None:
    root = bind_storage_root(
        spec=StorageRootSpec(kind=kind, visibility=_visibility(kind)),
        absolute_path=tmp_path / kind.value,
    )

    assert root.spec.kind is kind
    assert root.absolute_path.is_absolute()


def test_every_key_variant_resolves_stably_under_its_bound_root(tmp_path: Path) -> None:
    root = _root(tmp_path)
    resolver = ArtifactPathResolver()
    locations = tuple(
        resolver.resolve(ResolveArtifactLocationRequest(key=key, root=root, artifact=_ARTIFACT)) for key in _keys()
    )

    assert len({location.relative_path.value for location in locations}) == 6
    assert all(location.absolute_path.is_relative_to(tmp_path.resolve()) for location in locations)
    assert all(location.relative_path.value.endswith(f"aa/{_HASH}") for location in locations)


class TestContentAddressedPathProperties(TestCase):
    @given(st.text(alphabet="0123456789abcdef", min_size=64, max_size=64))
    def test_content_addressed_sharding_is_deterministic(self, content_hash: str) -> None:
        artifact = ArtifactRef(
            artifact_id=ArtifactId(value="artifact-" + "d" * 64),
            artifact_type=ArtifactType.RESULT_FREEZE,
            content_hash=content_hash,
            schema_version=ArtifactSchemaVersion(value="v1"),
            serialization_format=SerializationFormat.JSON,
        )
        with TemporaryDirectory() as directory:
            request = ResolveArtifactLocationRequest(
                key=_keys()[0],
                root=_root(Path(directory)),
                artifact=artifact,
            )
            resolver = ArtifactPathResolver()

            first = resolver.resolve(request)
            second = resolver.resolve(request)

        self.assertEqual(first, second)
        self.assertTrue(first.relative_path.value.endswith(f"{content_hash[:2]}/{content_hash}"))


def test_namespace_branches_cannot_collide(tmp_path: Path) -> None:
    resolver = ArtifactPathResolver()
    root = _root(tmp_path)
    anchor = resolver.resolve(
        ResolveArtifactLocationRequest(key=_keys(ArtifactNamespace.DATP_ANCHOR)[0], root=root, artifact=_ARTIFACT)
    )
    journal = resolver.resolve(
        ResolveArtifactLocationRequest(key=_keys(ArtifactNamespace.JOURNAL_EXTENSION)[0], root=root, artifact=_ARTIFACT)
    )

    assert anchor.absolute_path != journal.absolute_path


def test_recovery_and_test_namespaces_require_their_semantic_roots(tmp_path: Path) -> None:
    resolver = ArtifactPathResolver()
    report_root = _root(tmp_path)
    recovery_root = bind_storage_root(
        spec=StorageRootSpec(kind=StorageRootKind.RECOVERY_STATE, visibility=StorageVisibility.EPHEMERAL),
        absolute_path=tmp_path / "recovery",
    )
    test_root = bind_storage_root(
        spec=StorageRootSpec(kind=StorageRootKind.TEST_SANDBOX, visibility=StorageVisibility.TEST_ISOLATED),
        absolute_path=tmp_path / "test",
    )
    recovery_key = _keys(ArtifactNamespace.RECOVERY)[0]
    default_key = _keys()[0]
    test_key = _keys(ArtifactNamespace.TEST_SANDBOX)[0]
    recovery_request = ResolveArtifactLocationRequest(key=recovery_key, root=report_root, artifact=_ARTIFACT)
    report_request = ResolveArtifactLocationRequest(key=default_key, root=recovery_root, artifact=_ARTIFACT)
    test_request = ResolveArtifactLocationRequest(key=test_key, root=report_root, artifact=_ARTIFACT)
    sandbox_request = ResolveArtifactLocationRequest(key=default_key, root=test_root, artifact=_ARTIFACT)

    with pytest.raises(PathResolutionError):
        resolver.resolve(recovery_request)
    with pytest.raises(PathResolutionError):
        resolver.resolve(report_request)
    with pytest.raises(PathResolutionError):
        resolver.resolve(test_request)
    with pytest.raises(PathResolutionError):
        resolver.resolve(sandbox_request)


def test_symlinked_namespace_escape_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside"
    outside.mkdir()
    try:
        (tmp_path / ArtifactNamespace.DATP_ANCHOR.value).symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")
    resolver = ArtifactPathResolver()
    request = ResolveArtifactLocationRequest(
        key=_keys(ArtifactNamespace.DATP_ANCHOR)[0], root=_root(tmp_path), artifact=_ARTIFACT
    )

    with pytest.raises(PathResolutionError):
        resolver.resolve(request)

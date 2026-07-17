from pathlib import Path

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
from datp_core.domain.runtime.seeds import Seed
from datp_core.infrastructure.persistence.paths import ArtifactPathResolver, ResolveArtifactLocationRequest
from datp_core.infrastructure.persistence.roots import bind_storage_root

_CONTENT_HASH = "c" * 64
_STAGE = StageFingerprint(value="d" * 64)
_ARTIFACT = ArtifactRef(
    artifact_id=ArtifactId(value=f"artifact-{_CONTENT_HASH}"),
    artifact_type=ArtifactType.RESULT_FREEZE,
    content_hash=_CONTENT_HASH,
    schema_version=ArtifactSchemaVersion(value="v1"),
    serialization_format=SerializationFormat.JSON,
)


def test_synthetic_keys_resolve_beneath_their_independent_bound_roots(tmp_path: Path) -> None:
    keys = (
        DatasetArtifactKey(
            artifact_type=ArtifactType.RESULT_FREEZE,
            dataset=Dataset.N_BAIOT,
            stage_identity=_STAGE,
            namespace=ArtifactNamespace.COMPLETE,
        ),
        RegimeArtifactKey(
            artifact_type=ArtifactType.RESULT_FREEZE,
            dataset=Dataset.N_BAIOT,
            regime=Regime.A,
            stage_identity=_STAGE,
            namespace=ArtifactNamespace.COMPLETE,
        ),
        SeedScopedArtifactKey(
            artifact_type=ArtifactType.RESULT_FREEZE,
            dataset=Dataset.N_BAIOT,
            regime=Regime.A,
            seed=Seed(value=7),
            stage_identity=_STAGE,
            namespace=ArtifactNamespace.COMPLETE,
        ),
        CrossSeedArtifactKey(
            artifact_type=ArtifactType.RESULT_FREEZE,
            dataset=Dataset.N_BAIOT,
            regime=Regime.A,
            seed_cohort_identity=_STAGE,
            stage_identity=_STAGE,
            namespace=ArtifactNamespace.COMPLETE,
        ),
        RunArtifactKey(
            artifact_type=ArtifactType.RESULT_FREEZE,
            stage_identity=_STAGE,
            namespace=ArtifactNamespace.COMPLETE,
        ),
        ReportArtifactKey(
            artifact_type=ArtifactType.RESULT_FREEZE,
            stage_identity=_STAGE,
            namespace=ArtifactNamespace.COMPLETE,
        ),
    )
    root_kinds = (
        StorageRootKind.PROCESSED_DATA,
        StorageRootKind.SCIENTIFIC_CHECKPOINTS,
        StorageRootKind.SCORES,
        StorageRootKind.METRICS,
        StorageRootKind.STATISTICS,
        StorageRootKind.REPORTS,
    )
    resolver = ArtifactPathResolver()
    locations = tuple(
        resolver.resolve(
            ResolveArtifactLocationRequest(
                key=key,
                root=bind_storage_root(
                    spec=StorageRootSpec(kind=root_kind, visibility=StorageVisibility.SCIENTIFIC_OUTPUT),
                    absolute_path=tmp_path / root_kind.value,
                ),
                artifact=_ARTIFACT,
            )
        )
        for key, root_kind in zip(keys, root_kinds, strict=True)
    )

    assert len({location.relative_path.value for location in locations}) == len(keys)
    assert all(location.absolute_path.is_relative_to(location.root.absolute_path) for location in locations)
    assert all(location.relative_path.value.endswith(f"{_CONTENT_HASH[:2]}/{_CONTENT_HASH}") for location in locations)

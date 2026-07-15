from pathlib import Path

import pytest

from datp_core.domain.artifacts.bundles import ArtifactBundleId, ArtifactBundleManifest
from datp_core.domain.errors import IncompleteArtifactBundleError, PartialArtifactError
from datp_core.infrastructure.persistence.bundles import FileArtifactBundleStore
from tests.support.bundles import bundle_request, bundle_store


def test_synthetic_two_member_bundle_is_one_readable_aggregate(tmp_path: Path) -> None:
    store = bundle_store(tmp_path)
    request = bundle_request()

    committed = store.commit_bundle(request)

    assert store.read_bundle(committed.manifest.bundle_id).manifest.aggregate == request.aggregate
    assert committed.manifest.members.references == (
        request.members[0].declared_member.artifact,
        request.members[1].declared_member.artifact,
    )


def test_interruption_before_marker_makes_synthetic_bundle_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store: FileArtifactBundleStore = bundle_store(tmp_path)
    request = bundle_request()

    def interrupted_marker_write(*, path: Path, manifest: ArtifactBundleManifest) -> None:
        raise OSError("simulated interruption before commit marker write")

    monkeypatch.setattr("datp_core.infrastructure.persistence.bundles._write_marker", interrupted_marker_write)
    with pytest.raises(PartialArtifactError):
        store.commit_bundle(request)

    bundle_directory = next((tmp_path / ".artifact-bundles").iterdir())
    assert {path.name for path in bundle_directory.iterdir()} == {"benign", "attack"}
    with pytest.raises(IncompleteArtifactBundleError):
        store.read_bundle(ArtifactBundleId(value=bundle_directory.name))

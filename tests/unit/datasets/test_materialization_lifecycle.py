from enum import StrEnum
from pathlib import Path
from types import SimpleNamespace

import pytest

import datp_core.data.materialization_lifecycle as lifecycle
from datp_core.data.contracts import CanonicalAssetRole
from datp_core.data.materialization_lifecycle import CanonicalMaterializationRequest, materialize_canonical
from datp_core.data.nbaiot.schema import NBAIOT_SCHEMA, source_relative_path


class _Reason(StrEnum):
    NONE = "none"


def _request(
    *,
    source_paths: tuple[Path, ...] = (Path("a.csv"), Path("b.csv")),
    prepare_publication=lambda: None,
) -> CanonicalMaterializationRequest:
    return CanonicalMaterializationRequest(
        canonical_root=Path("canonical"),
        schema=NBAIOT_SCHEMA,
        canonicalization_contract="test-contract",
        source_paths=source_paths,
        source_path_resolver=source_relative_path,
        asset_role_type=CanonicalAssetRole,
        prepare_publication=prepare_publication,
    )


def test_reuse_short_circuits_dataset_specific_preparation(monkeypatch: pytest.MonkeyPatch) -> None:
    reused = object()
    prepared = False

    def prepare():
        nonlocal prepared
        prepared = True
        raise AssertionError("preparation must not run for reusable canonical data")

    monkeypatch.setattr(lifecycle, "reuse_published_canonical", lambda request: reused)
    assert materialize_canonical(_request(prepare_publication=prepare)) is reused
    assert prepared is False


def test_source_paths_must_be_unique_and_deterministically_ordered() -> None:
    with pytest.raises(ValueError, match="ordered"):
        _request(source_paths=(Path("b.csv"), Path("a.csv")))
    with pytest.raises(ValueError, match="unique"):
        _request(source_paths=(Path("a.csv"), Path("a.csv")))


def test_prepared_publication_cannot_change_the_requested_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lifecycle, "reuse_published_canonical", lambda request: None)
    publication = SimpleNamespace(
        canonical_root=Path("other"),
        schema=NBAIOT_SCHEMA,
        canonicalization_contract="test-contract",
        source_paths=(Path("a.csv"), Path("b.csv")),
    )
    with pytest.raises(ValueError, match="changed its requested root"):
        materialize_canonical(_request(prepare_publication=lambda: publication))

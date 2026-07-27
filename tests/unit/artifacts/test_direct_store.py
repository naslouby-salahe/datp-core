from __future__ import annotations

import os
from pathlib import Path

import pytest
import torch

from datp_core.artifacts.codecs.safetensors import (
    load_model_safetensors_from_store,
    save_model_safetensors_to_store,
)
from datp_core.artifacts.errors import (
    ArtifactChecksumMismatchError,
    ArtifactFileExistsError,
    ArtifactFileMissingError,
    InvalidArtifactPathError,
)
from datp_core.artifacts.store import ArtifactStore
from datp_core.core.hashing import compute_payload_checksum


def test_write_read_and_checksum_are_direct_file_operations(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)

    checksum = store.write_bytes_atomic("experiments/anchor/frozen_result.json", b"frozen")

    assert store.exists("experiments/anchor/frozen_result.json")
    assert store.read_bytes("experiments/anchor/frozen_result.json") == b"frozen"
    assert checksum == compute_payload_checksum(b"frozen")
    store.validate_file("experiments/anchor/frozen_result.json", checksum)
    assert not (tmp_path / "experiments" / "anchor" / "manifest.json").exists()


@pytest.mark.parametrize("relative_path", ("", "/outside.json", "../outside.json", "run/../../outside.json"))
def test_path_escape_is_rejected(tmp_path: Path, relative_path: str) -> None:
    with pytest.raises(InvalidArtifactPathError):
        ArtifactStore(tmp_path).write_bytes_atomic(relative_path, b"blocked")


def test_fresh_execution_cannot_silently_overwrite(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    store.write_bytes_atomic("result.json", b"first")

    with pytest.raises(ArtifactFileExistsError):
        store.write_bytes_atomic("result.json", b"second")

    assert store.read_bytes("result.json") == b"first"


def test_explicit_atomic_replacement_replaces_complete_file(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    store.write_bytes_atomic("result.json", b"first")

    checksum = store.write_bytes_atomic("result.json", b"second", replace=True)

    assert store.read_bytes("result.json") == b"second"
    assert checksum == compute_payload_checksum(b"second")


def test_copy_checksum_validation_and_missing_file_errors(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    source = tmp_path / "source.bin"
    source.write_bytes(b"source bytes")
    checksum = store.write_file_atomic("copied.bin", source)

    store.validate_file("copied.bin", checksum)
    with pytest.raises(ArtifactChecksumMismatchError):
        store.validate_file("copied.bin", compute_payload_checksum(b"wrong"))
    with pytest.raises(ArtifactFileMissingError):
        store.read_bytes("absent.bin")


def test_symlinked_parent_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(InvalidArtifactPathError):
        ArtifactStore(tmp_path).write_bytes_atomic("linked/escape.json", b"blocked")


def test_symlinked_root_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    root = tmp_path / "linked-root"
    root.symlink_to(target, target_is_directory=True)

    with pytest.raises(InvalidArtifactPathError, match="root may not be a symlink"):
        ArtifactStore(root)


def test_safetensors_direct_api_uses_store_checksum_validation(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    checksum = save_model_safetensors_to_store(
        {"weight": torch.tensor([1.0, 2.0])}, store=store, relative_path="models/checkpoint.safetensors"
    )

    loaded = load_model_safetensors_from_store("models/checkpoint.safetensors", store=store, expected_checksum=checksum)

    assert torch.equal(loaded["weight"], torch.tensor([1.0, 2.0]))


def test_write_bytes_batch_writes_all_and_returns_checksums(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    payloads = {
        "metrics/train.json": b'{"loss": 0.5}',
        "metrics/eval.json": b'{"accuracy": 0.95}',
    }
    checksums = store.write_bytes_batch(payloads)

    assert (tmp_path / "metrics" / "train.json").exists()
    assert (tmp_path / "metrics" / "eval.json").exists()
    assert store.read_bytes("metrics/train.json") == b'{"loss": 0.5}'
    assert store.read_bytes("metrics/eval.json") == b'{"accuracy": 0.95}'
    assert set(checksums.keys()) == {"metrics/train.json", "metrics/eval.json"}
    store.validate_file("metrics/train.json", checksums["metrics/train.json"])
    store.validate_file("metrics/eval.json", checksums["metrics/eval.json"])


def test_write_bytes_batch_failure_cleans_up_no_partial_output(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)

    blocked = tmp_path / "blocked"
    blocked.mkdir()
    os.chmod(blocked, 0o555)  # read+execute, no write — blocks file creation
    try:
        with pytest.raises(OSError):
            store.write_bytes_batch({
                "ok/file_a.bin": b"data a",
                "blocked/file_b.bin": b"data b",
            })

        assert not (tmp_path / "ok" / "file_a.bin").exists()
        assert not (tmp_path / "blocked" / "file_b.bin").exists()
    finally:
        os.chmod(blocked, 0o755)


def test_write_bytes_batch_rejects_existing(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    store.write_bytes_atomic("existing.bin", b"original")

    with pytest.raises(ArtifactFileExistsError):
        store.write_bytes_batch({"existing.bin": b"overwrite"})

    assert store.read_bytes("existing.bin") == b"original"

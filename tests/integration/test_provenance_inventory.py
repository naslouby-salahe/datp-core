from hashlib import sha256
from pathlib import Path
from subprocess import run

import pytest

from datp_core.infrastructure.runtime.provenance import GitCodeStateProvider, UvDependencyLockStateProvider


@pytest.mark.integration
def test_synthetic_clean_and_dirty_checkout_and_lock_remain_distinct(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "provenance@example.invalid")
    _git(tmp_path, "config", "user.name", "Provenance Test")
    tracked_file = tmp_path / "tracked.txt"
    tracked_file.write_text("tracked\n")
    lock_contents = _lock_contents()
    lock_path = tmp_path / "uv.lock"
    lock_path.write_bytes(lock_contents)
    _git(tmp_path, "add", "tracked.txt", "uv.lock")
    _git(tmp_path, "commit", "-m", "initial")

    clean = GitCodeStateProvider(repository=tmp_path, package_distribution="not-installed").inspect()
    tracked_file.write_text("tracked\n\t\n")
    dirty = GitCodeStateProvider(repository=tmp_path, package_distribution="not-installed").inspect()
    lock_state = UvDependencyLockStateProvider(lock_path=lock_path).inspect()

    assert clean.is_dirty is False
    assert dirty.is_dirty is True
    assert clean.dirty_diff_hash != dirty.dirty_diff_hash
    assert lock_state.lock_identity == sha256(lock_contents).hexdigest()
    assert lock_state.scikit_learn_version == "1.9.0"
    assert lock_state.msgspec_version == "0.21.1"


def _git(repository: Path, *arguments: str) -> None:
    run(("git", "-C", str(repository), *arguments), check=True, capture_output=True)


def _lock_contents() -> bytes:
    packages = (
        ("scikit-learn", "1.9.0"),
        ("pyarrow", "25.0.0"),
        ("numpy", "2.5.1"),
        ("scipy", "1.18.0"),
        ("blake3", "1.0.9"),
        ("msgspec", "0.21.1"),
    )
    return "\n".join(f'[[package]]\nname = "{name}"\nversion = "{version}"' for name, version in packages).encode()

"""Bootstrap/path authority: single root computation, raw-symlink policy enforcement, and
root-escape rejection.

Uses a temporary repository tree with a copy of the real ``runtime.yaml`` so the authored
raw-symlink policy (follow_symlink/reject_broken_symlink/reject_symlink_loop/
require_resolved_target_readable) is exercised exactly as authored, not a hypothetical.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from datp_core.config.runtime_settings import (
    PathAuthorityError,
    RuntimeBootstrapSettings,
    resolve_config_root,
    resolve_runtime_configuration,
)
from datp_core.config.yaml_loader import YamlConfigurationReader


def _build_repository(tmp_path: Path, raw_data_target: Path | None) -> Path:
    """A minimal repository tree: copied runtime.yaml, plus a raw_data root/symlink."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    shutil.copy("configs/runtime.yaml", repo_root / "runtime.yaml")
    (repo_root / "checkpoints").mkdir()
    (repo_root / "outputs").mkdir()
    (repo_root / ".runtime").mkdir()
    (repo_root / "data").mkdir()
    (repo_root / "data" / "processed").mkdir()
    if raw_data_target is not None:
        (repo_root / "data" / "raw").symlink_to(raw_data_target, target_is_directory=True)
    return repo_root


def _authored(repo_root: Path):
    return YamlConfigurationReader.read_runtime_document(repo_root / "runtime.yaml")


def test_valid_symlink_raw_data_root_resolves(tmp_path: Path) -> None:
    real_target = tmp_path / "actual_raw_data"
    real_target.mkdir()
    repo_root = _build_repository(tmp_path, raw_data_target=real_target)

    settings = RuntimeBootstrapSettings(repository_root=repo_root, execution_profile="scientific")
    runtime = resolve_runtime_configuration(authored_runtime=_authored(repo_root), bootstrap_settings=settings)

    assert runtime.paths.raw_data == real_target.resolve()


def test_broken_symlink_raw_data_root_is_rejected(tmp_path: Path) -> None:
    missing_target = tmp_path / "does_not_exist"
    repo_root = _build_repository(tmp_path, raw_data_target=missing_target)

    settings = RuntimeBootstrapSettings(repository_root=repo_root, execution_profile="scientific")
    with pytest.raises(PathAuthorityError, match="broken symlink"):
        resolve_runtime_configuration(authored_runtime=_authored(repo_root), bootstrap_settings=settings)


def test_symlink_loop_raw_data_root_is_rejected(tmp_path: Path) -> None:
    repo_root = _build_repository(tmp_path, raw_data_target=None)
    loop_a = repo_root / "data" / "loop_a"
    loop_b = repo_root / "data" / "loop_b"
    loop_a.symlink_to(loop_b, target_is_directory=True)
    loop_b.symlink_to(loop_a, target_is_directory=True)
    (repo_root / "data" / "raw").symlink_to(loop_a, target_is_directory=True)

    settings = RuntimeBootstrapSettings(repository_root=repo_root, execution_profile="scientific")
    with pytest.raises(PathAuthorityError, match="symlink loop"):
        resolve_runtime_configuration(authored_runtime=_authored(repo_root), bootstrap_settings=settings)


def test_unreadable_resolved_target_is_rejected(tmp_path: Path) -> None:
    real_target = tmp_path / "unreadable_raw_data"
    real_target.mkdir(mode=0o000)
    repo_root = _build_repository(tmp_path, raw_data_target=real_target)

    try:
        settings = RuntimeBootstrapSettings(repository_root=repo_root, execution_profile="scientific")
        with pytest.raises(PathAuthorityError, match="not readable"):
            resolve_runtime_configuration(authored_runtime=_authored(repo_root), bootstrap_settings=settings)
    finally:
        real_target.chmod(0o755)


def test_path_escaping_the_allowed_root_is_rejected(tmp_path: Path) -> None:
    real_target = tmp_path / "actual_raw_data"
    real_target.mkdir()
    repo_root = _build_repository(tmp_path, raw_data_target=real_target)

    runtime_text = (repo_root / "runtime.yaml").read_text()
    runtime_text = runtime_text.replace("checkpoints: checkpoints", "checkpoints: ../outside_the_repository")
    (repo_root / "runtime.yaml").write_text(runtime_text)

    settings = RuntimeBootstrapSettings(repository_root=repo_root, execution_profile="scientific")
    with pytest.raises(PathAuthorityError, match="outside the repository root"):
        resolve_runtime_configuration(authored_runtime=_authored(repo_root), bootstrap_settings=settings)


def test_custom_repository_root_is_the_single_authority_for_relative_paths(tmp_path: Path) -> None:
    real_target = tmp_path / "actual_raw_data"
    real_target.mkdir()
    repo_root = _build_repository(tmp_path, raw_data_target=real_target)

    settings = RuntimeBootstrapSettings(repository_root=repo_root, execution_profile="scientific")
    runtime = resolve_runtime_configuration(authored_runtime=_authored(repo_root), bootstrap_settings=settings)

    assert runtime.paths.repository_root == repo_root.resolve()
    assert runtime.paths.checkpoints == (repo_root / "checkpoints").resolve()
    assert runtime.paths.checkpoints.is_relative_to(repo_root.resolve())


def test_custom_configuration_root_resolves_relative_to_repository_root_not_cwd(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo_with_custom_config"
    repo_root.mkdir()
    custom_configs = repo_root / "settings"
    custom_configs.mkdir()

    settings = RuntimeBootstrapSettings(
        repository_root=repo_root, config_root=Path("settings"), execution_profile="scientific"
    )
    resolved = resolve_config_root(settings)

    assert resolved == custom_configs.resolve()
    assert resolved.is_relative_to(repo_root.resolve())


def test_conflicting_bootstrap_inputs_absolute_config_root_outside_repository_is_used_as_authored(
    tmp_path: Path,
) -> None:
    """An absolute config_root override is an explicit choice, not an accident of cwd -- it is
    honored even when it lies outside repository_root."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    elsewhere_configs = tmp_path / "elsewhere_configs"
    elsewhere_configs.mkdir()

    settings = RuntimeBootstrapSettings(
        repository_root=repo_root, config_root=elsewhere_configs, execution_profile="scientific"
    )
    resolved = resolve_config_root(settings)

    assert resolved == elsewhere_configs.resolve()

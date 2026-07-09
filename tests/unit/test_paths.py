from pathlib import Path

import pytest

from datp_core.utils.paths import (
    DATA_ROOT_ENV_VAR,
    PathResolutionError,
    find_repo_root,
    resolve_paths,
    safe_join,
)

REPO_ROOT = find_repo_root(Path(__file__))


def test_valid_repo_root_detection():
    assert (REPO_ROOT / "AGENTS.md").is_file()
    assert (REPO_ROOT / "pyproject.toml").is_file()


def test_raw_data_root_resolves_under_data_raw():
    paths = resolve_paths(REPO_ROOT, env={})
    assert paths.data_raw == REPO_ROOT / "data" / "raw"


def test_outputs_root_resolves_to_outputs():
    paths = resolve_paths(REPO_ROOT, env={})
    assert paths.outputs == REPO_ROOT / "outputs"


def test_results_root_resolves_to_results():
    paths = resolve_paths(REPO_ROOT, env={})
    assert paths.results == REPO_ROOT / "results"


def test_checkpoint_root_resolves_to_checkpoints():
    paths = resolve_paths(REPO_ROOT, env={})
    assert paths.checkpoints == REPO_ROOT / "checkpoints"


def test_env_override_applies_only_to_data_raw(tmp_path):
    override = tmp_path / "external-raw"
    override.mkdir()
    paths = resolve_paths(REPO_ROOT, env={DATA_ROOT_ENV_VAR: str(override)})
    assert paths.data_raw == override.resolve()
    assert paths.outputs == REPO_ROOT / "outputs"
    assert paths.checkpoints == REPO_ROOT / "checkpoints"


def test_unsupported_env_var_has_no_effect():
    paths = resolve_paths(REPO_ROOT, env={"DATP_OUTPUTS_ROOT": "/somewhere/else"})
    assert paths.outputs == REPO_ROOT / "outputs"


def test_path_escape_is_rejected():
    with pytest.raises(PathResolutionError):
        safe_join(REPO_ROOT / "outputs", "..", "..", "etc", "passwd")


def test_safe_join_allows_nested_path():
    result = safe_join(REPO_ROOT / "outputs", "scores", "run-1.json")
    assert result == (REPO_ROOT / "outputs" / "scores" / "run-1.json").resolve()


def test_missing_repo_marker_fails_clearly(tmp_path):
    with pytest.raises(PathResolutionError):
        find_repo_root(tmp_path)

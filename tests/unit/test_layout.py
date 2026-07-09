import subprocess

import pytest

from datp_core.utils.layout import (
    ArtifactPlacementError,
    validate_checkpoint_not_under_outputs,
    validate_repo_layout,
    validate_result_has_manifest,
)
from datp_core.utils.paths import RepoPaths, resolve_paths

_LAYOUT_DIRS = ("configs", "data", "checkpoints", "outputs", "results", "src", "tests")


def _repo_paths_for(root) -> RepoPaths:
    return RepoPaths(
        repo_root=root,
        configs=root / "configs",
        data=root / "data",
        data_raw=root / "data" / "raw",
        data_preprocessed=root / "data" / "preprocessed",
        data_manifests=root / "data" / "manifests",
        checkpoints=root / "checkpoints",
        outputs=root / "outputs",
        results=root / "results",
        outputs_logs=root / "outputs" / "logs",
        outputs_scores=root / "outputs" / "scores",
        outputs_metrics=root / "outputs" / "metrics",
        outputs_manifests=root / "outputs" / "manifests",
        outputs_tables=root / "outputs" / "tables",
        outputs_figures=root / "outputs" / "figures",
    )


def _init_tiny_git_repo(tmp_path, gitignore_lines, skip_dirs=()):
    repo = tmp_path / "repo"
    external_raw = tmp_path / "external_raw"
    external_raw.mkdir()
    for name in _LAYOUT_DIRS:
        if name not in skip_dirs:
            (repo / name).mkdir(parents=True)
    if "data" not in skip_dirs:
        (repo / "data" / "raw").symlink_to(external_raw, target_is_directory=True)
    (repo / ".gitignore").parent.mkdir(parents=True, exist_ok=True)
    (repo / ".gitignore").write_text("\n".join(gitignore_lines) + "\n")

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.email=t@t.com", "-c", "user.name=t", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-q", "-m", "init"],
        cwd=repo,
        check=True,
    )
    return repo


def test_layout_check_passes_on_expected_skeleton():
    result = validate_repo_layout(resolve_paths())
    assert result.passed, result.failures


def test_layout_check_passes_on_a_synthetic_correct_skeleton(tmp_path):
    repo = _init_tiny_git_repo(
        tmp_path,
        gitignore_lines=["checkpoints/*", "!checkpoints/README.md", "outputs/*"],
    )
    result = validate_repo_layout(_repo_paths_for(repo))
    assert result.passed, result.failures


def test_missing_required_directory_fails(tmp_path):
    repo = _init_tiny_git_repo(
        tmp_path,
        gitignore_lines=["checkpoints/*", "outputs/*"],
        skip_dirs=("tests",),
    )
    result = validate_repo_layout(_repo_paths_for(repo))
    assert not result.passed
    assert any("tests/" in f for f in result.failures)


def test_outputs_results_confusion_fails(tmp_path):
    # Misconfigured: results/ is ignored instead of checkpoints/outputs.
    repo = _init_tiny_git_repo(tmp_path, gitignore_lines=["results/*"])
    result = validate_repo_layout(_repo_paths_for(repo))
    assert not result.passed
    assert any("must not be git-ignored" in f for f in result.failures)
    assert any("must be git-ignored" in f for f in result.failures)


def test_checkpoint_path_under_outputs_fails_if_disallowed():
    with pytest.raises(ArtifactPlacementError):
        validate_checkpoint_not_under_outputs("outputs/checkpoints/ckpt-1.pt")
    validate_checkpoint_not_under_outputs("checkpoints/fedavg/nbaiot/ckpt-1.pt")


def test_result_file_without_manifest_fails(tmp_path):
    result_path = tmp_path / "table.csv"
    result_path.write_text("x")
    manifest_path = tmp_path / "table.manifest.json"
    with pytest.raises(ArtifactPlacementError):
        validate_result_has_manifest(result_path, manifest_path)

    manifest_path.write_text("{}")
    validate_result_has_manifest(result_path, manifest_path)

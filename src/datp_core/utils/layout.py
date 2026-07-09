"""Repository layout contract checks (docs/protocol/structure_decision.md,
docs/protocol/artifact_contracts.md #3).

Checks that the checked-in skeleton matches the accepted structure decision:
required top-level directories exist, `data/raw` stays a symlink to data
outside the repository, `checkpoints/` and `outputs/` contents are
git-ignored, and `results/` stays tracked (curated, not raw).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .paths import RepoPaths

_REQUIRED_DIRS = ("configs", "data", "checkpoints", "outputs", "results", "src", "tests")


class ArtifactPlacementError(RuntimeError):
    """Raised when an artifact is written to, or referenced from, the wrong root."""


@dataclass(frozen=True)
class LayoutCheckResult:
    passed: bool
    checks: tuple[str, ...]
    failures: tuple[str, ...]


def _is_git_ignored(repo_root: Path, relative: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", relative],
            cwd=repo_root,
            check=False,
            capture_output=True,
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0


def validate_repo_layout(paths: RepoPaths) -> LayoutCheckResult:
    checks: list[str] = []
    failures: list[str] = []

    for name in _REQUIRED_DIRS:
        directory = paths.repo_root / name
        checks.append(f"{name}/ exists")
        if not directory.is_dir():
            failures.append(f"required directory missing: {name}/")

    checks.append("data/raw is a symlink (raw data lives outside the repository)")
    if paths.data_raw.exists() and not paths.data_raw.is_symlink():
        failures.append(
            "data/raw must be a symlink to an external raw-data root, not a committed directory"
        )

    for relative in ("checkpoints/__layout_probe__", "outputs/__layout_probe__"):
        checks.append(f"{relative} is git-ignored")
        if not _is_git_ignored(paths.repo_root, relative):
            root = relative.split("/")[0]
            failures.append(f"{root}/ contents must be git-ignored but are not")

    checks.append("results/ is tracked (curated outputs are not git-ignored)")
    if _is_git_ignored(paths.repo_root, "results/__layout_probe__"):
        failures.append("results/ must not be git-ignored: curated outputs are tracked")

    return LayoutCheckResult(passed=not failures, checks=tuple(checks), failures=tuple(failures))


def validate_checkpoint_not_under_outputs(artifact_path: str) -> None:
    """Checkpoints are a separate frozen vault (checkpoints/); outputs/ holds runtime artifacts."""
    if artifact_path.startswith("outputs/"):
        raise ArtifactPlacementError(
            f"checkpoint artifact path {artifact_path!r} must not live under outputs/; "
            "checkpoints are a separate frozen vault"
        )


def validate_result_has_manifest(result_path: Path, manifest_path: Path) -> None:
    """Every curated result/ file must carry a companion manifest (artifact_contracts.md #2)."""
    if not manifest_path.exists():
        raise ArtifactPlacementError(
            f"curated result {result_path} has no companion manifest at {manifest_path}"
        )

"""Canonical repository path resolution.

Every other module resolves filesystem locations through this module instead
of building paths ad hoc. Only ``DATP_DATA_ROOT`` (documented in
``.env.example``) may override a root; every other root is derived from the
detected repository root.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

_REPO_MARKER_FILES = ("AGENTS.md", "pyproject.toml")
DATA_ROOT_ENV_VAR = "DATP_DATA_ROOT"


class PathResolutionError(RuntimeError):
    """Raised when a repository root or artifact path cannot be resolved safely."""


@dataclass(frozen=True)
class RepoPaths:
    """Canonical filesystem roots for a single repository checkout."""

    repo_root: Path
    configs: Path
    data: Path
    data_raw: Path
    data_preprocessed: Path
    data_manifests: Path
    checkpoints: Path
    outputs: Path
    results: Path
    outputs_logs: Path
    outputs_scores: Path
    outputs_metrics: Path
    outputs_manifests: Path
    outputs_tables: Path
    outputs_figures: Path


def find_repo_root(start: Path | None = None) -> Path:
    """Walk upward from ``start`` until a directory carries every repo marker file."""
    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if all((candidate / marker).is_file() for marker in _REPO_MARKER_FILES):
            return candidate
    raise PathResolutionError(f"no repository root found above {current}: missing marker files {_REPO_MARKER_FILES}")


def resolve_paths(
    repo_root: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> RepoPaths:
    """Resolve every canonical root relative to the detected (or given) repo root.

    ``env`` defaults to ``os.environ`` and is consulted only for
    ``DATP_DATA_ROOT``; any other variable has no effect on the resolved roots.
    """
    root = find_repo_root(repo_root) if repo_root is None else Path(repo_root).resolve()
    if repo_root is not None and not all((root / marker).is_file() for marker in _REPO_MARKER_FILES):
        raise PathResolutionError(f"{root} is not a valid repository root: missing marker files")

    env_map = os.environ if env is None else env
    data_root_override = env_map.get(DATA_ROOT_ENV_VAR)
    data_raw = Path(data_root_override).resolve() if data_root_override else root / "data" / "raw"

    outputs = root / "outputs"
    return RepoPaths(
        repo_root=root,
        configs=root / "configs",
        data=root / "data",
        data_raw=data_raw,
        data_preprocessed=root / "data" / "preprocessed",
        data_manifests=root / "data" / "manifests",
        checkpoints=root / "checkpoints",
        outputs=outputs,
        results=root / "results",
        outputs_logs=outputs / "logs",
        outputs_scores=outputs / "scores",
        outputs_metrics=outputs / "metrics",
        outputs_manifests=outputs / "manifests",
        outputs_tables=outputs / "tables",
        outputs_figures=outputs / "figures",
    )


def safe_join(root: Path, *segments: str) -> Path:
    """Join ``segments`` onto ``root``, rejecting any result that escapes ``root``."""
    resolved_root = root.resolve()
    candidate = resolved_root.joinpath(*segments).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise PathResolutionError(f"path escapes root {resolved_root}: {candidate}") from exc
    return candidate

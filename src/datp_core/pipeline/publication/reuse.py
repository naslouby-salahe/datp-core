"""Shared, side-effect-free reuse predicates for published directories."""

from pathlib import Path

from datp_core.domain.values import Checksum


def required_artifacts_exist(directory: Path, relative_paths: tuple[str | Path, ...]) -> bool:
    """Return whether every declared artifact exists as a regular file."""
    return all((directory / relative_path).is_file() for relative_path in relative_paths)


def complete_marker_matches(
    directory: Path,
    marker: str | Path,
    expected: Checksum,
) -> bool:
    """Compare one completion marker with a precomputed canonical digest."""
    path = directory / marker
    try:
        return path.is_file() and path.read_text(encoding="utf-8").strip() == expected.value
    except OSError:
        return False

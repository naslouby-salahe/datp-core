"""Git-revision provenance capture for artifact commits."""

from __future__ import annotations

import subprocess


def git_revision() -> str:
    """Capture the current git revision for artifact-commit provenance."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "unknown"

"""No-overwrite policy for produced artifacts and curated results.

Production outputs are never overwritten silently (docs/protocol/reuse_policy.md
"No stale labels"; MASTER_TICKET_LOG.md R14).
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path


class WriteMode(StrEnum):
    CREATE_NEW = "create_new"
    RESUME_SAME_RUN_IF_MANIFEST_MATCHES = "resume_same_run_if_manifest_matches"
    OVERWRITE_ONLY_IF_EXPLICIT_AND_MARKED_DEV = "overwrite_only_if_explicit_and_marked_dev"


class OverwriteGuardError(RuntimeError):
    """Raised when a write would silently clobber an existing artifact."""


def guard_artifact_write(
    path: Path,
    mode: WriteMode,
    existing_manifest_id: str | None = None,
    requested_manifest_id: str | None = None,
    explicit_dev_flag: bool = False,
) -> None:
    """Raise :class:`OverwriteGuardError` unless writing to ``path`` under ``mode`` is safe."""
    if not path.exists():
        return

    if mode is WriteMode.CREATE_NEW:
        raise OverwriteGuardError(f"{path} already exists; create_new mode never overwrites")

    if mode is WriteMode.RESUME_SAME_RUN_IF_MANIFEST_MATCHES:
        if existing_manifest_id != requested_manifest_id:
            raise OverwriteGuardError(
                f"{path} exists with manifest {existing_manifest_id!r}; requested manifest "
                f"{requested_manifest_id!r} does not match, resume rejected"
            )
        return

    if mode is WriteMode.OVERWRITE_ONLY_IF_EXPLICIT_AND_MARKED_DEV:
        if not explicit_dev_flag:
            raise OverwriteGuardError(f"{path} exists; overwrite requires explicit_dev_flag=True")
        return


def guard_results_overwrite(
    path: Path,
    existing_source_manifest_id: str | None,
    requested_source_manifest_id: str,
    explicit_refresh: bool = False,
) -> None:
    """Curated results (results/) may only be overwritten if the source manifest matches
    or an explicit refresh is requested (docs/protocol/artifact_contracts.md #2).
    """
    if not path.exists():
        return
    if explicit_refresh:
        return
    if existing_source_manifest_id != requested_source_manifest_id:
        raise OverwriteGuardError(
            f"{path} is a curated result from source manifest {existing_source_manifest_id!r}; "
            f"requested source manifest {requested_source_manifest_id!r} does not match and "
            "explicit_refresh was not set"
        )

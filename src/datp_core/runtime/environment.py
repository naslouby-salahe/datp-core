"""Runtime checks that refuse unsafe raw-source and device-policy conditions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class RawSourceStatus:
    root: Path
    readable: bool
    resolved: Path
    reason: str | None


def preflight_raw_source(root: Path, *, follow_symlink: bool, require_readable: bool) -> RawSourceStatus:
    if root.is_symlink() and not follow_symlink:
        return RawSourceStatus(root=root, readable=False, resolved=root, reason="raw source symlink is forbidden")
    try:
        resolved = root.resolve(strict=True)
    except OSError as error:
        return RawSourceStatus(root=root, readable=False, resolved=root, reason=str(error))
    readable = resolved.is_dir() and (not require_readable or any(resolved.iterdir()))
    return RawSourceStatus(
        root=root,
        readable=readable,
        resolved=resolved,
        reason=None if readable else "raw source is unreadable or empty",
    )

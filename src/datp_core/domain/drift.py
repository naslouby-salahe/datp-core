"""Deterministic structured diffing of two canonical configuration projections.

Replaces comparing two opaque fingerprint hash strings (or raw YAML text) with a small,
project-specific structural diff over the same ``CanonicalProjection`` tree the fingerprint
hash is computed from -- reporting the exact domain paths, old/new values, and additions or
removals that changed.
"""

from __future__ import annotations

from typing import Literal

from attrs import define

from datp_core.domain.fingerprints import CanonicalProjection


@define(frozen=True, slots=True, kw_only=True)
class DriftEntry:
    """One structural difference between two canonical projections."""

    path: str
    kind: Literal["changed", "added", "removed"]
    old_value: CanonicalProjection = None
    new_value: CanonicalProjection = None


def diff_canonical_projections(
    before: CanonicalProjection, after: CanonicalProjection, *, path: str = "$"
) -> tuple[DriftEntry, ...]:
    """Walk two canonical projections and report every changed, added, or removed path."""
    if isinstance(before, dict) and isinstance(after, dict):
        entries: list[DriftEntry] = []
        for key in sorted(set(before) | set(after)):
            child_path = f"{path}.{key}"
            if key not in before:
                entries.append(DriftEntry(path=child_path, kind="added", new_value=after[key]))
            elif key not in after:
                entries.append(DriftEntry(path=child_path, kind="removed", old_value=before[key]))
            else:
                entries.extend(diff_canonical_projections(before[key], after[key], path=child_path))
        return tuple(entries)

    if isinstance(before, list) and isinstance(after, list):
        entries = []
        for index in range(max(len(before), len(after))):
            child_path = f"{path}[{index}]"
            if index >= len(before):
                entries.append(DriftEntry(path=child_path, kind="added", new_value=after[index]))
            elif index >= len(after):
                entries.append(DriftEntry(path=child_path, kind="removed", old_value=before[index]))
            else:
                entries.extend(diff_canonical_projections(before[index], after[index], path=child_path))
        return tuple(entries)

    if before != after:
        return (DriftEntry(path=path, kind="changed", old_value=before, new_value=after),)
    return ()

"""Canonical-projection diffing and configuration drift use cases.

Walks two canonical projections and reports every changed, added, or removed path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from attrs import define

from datp_core.config.loading import YamlConfigurationReader
from datp_core.core.hashing import CanonicalProjection, canonicalize_value


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
    entries: list[DriftEntry] = []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            child_path = f"{path}.{key}"
            if key not in before:
                entries.append(DriftEntry(path=child_path, kind="added", new_value=after[key]))
            elif key not in after:
                entries.append(DriftEntry(path=child_path, kind="removed", old_value=before[key]))
            else:
                entries.extend(diff_canonical_projections(before[key], after[key], path=child_path))
    elif isinstance(before, list) and isinstance(after, list):
        for index in range(max(len(before), len(after))):
            child_path = f"{path}[{index}]"
            if index >= len(before):
                entries.append(DriftEntry(path=child_path, kind="added", new_value=after[index]))
            elif index >= len(after):
                entries.append(DriftEntry(path=child_path, kind="removed", old_value=before[index]))
            else:
                entries.extend(diff_canonical_projections(before[index], after[index], path=child_path))
    elif before != after:
        entries.append(DriftEntry(path=path, kind="changed", old_value=before, new_value=after))
    return tuple(entries)


@define(frozen=True, slots=True, kw_only=True)
class ConfigurationDriftReport:
    """Report detailing structural or value differences between two configurations."""

    has_drift: bool
    drift_kind: str
    diff_entries: tuple[DriftEntry, ...]


class ExplainAuthoredConfigurationDrift:
    """Use case comparing two authored YAML files and reporting parsed-value differences.

    Both documents are parsed (duplicate-key-safe) before comparison, so formatting, comments,
    whitespace, and key ordering never produce drift -- only an actual authored-value change does.
    """

    def execute(self, current_yaml_path: Path, expected_yaml_path: Path) -> ConfigurationDriftReport:
        current_document = canonicalize_value(YamlConfigurationReader.read_document(current_yaml_path))
        expected_document = canonicalize_value(YamlConfigurationReader.read_document(expected_yaml_path))
        entries = diff_canonical_projections(expected_document, current_document)
        return ConfigurationDriftReport(
            has_drift=len(entries) > 0,
            drift_kind="authored_yaml",
            diff_entries=entries,
        )


__all__ = [
    "ConfigurationDriftReport",
    "DriftEntry",
    "ExplainAuthoredConfigurationDrift",
    "diff_canonical_projections",
]

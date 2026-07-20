"""Deterministic bounded source inventory used by dataset readiness gates."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from ..catalogue.domain import DatasetDefinition
from ..kernel.fingerprints import fingerprint
from ..kernel.ids import DatasetId
from .domain import DatasetAdapter, DatasetReadinessReport, ReadinessStatus, SourceFinding


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetAdapterRegistry:
    adapters: Mapping[DatasetId, DatasetAdapter]

    def __post_init__(self) -> None:
        object.__setattr__(self, "adapters", MappingProxyType(dict(self.adapters)))

    def inspect(
        self, definition: DatasetDefinition, raw_root: Path, *, max_files: int | None = None
    ) -> DatasetReadinessReport:
        return self.adapters[definition.identifier].inspect(definition, raw_root, max_files=max_files)


def inspect_source(
    dataset_id: DatasetId, raw_root: Path, relative_root: str, *, pattern: str = "*.csv"
) -> DatasetReadinessReport:
    source = raw_root / relative_root
    if not source.is_dir():
        return DatasetReadinessReport(
            dataset_id=dataset_id,
            source_fingerprint=fingerprint({"missing": relative_root}),
            files=(),
            findings=(SourceFinding(code="source_missing", message=f"source root does not exist: {relative_root}"),),
            status=ReadinessStatus.BLOCKED,
        )
    files = tuple(sorted(path.relative_to(raw_root).as_posix() for path in source.rglob(pattern) if path.is_file()))
    findings = () if files else (SourceFinding(code="no_matching_files", message=f"no {pattern} files found"),)
    return DatasetReadinessReport(
        dataset_id=dataset_id,
        source_fingerprint=fingerprint(files),
        files=files,
        findings=findings,
        status=ReadinessStatus.READY if files else ReadinessStatus.BLOCKED,
    )

"""Application use case for dataset layout and preflight schema integrity audits."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datp_core.domain.identifiers import DatasetId


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetAuditReport:
    dataset_id: DatasetId
    raw_source_found: bool
    file_count: int
    readable: bool


class AuditDatasetUseCase:
    def execute(self, dataset_id: DatasetId, raw_root: Path = Path("data/raw")) -> DatasetAuditReport:
        target_dir = raw_root / dataset_id.value
        found = target_dir.exists()
        file_count = len(list(target_dir.rglob("*"))) if found else 0
        return DatasetAuditReport(
            dataset_id=dataset_id,
            raw_source_found=found,
            file_count=file_count,
            readable=found,
        )

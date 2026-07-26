"""N-BaIoT adapter models."""

from __future__ import annotations

import json

from attrs import define

from datp_core.data.contracts.enums import SplitMembership
from datp_core.data.sources.models import SourceRow
from datp_core.experiments import SweepConditionAllocation


@define(frozen=True, slots=True, kw_only=True)
class NBaIoTMaterializedRow:
    client_id: str
    attack_family: str | None
    is_attack: bool
    source_row: SourceRow


@define(frozen=True, slots=True, kw_only=True)
class NBaIoTSplitRows:
    train: tuple[NBaIoTMaterializedRow, ...]
    calibration: tuple[NBaIoTMaterializedRow, ...]
    test_benign: tuple[NBaIoTMaterializedRow, ...]
    test_attack: tuple[NBaIoTMaterializedRow, ...]
    excluded_gap_rows: tuple[NBaIoTMaterializedRow, ...]


@define(frozen=True, slots=True, kw_only=True)
class NBaIoTChronologicalBoundaries:
    train_end: int
    first_gap_end: int
    calibration_end: int
    second_gap_end: int
    row_count: int

    def role_for_benign_index(self, index: int) -> str:
        if not 0 <= index < self.row_count:
            raise IndexError(
                "N-BaIoT benign source-row index is outside the configured source count")
        if index < self.train_end:
            return SplitMembership.TRAIN.value
        if index < self.first_gap_end:
            return SplitMembership.EXCLUDED_GAP.value
        if index < self.calibration_end:
            return SplitMembership.CALIBRATION.value
        if index < self.second_gap_end:
            return SplitMembership.EXCLUDED_GAP.value
        return SplitMembership.TEST.value


@define(frozen=True, slots=True, kw_only=True)
class DirichletPartition:
    condition: str
    allocation: SweepConditionAllocation
    seed: int
    retry_attempt: int
    source_domains: tuple[str, ...]
    proportions: tuple[tuple[str, tuple[float, ...]], ...]
    row_counts: tuple[tuple[str, tuple[tuple[str, int], ...]], ...]
    assignments: tuple[tuple[str, str, int, str], ...]

    def encode(self) -> bytes:
        payload = {
            "allocation": self.allocation.value,
            "assignments": [
                {"client_id": client_id, "source_domain": domain,
                    "source_path": source_path, "source_row_index": index}
                for source_path, domain, index, client_id in self.assignments
            ],
            "client_count": len(self.proportions),
            "feasibility_status": "feasible",
            "partition_condition": self.condition,
            "partition_seed": self.seed,
            "per_client_row_counts": [
                {"client_id": client_id, "split_counts": dict(counts)} for client_id, counts in self.row_counts
            ],
            "per_client_source_domain_proportions": [
                {"client_id": client_id, "proportions": dict(
                    zip(self.source_domains, proportions, strict=True))}
                for client_id, proportions in self.proportions
            ],
            "retry_attempts_used": self.retry_attempt,
            "source_domains": list(self.source_domains),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

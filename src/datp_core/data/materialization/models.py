"""Shared materialization result model."""

from __future__ import annotations

from pathlib import Path

from attrs import define


@define(frozen=True, slots=True, kw_only=True)
class MaterializationResult:
    staged_path: Path
    row_count: int
    preprocessing_evidence: bytes
    partition_evidence: bytes | None = None

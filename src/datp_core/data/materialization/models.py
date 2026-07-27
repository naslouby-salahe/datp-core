"""Shared materialization result model."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class MaterializationResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    staged_path: Path
    row_count: int
    preprocessing_evidence: bytes
    partition_evidence: bytes | None = None

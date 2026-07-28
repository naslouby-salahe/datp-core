"""Strict configuration-model foundation for the data package."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        validate_default=True,
    )

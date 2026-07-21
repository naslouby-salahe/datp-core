"""Strict Pydantic 2 base classes shared by all authored configuration document models.

Every authored configuration model must inherit from one of these base classes
so that the strict parsing policy is defined in exactly one place.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class StrictFrozenConfigModel(BaseModel):
    """Base for every authored configuration model.

    ``extra="forbid"`` — unknown YAML keys are rejected.
    ``frozen=True`` — models are immutable after construction.
    ``strict=True`` — Pydantic's strict-mode coercion is enabled (no int→float, etc.).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class SchemaVersionOneConfigModel(StrictFrozenConfigModel):
    """Root document model for schema-version-1 authored documents.

    Declares the ``schema_version`` field locked to ``1``.  Any YAML document
    that supplies a different value, or omits the field, is rejected by Pydantic.
    """

    schema_version: Literal[1]

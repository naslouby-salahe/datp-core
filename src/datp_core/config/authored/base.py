"""Strict Pydantic 2 base classes shared by every authored configuration schema module.

Every authored configuration model inherits from one of the two base classes defined here, so the
strict parsing policy (``extra="forbid"``, ``frozen=True``, ``strict=True``, and the
``schema_version: Literal[1]`` lock) is defined in exactly one place across the whole authored schema.
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

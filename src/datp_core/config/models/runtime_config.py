"""Pydantic 2 models for authored runtime configuration (runtime.yaml)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuthoredRuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    roots: dict[str, str]
    raw_source_policy: dict[str, Any]
    determinism_enforcement: dict[str, Any]
    device_policy_rules: dict[str, Any]
    resource_pressure_policy: dict[str, Any]
    execution_profiles: dict[str, Any]

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError(f"Unsupported runtime schema version: {value}")
        return value

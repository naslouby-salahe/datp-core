"""Pydantic 2 models for authored runtime configuration (runtime.yaml)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator


class RawSourcePolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    follow_symlink: bool
    require_resolved_target_readable: bool
    reject_broken_symlink: bool
    reject_symlink_loop: bool
    write_access: str
    create_files_under_raw_root: str


class DeterminismEnforcementConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    strict: dict[str, JsonValue]


class DevicePolicyRulesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    cuda_required: dict[str, str]
    cpu_only: dict[str, list[str] | bool]


class ResourcePressurePolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    silent_reduction_of_batch_size: str
    silent_reduction_of_rounds_seeds_clients_or_sample_counts: str
    on_budget_exceeded: str


class ExecutionProfileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    device_policy: str
    determinism: str
    resource_budget: dict[str, int]
    concurrency: dict[str, int]
    data_loading: dict[str, int | bool]
    process_start_method: str
    log_interval_rounds: int
    atomic_write: bool
    temporary_storage: str | None = None
    temporary_storage_cleanup: str | None = None


class AuthoredRuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int = Field(ge=1)
    roots: dict[str, str]
    raw_source_policy: RawSourcePolicyConfig
    determinism_enforcement: DeterminismEnforcementConfig
    device_policy_rules: DevicePolicyRulesConfig
    resource_pressure_policy: ResourcePressurePolicyConfig
    execution_profiles: dict[str, ExecutionProfileConfig]

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError(f"Unsupported runtime schema version: {value}")
        return value

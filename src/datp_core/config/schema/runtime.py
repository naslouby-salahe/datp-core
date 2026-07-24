"""Strict Pydantic 2 models for the authored runtime configuration document (runtime.yaml)."""

from __future__ import annotations

from datp_core.config.schema import SchemaVersionOneConfigModel, StrictFrozenConfigModel


class DataLoadingConfig(StrictFrozenConfigModel):
    """Strict typed contract for per-execution-profile data-loading settings."""

    chunk_row_count: int
    streaming: bool


class ResourceBudgetConfig(StrictFrozenConfigModel):
    """Strict typed contract for per-execution-profile resource budget."""

    max_ram_gib: int
    max_vram_gib: int | None = None


class ConcurrencyConfig(StrictFrozenConfigModel):
    """Strict typed contract for per-execution-profile concurrency limits.

    Fields vary across execution profiles; all are optional except ``worker_count``.
    """

    worker_count: int
    training_concurrency: int | None = None
    scoring_concurrency: int | None = None
    audit_concurrency: int | None = None


class RawSourcePolicyConfig(StrictFrozenConfigModel):
    follow_symlink: bool
    require_resolved_target_readable: bool
    reject_broken_symlink: bool
    reject_symlink_loop: bool
    write_access: str
    create_files_under_raw_root: str


class DeterminismStrictConfig(StrictFrozenConfigModel):
    python_hash_seed: int
    cublas_workspace_config: str
    torch_use_deterministic_algorithms: bool
    torch_deterministic_algorithms_warn_only: bool
    cudnn_deterministic: bool
    cudnn_benchmark: bool
    float32_matmul_precision: str
    tensorfloat32_matmul: bool
    tensorfloat32_cudnn: bool
    dataloader_worker_seeding: str
    file_discovery_order: str
    client_iteration_order: str
    nondeterministic_operation_policy: str
    recorded_environment_fields: list[str]
    unavailable_determinism_policy: str


class DeterminismEnforcementConfig(StrictFrozenConfigModel):
    strict: DeterminismStrictConfig


class DevicePolicyRulesConfig(StrictFrozenConfigModel):
    cuda_required: dict[str, str]
    cpu_only: dict[str, list[str] | bool]


class ResourcePressurePolicyConfig(StrictFrozenConfigModel):
    silent_reduction_of_batch_size: str
    silent_reduction_of_rounds_seeds_clients_or_sample_counts: str
    on_budget_exceeded: str


class ExecutionProfileConfig(StrictFrozenConfigModel):
    device_policy: str
    determinism: str
    resource_budget: ResourceBudgetConfig
    concurrency: ConcurrencyConfig
    data_loading: DataLoadingConfig
    process_start_method: str
    log_interval_rounds: int
    atomic_write: bool
    temporary_storage: str | None = None
    temporary_storage_cleanup: str | None = None


class AuthoredRuntimeConfig(SchemaVersionOneConfigModel):
    roots: dict[str, str]
    raw_source_policy: RawSourcePolicyConfig
    determinism_enforcement: DeterminismEnforcementConfig
    device_policy_rules: DevicePolicyRulesConfig
    resource_pressure_policy: ResourcePressurePolicyConfig
    execution_profiles: dict[str, ExecutionProfileConfig]

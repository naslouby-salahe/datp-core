"""Environment and bootstrap runtime settings using pydantic-settings and single resolved paths authority."""

from __future__ import annotations

from pathlib import Path

from attrs import define
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from datp_core.config.models.runtime_config import AuthoredRuntimeConfig
from datp_core.domain.values import PositiveInt


class RuntimeBootstrapSettings(BaseSettings):
    """External bootstrap settings that cannot be authored in repository YAML."""

    model_config = SettingsConfigDict(
        env_prefix="DATP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    repository_root: Path = Field(default_factory=lambda: Path.cwd().resolve())
    config_root: Path = Field(default_factory=lambda: Path("configs").resolve())
    dagster_home: Path | None = None
    environment_identity: str = "local_linux"


@define(frozen=True, slots=True, kw_only=True)
class ResolvedProjectPaths:
    """Immutable resolved project paths resolved once at bootstrap time."""

    repository_root: Path
    config_root: Path
    raw_data: Path
    processed_data: Path
    manifests: Path
    checkpoints: Path
    outputs: Path
    runtime_state: Path

    def __attrs_post_init__(self) -> None:
        if not self.repository_root.is_absolute():
            raise ValueError(f"Repository root must be absolute: {self.repository_root}")
        if not self.config_root.is_absolute():
            raise ValueError(f"Config root must be absolute: {self.config_root}")


@define(frozen=True, slots=True, kw_only=True)
class ExecutionProfileRecord:
    """Pure resolved execution profile (runtime.yaml `execution_profiles`)."""

    identifier: str
    device_policy: str
    determinism: str
    resource_budget: dict[str, int]
    concurrency: dict[str, int]
    data_loading: dict[str, int | bool]
    process_start_method: str
    log_interval_rounds: PositiveInt
    atomic_write: bool
    temporary_storage: str | None
    temporary_storage_cleanup: str | None


@define(frozen=True, slots=True, kw_only=True)
class RawSourcePolicyRecord:
    """Pure resolved raw-source access policy (runtime.yaml `raw_source_policy`)."""

    follow_symlink: bool
    require_resolved_target_readable: bool
    reject_broken_symlink: bool
    reject_symlink_loop: bool
    write_access: str
    create_files_under_raw_root: str


@define(frozen=True, slots=True, kw_only=True)
class DeterminismStrictRecord:
    """Pure resolved strict determinism-enforcement contract."""

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
    recorded_environment_fields: tuple[str, ...]
    unavailable_determinism_policy: str


@define(frozen=True, slots=True, kw_only=True)
class DevicePolicyRecord:
    """Pure resolved device policy (runtime.yaml `device_policy_rules`)."""

    cuda_required: dict[str, str]
    cpu_only: dict[str, tuple[str, ...] | bool]


@define(frozen=True, slots=True, kw_only=True)
class ResourcePressureRecord:
    """Pure resolved resource-pressure policy (runtime.yaml `resource_pressure_policy`)."""

    silent_reduction_of_batch_size: str
    silent_reduction_of_rounds_seeds_clients_or_sample_counts: str
    on_budget_exceeded: str


@define(frozen=True, slots=True, kw_only=True)
class ResolvedRuntimeConfiguration:
    """Fully resolved runtime configuration combining bootstrap settings and runtime.yaml."""

    bootstrap: RuntimeBootstrapSettings
    paths: ResolvedProjectPaths
    raw_source_policy: RawSourcePolicyRecord
    determinism_enforcement: DeterminismStrictRecord
    device_policy_rules: DevicePolicyRecord
    resource_pressure_policy: ResourcePressureRecord
    execution_profiles: dict[str, ExecutionProfileRecord]


def resolve_runtime_configuration(
    authored_runtime: AuthoredRuntimeConfig,
    bootstrap_settings: RuntimeBootstrapSettings | None = None,
) -> ResolvedRuntimeConfiguration:
    """Resolve runtime paths and configuration once during composition."""
    settings = bootstrap_settings or RuntimeBootstrapSettings()
    repo_root = settings.repository_root.resolve()
    config_root = (
        (repo_root / settings.config_root).resolve()
        if not settings.config_root.is_absolute()
        else settings.config_root.resolve()
    )

    roots = authored_runtime.roots
    resolved_paths = ResolvedProjectPaths(
        repository_root=repo_root,
        config_root=config_root,
        raw_data=(repo_root / roots["raw_data"]).resolve(),
        processed_data=(repo_root / roots["processed_data"]).resolve(),
        manifests=(repo_root / roots["manifests"]).resolve(),
        checkpoints=(repo_root / roots["checkpoints"]).resolve(),
        outputs=(repo_root / roots["outputs"]).resolve(),
        runtime_state=(repo_root / roots["runtime_state"]).resolve(),
    )

    raw = authored_runtime.raw_source_policy
    strict = authored_runtime.determinism_enforcement.strict
    device = authored_runtime.device_policy_rules
    pressure = authored_runtime.resource_pressure_policy
    return ResolvedRuntimeConfiguration(
        bootstrap=settings,
        paths=resolved_paths,
        raw_source_policy=RawSourcePolicyRecord(
            follow_symlink=raw.follow_symlink,
            require_resolved_target_readable=raw.require_resolved_target_readable,
            reject_broken_symlink=raw.reject_broken_symlink,
            reject_symlink_loop=raw.reject_symlink_loop,
            write_access=raw.write_access,
            create_files_under_raw_root=raw.create_files_under_raw_root,
        ),
        determinism_enforcement=DeterminismStrictRecord(
            python_hash_seed=strict.python_hash_seed,
            cublas_workspace_config=strict.cublas_workspace_config,
            torch_use_deterministic_algorithms=strict.torch_use_deterministic_algorithms,
            torch_deterministic_algorithms_warn_only=strict.torch_deterministic_algorithms_warn_only,
            cudnn_deterministic=strict.cudnn_deterministic,
            cudnn_benchmark=strict.cudnn_benchmark,
            float32_matmul_precision=strict.float32_matmul_precision,
            tensorfloat32_matmul=strict.tensorfloat32_matmul,
            tensorfloat32_cudnn=strict.tensorfloat32_cudnn,
            dataloader_worker_seeding=strict.dataloader_worker_seeding,
            file_discovery_order=strict.file_discovery_order,
            client_iteration_order=strict.client_iteration_order,
            nondeterministic_operation_policy=strict.nondeterministic_operation_policy,
            recorded_environment_fields=tuple(strict.recorded_environment_fields),
            unavailable_determinism_policy=strict.unavailable_determinism_policy,
        ),
        device_policy_rules=DevicePolicyRecord(
            cuda_required=dict(device.cuda_required),
            cpu_only={k: (tuple(v) if isinstance(v, list) else v) for k, v in device.cpu_only.items()},
        ),
        resource_pressure_policy=ResourcePressureRecord(
            silent_reduction_of_batch_size=pressure.silent_reduction_of_batch_size,
            silent_reduction_of_rounds_seeds_clients_or_sample_counts=(
                pressure.silent_reduction_of_rounds_seeds_clients_or_sample_counts
            ),
            on_budget_exceeded=pressure.on_budget_exceeded,
        ),
        execution_profiles={
            key: ExecutionProfileRecord(
                identifier=key,
                device_policy=profile.device_policy,
                determinism=profile.determinism,
                resource_budget=dict(profile.resource_budget),
                concurrency=dict(profile.concurrency),
                data_loading=dict(profile.data_loading),
                process_start_method=profile.process_start_method,
                log_interval_rounds=PositiveInt(profile.log_interval_rounds),
                atomic_write=profile.atomic_write,
                temporary_storage=profile.temporary_storage,
                temporary_storage_cleanup=profile.temporary_storage_cleanup,
            )
            for key, profile in authored_runtime.execution_profiles.items()
        },
    )

"""Resolution of runtime.yaml plus bootstrap settings into the fully resolved runtime configuration.

Kept as its own module (parallel to config/resolve/{datasets,experiments,protocols}.py) because it
resolves exactly one authored document (runtime.yaml) into typed records, the same axis those three
siblings use.
"""

from __future__ import annotations

import errno
import os
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from attrs import define, field

from datp_core.config.loading import RuntimeBootstrapSettings, resolve_config_root
from datp_core.config.schema.runtime import AuthoredRuntimeConfig, RawSourcePolicyConfig
from datp_core.core.values import PositiveInt, TypedDomainRegistry, deep_freeze


class PathAuthorityError(ValueError):
    """Raised when a configured root violates the raw-symlink policy or escapes the repository root."""


def _resolve_raw_data_root(candidate: Path, policy: RawSourcePolicyConfig) -> Path:
    """Enforce the authored raw-source symlink policy before ever calling ``.resolve()``.

    ``.resolve()`` silently collapses symlinks; policy violations must be rejected first,
    while the symlink is still intact and inspectable.
    """
    if not candidate.is_symlink():
        if not candidate.exists():
            raise PathAuthorityError(f"Raw data root does not exist: {candidate}")
        return candidate.resolve()

    if not policy.follow_symlink:
        raise PathAuthorityError(f"Raw data root '{candidate}' is a symlink but follow_symlink is disabled")

    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        is_loop = isinstance(exc, RuntimeError) or (isinstance(exc, OSError) and exc.errno == errno.ELOOP)
        if is_loop:
            if policy.reject_symlink_loop:
                raise PathAuthorityError(f"Raw data root '{candidate}' has a symlink loop") from exc
        elif policy.reject_broken_symlink:
            raise PathAuthorityError(f"Raw data root '{candidate}' is a broken symlink") from exc
        resolved = candidate.resolve(strict=False)

    if policy.require_resolved_target_readable and not os.access(resolved, os.R_OK):
        raise PathAuthorityError(f"Raw data root resolved target '{resolved}' is not readable")
    return resolved


def _resolve_contained_root(repository_root: Path, relative_root: str) -> Path:
    """Resolve a non-raw project root and reject any escape outside ``repository_root``."""
    resolved = (repository_root / relative_root).resolve()
    if not resolved.is_relative_to(repository_root):
        raise PathAuthorityError(f"Configured root '{relative_root}' resolves outside the repository root: {resolved}")
    return resolved


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
class DataLoadingRecord:
    """Pure resolved data-loading contract (runtime.yaml ``data_loading``)."""

    chunk_row_count: PositiveInt
    streaming: bool


@define(frozen=True, slots=True, kw_only=True)
class ResourceBudgetRecord:
    """Pure resolved resource-budget contract (runtime.yaml ``resource_budget``)."""

    max_ram_gib: PositiveInt
    max_vram_gib: int | None = None


@define(frozen=True, slots=True, kw_only=True)
class ConcurrencyRecord:
    """Pure resolved concurrency contract (runtime.yaml ``concurrency``)."""

    worker_count: PositiveInt
    training_concurrency: int | None = None
    scoring_concurrency: int | None = None
    audit_concurrency: int | None = None


@define(frozen=True, slots=True, kw_only=True)
class ExecutionProfileRecord:
    """Pure resolved execution profile (runtime.yaml ``execution_profiles``)."""

    identifier: str
    device_policy: str
    determinism: str
    resource_budget: ResourceBudgetRecord
    concurrency: ConcurrencyRecord
    data_loading: DataLoadingRecord
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


def _as_mapping_str_str(value: object) -> Mapping[str, str]:
    return cast("Mapping[str, str]", deep_freeze(value))


def _as_mapping_str_tuple_or_bool(value: object) -> Mapping[str, tuple[str, ...] | bool]:
    return cast("Mapping[str, tuple[str, ...] | bool]", deep_freeze(value))


@define(frozen=True, slots=True, kw_only=True)
class DevicePolicyRecord:
    """Pure resolved device policy (runtime.yaml `device_policy_rules`)."""

    cuda_required: Mapping[str, str] = field(converter=_as_mapping_str_str)
    cpu_only: Mapping[str, tuple[str, ...] | bool] = field(converter=_as_mapping_str_tuple_or_bool)


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
    execution_profiles: TypedDomainRegistry[str, ExecutionProfileRecord]
    active_execution_profile: ExecutionProfileRecord


def resolve_runtime_configuration(
    authored_runtime: AuthoredRuntimeConfig,
    bootstrap_settings: RuntimeBootstrapSettings | None = None,
) -> ResolvedRuntimeConfiguration:
    """Resolve runtime paths and configuration once during composition."""
    # execution_profile has no default and is not passed positionally here by design -- it is
    # required from the environment (DATP_EXECUTION_PROFILE) or an explicit .env entry; pydantic-
    # settings supplies it at runtime even though pyright cannot see that a Settings subclass'
    # required fields may be sourced from the environment instead of the constructor call site.
    settings = bootstrap_settings or RuntimeBootstrapSettings()  # pyright: ignore[reportCallIssue]
    repo_root = settings.repository_root.resolve()
    config_root = resolve_config_root(settings)

    roots = authored_runtime.roots
    raw = authored_runtime.raw_source_policy
    raw_data_root = _resolve_raw_data_root(repo_root / roots["raw_data"], raw)
    resolved_paths = ResolvedProjectPaths(
        repository_root=repo_root,
        config_root=config_root,
        raw_data=raw_data_root,
        processed_data=_resolve_contained_root(repo_root, roots["processed_data"]),
        manifests=_resolve_contained_root(repo_root, roots["manifests"]),
        checkpoints=_resolve_contained_root(repo_root, roots["checkpoints"]),
        outputs=_resolve_contained_root(repo_root, roots["outputs"]),
        runtime_state=_resolve_contained_root(repo_root, roots["runtime_state"]),
    )

    strict = authored_runtime.determinism_enforcement.strict
    device = authored_runtime.device_policy_rules
    pressure = authored_runtime.resource_pressure_policy
    execution_profiles = {
        key: ExecutionProfileRecord(
            identifier=key,
            device_policy=profile.device_policy,
            determinism=profile.determinism,
            resource_budget=ResourceBudgetRecord(
                max_ram_gib=PositiveInt(profile.resource_budget.max_ram_gib),
                max_vram_gib=profile.resource_budget.max_vram_gib,
            ),
            concurrency=ConcurrencyRecord(
                worker_count=PositiveInt(profile.concurrency.worker_count),
                training_concurrency=profile.concurrency.training_concurrency,
                scoring_concurrency=profile.concurrency.scoring_concurrency,
                audit_concurrency=profile.concurrency.audit_concurrency,
            ),
            data_loading=DataLoadingRecord(
                chunk_row_count=PositiveInt(profile.data_loading.chunk_row_count),
                streaming=profile.data_loading.streaming,
            ),
            process_start_method=profile.process_start_method,
            log_interval_rounds=PositiveInt(profile.log_interval_rounds),
            atomic_write=profile.atomic_write,
            temporary_storage=profile.temporary_storage,
            temporary_storage_cleanup=profile.temporary_storage_cleanup,
        )
        for key, profile in authored_runtime.execution_profiles.items()
    }
    if settings.execution_profile not in execution_profiles:
        raise ValueError(
            f"Active execution profile '{settings.execution_profile}' is not defined in runtime.yaml execution_profiles"
        )
    active_execution_profile = execution_profiles[settings.execution_profile]
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
        execution_profiles=TypedDomainRegistry(_items=execution_profiles),
        active_execution_profile=active_execution_profile,
    )

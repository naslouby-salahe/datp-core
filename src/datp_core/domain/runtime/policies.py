from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from datp_core.domain.runtime.admissibility import GpuIndex

MAXIMUM_CONCURRENT_GPU_JOBS: Final = 1

if TYPE_CHECKING:
    from datp_core.domain.experiments.identities import CellId
    from datp_core.domain.runtime.admissibility import (
        ChunkRowCount,
        CsvBlockBytes,
        DiskBudgetBytes,
        PrefetchCapacity,
        RamBudgetBytes,
        VramBudgetBytes,
        VramFraction,
        WorkerCount,
    )
    from datp_core.domain.runtime.seeds import EnumMap


class ExecutionMode(StrEnum):
    DEVELOPMENT = "development"
    SMOKE = "smoke"
    SCIENTIFIC = "scientific"
    PRINT_GRADE = "print_grade"


class DevicePolicy(StrEnum):
    CUDA_REQUIRED = "cuda_required"
    CPU_ALLOWED = "cpu_allowed"


class PipelineStage(StrEnum):
    SOURCE_INSPECTION = "source_inspection"
    FEASIBILITY_AUDIT = "feasibility_audit"
    PARTITION = "partition"
    SPLIT_BUILD = "split_build"
    PREPROCESSOR_FIT = "preprocessor_fit"
    SPLIT_MATERIALIZE = "split_materialize"
    TRAIN = "train"
    CHECKPOINT_SELECT = "checkpoint_select"
    CALIBRATION_SCORE = "calibration_score"
    TEST_SCORE = "test_score"
    TEMPORAL_SCORE = "temporal_score"
    THRESHOLD = "threshold"
    EVALUATE = "evaluate"
    ANALYZE = "analyze"
    RESOURCE_COST = "resource_cost"
    RESULT_FREEZE = "result_freeze"
    REPORT = "report"


class RunStatus(StrEnum):
    PLANNED = "planned"
    READY = "ready"
    RUNNING = "running"
    REUSED = "reused"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    PAUSED = "paused"
    RECOVERED = "recovered"


class StageConcurrency(StrEnum):
    SEQUENTIAL = "sequential"
    BOUNDED_PARALLEL = "bounded_parallel"


class ProcessStartMethod(StrEnum):
    SPAWN = "spawn"
    FORK = "fork"
    FORKSERVER = "forkserver"


class WorkerRole(StrEnum):
    MAIN = "main"
    CPU_WORKER = "cpu_worker"
    GPU_WORKER = "gpu_worker"


class RoundDisposition(StrEnum):
    COMPLETED = "completed"
    ABORTED = "aborted"
    RETRYABLE_TRANSIENT_FAILURE = "retryable_transient_failure"


class ResourcePressureLevel(StrEnum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    CRITICAL = "critical"


class PauseDecision(StrEnum):
    CONTINUE = "continue"
    PAUSE_AT_SAFE_BOUNDARY = "pause_at_safe_boundary"
    EXIT_AFTER_RECOVERY_COMMIT = "exit_after_recovery_commit"


def _validation_error(*, detail: str, value: str, constraint: str) -> None:
    from datp_core.domain.errors import DomainValidationError

    raise DomainValidationError(detail=detail, value=value, constraint=constraint)


@dataclass(frozen=True, slots=True, kw_only=True)
class DeviceSpec:
    policy: DevicePolicy
    gpu_index: GpuIndex | None

    def __post_init__(self) -> None:
        from datp_core.domain.runtime.admissibility import GpuIndex

        if type(self.policy) is not DevicePolicy:
            _validation_error(detail="device policy must be typed", value=repr(self.policy), constraint="DevicePolicy")
        if self.policy is DevicePolicy.CUDA_REQUIRED and type(self.gpu_index) is not GpuIndex:
            _validation_error(
                detail="CUDA-required device selection requires a GPU index",
                value=repr(self.gpu_index),
                constraint="GpuIndex",
            )
        if (
            self.policy is DevicePolicy.CPU_ALLOWED
            and self.gpu_index is not None
            and type(self.gpu_index) is not GpuIndex
        ):
            _validation_error(
                detail="CPU-allowed device selection may carry only a typed GPU index",
                value=repr(self.gpu_index),
                constraint="GpuIndex | None",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ResourceBudget:
    maximum_ram_bytes: RamBudgetBytes
    maximum_vram_bytes: VramBudgetBytes
    maximum_worker_count: WorkerCount
    maximum_prefetch_capacity: PrefetchCapacity
    maximum_disk_bytes: DiskBudgetBytes
    storage_safety_reserve: DiskBudgetBytes

    def __post_init__(self) -> None:
        from datp_core.domain.runtime.admissibility import (
            DiskBudgetBytes,
            PrefetchCapacity,
            RamBudgetBytes,
            VramBudgetBytes,
            WorkerCount,
        )

        if (
            type(self.maximum_ram_bytes) is not RamBudgetBytes
            or type(self.maximum_vram_bytes) is not VramBudgetBytes
            or type(self.maximum_worker_count) is not WorkerCount
            or type(self.maximum_prefetch_capacity) is not PrefetchCapacity
            or type(self.maximum_disk_bytes) is not DiskBudgetBytes
            or type(self.storage_safety_reserve) is not DiskBudgetBytes
            or self.storage_safety_reserve.value > self.maximum_disk_bytes.value
        ):
            _validation_error(
                detail="resource budget must contain typed ceilings and a feasible storage reserve",
                value=repr(self),
                constraint="typed ceilings; 0 <= reserve <= maximum disk bytes",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class StreamingChunkPolicy:
    csv_block_bytes: CsvBlockBytes
    parquet_batch_rows: ChunkRowCount

    def __post_init__(self) -> None:
        from datp_core.domain.runtime.admissibility import ChunkRowCount, CsvBlockBytes

        if type(self.csv_block_bytes) is not CsvBlockBytes or type(self.parquet_batch_rows) is not ChunkRowCount:
            _validation_error(
                detail="streaming chunk policy must contain typed CSV block bytes and parquet batch rows",
                value=repr(self),
                constraint="CsvBlockBytes and ChunkRowCount",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ParallelismSpec:
    maximum_cpu_workers: WorkerCount
    maximum_gpu_jobs: WorkerCount
    per_stage_concurrency: EnumMap[PipelineStage, StageConcurrency]
    per_stage_start_method: EnumMap[PipelineStage, ProcessStartMethod]
    per_stage_reason: EnumMap[PipelineStage, str]
    thread_limit: WorkerCount

    def __post_init__(self) -> None:
        from datp_core.domain.runtime.admissibility import WorkerCount
        from datp_core.domain.runtime.seeds import EnumMap

        if not _is_valid_parallelism_specification(self, WorkerCount, EnumMap):
            _validation_error(
                detail="parallelism must define matching typed per-stage plans and at most one GPU job",
                value=repr(self),
                constraint="matching stage EnumMaps; non-empty reasons; maximum_gpu_jobs <= 1",
            )


def _is_valid_parallelism_specification(
    specification: ParallelismSpec,
    worker_count_type: type[WorkerCount],
    enum_map_type: type[EnumMap[PipelineStage, StageConcurrency]],
) -> bool:
    return all(
        (
            _has_parallelism_component_types(specification, worker_count_type, enum_map_type),
            specification.maximum_gpu_jobs.value <= MAXIMUM_CONCURRENT_GPU_JOBS,
            _has_matching_parallelism_stage_keys(specification),
            _has_non_empty_parallelism_reasons(specification),
        )
    )


def _has_parallelism_component_types(
    specification: ParallelismSpec,
    worker_count_type: type[WorkerCount],
    enum_map_type: type[EnumMap[PipelineStage, StageConcurrency]],
) -> bool:
    return all(
        (
            type(specification.maximum_cpu_workers) is worker_count_type,
            type(specification.maximum_gpu_jobs) is worker_count_type,
            type(specification.per_stage_concurrency) is enum_map_type,
            type(specification.per_stage_start_method) is enum_map_type,
            type(specification.per_stage_reason) is enum_map_type,
            type(specification.thread_limit) is worker_count_type,
        )
    )


def _has_matching_parallelism_stage_keys(specification: ParallelismSpec) -> bool:
    concurrency_keys = tuple(entry.key for entry in specification.per_stage_concurrency.entries)
    return concurrency_keys == tuple(
        entry.key for entry in specification.per_stage_start_method.entries
    ) and concurrency_keys == tuple(entry.key for entry in specification.per_stage_reason.entries)


def _has_non_empty_parallelism_reasons(specification: ParallelismSpec) -> bool:
    return all(entry.value for entry in specification.per_stage_reason.entries)


@dataclass(frozen=True, slots=True, kw_only=True)
class ResourcePressurePolicy:
    ram_pressure_fraction: VramFraction
    vram_pressure_fraction: VramFraction
    load_pressure_fraction: VramFraction
    elevated_response: PauseDecision
    critical_response: PauseDecision

    def __post_init__(self) -> None:
        from datp_core.domain.runtime.admissibility import VramFraction

        if not _is_valid_resource_pressure_policy(self, VramFraction):
            _validation_error(
                detail="resource-pressure policy must use typed thresholds and a non-continuing critical response",
                value=repr(self),
                constraint="VramFraction thresholds and safe critical PauseDecision",
            )


def _is_valid_resource_pressure_policy(
    policy: ResourcePressurePolicy,
    fraction_type: type[VramFraction],
) -> bool:
    return all(
        (
            type(policy.ram_pressure_fraction) is fraction_type,
            type(policy.vram_pressure_fraction) is fraction_type,
            type(policy.load_pressure_fraction) is fraction_type,
            type(policy.elevated_response) is PauseDecision,
            type(policy.critical_response) is PauseDecision,
            policy.critical_response is not PauseDecision.CONTINUE,
        )
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class HardwareInventory:
    cuda_available: bool
    gpu_name: str | None
    gpu_count: int
    vram_bytes: int | None
    torch_version: str | None
    cuda_runtime: str | None
    driver_version: str | None
    cpu_count: int
    ram_bytes: int | None


@dataclass(frozen=True, slots=True, kw_only=True)
class GpuAssignment:
    stage: PipelineStage
    cell_id: CellId
    gpu_index: GpuIndex


@dataclass(frozen=True, slots=True, kw_only=True)
class ResourcePressureRequest:
    resource_budget: ResourceBudget
    pressure_policy: ResourcePressurePolicy


@dataclass(frozen=True, slots=True, kw_only=True)
class ResourcePressureSnapshot:
    level: ResourcePressureLevel
    ram_usage_fraction: float
    vram_usage_fraction: float | None
    load_usage_fraction: float
    recommended_action: PauseDecision

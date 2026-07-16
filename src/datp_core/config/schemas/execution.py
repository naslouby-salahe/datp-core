from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from datp_core.domain.learning.checkpoints import RecoveryCadence
from datp_core.domain.runtime.policies import (
    DevicePolicy,
    ExecutionMode,
    PauseDecision,
    PipelineStage,
    ProcessStartMethod,
    StageConcurrency,
)
from datp_core.domain.runtime.seeds import SeedRole

type PositiveInteger = Annotated[int, Field(gt=0)]
type NonNegativeInteger = Annotated[int, Field(ge=0)]
type UnitFraction = Annotated[Decimal, Field(gt=Decimal(0), le=Decimal(1))]


class ExecutionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ResourceBudgetConfig(ExecutionSchema):
    maximum_ram_bytes: PositiveInteger
    maximum_vram_bytes: PositiveInteger
    maximum_worker_count: NonNegativeInteger
    maximum_prefetch_capacity: NonNegativeInteger
    maximum_disk_bytes: PositiveInteger
    storage_safety_reserve: PositiveInteger


class StageExecutionConfig(ExecutionSchema):
    stage: PipelineStage
    concurrency: StageConcurrency
    start_method: ProcessStartMethod
    reason: str


class ParallelismConfig(ExecutionSchema):
    maximum_cpu_workers: NonNegativeInteger
    maximum_gpu_jobs: NonNegativeInteger
    stage_execution: tuple[StageExecutionConfig, ...]
    thread_limit: NonNegativeInteger


class ResourcePressureConfig(ExecutionSchema):
    ram_pressure_fraction: UnitFraction
    vram_pressure_fraction: UnitFraction
    load_pressure_fraction: UnitFraction
    elevated_response: PauseDecision
    critical_response: PauseDecision


class RecoveryConfig(ExecutionSchema):
    cadence: RecoveryCadence
    cadence_interval: PositiveInteger
    retention: PositiveInteger
    compatibility_identity: str


class StreamingChunkConfig(ExecutionSchema):
    csv_block_bytes: PositiveInteger
    parquet_batch_rows: PositiveInteger


class ExecutionConfig(ExecutionSchema):
    mode: ExecutionMode
    device_policy: DevicePolicy
    gpu_index: NonNegativeInteger | None
    budget: ResourceBudgetConfig
    parallelism: ParallelismConfig
    seed_roles: tuple[SeedRole, ...]
    resource_pressure: ResourcePressureConfig
    recovery: RecoveryConfig
    unresolved_fields: tuple[str, ...]

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class ScoringBatchConfig(ExecutionSchema):
    calibration_batch_size: PositiveInteger
    test_batch_size: PositiveInteger
    temporal_batch_size: PositiveInteger


class ExecutionProfileConfig(ExecutionSchema):
    profile_id: str
    scoring_batch: ScoringBatchConfig
    streaming_chunk: StreamingChunkConfig


class ExecutionProfilesConfig(ExecutionSchema):
    profiles: tuple[ExecutionProfileConfig, ...]

    @field_validator("profiles")
    @classmethod
    def _unique_profile_ids(cls, values: tuple[ExecutionProfileConfig, ...]) -> tuple[ExecutionProfileConfig, ...]:
        profile_ids = tuple(value.profile_id for value in values)
        if not values or len(set(profile_ids)) != len(profile_ids):
            raise ValueError("execution profile catalogue must contain unique non-empty profiles")
        if any(not profile_id for profile_id in profile_ids):
            raise ValueError("execution profile identifiers must be non-empty")
        return values


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

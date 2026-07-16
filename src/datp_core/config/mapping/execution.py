from datp_core.config.schemas.execution import (
    B0ScoreGenerationConfig,
    ExecutionConfig,
    ParallelismConfig,
    ScoringBatchConfig,
    StreamingChunkConfig,
)
from datp_core.domain.artifacts.lineage import RecoveryCompatibilityIdentity
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.errors import ConfigurationError
from datp_core.domain.experiments.protocols import ExecutionPolicy
from datp_core.domain.learning.checkpoints import RecoveryCheckpointPolicy
from datp_core.domain.learning.scores import B0ScoringBatchSpec, ScoringBatchSpec
from datp_core.domain.runtime.admissibility import (
    BatchSize,
    ChunkRowCount,
    CsvBlockBytes,
    DiskBudgetBytes,
    GpuIndex,
    PrefetchCapacity,
    RamBudgetBytes,
    VramBudgetBytes,
    VramFraction,
    WorkerCount,
)
from datp_core.domain.runtime.policies import (
    DeviceSpec,
    ExecutionMode,
    ParallelismSpec,
    ResourceBudget,
    ResourcePressurePolicy,
    StreamingChunkPolicy,
)
from datp_core.domain.runtime.seeds import EnumMap, EnumMapEntry, SeedRoleTuple


def map_execution_config(schema: ExecutionConfig) -> ExecutionPolicy:
    _reject_scientific_unresolved_fields(schema)
    return ExecutionPolicy(
        execution_mode=schema.mode,
        device=DeviceSpec(
            policy=schema.device_policy,
            gpu_index=GpuIndex(value=schema.gpu_index) if schema.gpu_index is not None else None,
        ),
        budget=ResourceBudget(
            maximum_ram_bytes=RamBudgetBytes(value=schema.budget.maximum_ram_bytes),
            maximum_vram_bytes=VramBudgetBytes(value=schema.budget.maximum_vram_bytes),
            maximum_worker_count=WorkerCount(value=schema.budget.maximum_worker_count),
            maximum_prefetch_capacity=PrefetchCapacity(value=schema.budget.maximum_prefetch_capacity),
            maximum_disk_bytes=DiskBudgetBytes(value=schema.budget.maximum_disk_bytes),
            storage_safety_reserve=DiskBudgetBytes(value=schema.budget.storage_safety_reserve),
        ),
        parallelism=_map_parallelism(schema.parallelism),
        seed_roles=SeedRoleTuple(values=schema.seed_roles),
        resource_pressure=ResourcePressurePolicy(
            ram_pressure_fraction=VramFraction(value=float(schema.resource_pressure.ram_pressure_fraction)),
            vram_pressure_fraction=VramFraction(value=float(schema.resource_pressure.vram_pressure_fraction)),
            load_pressure_fraction=VramFraction(value=float(schema.resource_pressure.load_pressure_fraction)),
            elevated_response=schema.resource_pressure.elevated_response,
            critical_response=schema.resource_pressure.critical_response,
        ),
        recovery=RecoveryCheckpointPolicy(
            cadence=schema.recovery.cadence,
            cadence_interval=schema.recovery.cadence_interval,
            retention=schema.recovery.retention,
            compatibility_identity=RecoveryCompatibilityIdentity(
                value=StageFingerprint(value=schema.recovery.compatibility_identity)
            ),
        ),
    )


def _reject_scientific_unresolved_fields(schema: ExecutionConfig) -> None:
    if schema.mode in {ExecutionMode.SCIENTIFIC, ExecutionMode.PRINT_GRADE} and schema.unresolved_fields:
        raise ConfigurationError(
            detail="scientific and print-grade execution cannot carry unresolved configuration fields",
            section="execution",
            field=schema.unresolved_fields[0],
            mode=schema.mode.value,
        )


def _map_parallelism(schema: ParallelismConfig) -> ParallelismSpec:
    stages = tuple(item.stage for item in schema.stage_execution)
    return ParallelismSpec(
        maximum_cpu_workers=WorkerCount(value=schema.maximum_cpu_workers),
        maximum_gpu_jobs=WorkerCount(value=schema.maximum_gpu_jobs),
        per_stage_concurrency=EnumMap(
            entries=tuple(EnumMapEntry(key=item.stage, value=item.concurrency) for item in schema.stage_execution),
            allowed_keys=stages,
            is_sparse=False,
        ),
        per_stage_start_method=EnumMap(
            entries=tuple(EnumMapEntry(key=item.stage, value=item.start_method) for item in schema.stage_execution),
            allowed_keys=stages,
            is_sparse=False,
        ),
        per_stage_reason=EnumMap(
            entries=tuple(EnumMapEntry(key=item.stage, value=item.reason) for item in schema.stage_execution),
            allowed_keys=stages,
            is_sparse=False,
        ),
        thread_limit=WorkerCount(value=schema.thread_limit),
    )


def map_streaming_chunk_config(schema: StreamingChunkConfig) -> StreamingChunkPolicy:
    return StreamingChunkPolicy(
        csv_block_bytes=CsvBlockBytes(value=schema.csv_block_bytes),
        parquet_batch_rows=ChunkRowCount(value=schema.parquet_batch_rows),
    )


def map_scoring_batch_config(schema: ScoringBatchConfig) -> ScoringBatchSpec:
    return ScoringBatchSpec(
        calibration_batch_size=BatchSize(value=schema.calibration_batch_size),
        test_batch_size=BatchSize(value=schema.test_batch_size),
        temporal_batch_size=BatchSize(value=schema.temporal_batch_size),
    )


def map_b0_score_generation_config(schema: B0ScoreGenerationConfig) -> B0ScoringBatchSpec:
    return B0ScoringBatchSpec(
        calibration_batch_size=BatchSize(value=schema.calibration_batch_size),
        test_batch_size=BatchSize(value=schema.test_batch_size),
    )

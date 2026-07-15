from datp_core.application.planning.plan import (
    DraftExecutionPlan,
    DraftPlannedStage,
    ScientificStageGateDecision,
)
from datp_core.application.runtime.preflight import (
    ArtifactCatalogueSnapshot,
    PreflightRequest,
    ResolvedBatchExecutionProfile,
    ResourcePreflightRequirements,
    StoragePreflightEvidence,
)
from datp_core.domain.artifacts.keys import ByteCount, DiskCapacity
from datp_core.domain.artifacts.lineage import StageDependencyCollection
from datp_core.domain.artifacts.references import ArtifactReferenceCollection, StageFingerprint
from datp_core.domain.data.preprocessing import PreprocessingChunkSpec
from datp_core.domain.experiments.feasibility import ScientificReadinessResult
from datp_core.domain.experiments.identities import CellId
from datp_core.domain.learning.scores import ScoringBatchSpec
from datp_core.domain.learning.training import (
    ClientBatchPartitioning,
    OptimizerStepSemantics,
    TrainingBatchSpec,
)
from datp_core.domain.runtime.admissibility import (
    BatchSize,
    ChunkRowCount,
    DiskBudgetBytes,
    GpuIndex,
    GradientAccumulationSteps,
    PrefetchCapacity,
    RamBudgetBytes,
    VramBudgetBytes,
    WorkerCount,
)
from datp_core.domain.runtime.policies import (
    DevicePolicy,
    DeviceSpec,
    HardwareInventory,
    ParallelismSpec,
    PipelineStage,
    ProcessStartMethod,
    ResourceBudget,
    StageConcurrency,
)
from datp_core.domain.runtime.seeds import EnumMap, EnumMapEntry


def runtime_fingerprint(character: str = "a") -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def runtime_profile() -> ResolvedBatchExecutionProfile:
    batch_size = BatchSize(value=8)
    return ResolvedBatchExecutionProfile(
        training=TrainingBatchSpec(
            micro_batch_size=batch_size,
            gradient_accumulation_steps=GradientAccumulationSteps(value=1),
            effective_batch_size=batch_size,
            dataloader_batch_size=batch_size,
            client_batch_partitioning=ClientBatchPartitioning.WHOLE_CLIENT,
            optimizer_step_semantics=OptimizerStepSemantics.AFTER_GRADIENT_ACCUMULATION,
        ),
        scoring=ScoringBatchSpec(
            calibration_batch_size=batch_size,
            test_batch_size=batch_size,
            temporal_batch_size=batch_size,
        ),
        preprocessing=PreprocessingChunkSpec(
            source_scan_batch_rows=ChunkRowCount(value=8),
            preprocessing_chunk_rows=ChunkRowCount(value=8),
            parquet_write_batch_rows=ChunkRowCount(value=8),
        ),
    )


def runtime_resources() -> ResourcePreflightRequirements:
    stages = tuple(PipelineStage)
    return ResourcePreflightRequirements(
        budget=ResourceBudget(
            maximum_ram_bytes=RamBudgetBytes(value=1),
            maximum_vram_bytes=VramBudgetBytes(value=1),
            maximum_worker_count=WorkerCount(value=1),
            maximum_prefetch_capacity=PrefetchCapacity(value=0),
            maximum_disk_bytes=DiskBudgetBytes(value=1),
            storage_safety_reserve=DiskBudgetBytes(value=1),
        ),
        parallelism=ParallelismSpec(
            maximum_cpu_workers=WorkerCount(value=1),
            maximum_gpu_jobs=WorkerCount(value=1),
            per_stage_concurrency=EnumMap(
                entries=tuple(EnumMapEntry(key=stage, value=StageConcurrency.SEQUENTIAL) for stage in stages),
                allowed_keys=stages,
                is_sparse=False,
            ),
            per_stage_start_method=EnumMap(
                entries=tuple(EnumMapEntry(key=stage, value=ProcessStartMethod.SPAWN) for stage in stages),
                allowed_keys=stages,
                is_sparse=False,
            ),
            per_stage_reason=EnumMap(
                entries=tuple(EnumMapEntry(key=stage, value="synthetic") for stage in stages),
                allowed_keys=stages,
                is_sparse=False,
            ),
            thread_limit=WorkerCount(value=1),
        ),
        storage=(
            StoragePreflightEvidence(
                root="synthetic",
                available_bytes=DiskCapacity(value=1),
                projected_bytes=ByteCount(value=0),
                writable=True,
                supports_atomic_replace=True,
            ),
        ),
    )


def runtime_preflight_request() -> PreflightRequest:
    stage = DraftPlannedStage(
        stage=PipelineStage.CALIBRATION_SCORE,
        cell_id=CellId(value="E-C1#0123456789abcdef"),
        stage_fingerprint=runtime_fingerprint(),
        inputs=ArtifactReferenceCollection(references=()),
        dependencies=StageDependencyCollection(dependencies=()),
        scientific_gate_decision=ScientificStageGateDecision(readiness=ScientificReadinessResult(blockers=())),
    )
    return PreflightRequest(
        draft=DraftExecutionPlan(
            stages=(stage,),
            dependencies=StageDependencyCollection(dependencies=()),
            scientific_readiness=ScientificReadinessResult(blockers=()),
        ),
        artifact_catalogue=ArtifactCatalogueSnapshot(entries=()),
        hardware=HardwareInventory(
            cuda_available=True,
            gpu_name="synthetic",
            gpu_count=1,
            vram_bytes=1,
            torch_version=None,
            cuda_runtime=None,
            driver_version=None,
            cpu_count=1,
            ram_bytes=1,
        ),
        device=DeviceSpec(policy=DevicePolicy.CUDA_REQUIRED, gpu_index=GpuIndex(value=0)),
        resolved_batch_profile=runtime_profile(),
        resources=runtime_resources(),
    )

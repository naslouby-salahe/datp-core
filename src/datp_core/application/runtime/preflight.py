from dataclasses import dataclass

from datp_core.application.planning.plan import DraftExecutionPlan, DraftPlannedStage
from datp_core.application.planning.reuse import (
    BlockedReuseDecision,
    RecomputeArtifactDecision,
    ReuseArtifactDecision,
    ReuseDecision,
)
from datp_core.domain.artifacts.keys import ByteCount, DiskCapacity
from datp_core.domain.artifacts.lineage import StageDependencyCollection
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.data.preprocessing import PreprocessingChunkSpec
from datp_core.domain.errors import (
    CudaDeviceMismatchError,
    CudaUnavailableError,
    DiskSpaceError,
    DomainValidationError,
    RamPreflightError,
    ResourceBudgetExceededError,
    UnsafeParallelismError,
)
from datp_core.domain.experiments.identities import CellId
from datp_core.domain.learning.scores import (
    CalibrationScoreArtifactSet,
    ScoringBatchSpec,
    TemporalScoreArtifactSet,
    TestScoreArtifactSet,
)
from datp_core.domain.learning.training import TrainingBatchSpec
from datp_core.domain.runtime.policies import (
    MAXIMUM_CONCURRENT_GPU_JOBS,
    DevicePolicy,
    DeviceSpec,
    HardwareInventory,
    ParallelismSpec,
    PipelineStage,
    ResourceBudget,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedBatchExecutionProfile:
    training: TrainingBatchSpec
    scoring: ScoringBatchSpec
    preprocessing: PreprocessingChunkSpec

    def __post_init__(self) -> None:
        if (
            type(self.training) is not TrainingBatchSpec
            or type(self.scoring) is not ScoringBatchSpec
            or type(self.preprocessing) is not PreprocessingChunkSpec
        ):
            raise DomainValidationError(
                detail="resolved batch execution profile must retain its exact typed components",
                value=repr(self),
                constraint="TrainingBatchSpec, ScoringBatchSpec, and PreprocessingChunkSpec",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class StoragePreflightEvidence:
    root: str
    available_bytes: DiskCapacity
    projected_bytes: ByteCount
    writable: bool
    supports_atomic_replace: bool

    def __post_init__(self) -> None:
        if not _has_valid_storage_evidence(self):
            raise DomainValidationError(
                detail="storage preflight evidence must describe one writable atomic storage root",
                value=repr(self),
                constraint="non-empty root and typed storage capacity evidence",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ResourcePreflightRequirements:
    budget: ResourceBudget
    parallelism: ParallelismSpec
    storage: tuple[StoragePreflightEvidence, ...]

    def __post_init__(self) -> None:
        if not _has_valid_resource_requirements(self):
            raise DomainValidationError(
                detail="resource preflight requirements must contain unique typed storage evidence",
                value=repr(self.storage),
                constraint="ResourceBudget, ParallelismSpec, and unique StoragePreflightEvidence",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class StageRuntimeRequirements:
    device: DeviceSpec
    batch_profile: ResolvedBatchExecutionProfile
    resources: ResourcePreflightRequirements


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactCatalogueEntry:
    stage_fingerprint: StageFingerprint
    reuse_decision: ReuseDecision


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactCatalogueSnapshot:
    entries: tuple[ArtifactCatalogueEntry, ...]

    def __post_init__(self) -> None:
        fingerprints = tuple(entry.stage_fingerprint for entry in self.entries)
        if len(set(fingerprints)) != len(fingerprints):
            raise DomainValidationError(
                detail="artifact catalogue snapshot must contain one decision per stage fingerprint",
                value=repr(fingerprints),
                constraint="unique stage fingerprints",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class FinalPlannedStage:
    stage: PipelineStage
    cell_id: CellId
    stage_fingerprint: StageFingerprint
    dependencies: StageDependencyCollection
    reuse_decision: ReuseDecision
    validated_runtime_requirements: StageRuntimeRequirements


@dataclass(frozen=True, slots=True, kw_only=True)
class FinalExecutionPlan:
    stages: tuple[FinalPlannedStage, ...]
    dependencies: StageDependencyCollection
    blocked_stages: tuple[StageFingerprint, ...]
    resolved_batch_profile: ResolvedBatchExecutionProfile


@dataclass(frozen=True, slots=True, kw_only=True)
class PreflightRequest:
    draft: DraftExecutionPlan
    artifact_catalogue: ArtifactCatalogueSnapshot
    hardware: HardwareInventory
    device: DeviceSpec
    resolved_batch_profile: ResolvedBatchExecutionProfile
    resources: ResourcePreflightRequirements


@dataclass(frozen=True, slots=True, kw_only=True)
class PreflightResult:
    final_plan: FinalExecutionPlan
    artifact_catalogue: ArtifactCatalogueSnapshot
    hardware: HardwareInventory


class ExecutionPreflight:
    def validate(self, request: PreflightRequest) -> PreflightResult:
        _validate_readiness(request)
        requirements = StageRuntimeRequirements(
            device=request.device,
            batch_profile=request.resolved_batch_profile,
            resources=request.resources,
        )
        stages = tuple(
            _final_stage(
                draft_stage=stage,
                reuse_decision=_final_reuse_decision(draft_stage=stage, catalogue=request.artifact_catalogue),
                requirements=requirements,
            )
            for stage in request.draft.stages
        )
        blocked_stages = tuple(
            stage.stage_fingerprint for stage in stages if isinstance(stage.reuse_decision, BlockedReuseDecision)
        )
        return PreflightResult(
            final_plan=FinalExecutionPlan(
                stages=stages,
                dependencies=request.draft.dependencies,
                blocked_stages=blocked_stages,
                resolved_batch_profile=request.resolved_batch_profile,
            ),
            artifact_catalogue=request.artifact_catalogue,
            hardware=request.hardware,
        )


def _final_stage(
    *,
    draft_stage: DraftPlannedStage,
    reuse_decision: ReuseDecision,
    requirements: StageRuntimeRequirements,
) -> FinalPlannedStage:
    _validate_reuse_stage_match(stage=draft_stage.stage, decision=reuse_decision)
    return FinalPlannedStage(
        stage=draft_stage.stage,
        cell_id=draft_stage.cell_id,
        stage_fingerprint=draft_stage.stage_fingerprint,
        dependencies=draft_stage.dependencies,
        reuse_decision=reuse_decision,
        validated_runtime_requirements=requirements,
    )


def _validate_readiness(request: PreflightRequest) -> None:
    _validate_device(device=request.device, hardware=request.hardware)
    _validate_ram_and_vram(hardware=request.hardware, resources=request.resources, device=request.device)
    _validate_parallelism(hardware=request.hardware, resources=request.resources, device=request.device)
    _validate_storage(resources=request.resources)


def _validate_device(*, device: DeviceSpec, hardware: HardwareInventory) -> None:
    if device.policy is not DevicePolicy.CUDA_REQUIRED:
        return
    if not hardware.cuda_available:
        raise CudaUnavailableError(
            detail="preflight requires CUDA but the inspected host has none", required_stage="runtime"
        )
    if device.gpu_index is None or device.gpu_index.value >= hardware.gpu_count:
        raise CudaDeviceMismatchError(
            detail="preflight GPU index is not present in the inspected hardware inventory",
            expected_device=repr(device.gpu_index),
            actual_device=f"gpu_count={hardware.gpu_count}",
        )


def _validate_ram_and_vram(
    *,
    hardware: HardwareInventory,
    resources: ResourcePreflightRequirements,
    device: DeviceSpec,
) -> None:
    budget = resources.budget
    if hardware.ram_bytes is None or hardware.ram_bytes < budget.maximum_ram_bytes.value:
        raise RamPreflightError(
            detail="inspected RAM cannot satisfy the frozen execution budget",
            budget=str(budget.maximum_ram_bytes.value),
            need=str(hardware.ram_bytes),
        )
    if device.policy is DevicePolicy.CUDA_REQUIRED and not _has_sufficient_vram(hardware=hardware, budget=budget):
        raise ResourceBudgetExceededError(
            detail="inspected VRAM cannot satisfy the frozen execution budget",
            budget=str(budget.maximum_vram_bytes.value),
            estimate=str(hardware.vram_bytes),
        )


def _validate_parallelism(
    *,
    hardware: HardwareInventory,
    resources: ResourcePreflightRequirements,
    device: DeviceSpec,
) -> None:
    _validate_cpu_parallelism(hardware=hardware, resources=resources)
    _validate_gpu_parallelism(hardware=hardware, resources=resources, device=device)


def _validate_storage(*, resources: ResourcePreflightRequirements) -> None:
    projected_total = sum(evidence.projected_bytes.value for evidence in resources.storage)
    if projected_total > resources.budget.maximum_disk_bytes.value:
        raise ResourceBudgetExceededError(
            detail="projected storage exceeds the frozen disk budget",
            budget=str(resources.budget.maximum_disk_bytes.value),
            estimate=str(projected_total),
        )
    for evidence in resources.storage:
        required_bytes = evidence.projected_bytes.value + resources.budget.storage_safety_reserve.value
        if not _storage_root_is_admissible(evidence=evidence, required_bytes=required_bytes):
            raise DiskSpaceError(
                detail="storage root cannot satisfy the frozen preflight requirements",
                root=evidence.root,
                projected_bytes=evidence.projected_bytes.value,
                reserve_bytes=resources.budget.storage_safety_reserve.value,
                available_bytes=evidence.available_bytes.value,
            )


def _decision_for(*, fingerprint: StageFingerprint, catalogue: ArtifactCatalogueSnapshot) -> ReuseDecision:
    for entry in catalogue.entries:
        if entry.stage_fingerprint == fingerprint:
            return entry.reuse_decision
    return RecomputeArtifactDecision(incompatibility=None)


def _final_reuse_decision(*, draft_stage: DraftPlannedStage, catalogue: ArtifactCatalogueSnapshot) -> ReuseDecision:
    readiness = draft_stage.scientific_gate_decision.readiness
    if not readiness.is_ready:
        return BlockedReuseDecision(reason=readiness.blockers[0])
    return _decision_for(fingerprint=draft_stage.stage_fingerprint, catalogue=catalogue)


def _validate_reuse_stage_match(*, stage: PipelineStage, decision: ReuseDecision) -> None:
    if not isinstance(decision, ReuseArtifactDecision):
        return
    artifact = decision.artifact
    expected_artifact_type = _expected_reused_artifact_type(stage)
    if expected_artifact_type is not None and type(artifact) is expected_artifact_type:
        return
    raise DomainValidationError(
        detail="a reused score artifact must be finalized only for its matching score stage",
        value=f"{stage.value}/{type(artifact).__name__}",
        constraint="calibration, test, or temporal score stage and artifact role must match",
    )


def _has_valid_storage_evidence(evidence: StoragePreflightEvidence) -> bool:
    return all(
        (
            bool(evidence.root),
            type(evidence.available_bytes) is DiskCapacity,
            type(evidence.projected_bytes) is ByteCount,
            type(evidence.writable) is bool,
            type(evidence.supports_atomic_replace) is bool,
        )
    )


def _has_valid_resource_requirements(requirements: ResourcePreflightRequirements) -> bool:
    root_names = tuple(evidence.root for evidence in requirements.storage)
    return all(
        (
            type(requirements.budget) is ResourceBudget,
            type(requirements.parallelism) is ParallelismSpec,
            bool(requirements.storage),
            all(type(evidence) is StoragePreflightEvidence for evidence in requirements.storage),
            len(set(root_names)) == len(root_names),
        )
    )


def _has_sufficient_vram(*, hardware: HardwareInventory, budget: ResourceBudget) -> bool:
    return hardware.vram_bytes is not None and hardware.vram_bytes >= budget.maximum_vram_bytes.value


def _validate_cpu_parallelism(*, hardware: HardwareInventory, resources: ResourcePreflightRequirements) -> None:
    requested_workers = resources.parallelism.maximum_cpu_workers.value
    maximum_workers = min(hardware.cpu_count, resources.budget.maximum_worker_count.value)
    if requested_workers > maximum_workers:
        raise UnsafeParallelismError(
            detail="preflight parallelism exceeds the inspected host or frozen resource budget",
            requested_concurrency=requested_workers,
        )


def _validate_gpu_parallelism(
    *, hardware: HardwareInventory, resources: ResourcePreflightRequirements, device: DeviceSpec
) -> None:
    requested_jobs = resources.parallelism.maximum_gpu_jobs.value
    if requested_jobs > min(MAXIMUM_CONCURRENT_GPU_JOBS, hardware.gpu_count):
        raise UnsafeParallelismError(
            detail="preflight permits at most one GPU job on an available selected GPU",
            requested_concurrency=requested_jobs,
        )
    if device.policy is DevicePolicy.CUDA_REQUIRED and requested_jobs != MAXIMUM_CONCURRENT_GPU_JOBS:
        raise UnsafeParallelismError(
            detail="CUDA-required execution must reserve exactly one GPU job",
            requested_concurrency=requested_jobs,
        )


def _storage_root_is_admissible(*, evidence: StoragePreflightEvidence, required_bytes: int) -> bool:
    return all((evidence.writable, evidence.supports_atomic_replace, required_bytes <= evidence.available_bytes.value))


def _expected_reused_artifact_type(
    stage: PipelineStage,
) -> type[CalibrationScoreArtifactSet] | type[TestScoreArtifactSet] | type[TemporalScoreArtifactSet] | None:
    return {
        PipelineStage.CALIBRATION_SCORE: CalibrationScoreArtifactSet,
        PipelineStage.TEST_SCORE: TestScoreArtifactSet,
        PipelineStage.TEMPORAL_SCORE: TemporalScoreArtifactSet,
    }.get(stage)

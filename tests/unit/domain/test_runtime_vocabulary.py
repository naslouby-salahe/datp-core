from datp_core.domain.artifacts.lineage import ReuseDecisionKind, ReuseImpact
from datp_core.domain.runtime.failure_dispositions import FailureDisposition
from datp_core.domain.runtime.policies import (
    DevicePolicy,
    ExecutionMode,
    PauseDecision,
    PipelineStage,
    ProcessStartMethod,
    ResourcePressureLevel,
    RoundDisposition,
    RunStatus,
    StageConcurrency,
    WorkerRole,
)
from datp_core.domain.runtime.seeds import SeedRole


def test_pipeline_stage_order_matches_the_architecture_exactly() -> None:
    assert tuple(PipelineStage) == (
        PipelineStage.SOURCE_INSPECTION,
        PipelineStage.FEASIBILITY_AUDIT,
        PipelineStage.PARTITION,
        PipelineStage.SPLIT_BUILD,
        PipelineStage.PREPROCESSOR_FIT,
        PipelineStage.SPLIT_MATERIALIZE,
        PipelineStage.TRAIN,
        PipelineStage.CHECKPOINT_SELECT,
        PipelineStage.CALIBRATION_SCORE,
        PipelineStage.TEST_SCORE,
        PipelineStage.TEMPORAL_SCORE,
        PipelineStage.THRESHOLD,
        PipelineStage.EVALUATE,
        PipelineStage.ANALYZE,
        PipelineStage.RESOURCE_COST,
        PipelineStage.RESULT_FREEZE,
        PipelineStage.REPORT,
    )


def test_seed_roles_cover_every_declared_random_state_owner() -> None:
    assert tuple(SeedRole) == (
        SeedRole.TRAINING_INIT,
        SeedRole.DATA_PARTITION,
        SeedRole.DATALOADER_SHUFFLE,
        SeedRole.DATALOADER_WORKER,
        SeedRole.SAMPLER,
        SeedRole.CLIENT_ORDERING,
        SeedRole.CLUSTERING,
        SeedRole.BOOTSTRAP,
        SeedRole.PERSONALIZATION,
        SeedRole.COMPARATOR,
    )


def test_runtime_vocabulary_excludes_multi_gpu_and_multi_node_execution() -> None:
    enum_types = (
        ExecutionMode,
        DevicePolicy,
        RunStatus,
        StageConcurrency,
        ProcessStartMethod,
        WorkerRole,
        FailureDisposition,
        RoundDisposition,
        ResourcePressureLevel,
        PauseDecision,
    )
    values = {member.value for enum_type in enum_types for member in enum_type}
    assert not {"multi_gpu", "multi_node"} & values


def test_reuse_vocabularies_are_closed_and_precise() -> None:
    assert tuple(ReuseDecisionKind) == (
        ReuseDecisionKind.REUSE,
        ReuseDecisionKind.RECOMPUTE,
        ReuseDecisionKind.BLOCKED,
    )
    assert tuple(ReuseImpact) == (
        ReuseImpact.TRAINING_INVALIDATED,
        ReuseImpact.SCORING_INVALIDATED,
        ReuseImpact.THRESHOLD_INVALIDATED,
        ReuseImpact.EVALUATION_STATISTICS_INVALIDATED,
        ReuseImpact.NO_OUTPUT_IMPACT,
    )

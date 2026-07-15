from dataclasses import dataclass

from datp_core.domain.artifacts.lineage import StageDependencyCollection
from datp_core.domain.artifacts.references import ArtifactReferenceCollection, StageFingerprint
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.feasibility import ScientificReadinessResult
from datp_core.domain.experiments.identities import CellId
from datp_core.domain.runtime.policies import PipelineStage


@dataclass(frozen=True, slots=True, kw_only=True)
class ScientificStageGateDecision:
    readiness: ScientificReadinessResult


@dataclass(frozen=True, slots=True, kw_only=True)
class DraftPlannedStage:
    stage: PipelineStage
    cell_id: CellId
    stage_fingerprint: StageFingerprint
    inputs: ArtifactReferenceCollection
    dependencies: StageDependencyCollection
    scientific_gate_decision: ScientificStageGateDecision


@dataclass(frozen=True, slots=True, kw_only=True)
class DraftExecutionPlan:
    stages: tuple[DraftPlannedStage, ...]
    dependencies: StageDependencyCollection
    scientific_readiness: ScientificReadinessResult

    def __post_init__(self) -> None:
        stage_keys = tuple((stage.stage, stage.stage_fingerprint) for stage in self.stages)
        if len(set(stage_keys)) != len(stage_keys):
            raise DomainValidationError(
                detail="a draft execution plan cannot contain duplicate stage and fingerprint pairs",
                value=repr(stage_keys),
                constraint="unique ordered stage/fingerprint pairs",
            )

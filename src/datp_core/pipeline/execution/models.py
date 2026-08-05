"""Execution enums, recipes, provenance, and campaign contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from datp_core.domain.values import Checksum, checksum_text
from datp_core.pipeline.planning import ExperimentCoordinate


class PipelineStage(StrEnum):
    PREFLIGHT = "preflight"
    MATERIALIZE_DATASET = "materialize_dataset"
    CONSTRUCT_POPULATION = "construct_population"
    FIT_PREPROCESSING = "fit_preprocessing"
    TRAIN_DETECTOR = "train_detector"
    SELECT_CHECKPOINT = "select_checkpoint"
    GENERATE_SCORES = "generate_scores"
    BUILD_CALIBRATION = "build_calibration"
    CONSTRUCT_THRESHOLDS = "construct_thresholds"
    EVALUATE_DETECTOR = "evaluate_detector"
    ANALYZE_EVIDENCE = "analyze_evidence"
    VERIFY_ANCHOR = "verify_anchor"
    PUBLISH_REPORT = "publish_report"
    FINALIZE_PUBLICATION = "finalize_publication"


class ExecutionRecipeId(StrEnum):
    """Typed stage sequence selected for one single-coordinate experiment."""

    STANDARD_FEDERATED = "standard_federated"
    ANCHOR_REPRODUCTION = "anchor_reproduction"


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionRecipe:
    recipe_id: ExecutionRecipeId
    stages: tuple[PipelineStage, ...]

    def __post_init__(self) -> None:
        if not self.stages:
            raise ValueError("an execution recipe requires at least one stage")
        if len(self.stages) != len(frozenset(self.stages)):
            raise ValueError("an execution recipe cannot repeat a stage")


_POPULATION_FRAGMENT: tuple[PipelineStage, ...] = (
    PipelineStage.PREFLIGHT,
    PipelineStage.MATERIALIZE_DATASET,
    PipelineStage.CONSTRUCT_POPULATION,
    PipelineStage.FIT_PREPROCESSING,
)
_TRAINING_FRAGMENT: tuple[PipelineStage, ...] = (
    PipelineStage.TRAIN_DETECTOR,
    PipelineStage.SELECT_CHECKPOINT,
    PipelineStage.GENERATE_SCORES,
)
_THRESHOLD_EVALUATION_FRAGMENT: tuple[PipelineStage, ...] = (
    PipelineStage.BUILD_CALIBRATION,
    PipelineStage.CONSTRUCT_THRESHOLDS,
    PipelineStage.EVALUATE_DETECTOR,
    PipelineStage.ANALYZE_EVIDENCE,
)

STANDARD_FEDERATED_RECIPE = ExecutionRecipe(
    recipe_id=ExecutionRecipeId.STANDARD_FEDERATED,
    stages=_POPULATION_FRAGMENT
    + _TRAINING_FRAGMENT
    + _THRESHOLD_EVALUATION_FRAGMENT
    + (PipelineStage.FINALIZE_PUBLICATION,),
)
ANCHOR_REPRODUCTION_RECIPE = ExecutionRecipe(
    recipe_id=ExecutionRecipeId.ANCHOR_REPRODUCTION,
    stages=_POPULATION_FRAGMENT
    + _TRAINING_FRAGMENT
    + _THRESHOLD_EVALUATION_FRAGMENT
    + (PipelineStage.VERIFY_ANCHOR, PipelineStage.FINALIZE_PUBLICATION),
)


class StageOutcome(StrEnum):
    COMPLETED = "completed"
    REUSED = "reused"
    BLOCKED = "blocked"
    FAILED = "failed"


class ExistingExperimentState(StrEnum):
    ABSENT = "absent"
    COMPLETE_VALID = "complete_valid"
    COMPLETE_INVALID = "complete_invalid"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionProvenance:
    plan_digest: Checksum
    campaign_digest: Checksum
    protocol_digest: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class StageExecution:
    stage: PipelineStage
    outcome: StageOutcome
    evidence: str

    def __post_init__(self) -> None:
        if not self.evidence.strip():
            raise ValueError("stage execution requires evidence")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentExecution:
    coordinate: ExperimentCoordinate
    recipe: ExecutionRecipe
    stages: tuple[StageExecution, ...]
    reused_complete_experiment: bool = False

    def __post_init__(self) -> None:
        completed_stage_ids = tuple(item.stage for item in self.stages)
        expected_prefix = self.recipe.stages[: len(completed_stage_ids)]
        if completed_stage_ids != expected_prefix:
            raise ValueError("pipeline stages must execute in the selected recipe's order")
        if self.reused_complete_experiment and self.stages:
            raise ValueError("a reused complete experiment must not execute stages")

    @property
    def successful(self) -> bool:
        if self.reused_complete_experiment:
            return True
        return (
            bool(self.stages)
            and len(self.stages) == len(self.recipe.stages)
            and all(item.outcome in {StageOutcome.COMPLETED, StageOutcome.REUSED} for item in self.stages)
        )


class StageRunner(Protocol):
    def run(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        provenance: ExecutionProvenance,
        output_root: Path,
    ) -> StageExecution: ...


class ExperimentOutputStore(Protocol):
    def state(self, coordinate: ExperimentCoordinate, output_root: Path) -> ExistingExperimentState: ...

    def delete(self, coordinate: ExperimentCoordinate, output_root: Path) -> None: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class CampaignEntry:
    ordinal: int
    coordinate: ExperimentCoordinate

    def __post_init__(self) -> None:
        if self.ordinal < 0:
            raise ValueError("campaign ordinals must be non-negative")


def campaign_digest(entries: tuple[CampaignEntry, ...]) -> Checksum:
    payload = "\n".join(f"{entry.ordinal}|{entry.coordinate.stable_key}" for entry in entries)
    return checksum_text(payload)


@dataclass(frozen=True, slots=True, kw_only=True)
class CampaignPlan:
    entries: tuple[CampaignEntry, ...]
    digest: Checksum
    plan_digest: Checksum

    def __post_init__(self) -> None:
        if tuple(item.ordinal for item in self.entries) != tuple(range(len(self.entries))):
            raise ValueError("campaign entries must use contiguous deterministic ordinals")
        if self.digest != campaign_digest(self.entries):
            raise ValueError("campaign digest does not match campaign entries")


@dataclass(frozen=True, slots=True, kw_only=True)
class CampaignExecution:
    campaign_digest: Checksum
    experiments: tuple[ExperimentExecution, ...]

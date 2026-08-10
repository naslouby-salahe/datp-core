from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from datp_core.core.identifiers import StageExecutionEvidence
from datp_core.core.numeric import CampaignCoordinateCount, CampaignOrdinal, ElapsedSeconds, RoundNumber
from datp_core.experiments.common.coordinates import ExperimentCoordinate


class PipelineStage(StrEnum):
    PREFLIGHT = "preflight"
    MATERIALIZE_DATASET = "materialize_dataset"
    CONSTRUCT_POPULATION = "construct_population"
    FIT_PREPROCESSING = "fit_preprocessing"
    TRAIN_DETECTOR = "train_detector"
    GENERATE_SCORES = "generate_scores"
    BUILD_CALIBRATION = "build_calibration"
    CONSTRUCT_THRESHOLDS = "construct_thresholds"
    EVALUATE_DETECTOR = "evaluate_detector"
    ANALYZE_EVIDENCE = "analyze_evidence"
    FINALIZE_PUBLICATION = "finalize_publication"


class ExecutionRecipeId(StrEnum):
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
    PipelineStage.GENERATE_SCORES,
)
_THRESHOLD_EVALUATION_FRAGMENT: tuple[PipelineStage, ...] = (
    PipelineStage.BUILD_CALIBRATION,
    PipelineStage.CONSTRUCT_THRESHOLDS,
    PipelineStage.EVALUATE_DETECTOR,
    PipelineStage.ANALYZE_EVIDENCE,
)
_STANDARD_STAGE_SEQUENCE = (
    _POPULATION_FRAGMENT + _TRAINING_FRAGMENT + _THRESHOLD_EVALUATION_FRAGMENT + (PipelineStage.FINALIZE_PUBLICATION,)
)

STANDARD_FEDERATED_RECIPE = ExecutionRecipe(
    recipe_id=ExecutionRecipeId.STANDARD_FEDERATED,
    stages=_STANDARD_STAGE_SEQUENCE,
)
ANCHOR_REPRODUCTION_RECIPE = ExecutionRecipe(
    recipe_id=ExecutionRecipeId.ANCHOR_REPRODUCTION,
    stages=_STANDARD_STAGE_SEQUENCE,
)


class StageOutcome(StrEnum):
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class ProgressEventKind(StrEnum):
    CAMPAIGN_BEGIN = "campaign_begin"
    CAMPAIGN_END = "campaign_end"
    COORDINATE_BEGIN = "coordinate_begin"
    COORDINATE_END = "coordinate_end"
    STAGE_BEGIN = "stage_begin"
    STAGE_END = "stage_end"
    TRAINING_ROUND = "training_round"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProgressEvent:
    kind: ProgressEventKind
    coordinate: ExperimentCoordinate | None = None
    stage: PipelineStage | None = None
    ordinal: CampaignOrdinal | None = None
    total: CampaignCoordinateCount | None = None
    round_number: RoundNumber | None = None
    maximum_round: RoundNumber | None = None
    outcome: StageOutcome | None = None
    detail: StageExecutionEvidence | None = None
    elapsed_seconds: ElapsedSeconds | None = None

    def __post_init__(self) -> None:
        if self.kind is ProgressEventKind.TRAINING_ROUND and (self.round_number is None or self.maximum_round is None):
            raise ValueError("training round progress requires round_number and maximum_round")
        campaign_events = {ProgressEventKind.CAMPAIGN_BEGIN, ProgressEventKind.CAMPAIGN_END}
        if self.coordinate is None and self.kind not in campaign_events:
            raise ValueError("coordinate progress events require a coordinate")


class ProgressHook(Protocol):
    def emit(self, event: ProgressEvent) -> None: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class StageExecution:
    stage: PipelineStage
    outcome: StageOutcome
    evidence: StageExecutionEvidence


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentExecution:
    coordinate: ExperimentCoordinate
    recipe: ExecutionRecipe
    stages: tuple[StageExecution, ...]

    def __post_init__(self) -> None:
        completed_stage_ids = tuple(item.stage for item in self.stages)
        expected_prefix = self.recipe.stages[: len(completed_stage_ids)]
        if completed_stage_ids != expected_prefix:
            raise ValueError("pipeline stages must execute in the selected recipe's order")

    @property
    def successful(self) -> bool:
        return (
            bool(self.stages)
            and len(self.stages) == len(self.recipe.stages)
            and all(item.outcome is StageOutcome.COMPLETED for item in self.stages)
        )


class StageRunner(Protocol):
    def run(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        output_root: Path,
    ) -> StageExecution: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class CampaignEntry:
    ordinal: CampaignOrdinal
    coordinate: ExperimentCoordinate


@dataclass(frozen=True, slots=True, kw_only=True)
class CampaignPlan:
    entries: tuple[CampaignEntry, ...]

    def __post_init__(self) -> None:
        if tuple(item.ordinal.value for item in self.entries) != tuple(range(len(self.entries))):
            raise ValueError("campaign entries must use contiguous deterministic ordinals")


@dataclass(frozen=True, slots=True, kw_only=True)
class CampaignExecution:
    experiments: tuple[ExperimentExecution, ...]

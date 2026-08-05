"""Canonical experiment execution order and reusable execution contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from datp_core.domain.enums import ExperimentId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum
from datp_core.pipeline.planning import ExecutionRoute, ExperimentCoordinate, execution_route_for


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
    """Which typed stage sequence a single-coordinate experiment executes.

    Every declared experiment resolves to exactly one of these. Both recipes
    share the same population/training/threshold-evaluation fragments (rule:
    reuse a fragment only when stage order and invariants are identical);
    ANCHOR_REPRODUCTION differs solely by inserting the real anchor gate
    before finalization.
    """

    STANDARD_FEDERATED = "standard_federated"
    ANCHOR_REPRODUCTION = "anchor_reproduction"


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


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionRecipe:
    recipe_id: ExecutionRecipeId
    stages: tuple[PipelineStage, ...]

    def __post_init__(self) -> None:
        if not self.stages:
            raise ValueError("an execution recipe requires at least one stage")
        if len(self.stages) != len(frozenset(self.stages)):
            raise ValueError("an execution recipe cannot repeat a stage")


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


def resolve_execution_recipe(coordinate: ExperimentCoordinate) -> ExecutionRecipe:
    route = execution_route_for(coordinate)
    if route is not ExecutionRoute.SINGLE_COORDINATE:
        raise ScientificContractError(
            f"{route.value} coordinates execute through their dedicated joint workflow, not a single-coordinate recipe",
            subject=coordinate.experiment,
        )
    if coordinate.experiment is ExperimentId.HISTORICAL_DATP_REPRODUCTION:
        return ANCHOR_REPRODUCTION_RECIPE
    return STANDARD_FEDERATED_RECIPE


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
    """The deterministic plan/campaign/protocol identity a coordinate was executed under.

    Carried explicitly alongside the coordinate (never inferred or defaulted) so
    FINALIZE_PUBLICATION can bind each experiment's completion record to the exact
    declared plan and protocol graph that produced it, with no hidden run/job token."""

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
    ) -> StageExecution: ...


class ExperimentOutputStore(Protocol):
    def state(self, coordinate: ExperimentCoordinate, output_root: Path) -> ExistingExperimentState: ...

    def delete(self, coordinate: ExperimentCoordinate, output_root: Path) -> None: ...


def execute_experiment(
    *,
    coordinate: ExperimentCoordinate,
    provenance: ExecutionProvenance,
    stage_runner: StageRunner,
    output_store: ExperimentOutputStore,
    output_root: Path,
    overwrite: bool = False,
) -> ExperimentExecution:
    recipe = resolve_execution_recipe(coordinate)
    existing_state = output_store.state(coordinate, output_root)
    if overwrite:
        if existing_state is not ExistingExperimentState.ABSENT:
            output_store.delete(coordinate, output_root)
    elif existing_state is ExistingExperimentState.COMPLETE_VALID:
        return ExperimentExecution(
            coordinate=coordinate,
            recipe=recipe,
            stages=(),
            reused_complete_experiment=True,
        )
    elif existing_state is ExistingExperimentState.COMPLETE_INVALID:
        raise ValueError("completed experiment failed publication validation")
    elif existing_state is ExistingExperimentState.INCOMPLETE:
        output_store.delete(coordinate, output_root)

    executions: list[StageExecution] = []
    for stage in recipe.stages:
        result = stage_runner.run(stage, coordinate, provenance)
        if result.stage is not stage:
            raise ValueError("stage runner returned a result for the wrong stage")
        executions.append(result)
        if result.outcome in {StageOutcome.BLOCKED, StageOutcome.FAILED}:
            break
    return ExperimentExecution(coordinate=coordinate, recipe=recipe, stages=tuple(executions))

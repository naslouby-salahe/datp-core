from pathlib import Path

import pytest

from datp_core.domain.enums import (
    DatasetId,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.values import Seed
from datp_core.pipeline.execution import (
    PIPELINE_SEQUENCE,
    ExistingExperimentState,
    PipelineStage,
    StageExecution,
    StageOutcome,
    execute_experiment,
)
from datp_core.pipeline.planning import ExperimentCoordinate


class Runner:
    def __init__(self) -> None:
        self.stages: list[PipelineStage] = []

    def run(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        self.stages.append(stage)
        return StageExecution(stage=stage, outcome=StageOutcome.COMPLETED, evidence=coordinate.stable_key)


class OutputStore:
    def __init__(self, state: ExistingExperimentState) -> None:
        self.existing_state = state
        self.deleted = False

    def state(self, coordinate: ExperimentCoordinate, output_root: Path) -> ExistingExperimentState:
        assert coordinate.stable_key
        assert output_root.parts
        return self.existing_state

    def delete(self, coordinate: ExperimentCoordinate, output_root: Path) -> None:
        assert coordinate.stable_key
        assert output_root.parts
        self.deleted = True


def coordinate() -> ExperimentCoordinate:
    return ExperimentCoordinate(
        experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        evidence_role=EvidenceRole.CONFIRMATORY,
        dataset=DatasetId.NBAIOT,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        training_seed=Seed(0),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        model_coefficient=None,
        threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        temporal_state=None,
    )


def test_absent_experiment_runs_every_stage_without_deletion() -> None:
    runner = Runner()
    output_store = OutputStore(ExistingExperimentState.ABSENT)
    result = execute_experiment(
        coordinate=coordinate(),
        stage_runner=runner,
        output_store=output_store,
        output_root=Path("outputs"),
    )
    assert not output_store.deleted
    assert tuple(runner.stages) == PIPELINE_SEQUENCE
    assert result.successful


def test_complete_valid_experiment_is_reused_without_execution() -> None:
    runner = Runner()
    output_store = OutputStore(ExistingExperimentState.COMPLETE_VALID)
    result = execute_experiment(
        coordinate=coordinate(),
        stage_runner=runner,
        output_store=output_store,
        output_root=Path("outputs"),
    )
    assert result.reused_complete_experiment
    assert result.successful
    assert not runner.stages
    assert not output_store.deleted


def test_incomplete_experiment_is_deleted_and_restarted() -> None:
    runner = Runner()
    output_store = OutputStore(ExistingExperimentState.INCOMPLETE)
    result = execute_experiment(
        coordinate=coordinate(),
        stage_runner=runner,
        output_store=output_store,
        output_root=Path("outputs"),
    )
    assert output_store.deleted
    assert tuple(runner.stages) == PIPELINE_SEQUENCE
    assert result.successful


def test_overwrite_deletes_complete_coordinate_before_execution() -> None:
    runner = Runner()
    output_store = OutputStore(ExistingExperimentState.COMPLETE_VALID)
    result = execute_experiment(
        coordinate=coordinate(),
        stage_runner=runner,
        output_store=output_store,
        output_root=Path("outputs"),
        overwrite=True,
    )
    assert output_store.deleted
    assert tuple(runner.stages) == PIPELINE_SEQUENCE
    assert result.successful


def test_invalid_completed_experiment_is_not_reused_or_deleted_silently() -> None:
    runner = Runner()
    output_store = OutputStore(ExistingExperimentState.COMPLETE_INVALID)
    with pytest.raises(ValueError, match="failed publication validation"):
        execute_experiment(
            coordinate=coordinate(),
            stage_runner=runner,
            output_store=output_store,
            output_root=Path("outputs"),
        )
    assert not output_store.deleted
    assert not runner.stages

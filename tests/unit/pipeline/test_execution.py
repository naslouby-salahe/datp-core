from pathlib import Path

from datp_core.domain.enums import (
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    TrainingModelId,
)
from datp_core.domain.values import Seed
from datp_core.pipeline.execution import (
    PIPELINE_SEQUENCE,
    PipelineStage,
    StageExecution,
    StageOutcome,
    execute_experiment,
)
from datp_core.pipeline.planning import ExperimentCoordinate


class Runner:
    def run(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        return StageExecution(stage=stage, outcome=StageOutcome.COMPLETED, evidence=coordinate.stable_key)


class Cleaner:
    def __init__(self) -> None:
        self.called = False

    def remove(self, coordinate: ExperimentCoordinate, output_root: Path) -> None:
        self.called = bool(coordinate.stable_key and output_root.parts)


def test_single_execution_spine_runs_every_stage_in_order() -> None:
    coordinate = ExperimentCoordinate(
        experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        training_seed=Seed(0),
        threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        temporal_state=None,
    )
    cleaner = Cleaner()
    result = execute_experiment(
        coordinate=coordinate,
        stage_runner=Runner(),
        cleaner=cleaner,
        output_root=Path("outputs"),
    )
    assert cleaner.called
    assert tuple(item.stage for item in result.stages) == PIPELINE_SEQUENCE
    assert result.successful

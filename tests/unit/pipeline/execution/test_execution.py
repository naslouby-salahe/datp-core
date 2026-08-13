from dataclasses import replace
from pathlib import Path

import pytest

from datp_core.artifacts.layout import experiment_output_directory
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import (
    DatasetId,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    StageExecutionEvidence,
    TemporalState,
    TrainingModelId,
)
from datp_core.core.numeric import ModelCoefficientValue, Seed
from datp_core.detector.training.protocols import DITTO_TRAINING_PROTOCOLS
from datp_core.experiments.common.coordinates import ExperimentCoordinate
from datp_core.experiments.execution.engine import execute_experiment, resolve_execution_recipe
from datp_core.experiments.execution.models import (
    ANCHOR_REPRODUCTION_RECIPE,
    STANDARD_FEDERATED_RECIPE,
    PipelineStage,
    StageExecution,
    StageOutcome,
)
from datp_core.thresholds.protocols import ClusterFingerprintFeature


class Runner:
    def __init__(self) -> None:
        self.stages: list[PipelineStage] = []

    def run(self, stage: PipelineStage, coordinate: ExperimentCoordinate, output_root: Path) -> StageExecution:
        assert coordinate.stable_key
        assert output_root.parts
        self.stages.append(stage)
        return StageExecution(stage=stage, outcome=StageOutcome.COMPLETED, evidence=StageExecutionEvidence("fixture"))


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


def test_cluster_fingerprint_omission_is_part_of_the_execution_identity() -> None:
    canonical = coordinate()
    ablation = replace(
        canonical,
        threshold_method=FederatedThresholdMethod.CLUSTER_THRESHOLD,
        cluster_fingerprint_omission=ClusterFingerprintFeature.BENIGN_ERROR_P95,
    )

    assert canonical.execution_key != ablation.execution_key


def test_clean_experiment_runs_every_stage(tmp_path: Path) -> None:
    runner = Runner()
    result = execute_experiment(
        coordinate=coordinate(),
        stage_runner=runner,
        output_root=tmp_path,
        overwrite=False,
    )
    assert tuple(runner.stages) == resolve_execution_recipe(coordinate()).stages
    assert result.successful


def test_existing_experiment_requires_explicit_overwrite(tmp_path: Path) -> None:
    runner = Runner()
    directory = experiment_output_directory(tmp_path, coordinate())
    directory.mkdir(parents=True)
    with pytest.raises(FileExistsError, match="already exists"):
        execute_experiment(coordinate=coordinate(), stage_runner=runner, output_root=tmp_path, overwrite=False)
    assert not runner.stages


def test_overwrite_replaces_existing_experiment(tmp_path: Path) -> None:
    runner = Runner()
    output = experiment_output_directory(tmp_path, coordinate())
    output.mkdir(parents=True)
    output.joinpath("old").write_text("old", encoding="utf-8")
    result = execute_experiment(coordinate=coordinate(), stage_runner=runner, output_root=tmp_path, overwrite=True)
    assert result.successful
    assert not output.joinpath("old").exists()


def test_standard_recipe_has_terminal_training_and_scoring_stages() -> None:
    assert resolve_execution_recipe(coordinate()) == STANDARD_FEDERATED_RECIPE


def test_anchor_reproduction_uses_the_standard_sequence() -> None:
    anchor_coordinate = replace(coordinate(), experiment=ExperimentId.HISTORICAL_DATP_REPRODUCTION)
    assert resolve_execution_recipe(anchor_coordinate) == ANCHOR_REPRODUCTION_RECIPE


def test_ditto_coordinate_requires_its_joint_route() -> None:
    ditto_coordinate = replace(
        coordinate(),
        experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        training_model=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
        model_coefficient=ModelCoefficientValue(DITTO_TRAINING_PROTOCOLS[0].regularization.value),
    )
    with pytest.raises(ScientificContractError, match="ditto_joint_publication"):
        resolve_execution_recipe(ditto_coordinate)


def test_temporal_coordinate_requires_its_paired_route() -> None:
    with pytest.raises(ScientificContractError, match="temporal_paired_execution"):
        resolve_execution_recipe(replace(coordinate(), temporal_state=TemporalState.FROZEN_FUTURE))

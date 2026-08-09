from dataclasses import replace
from pathlib import Path

import pytest

from datp_core.artifacts.provenance import Checksum
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
    ExecutionProvenance,
    ExistingExperimentState,
    PipelineStage,
    StageExecution,
    StageOutcome,
)

OUTPUT_ROOT = Path("outputs")


class Runner:
    def __init__(self) -> None:
        self.stages: list[PipelineStage] = []
        self.output_roots: list[Path] = []

    def run(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        provenance: ExecutionProvenance,
        output_root: Path,
    ) -> StageExecution:
        assert provenance.plan_digest.value
        self.stages.append(stage)
        self.output_roots.append(output_root)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=StageExecutionEvidence(coordinate.stable_key),
        )


class OutputStore:
    def __init__(self, state: ExistingExperimentState) -> None:
        self.existing_state = state
        self.deleted = False

    def state(
        self,
        coordinate: ExperimentCoordinate,
        output_root: Path,
        provenance=None,
    ) -> ExistingExperimentState:
        assert coordinate.stable_key
        assert output_root.parts
        del provenance
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


def provenance() -> ExecutionProvenance:
    return ExecutionProvenance(
        plan_digest=Checksum("plan"),
        campaign_digest=Checksum("campaign"),
        protocol_digest=Checksum("protocol"),
    )


def test_absent_experiment_runs_every_stage_without_deletion() -> None:
    runner = Runner()
    output_store = OutputStore(ExistingExperimentState.ABSENT)
    result = execute_experiment(
        coordinate=coordinate(),
        provenance=provenance(),
        stage_runner=runner,
        output_store=output_store,
        output_root=OUTPUT_ROOT,
        overwrite=False,
    )
    assert not output_store.deleted
    assert tuple(runner.stages) == resolve_execution_recipe(coordinate()).stages
    assert set(runner.output_roots) == {OUTPUT_ROOT}
    assert result.successful


def test_complete_valid_experiment_is_reused_without_execution() -> None:
    runner = Runner()
    output_store = OutputStore(ExistingExperimentState.COMPLETE_VALID)
    result = execute_experiment(
        coordinate=coordinate(),
        provenance=provenance(),
        stage_runner=runner,
        output_store=output_store,
        output_root=OUTPUT_ROOT,
        overwrite=False,
    )
    assert result.reused_complete_experiment
    assert result.successful
    assert not runner.stages
    assert not runner.output_roots
    assert not output_store.deleted


def test_incomplete_experiment_is_deleted_and_restarted() -> None:
    runner = Runner()
    output_store = OutputStore(ExistingExperimentState.INCOMPLETE)
    result = execute_experiment(
        coordinate=coordinate(),
        provenance=provenance(),
        stage_runner=runner,
        output_store=output_store,
        output_root=OUTPUT_ROOT,
        overwrite=False,
    )
    assert output_store.deleted
    assert tuple(runner.stages) == resolve_execution_recipe(coordinate()).stages
    assert set(runner.output_roots) == {OUTPUT_ROOT}
    assert result.successful


def test_overwrite_deletes_complete_coordinate_before_execution() -> None:
    runner = Runner()
    output_store = OutputStore(ExistingExperimentState.COMPLETE_VALID)
    result = execute_experiment(
        coordinate=coordinate(),
        provenance=provenance(),
        stage_runner=runner,
        output_store=output_store,
        output_root=OUTPUT_ROOT,
        overwrite=True,
    )
    assert output_store.deleted
    assert tuple(runner.stages) == resolve_execution_recipe(coordinate()).stages
    assert set(runner.output_roots) == {OUTPUT_ROOT}
    assert result.successful


def test_invalid_completed_experiment_is_not_reused_or_deleted_silently() -> None:
    runner = Runner()
    output_store = OutputStore(ExistingExperimentState.COMPLETE_INVALID)
    experiment_coordinate = coordinate()
    execution_provenance = provenance()
    with pytest.raises(ValueError, match="failed publication validation"):
        execute_experiment(
            coordinate=experiment_coordinate,
            provenance=execution_provenance,
            stage_runner=runner,
            output_store=output_store,
            output_root=OUTPUT_ROOT,
            overwrite=False,
        )
    assert not output_store.deleted
    assert not runner.stages
    assert not runner.output_roots


def test_confirmatory_experiment_resolves_the_standard_federated_recipe() -> None:
    assert resolve_execution_recipe(coordinate()) == STANDARD_FEDERATED_RECIPE
    assert PipelineStage.ANALYZE_EVIDENCE in STANDARD_FEDERATED_RECIPE.stages
    assert PipelineStage.FINALIZE_PUBLICATION in STANDARD_FEDERATED_RECIPE.stages
    assert "publish_report" not in {stage.value for stage in PipelineStage}


def test_anchor_reproduction_experiment_resolves_its_declared_recipe() -> None:
    anchor_coordinate = replace(coordinate(), experiment=ExperimentId.HISTORICAL_DATP_REPRODUCTION)
    recipe = resolve_execution_recipe(anchor_coordinate)
    assert recipe == ANCHOR_REPRODUCTION_RECIPE
    assert recipe.stages == STANDARD_FEDERATED_RECIPE.stages
    assert recipe.stages[-1] is PipelineStage.FINALIZE_PUBLICATION


def test_repeated_recipe_resolution_is_deterministic() -> None:
    assert resolve_execution_recipe(coordinate()) is resolve_execution_recipe(coordinate())


def test_completed_execution_contains_every_stage_in_its_selected_recipe() -> None:
    runner = Runner()
    output_store = OutputStore(ExistingExperimentState.ABSENT)
    result = execute_experiment(
        coordinate=coordinate(),
        provenance=provenance(),
        stage_runner=runner,
        output_store=output_store,
        output_root=OUTPUT_ROOT,
        overwrite=False,
    )
    assert result.recipe == STANDARD_FEDERATED_RECIPE
    assert tuple(item.stage for item in result.stages) == STANDARD_FEDERATED_RECIPE.stages
    assert set(runner.output_roots) == {OUTPUT_ROOT}


def test_partial_execution_is_a_valid_recipe_prefix() -> None:
    class _BlocksAfterTraining:
        def run(
            self,
            stage: PipelineStage,
            coordinate: ExperimentCoordinate,
            provenance: ExecutionProvenance,
            output_root: Path,
        ) -> StageExecution:
            del coordinate, provenance
            assert output_root == OUTPUT_ROOT
            if stage is PipelineStage.SELECT_CHECKPOINT:
                return StageExecution(
                    stage=stage,
                    outcome=StageOutcome.BLOCKED,
                    evidence=StageExecutionEvidence("fixture halts here"),
                )
            return StageExecution(
                stage=stage,
                outcome=StageOutcome.COMPLETED,
                evidence=StageExecutionEvidence("fixture"),
            )

    result = execute_experiment(
        coordinate=coordinate(),
        provenance=provenance(),
        stage_runner=_BlocksAfterTraining(),
        output_store=OutputStore(ExistingExperimentState.ABSENT),
        output_root=OUTPUT_ROOT,
        overwrite=False,
    )
    completed_stage_ids = tuple(item.stage for item in result.stages)
    assert completed_stage_ids == STANDARD_FEDERATED_RECIPE.stages[: len(completed_stage_ids)]
    assert not result.successful


def test_ditto_coordinate_cannot_resolve_a_single_coordinate_recipe() -> None:
    ditto_coordinate = replace(
        coordinate(),
        experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        training_model=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
        model_coefficient=ModelCoefficientValue(DITTO_TRAINING_PROTOCOLS[0].regularization.value),
    )
    with pytest.raises(ScientificContractError, match="ditto_joint_publication"):
        resolve_execution_recipe(ditto_coordinate)


def test_temporal_coordinate_cannot_resolve_a_single_coordinate_recipe() -> None:
    temporal_coordinate = replace(coordinate(), temporal_state=TemporalState.FROZEN_FUTURE)
    with pytest.raises(ScientificContractError, match="temporal_paired_execution"):
        resolve_execution_recipe(temporal_coordinate)


def test_execute_experiment_fails_fast_for_a_ditto_coordinate_instead_of_running_stages() -> None:
    ditto_coordinate = replace(
        coordinate(),
        experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        training_model=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
        model_coefficient=ModelCoefficientValue(DITTO_TRAINING_PROTOCOLS[0].regularization.value),
    )
    runner = Runner()
    output_store = OutputStore(ExistingExperimentState.ABSENT)
    execution_provenance = provenance()
    with pytest.raises(ScientificContractError):
        execute_experiment(
            coordinate=ditto_coordinate,
            provenance=execution_provenance,
            stage_runner=runner,
            output_store=output_store,
            output_root=OUTPUT_ROOT,
            overwrite=False,
        )
    assert not runner.stages
    assert not runner.output_roots

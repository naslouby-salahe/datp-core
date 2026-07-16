from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from datp_core.application.planning import planner
from datp_core.application.planning.planner import CreateExecutionPlanRequest, ExperimentPlanner
from datp_core.application.planning.reuse import (
    RecomputeArtifactDecision,
    ReuseArtifactDecision,
    ScoreReuseGate,
)
from datp_core.config.mapping.scientific import map_experiment_schema
from datp_core.domain.artifacts.lineage import FeatureSchemaIdentity
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.errors import AmbiguousPlanError
from datp_core.domain.experiments.feasibility import ReuseIncompatibilityReason, ScientificReadinessResult
from datp_core.domain.experiments.specifications import ExperimentSpec
from datp_core.domain.runtime.policies import PipelineStage
from datp_core.domain.thresholding.policies import LocalThresholdSpec, ThresholdPercentile, ThresholdSuiteSpec
from tests.support.composed_configuration import composed_profile_catalogue
from tests.support.score_artifacts import calibration_scores_and_eligible_clients
from tests.unit.application.test_stage_services import evaluation_request
from tests.unit.config.test_mapping import experiment_config


def _fingerprint(value: int) -> StageFingerprint:
    return StageFingerprint(value=f"{value:064x}")


def _specifications(*, threshold_percentile: float) -> tuple[ExperimentSpec, ...]:
    specification = map_experiment_schema(experiment_config(), catalogue=composed_profile_catalogue())
    _, local_policy = specification.scientific_protocol.thresholds.constructions
    assert isinstance(local_policy, LocalThresholdSpec)
    threshold_policy = LocalThresholdSpec(
        kind=local_policy.kind,
        percentile=ThresholdPercentile(value=threshold_percentile),
        estimator=local_policy.estimator,
    )
    threshold_protocol = replace(
        specification.scientific_protocol,
        thresholds=ThresholdSuiteSpec(
            constructions=(specification.scientific_protocol.thresholds.constructions[0], threshold_policy)
        ),
    )
    profile = replace(
        specification.profile,
        authorized_protocols=(specification.scientific_protocol, threshold_protocol),
    )
    return (replace(specification, profile=profile),)


def test_planner_is_deterministic_and_deduplicates_shared_expensive_stages() -> None:
    request = CreateExecutionPlanRequest(
        specifications=_specifications(threshold_percentile=0.975),
        scientific_readiness=ScientificReadinessResult(blockers=()),
    )

    first = ExperimentPlanner().create_plan(request)
    second = ExperimentPlanner().create_plan(request)

    assert first == second
    assert first.stages
    assert tuple(stage.stage.value for stage in first.stages[:9]) == (
        "source_inspection",
        "feasibility_audit",
        "partition",
        "split_build",
        "preprocessor_fit",
        "split_materialize",
        "train",
        "checkpoint_select",
        "calibration_score",
    )


def test_planner_refuses_a_cell_id_collision_between_distinct_cells() -> None:
    specifications = _specifications(threshold_percentile=0.975)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(planner, "_cell_id", _collided_cell_id)
        request = CreateExecutionPlanRequest(
            specifications=specifications,
            scientific_readiness=ScientificReadinessResult(blockers=()),
        )
        experiment_planner = ExperimentPlanner()
        with pytest.raises(AmbiguousPlanError, match="share a cell id"):
            experiment_planner.create_plan(request)


def test_planner_never_calls_a_persistence_spy() -> None:
    class PersistenceSpy:
        called = False

        def __getattr__(self, name: str) -> object:
            self.called = True
            raise AssertionError(f"planner attempted persistence access through {name}")

    persistence_spy = PersistenceSpy()
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(planner, "persistence", persistence_spy, raising=False)
        ExperimentPlanner().create_plan(
            CreateExecutionPlanRequest(
                specifications=_specifications(threshold_percentile=0.975),
                scientific_readiness=ScientificReadinessResult(blockers=()),
            )
        )
    assert not persistence_spy.called


def _collided_cell_id(*, specification: ExperimentSpec, seed: object) -> planner.CellId:
    del specification, seed
    return planner.CellId(value="E-C1#0000000000000000")


def test_score_reuse_gate_requires_exact_typed_lineage() -> None:
    calibration_scores, _ = calibration_scores_and_eligible_clients()
    test_request = evaluation_request()
    gate = ScoreReuseGate()

    calibration_reuse = gate.decide_calibration(calibration_scores.lineage, calibration_scores)
    absent_recompute = gate.decide_calibration(calibration_scores.lineage, None)
    schema_mismatch = gate.decide_test(
        replace(
            test_request.score_set.lineage,
            context=replace(
                test_request.score_set.lineage.context,
                feature_schema_identity=FeatureSchemaIdentity(value=_fingerprint(42)),
            ),
        ),
        test_request.score_set,
    )

    assert isinstance(calibration_reuse, ReuseArtifactDecision)
    assert calibration_reuse.artifact is calibration_scores
    assert isinstance(absent_recompute, RecomputeArtifactDecision)
    assert absent_recompute.incompatibility is None
    assert isinstance(schema_mismatch, RecomputeArtifactDecision)
    assert schema_mismatch.incompatibility is ReuseIncompatibilityReason.SCORING_MISMATCH


@given(
    threshold_percentile=st.integers(min_value=900_001, max_value=999_999)
    .filter(lambda value: value != 950_000)
    .map(lambda value: value / 1_000_000)
)
def test_threshold_only_variations_share_the_calibration_and_test_score_stages(threshold_percentile: float) -> None:
    specifications = _specifications(threshold_percentile=threshold_percentile)
    plan = ExperimentPlanner().create_plan(
        CreateExecutionPlanRequest(
            specifications=specifications,
            scientific_readiness=ScientificReadinessResult(blockers=()),
        )
    )

    seed_count = len(specifications[0].profile.authorized_seed_plan.values)
    assert sum(stage.stage is PipelineStage.CALIBRATION_SCORE for stage in plan.stages) == seed_count
    assert sum(stage.stage is PipelineStage.TEST_SCORE for stage in plan.stages) == seed_count

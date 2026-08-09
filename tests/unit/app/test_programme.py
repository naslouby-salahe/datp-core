"""Programme registry, planning, feasibility, and scientific naming invariants."""

from pathlib import Path

import pytest

from datp_core.app.campaign import build_programme_plan, seed_cohort_for
from datp_core.app.contracts import OverwriteMode
from datp_core.app.models import DetailText, ReportResult
from datp_core.app.planning import PlanDisposition
from datp_core.app.recipes import recipe_for
from datp_core.app.research import registered_experiment_ids
from datp_core.app.validation import require_experiment_execution_ready, validate_programme
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import ExperimentId, ExperimentReadiness, FederatedThresholdMethod
from datp_core.experiments.common.seeds import BOUNDED_EVIDENCE_SEED_COHORT, CONFIRMATORY_SEED_COHORT
from datp_core.experiments.registry import EXPERIMENTS
from datp_core.runtime.configuration import OUTPUTS_ROOT


def test_every_non_suppressed_experiment_has_exactly_one_recipe() -> None:
    validation = validate_programme(None)
    expected = tuple(
        declaration.id
        for declaration in EXPERIMENTS
        if declaration.id is not ExperimentId.HISTORICAL_DATP_REPRODUCTION
        and declaration.readiness is not ExperimentReadiness.SUPPRESSED
    )
    assert frozenset(validation.registered_recipes) == frozenset(expected)
    assert len(validation.registered_recipes) == len(frozenset(validation.registered_recipes))


def test_supplementary_experiments_are_wired_and_suppressed_experiments_are_not() -> None:
    registered = frozenset(registered_experiment_ids())
    assert ExperimentId.GROUP_MEDIAN_SUPPLEMENT in registered
    assert ExperimentId.OPTIONAL_EQUITY_INDICES in registered
    assert ExperimentId.ALERT_BURDEN_TRANSLATION not in registered


def test_seed_cohorts_follow_population_contracts() -> None:
    assert seed_cohort_for(ExperimentId.SHARED_VS_LOCAL_CONFIRMATION) == CONFIRMATORY_SEED_COHORT
    assert seed_cohort_for(ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION) == BOUNDED_EVIDENCE_SEED_COHORT
    assert seed_cohort_for(ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY) == BOUNDED_EVIDENCE_SEED_COHORT
    assert seed_cohort_for(ExperimentId.EDGE_ONE_SHOT_RECALIBRATION) == BOUNDED_EVIDENCE_SEED_COHORT


def test_full_plan_preserves_each_experiments_seed_cohort() -> None:
    plan = build_programme_plan(None).plan
    confirmatory = frozenset(
        entry.coordinate.training_seed
        for entry in plan.entries
        if entry.coordinate.experiment is ExperimentId.SHARED_VS_LOCAL_CONFIRMATION
    )
    edge = frozenset(
        entry.coordinate.training_seed
        for entry in plan.entries
        if entry.coordinate.experiment is ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION
    )
    assert confirmatory == frozenset(CONFIRMATORY_SEED_COHORT.values)
    assert edge == frozenset(BOUNDED_EVIDENCE_SEED_COHORT.values)


def test_calibration_size_ablation_is_executable_once_replicate_count_is_declared() -> None:
    presentation = build_programme_plan(ExperimentId.CALIBRATION_SIZE_ABLATION)
    assert presentation.plan.entries
    assert all(entry.disposition is PlanDisposition.EXECUTABLE for entry in presentation.plan.entries)

    require_experiment_execution_ready(ExperimentId.CALIBRATION_SIZE_ABLATION)


def test_runtime_threshold_identifiers_are_descriptive() -> None:
    forbidden = frozenset({"b0", "b1", "b2", "b3", "b4", "b5"})
    assert all(method.value.casefold() not in forbidden for method in FederatedThresholdMethod)
    assert FederatedThresholdMethod.SHARED_THRESHOLD.value == "shared_threshold"
    assert FederatedThresholdMethod.LOCAL_THRESHOLD.value == "local_threshold"
    assert FederatedThresholdMethod.FAMILY_THRESHOLD.value == "family_threshold"
    assert FederatedThresholdMethod.CLUSTER_THRESHOLD.value == "cluster_threshold"


def test_analysis_only_recipe_generates_or_validates_its_publication_before_reporting_completion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observed: list[ExperimentId] = []

    def report(experiment_id: ExperimentId, overwrite: OverwriteMode) -> ReportResult:
        assert overwrite is OverwriteMode.KEEP_EXISTING
        observed.append(experiment_id)
        return ReportResult(
            experiment=experiment_id,
            paths=(tmp_path,),
            detail=DetailText("validated mechanism publication"),
        )

    monkeypatch.setattr("datp_core.app.recipes._report_heterogeneity", report)
    recipe = recipe_for(ExperimentId.PER_CLIENT_SCORE_GEOMETRY)

    outcome = recipe.dispatch((), OUTPUTS_ROOT, OverwriteMode.KEEP_EXISTING)

    assert observed == [ExperimentId.PER_CLIENT_SCORE_GEOMETRY]
    assert all(item.status.value == "completed" for item in outcome.method_outcomes)
    assert "validated frozen evidence" in outcome.detail


def test_analysis_only_recipe_cannot_report_completion_from_smoke_output() -> None:
    recipe = recipe_for(ExperimentId.PER_CLIENT_SCORE_GEOMETRY)

    with pytest.raises(ScientificContractError, match="full frozen confirmatory evidence"):
        recipe.dispatch((), Path("smoke_outputs"), OverwriteMode.KEEP_EXISTING)

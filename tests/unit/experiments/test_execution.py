from dataclasses import replace
from pathlib import Path
from threading import current_thread
from typing import cast

import pytest

from datp_core.app.planning import PlanDisposition, PlanningEvidence, PlanReason, expand_experiment_plan
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import (
    AvailabilityStatus,
    CanonicalAssetRoleToken,
    CanonicalizationContractName,
    CanonicalSourcePath,
    ColumnName,
    DatasetId,
    ExperimentId,
    FederatedThresholdMethod,
)
from datp_core.core.numeric import RowCount, Seed, SourceFileCount, ValidationIssueCount
from datp_core.data.contracts import (
    CanonicalManifestDocument,
    ManifestAssetEntry,
    ManifestInventoryEntry,
    ManifestValidationReportEntry,
)
from datp_core.data.materialization import DATASET_MANIFEST_FILENAME
from datp_core.data.paths import canonical_root_under
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.experiments.execution import build_campaign, engine, execute_declared_experiment_seed
from datp_core.experiments.execution.context import training_coordinate_for
from datp_core.experiments.execution.layout import federated_training_directory
from datp_core.experiments.registry import EXPERIMENTS


def _valid_canonical_manifest(dataset: DatasetId) -> CanonicalManifestDocument:
    return CanonicalManifestDocument(
        assets=(
            ManifestAssetEntry(
                columns=(ColumnName("feature_0"),),
                path=CanonicalSourcePath("data/part-0.parquet"),
                row_count=RowCount(1),
                role=CanonicalAssetRoleToken("primary"),
            ),
        ),
        canonicalization_contract=CanonicalizationContractName("fixture_contract"),
        chronology=(),
        dataset=dataset,
        inventory=ManifestInventoryEntry(
            dataset=dataset,
            sources=(),
            accepted_source_count=SourceFileCount(0),
            excluded_source_count=SourceFileCount(0),
            excluded_sources=(),
        ),
        validation_report=ManifestValidationReportEntry(
            dataset=dataset,
            issues=(),
            exclusions=(),
            accepted_rows=RowCount(1),
            excluded_rows=RowCount(0),
            invalid_rows=RowCount(0),
            warning_count=ValidationIssueCount(0),
            status=AvailabilityStatus.AVAILABLE,
        ),
    )


def _declaration(experiment_id: ExperimentId):
    matches = tuple(item for item in EXPERIMENTS if item.id is experiment_id)
    assert len(matches) == 1
    return matches[0]


def test_execute_declared_experiment_seed_raises_on_empty_campaign(tmp_path: Path) -> None:
    declaration = _declaration(ExperimentId.DITTO_ABSORPTION_STRESS_TEST)
    with pytest.raises(ScientificContractError):
        execute_declared_experiment_seed(
            declaration=declaration,
            seed_cohort=SeedCohort(values=(Seed(0),)),
            reason=PlanReason("fixture"),
            output_root=tmp_path,
            overwrite=False,
        )


def test_execute_declared_experiment_seed_rejects_infeasible_cells_instead_of_omitting_them(tmp_path: Path) -> None:
    declaration = _declaration(ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY).model_copy(
        update={"federated_thresholds": (FederatedThresholdMethod.FAMILY_THRESHOLD,)}
    )

    with pytest.raises(ScientificContractError, match="contains non-executable coordinates and cannot omit them"):
        execute_declared_experiment_seed(
            declaration=declaration,
            seed_cohort=SeedCohort(values=(Seed(0),)),
            reason=PlanReason("fixture"),
            output_root=tmp_path,
            overwrite=False,
        )


def test_pipeline_runner_shares_fixed_detector_evidence_only_within_one_campaign(monkeypatch, tmp_path: Path) -> None:
    declaration = _declaration(ExperimentId.SHARED_VS_LOCAL_CONFIRMATION)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0),)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason=PlanReason("fixture"),
            ),
        ),
    )
    first_coordinate = plan.executable[0].coordinate
    alternate_method = next(
        method
        for method in (FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD)
        if method is not first_coordinate.threshold_method
    )
    second_coordinate = replace(first_coordinate, threshold_method=alternate_method)

    class Workspace:
        def __init__(self, **kwargs: object) -> None:
            self.coordinate = kwargs["coordinate"]
            self.output_root = kwargs["output_root"]
            self.context = object()
            self.training = object()
            self.scores = object()
            self.fixed_context = kwargs.get("fixed_context")
            self.fixed_training = kwargs.get("fixed_training")
            self.fixed_scores = kwargs.get("fixed_scores")

    monkeypatch.setattr(engine, "ExperimentWorkspace", Workspace)
    runner = engine.PipelineStageRunner()

    first = runner._workspace_for(first_coordinate, tmp_path)
    second = runner._workspace_for(second_coordinate, tmp_path)

    assert second.fixed_context is first.context
    assert second.fixed_training is first.training
    assert second.fixed_scores is first.scores


def test_pipeline_runner_releases_completed_training_coordinate_evidence(tmp_path: Path) -> None:
    declaration = _declaration(ExperimentId.SHARED_VS_LOCAL_CONFIRMATION)
    coordinate = (
        expand_experiment_plan(
            declarations=(declaration,),
            seed_cohort=SeedCohort(values=(Seed(0),)),
            evidence=(
                PlanningEvidence(
                    experiment=declaration.id,
                    disposition=PlanDisposition.EXECUTABLE,
                    reason=PlanReason("fixture"),
                ),
            ),
        )
        .executable[0]
        .coordinate
    )
    runner = engine.PipelineStageRunner()
    workspace = object()
    runner._workspace = cast(engine.ExperimentWorkspace, workspace)
    runner._fixed_score_workspaces[(training_coordinate_for(coordinate), tmp_path)] = cast(
        engine.ExperimentWorkspace,
        workspace,
    )

    runner.release_completed_training_coordinate()

    assert runner._workspace is None
    assert runner._fixed_score_workspaces == {}


def test_campaign_builder_collapses_metric_variants_for_every_declared_experiment() -> None:
    plan = expand_experiment_plan(
        declarations=tuple(
            declaration
            for declaration in EXPERIMENTS
            if declaration.id
            not in {
                ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
                ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
            }
        ),
        seed_cohort=SeedCohort(values=(Seed(0),)),
        evidence=tuple(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason=PlanReason("fixture"),
            )
            for declaration in EXPERIMENTS
        ),
    )

    campaign = build_campaign(plan)

    assert len(frozenset(entry.coordinate.execution_key for entry in campaign.entries)) == len(campaign.entries)


@pytest.mark.parametrize(
    "experiment",
    (
        ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
    ),
)
def test_campaign_builder_rejects_coordinates_owned_by_dedicated_routes(experiment: ExperimentId) -> None:
    declaration = _declaration(experiment)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0),)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason=PlanReason("fixture"),
            ),
        ),
    )

    with pytest.raises(ScientificContractError, match="generic campaign construction cannot omit it"):
        build_campaign(plan)


def test_pipeline_runner_reuses_existing_canonical_dataset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    declaration = _declaration(ExperimentId.SHARED_VS_LOCAL_CONFIRMATION)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0),)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason=PlanReason("fixture"),
            ),
        ),
    )
    coordinate = plan.executable[0].coordinate
    canonical_root = canonical_root_under(tmp_path, coordinate.dataset)
    canonical_root.mkdir(parents=True)
    (canonical_root / DATASET_MANIFEST_FILENAME).write_text(
        canonical_json_text(_valid_canonical_manifest(coordinate.dataset)), encoding="utf-8"
    )
    monkeypatch.setattr(engine, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(engine, "materialize_datasets", lambda _: pytest.fail("canonical data must be reused"))

    result = engine.PipelineStageRunner()._materialize_dataset(engine.PipelineStage.MATERIALIZE_DATASET, coordinate)

    assert result.outcome is engine.StageOutcome.COMPLETED


def test_campaign_overwrite_removes_only_its_shared_training_artifact(tmp_path: Path) -> None:
    declaration = _declaration(ExperimentId.SHARED_VS_LOCAL_CONFIRMATION)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0),)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason=PlanReason("fixture"),
            ),
        ),
    )
    campaign = build_campaign(plan)
    training_directory = federated_training_directory(training_coordinate_for(campaign.entries[0].coordinate), tmp_path)
    training_directory.mkdir(parents=True)
    (training_directory / "stale.txt").touch()
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()

    engine._remove_rebuilt_training_artifacts(campaign, tmp_path)

    assert not training_directory.exists()
    assert unrelated.exists()


def test_campaign_parallelizes_threshold_evaluations_after_shared_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    declaration = _declaration(ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY)
    assert declaration.federated_thresholds == (
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
        FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
        FederatedThresholdMethod.FEDERATED_KLL_SHARED_THRESHOLD,
        FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    )
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0),)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason=PlanReason("fixture"),
            ),
        ),
    )
    campaign = build_campaign(plan)
    runner = engine.PipelineStageRunner()

    class Workspace:
        def __init__(self) -> None:
            self.coordinate = campaign.entries[0].coordinate
            self.output_root = tmp_path

    runner._workspace = cast(engine.ExperimentWorkspace, Workspace())
    threads: list[str] = []

    def execute(coordinate, stage_runner, output_root, overwrite):
        assert output_root == tmp_path
        assert not overwrite
        threads.append(current_thread().name)
        recipe = engine.resolve_execution_recipe(coordinate)
        return engine.ExperimentExecution(
            coordinate=coordinate,
            recipe=recipe,
            stages=tuple(
                engine.StageExecution(
                    stage=stage,
                    outcome=engine.StageOutcome.COMPLETED,
                    evidence=engine.StageExecutionEvidence("fixture"),
                )
                for stage in recipe.stages
            ),
        )

    monkeypatch.setattr(engine, "execute_experiment", execute)

    result = engine.execute_campaign(
        campaign=campaign,
        stage_runner=runner,
        output_root=tmp_path,
        overwrite=False,
    )

    assert len(result.experiments) == len(campaign.entries)
    assert threads[0] == "MainThread"
    assert all(thread.startswith("ThreadPoolExecutor") for thread in threads[1:])


def test_resource_aware_worker_cap_never_exceeds_available_cpus(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine.os, "cpu_count", lambda: 2)

    assert engine._resource_aware_worker_cap(100) == 2
    assert engine._resource_aware_worker_cap(1) == 1


def test_resource_aware_worker_cap_never_exceeds_declared_maximum(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine.os, "cpu_count", lambda: 64)

    assert engine._resource_aware_worker_cap(100) == engine.MAXIMUM_PARALLEL_THRESHOLD_EVALUATIONS.value


def test_resource_aware_worker_cap_is_at_least_one_when_cpu_count_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(engine.os, "cpu_count", lambda: None)

    assert engine._resource_aware_worker_cap(5) == 1

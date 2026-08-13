from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from datp_core.analysis.mechanisms.absorption import AbsorptionSeedObservation
from datp_core.analysis.mechanisms.model_alignment import ModelAlignmentMetric, ModelAlignmentResult
from datp_core.app.campaign import build_programme_plan
from datp_core.app.contracts import AnchorRequirement, OverwriteMode
from datp_core.app.models import DetailText, ReportResult
from datp_core.app.planning import PlanDisposition, seed_cohort_for
from datp_core.app.recipes import _common_alignment_tuple_rows, evaluation_document_experiment_ids
from datp_core.app.research import (
    _campaign_publication_marker_present,
    _require_report_publication,
    generate_report,
    registered_experiment_ids,
    run_campaign,
    run_smoke,
)
from datp_core.app.validation import require_experiment_execution_ready, validate_programme
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.errors import ErrorMessage, ReportEvidenceError
from datp_core.core.identifiers import (
    AvailabilityStatus,
    CanonicalAssetRoleToken,
    CanonicalizationContractName,
    CanonicalSourcePath,
    ColumnName,
    DatasetId,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    ProgrammeStatus,
)
from datp_core.core.numeric import MetricValue, RowCount, Seed, SourceFileCount, ValidationIssueCount
from datp_core.data.contracts import (
    CanonicalManifestDocument,
    ManifestAssetEntry,
    ManifestInventoryEntry,
    ManifestValidationReportEntry,
)
from datp_core.data.materialization import DATASET_MANIFEST_FILENAME
from datp_core.data.paths import canonical_root_under
from datp_core.data.registry import population_capabilities
from datp_core.experiments.common.seeds import BOUNDED_EVIDENCE_SEED_COHORT, CONFIRMATORY_SEED_COHORT
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


def test_common_alignment_tuple_reports_raw_scope_absorption_and_unavailable_reference() -> None:
    alignment = SimpleNamespace(
        metrics=tuple(
            SimpleNamespace(metric=metric, value=MetricValue(index / 10.0))
            for index, metric in enumerate(ModelAlignmentMetric, start=1)
        )
    )
    available = SimpleNamespace(reference_effect=MetricValue(0.4), personalized_effect=MetricValue(0.1))
    unavailable = SimpleNamespace(reference_effect=MetricValue(1e-12), personalized_effect=MetricValue(0.1))

    rows = _common_alignment_tuple_rows(
        (
            (Seed(1), cast(ModelAlignmentResult, alignment), cast(AbsorptionSeedObservation, available)),
            (Seed(2), cast(ModelAlignmentResult, alignment), cast(AbsorptionSeedObservation, unavailable)),
        )
    )

    assert "| 1 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.1 | 0.75 |" in rows
    assert rows[-1].endswith("| 0.1 | UNAVAILABLE_NO_POSITIVE_FEDAVG_GAP |")


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


def test_scientific_mechanism_analyses_remain_registered() -> None:
    registered = frozenset(registered_experiment_ids())
    assert ExperimentId.PER_CLIENT_SCORE_GEOMETRY in registered
    assert ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION in registered
    assert ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF in registered


def test_evaluation_document_completeness_excludes_analysis_only_recipes() -> None:
    evaluation_experiments = frozenset(evaluation_document_experiment_ids())

    assert ExperimentId.SHARED_VS_LOCAL_CONFIRMATION in evaluation_experiments
    assert ExperimentId.PER_CLIENT_SCORE_GEOMETRY not in evaluation_experiments
    assert ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION not in evaluation_experiments
    assert ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF not in evaluation_experiments


def test_report_never_executes_and_consumes_existing_evidence_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    experiment = ExperimentId.OPTIONAL_EQUITY_INDICES
    report = ReportResult(experiment=experiment, paths=(tmp_path,), detail=DetailText("existing evidence"))

    def _fail_if_executed(*_args: object, **_kwargs: object) -> None:
        pytest.fail("generate_report must never execute an experiment or campaign")

    monkeypatch.setattr("datp_core.app.research.run_experiment", _fail_if_executed)
    monkeypatch.setattr("datp_core.app.research.run_campaign", _fail_if_executed)
    monkeypatch.setattr("datp_core.app.research._enforce_anchor_gate", lambda *_: None)
    monkeypatch.setattr(
        "datp_core.app.research.recipe_for",
        lambda _: SimpleNamespace(anchor_requirement=AnchorRequirement.NOT_REQUIRED, report=lambda _: report),
    )

    assert generate_report(experiment) is report


def test_report_propagates_missing_evidence_instead_of_computing_it(monkeypatch: pytest.MonkeyPatch) -> None:
    experiment = ExperimentId.OPTIONAL_EQUITY_INDICES

    def _fail_if_executed(*_args: object, **_kwargs: object) -> None:
        pytest.fail("generate_report must never execute an experiment or campaign")

    def _missing_evidence(_experiment_id: ExperimentId) -> ReportResult:
        raise ReportEvidenceError(ErrorMessage("evaluation evidence is missing"), subject=experiment)

    monkeypatch.setattr("datp_core.app.research.run_experiment", _fail_if_executed)
    monkeypatch.setattr("datp_core.app.research.run_campaign", _fail_if_executed)
    monkeypatch.setattr("datp_core.app.research._enforce_anchor_gate", lambda *_: None)
    monkeypatch.setattr(
        "datp_core.app.research.recipe_for",
        lambda _: SimpleNamespace(anchor_requirement=AnchorRequirement.NOT_REQUIRED, report=_missing_evidence),
    )

    with pytest.raises(ReportEvidenceError):
        generate_report(experiment)


def test_campaign_publication_requires_materialized_report_artifacts(tmp_path: Path) -> None:
    report = ReportResult(experiment=None, paths=(), detail=DetailText("empty"))
    with pytest.raises(ReportEvidenceError, match="produced no publication artifacts"):
        _require_report_publication(report)

    missing = ReportResult(experiment=None, paths=(tmp_path / "missing",), detail=DetailText("missing"))
    with pytest.raises(ReportEvidenceError, match="references missing publication artifacts"):
        _require_report_publication(missing)

    present = tmp_path / "publication.md"
    present.write_text("evidence\n", encoding="utf-8")
    _require_report_publication(ReportResult(experiment=None, paths=(present,), detail=DetailText("present")))

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ReportEvidenceError, match="references empty publication artifacts"):
        _require_report_publication(ReportResult(experiment=None, paths=(empty,), detail=DetailText("empty")))


def test_campaign_execution_and_publication_do_not_depend_on_anchor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    experiment = ExperimentId.OPTIONAL_EQUITY_INDICES
    recipe = SimpleNamespace(experiment=experiment)
    observed_anchor_requirements: list[bool] = []
    observed_completeness_plans: list[object] = []
    result = SimpleNamespace(experiment=experiment)
    report_path = tmp_path / "campaign.md"
    report_path.write_text("published\n", encoding="utf-8")
    report = ReportResult(experiment=None, paths=(report_path,), detail=DetailText("published"))

    monkeypatch.setattr("datp_core.app.research.EXPERIMENT_RECIPES", (recipe,))
    monkeypatch.setattr("datp_core.app.research.validate_programme", lambda _: None)
    monkeypatch.setattr("datp_core.app.research.require_experiment_execution_ready", lambda _: None)
    monkeypatch.setattr("datp_core.app.research.preprocess_datasets", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("datp_core.app.research._run_centralized_reference", lambda _: None)
    monkeypatch.setattr(
        "datp_core.app.research._dispatch_experiment",
        lambda *_args, require_anchor, **_kwargs: (
            observed_anchor_requirements.append(require_anchor),
            result,
        )[1],
    )
    monkeypatch.setattr("datp_core.app.research._generate_campaign_report", lambda *, require_anchor: report)
    monkeypatch.setattr(
        "datp_core.app.research.require_materialized_execution_completeness",
        lambda plan, _root: observed_completeness_plans.append(plan),
    )
    monkeypatch.setattr("datp_core.app.research.CAMPAIGN_EXECUTION_MARKER", tmp_path / "execution.txt")
    monkeypatch.setattr("datp_core.app.research.CAMPAIGN_PUBLICATION_MARKER", tmp_path / "publication.txt")
    monkeypatch.setattr(
        "datp_core.app.research._enforce_anchor_gate",
        lambda *_: pytest.fail("campaign must not enforce the anchor gate"),
    )

    campaign = run_campaign(overwrite=OverwriteMode.KEEP_EXISTING)

    assert campaign.experiments == (result,)
    assert campaign.anchor_failure is None
    assert observed_anchor_requirements == [False]
    assert len(observed_completeness_plans) == 1


def test_campaign_publication_marker_requires_nonempty_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    marker = tmp_path / "campaign_publication.txt"
    monkeypatch.setattr("datp_core.app.research.CAMPAIGN_PUBLICATION_MARKER", marker)
    assert _campaign_publication_marker_present() is False
    marker.write_text("", encoding="utf-8")
    assert _campaign_publication_marker_present() is False
    marker.write_text("campaign evidence\n", encoding="utf-8")
    assert _campaign_publication_marker_present() is True


def test_status_recognizes_dataset_manifest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from datp_core.app import research

    experiment = ExperimentId.SHARED_VS_LOCAL_CONFIRMATION
    dataset = population_capabilities(next(item for item in EXPERIMENTS if item.id is experiment).population).dataset
    canonical = canonical_root_under(tmp_path, dataset)
    canonical.mkdir(parents=True)
    (canonical / DATASET_MANIFEST_FILENAME).write_text(
        canonical_json_text(_valid_canonical_manifest(dataset)), encoding="utf-8"
    )
    monkeypatch.setattr(research, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(
        research,
        "recipe_for",
        lambda _: SimpleNamespace(
            anchor_requirement=AnchorRequirement.NOT_REQUIRED,
            analysis_marker=lambda _: False,
        ),
    )

    status = research._status_for_experiment(experiment, research.AnchorGateStatus.PASS)

    assert status.status is ProgrammeStatus.DATASET_READY


def test_single_smoke_overwrite_clears_shared_smoke_artifacts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from datp_core.app import research

    experiment = ExperimentId.SHARED_VS_LOCAL_CONFIRMATION
    smoke_root = tmp_path / "smoke"
    stale_training = smoke_root / "federated" / "stale"
    stale_training.mkdir(parents=True)
    (stale_training / "artifact.txt").write_text("stale", encoding="utf-8")
    result = SimpleNamespace(experiment=experiment, seeds=(Seed(0),))
    monkeypatch.setattr(research, "SMOKE_OUTPUT_ROOT", smoke_root)
    monkeypatch.setattr(research, "SMOKE_SUMMARY_DIRECTORY", smoke_root / "summary")
    monkeypatch.setattr(research, "run_experiment", lambda *_args, **_kwargs: result)

    run_smoke(experiment, overwrite=OverwriteMode.REBUILD)

    assert not stale_training.exists()

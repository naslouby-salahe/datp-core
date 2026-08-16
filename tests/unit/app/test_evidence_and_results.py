from pathlib import Path

import pytest

from datp_core.analysis.evidence import ExperimentMetricResults, MetricObservation
from datp_core.analysis.metrics.models import MetricStatus
from datp_core.app.contracts import (
    ArtifactKind,
    CampaignRole,
    DeliveryBundleDisposition,
    EvidenceCompletion,
    ExperimentRunDisposition,
    OverwriteMode,
    ProgrammeExecutionMode,
)
from datp_core.app.evidence import (
    evidence_contract,
    inspect_experiment_evidence,
    purge_experiment_artifacts,
    require_experiment_passed,
)
from datp_core.app.layout import DeliveryArtifactName, ResearchDirectory
from datp_core.app.models import DetailText, DispatchOutcome, ExperimentRunResult
from datp_core.app.recipes import registered_experiment_ids
from datp_core.app.research import (
    _dispatch_experiment,
    format_experiment_completion,
    generate_delivery_results,
    run_campaign,
)
from datp_core.app.results import generate_delivery_bundle
from datp_core.artifacts.serializers.json import serialize_json_model
from datp_core.core.errors import ArtifactIntegrityError, ErrorMessage, ScientificContractError
from datp_core.core.identifiers import ExperimentId, FederatedThresholdMethod, MetricId, ProgrammeStatus
from datp_core.core.numeric import MetricValue, Seed
from datp_core.experiments.registry import require_experiment_declaration


def _metric_results(experiment: ExperimentId) -> ExperimentMetricResults:
    declaration = require_experiment_declaration(experiment)
    return ExperimentMetricResults(
        experiment=experiment,
        population=declaration.population,
        evidence_role=declaration.role,
        observations=(
            MetricObservation(
                seed=Seed(0),
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                status=MetricStatus.AVAILABLE,
                threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
                value=MetricValue(0.12),
            ),
        ),
    )


def _write_supplementary_evidence(output_root: Path, experiment: ExperimentId) -> None:
    directory = output_root / ResearchDirectory.SUPPLEMENTARY.value / experiment.value
    directory.mkdir(parents=True)
    serialize_json_model(_metric_results(experiment), directory / "results.json")
    (directory / "results.csv").write_text("seed,metric,value\n0,fpr_coefficient_of_variation,0.12\n", encoding="utf-8")
    (directory / "evidence_report.md").write_text("# evidence\n", encoding="utf-8")


def test_every_registered_recipe_has_a_result_json_contract() -> None:
    for experiment_id in registered_experiment_ids():
        contract = evidence_contract(experiment_id)
        json_specs = tuple(item for item in contract.artifacts if item.kind is ArtifactKind.JSON)
        assert json_specs
        assert any(item.json_validator is not None for item in json_specs)


def test_suppressed_experiment_has_no_delivery_contract() -> None:
    with pytest.raises(ScientificContractError, match="no evidence contract"):
        evidence_contract(ExperimentId.ALERT_BURDEN_TRANSLATION)


def test_missing_json_prevents_pass(tmp_path: Path) -> None:
    experiment = ExperimentId.OPTIONAL_EQUITY_INDICES
    directory = tmp_path / ResearchDirectory.SUPPLEMENTARY.value / experiment.value
    directory.mkdir(parents=True)
    (directory / "evidence_report.md").write_text("# evidence\n", encoding="utf-8")
    evidence = inspect_experiment_evidence(experiment, output_root=tmp_path)
    assert evidence.completion is not EvidenceCompletion.PASSED
    with pytest.raises(ArtifactIntegrityError):
        require_experiment_passed(experiment, output_root=tmp_path)


def test_empty_json_prevents_pass(tmp_path: Path) -> None:
    experiment = ExperimentId.OPTIONAL_EQUITY_INDICES
    directory = tmp_path / ResearchDirectory.SUPPLEMENTARY.value / experiment.value
    directory.mkdir(parents=True)
    (directory / "results.json").write_text("", encoding="utf-8")
    (directory / "results.csv").write_text("seed,metric\n", encoding="utf-8")
    (directory / "evidence_report.md").write_text("# evidence\n", encoding="utf-8")
    evidence = inspect_experiment_evidence(experiment, output_root=tmp_path)
    assert evidence.completion is EvidenceCompletion.INVALID


def test_malformed_json_prevents_pass(tmp_path: Path) -> None:
    experiment = ExperimentId.OPTIONAL_EQUITY_INDICES
    directory = tmp_path / ResearchDirectory.SUPPLEMENTARY.value / experiment.value
    directory.mkdir(parents=True)
    (directory / "results.json").write_text("{}", encoding="utf-8")
    (directory / "results.csv").write_text("seed,metric\n", encoding="utf-8")
    (directory / "evidence_report.md").write_text("# evidence\n", encoding="utf-8")
    evidence = inspect_experiment_evidence(experiment, output_root=tmp_path)
    assert evidence.completion is EvidenceCompletion.INVALID


def test_empty_observations_prevent_pass(tmp_path: Path) -> None:
    experiment = ExperimentId.OPTIONAL_EQUITY_INDICES
    declaration = require_experiment_declaration(experiment)
    directory = tmp_path / ResearchDirectory.SUPPLEMENTARY.value / experiment.value
    directory.mkdir(parents=True)
    serialize_json_model(
        ExperimentMetricResults(
            experiment=experiment,
            population=declaration.population,
            evidence_role=declaration.role,
            observations=(),
        ),
        directory / "results.json",
    )
    (directory / "results.csv").write_text("seed,metric\n", encoding="utf-8")
    (directory / "evidence_report.md").write_text("# evidence\n", encoding="utf-8")
    evidence = inspect_experiment_evidence(experiment, output_root=tmp_path)
    assert evidence.completion is EvidenceCompletion.INVALID


def test_complete_supplementary_evidence_passes(tmp_path: Path) -> None:
    experiment = ExperimentId.OPTIONAL_EQUITY_INDICES
    _write_supplementary_evidence(tmp_path, experiment)
    evidence = inspect_experiment_evidence(experiment, output_root=tmp_path)
    assert evidence.completion is EvidenceCompletion.PASSED
    assert evidence.paths_for(ArtifactKind.JSON)


def test_incomplete_artifacts_are_not_passed(tmp_path: Path) -> None:
    experiment = ExperimentId.OPTIONAL_EQUITY_INDICES
    directory = tmp_path / ResearchDirectory.SUPPLEMENTARY.value / experiment.value
    directory.mkdir(parents=True)
    serialize_json_model(_metric_results(experiment), directory / "results.json")
    evidence = inspect_experiment_evidence(experiment, output_root=tmp_path)
    assert evidence.completion is EvidenceCompletion.ANALYSIS_COMPLETE


def test_overwrite_removes_only_experiment_owned_artifacts(tmp_path: Path) -> None:
    experiment = ExperimentId.OPTIONAL_EQUITY_INDICES
    _write_supplementary_evidence(tmp_path, experiment)
    owned = tmp_path / experiment.value
    owned.mkdir()
    (owned / "stale.json").write_text("owned\n", encoding="utf-8")
    shared = tmp_path / "federated" / "shared"
    shared.mkdir(parents=True)
    (shared / "model.txt").write_text("shared\n", encoding="utf-8")
    other = tmp_path / ExperimentId.GROUP_MEDIAN_SUPPLEMENT.value
    other.mkdir()
    (other / "keep.json").write_text("other\n", encoding="utf-8")
    dataset = tmp_path / "canonical"
    dataset.mkdir()
    (dataset / "keep.parquet").write_text("data\n", encoding="utf-8")

    purge_experiment_artifacts(experiment, output_root=tmp_path)

    assert not owned.exists()
    assert not (tmp_path / ResearchDirectory.SUPPLEMENTARY.value / experiment.value).exists()
    assert (shared / "model.txt").is_file()
    assert (other / "keep.json").is_file()
    assert (dataset / "keep.parquet").is_file()


def test_repeated_full_execution_returns_already_passed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    experiment = ExperimentId.OPTIONAL_EQUITY_INDICES
    _write_supplementary_evidence(tmp_path, experiment)
    dispatched: list[bool] = []

    monkeypatch.setattr("datp_core.app.research.OUTPUTS_ROOT", tmp_path)
    monkeypatch.setattr("datp_core.app.research.reject_anchor_as_experiment", lambda *_: None)
    monkeypatch.setattr("datp_core.app.research.require_experiment_execution_ready", lambda *_: None)
    monkeypatch.setattr("datp_core.app.research._enforce_anchor_gate", lambda *_: None)
    monkeypatch.setattr(
        "datp_core.app.research.recipe_for",
        lambda *_: type(
            "Recipe",
            (),
            {
                "anchor_requirement": None,
                "dispatch": staticmethod(lambda *_args, **_kwargs: dispatched.append(True)),
                "report": staticmethod(lambda *_args, **_kwargs: dispatched.append(True)),
            },
        )(),
    )
    monkeypatch.setattr(
        "datp_core.app.research.inspect_experiment_evidence",
        lambda *_args, **_kwargs: inspect_experiment_evidence(experiment, output_root=tmp_path),
    )

    result = _dispatch_experiment(
        experiment,
        overwrite=OverwriteMode.KEEP_EXISTING,
        mode=ProgrammeExecutionMode.FULL,
        require_anchor=False,
    )

    assert result.disposition is ExperimentRunDisposition.ALREADY_PASSED
    assert "already_passed" in result.detail
    assert dispatched == []
    assert format_experiment_completion(result) == f"experiment={experiment.value} status=already_passed"


def test_overwrite_performs_fresh_execution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    experiment = ExperimentId.OPTIONAL_EQUITY_INDICES
    _write_supplementary_evidence(tmp_path, experiment)
    purged: list[ExperimentId] = []
    dispatched: list[bool] = []

    monkeypatch.setattr("datp_core.app.research.OUTPUTS_ROOT", tmp_path)
    monkeypatch.setattr("datp_core.app.research.reject_anchor_as_experiment", lambda *_: None)
    monkeypatch.setattr("datp_core.app.research.require_experiment_execution_ready", lambda *_: None)
    monkeypatch.setattr(
        "datp_core.app.research.purge_experiment_artifacts",
        lambda experiment_id, **_kwargs: purged.append(experiment_id),
    )
    monkeypatch.setattr(
        "datp_core.app.research.recipe_for",
        lambda *_: type(
            "Recipe",
            (),
            {
                "anchor_requirement": None,
                "dispatch": staticmethod(
                    lambda *_args, **_kwargs: (
                        dispatched.append(True),
                        DispatchOutcome(detail=DetailText("ran"), method_outcomes=()),
                    )[1]
                ),
                "report": staticmethod(lambda *_args, **_kwargs: None),
            },
        )(),
    )
    monkeypatch.setattr(
        "datp_core.app.research.require_experiment_passed",
        lambda *_args, **_kwargs: inspect_experiment_evidence(experiment, output_root=tmp_path),
    )

    result = _dispatch_experiment(
        experiment,
        overwrite=OverwriteMode.REBUILD,
        mode=ProgrammeExecutionMode.FULL,
        require_anchor=False,
    )

    assert purged == [experiment]
    assert dispatched == [True]
    assert result.disposition is ExperimentRunDisposition.COMPLETED


def test_failed_execution_cannot_leave_pass_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    experiment = ExperimentId.OPTIONAL_EQUITY_INDICES
    _write_supplementary_evidence(tmp_path, experiment)

    monkeypatch.setattr("datp_core.app.research.OUTPUTS_ROOT", tmp_path)
    monkeypatch.setattr("datp_core.app.research.reject_anchor_as_experiment", lambda *_: None)
    monkeypatch.setattr("datp_core.app.research.require_experiment_execution_ready", lambda *_: None)
    monkeypatch.setattr(
        "datp_core.app.research.recipe_for",
        lambda *_: type(
            "Recipe",
            (),
            {
                "anchor_requirement": None,
                "dispatch": staticmethod(
                    lambda *_args, **_kwargs: (_ for _ in ()).throw(ScientificContractError(ErrorMessage("boom")))
                ),
                "report": staticmethod(
                    lambda *_args, **_kwargs: pytest.fail("report must not run after failed dispatch")
                ),
            },
        )(),
    )

    with pytest.raises(ScientificContractError, match="boom"):
        _dispatch_experiment(
            experiment,
            overwrite=OverwriteMode.REBUILD,
            mode=ProgrammeExecutionMode.FULL,
            require_anchor=False,
        )
    assert inspect_experiment_evidence(experiment, output_root=tmp_path).passed is False


def test_failed_report_does_not_mark_complete(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    experiment = ExperimentId.OPTIONAL_EQUITY_INDICES

    monkeypatch.setattr("datp_core.app.research.OUTPUTS_ROOT", tmp_path)
    monkeypatch.setattr("datp_core.app.research.reject_anchor_as_experiment", lambda *_: None)
    monkeypatch.setattr("datp_core.app.research.require_experiment_execution_ready", lambda *_: None)
    monkeypatch.setattr(
        "datp_core.app.research.recipe_for",
        lambda *_: type(
            "Recipe",
            (),
            {
                "anchor_requirement": None,
                "dispatch": staticmethod(
                    lambda *_args, **_kwargs: DispatchOutcome(detail=DetailText("ran"), method_outcomes=())
                ),
                "report": staticmethod(
                    lambda *_args, **_kwargs: (_ for _ in ()).throw(ArtifactIntegrityError(ErrorMessage("incomplete")))
                ),
            },
        )(),
    )

    with pytest.raises(ArtifactIntegrityError, match="incomplete"):
        _dispatch_experiment(
            experiment,
            overwrite=OverwriteMode.KEEP_EXISTING,
            mode=ProgrammeExecutionMode.FULL,
            require_anchor=False,
        )
    assert inspect_experiment_evidence(experiment, output_root=tmp_path).completion is EvidenceCompletion.NOT_STARTED


def test_results_bundle_generation_and_idempotence(tmp_path: Path) -> None:
    output_root = tmp_path / "outputs"
    results_root = tmp_path / "results"
    output_root.mkdir()
    _write_supplementary_evidence(output_root, ExperimentId.OPTIONAL_EQUITY_INDICES)

    first = generate_delivery_bundle(overwrite=False, output_root=output_root, results_root=results_root)
    assert first.disposition is DeliveryBundleDisposition.GENERATED
    assert (results_root / DeliveryArtifactName.MANIFEST).is_file()
    assert (results_root / DeliveryArtifactName.SUMMARY).is_file()
    assert first.manifest.artifacts
    assert all((results_root / item.bundle_path).is_file() for item in first.manifest.artifacts)
    assert any(item.kind is ArtifactKind.JSON for item in first.manifest.artifacts)

    second = generate_delivery_bundle(overwrite=False, output_root=output_root, results_root=results_root)
    assert second.disposition is DeliveryBundleDisposition.ALREADY_CURRENT

    stale = results_root / "json" / "duplicate.json"
    stale.write_text("{}\n", encoding="utf-8")
    third = generate_delivery_bundle(overwrite=True, output_root=output_root, results_root=results_root)
    assert third.disposition is DeliveryBundleDisposition.GENERATED
    assert not stale.exists()
    names = tuple(item.bundle_path for item in third.manifest.artifacts)
    assert len(names) == len(frozenset(names))


def test_results_command_is_idempotent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from datp_core.app import research

    output_root = tmp_path / "outputs"
    results_root = tmp_path / "results"
    output_root.mkdir()
    _write_supplementary_evidence(output_root, ExperimentId.OPTIONAL_EQUITY_INDICES)
    monkeypatch.setattr(research, "OUTPUTS_ROOT", output_root)
    monkeypatch.setattr(research, "RESULTS_ROOT", results_root)

    first = generate_delivery_results(overwrite=OverwriteMode.KEEP_EXISTING)
    second = generate_delivery_results(overwrite=OverwriteMode.KEEP_EXISTING)
    assert "generated" in first or "already_current" in first
    assert "already_current" in second


def test_optional_and_suppressed_experiments_are_not_required_for_delivery(tmp_path: Path) -> None:
    output_root = tmp_path / "outputs"
    results_root = tmp_path / "results"
    output_root.mkdir()
    bundle = generate_delivery_bundle(overwrite=True, output_root=output_root, results_root=results_root)
    included = frozenset(item.experiment for item in bundle.summary.experiments)
    assert ExperimentId.ALERT_BURDEN_TRANSLATION not in included
    assert ExperimentId.OPTIONAL_EQUITY_INDICES not in included
    assert ExperimentId.OPTIONAL_EQUITY_INDICES in bundle.summary.omitted_optional


def test_campaign_requires_mandatory_completeness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    recipe = type(
        "Recipe",
        (),
        {"experiment": ExperimentId.SHARED_VS_LOCAL_CONFIRMATION, "campaign_role": CampaignRole.MANDATORY},
    )()
    monkeypatch.setattr("datp_core.app.research.EXPERIMENT_RECIPES", (recipe,))
    monkeypatch.setattr("datp_core.app.research.validate_programme", lambda _: None)
    monkeypatch.setattr("datp_core.app.research.require_experiment_execution_ready", lambda *_: None)
    monkeypatch.setattr("datp_core.app.research.preprocess_datasets", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("datp_core.app.research._run_centralized_reference", lambda _: None)
    monkeypatch.setattr(
        "datp_core.app.research._dispatch_experiment",
        lambda *_args, **_kwargs: ExperimentRunResult(
            experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
            seeds=(Seed(0),),
            mode=ProgrammeExecutionMode.FULL,
            output_root=tmp_path,
            detail=DetailText("ran"),
            method_outcomes=(),
            disposition=ExperimentRunDisposition.COMPLETED,
        ),
    )
    monkeypatch.setattr("datp_core.app.research.require_materialized_execution_completeness", lambda *_: None)
    monkeypatch.setattr(
        "datp_core.app.research.require_experiment_passed",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ArtifactIntegrityError(ErrorMessage("missing json"))),
    )

    with pytest.raises(ArtifactIntegrityError, match="missing json"):
        run_campaign(overwrite=OverwriteMode.KEEP_EXISTING)


def test_status_maps_evidence_completion() -> None:
    from datp_core.app.research import _programme_status

    assert _programme_status(EvidenceCompletion.PASSED) is ProgrammeStatus.PASSED
    assert _programme_status(EvidenceCompletion.INVALID) is ProgrammeStatus.INVALID
    assert _programme_status(EvidenceCompletion.INCOMPLETE) is ProgrammeStatus.INCOMPLETE
    assert _programme_status(EvidenceCompletion.EXECUTION_COMPLETE) is ProgrammeStatus.EXECUTION_COMPLETE
    assert _programme_status(EvidenceCompletion.ANALYSIS_COMPLETE) is ProgrammeStatus.ANALYSIS_COMPLETE
    assert _programme_status(EvidenceCompletion.NOT_STARTED) is ProgrammeStatus.DATASET_READY

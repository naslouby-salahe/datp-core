from __future__ import annotations

import sys
from pathlib import Path
from shutil import rmtree

from datp_core.app.anchor import (
    anchor_status,
    reproduce_anchor,
    verify_anchor_programme,
)
from datp_core.app.campaign import preprocess_datasets
from datp_core.app.contracts import (
    AnchorRequirement,
    ArtifactKind,
    ArtifactPresence,
    CampaignRole,
    EvidenceCompletion,
    ExperimentRunDisposition,
    OverwriteMode,
    ProgrammeExecutionMode,
    RecipeRegistration,
)
from datp_core.app.evidence import (
    ExperimentEvidence,
    inspect_experiment_evidence,
    purge_experiment_artifacts,
    require_experiment_passed,
)
from datp_core.app.layout import (
    ANCHOR_DIAGNOSTICS_DIRECTORY,
    CAMPAIGN_EXECUTION_MARKER,
    CAMPAIGN_PUBLICATION_MARKER,
    SMOKE_OUTPUT_ROOT,
    SMOKE_SUMMARY_DIRECTORY,
    ResearchArtifact,
)
from datp_core.app.models import (
    CampaignRunResult,
    DetailText,
    ExperimentRunResult,
    ExperimentStatusRecord,
    ProgrammeStatusReport,
    ReportResult,
    ThresholdMethodOutcome,
)
from datp_core.app.planning import restrict_plan_to_experiments, seed_cohort_for
from datp_core.app.progress import progress_hook
from datp_core.app.recipes import (
    EXPERIMENT_RECIPES,
    anchor_gated_experiment_ids,
    evaluation_document_experiment_ids,
    mandatory_experiment_ids,
    recipe_for,
    registered_experiment_ids,
)
from datp_core.app.results import generate_delivery_bundle
from datp_core.app.validation import (
    reject_anchor_as_experiment,
    require_experiment_declaration,
    require_experiment_execution_ready,
    validate_programme,
)
from datp_core.core.errors import (
    AnchorReproductionError,
    ArtifactIntegrityError,
    ErrorMessage,
    MissingPrerequisiteError,
    MissingPrerequisiteReason,
    ReportEvidenceError,
    ScientificContractError,
    UnresolvedScientificValueError,
)
from datp_core.core.identifiers import ExperimentId, ExperimentReadiness, FileContentText, ProgrammeStatus
from datp_core.core.numeric import Seed
from datp_core.data.materialization import canonical_dataset_is_materialized
from datp_core.data.paths import canonical_root_under
from datp_core.data.populations.declarations import POPULATIONS
from datp_core.experiments.anchor.contracts import AnchorGateStatus
from datp_core.experiments.anchor.gate import (
    load_anchor_confirmatory_handoff,
    load_verified_anchor_gate_artifact,
)
from datp_core.experiments.centralized_reference import (
    CIC_CENTRALIZED_REFERENCE,
    NBAIOT_CENTRALIZED_REFERENCE,
    centralized_reference_directory,
    run_centralized_reference_seed,
)
from datp_core.experiments.execution.evidence import require_materialized_execution_completeness
from datp_core.experiments.graph import CANONICAL_PROTOCOL_GRAPH, validate_protocol_graph
from datp_core.runtime.configuration import DATA_ROOT, OUTPUTS_ROOT, RESULTS_ROOT
from datp_core.runtime.filesystem import write_text_atomically

__all__ = (
    "anchor_gated_experiment_ids",
    "anchor_status",
    "format_status",
    "generate_delivery_results",
    "generate_report",
    "mandatory_experiment_ids",
    "programme_status",
    "registered_experiment_ids",
    "reproduce_anchor",
    "run_campaign",
    "run_experiment",
    "run_smoke",
    "verify_anchor_programme",
)


def _output_root(mode: ProgrammeExecutionMode) -> Path:
    return SMOKE_OUTPUT_ROOT if mode is ProgrammeExecutionMode.SMOKE else OUTPUTS_ROOT


def progress_log_path(output_root: Path, name: str) -> Path:
    return output_root / "logs" / f"{name}.progress.log"


def canonical_smoke_seed(experiment_id: ExperimentId) -> Seed:
    return seed_cohort_for(experiment_id).values[0]


def _enforce_anchor_gate(experiment_id: ExperimentId, requirement: AnchorRequirement) -> None:
    if requirement is AnchorRequirement.NOT_REQUIRED:
        return
    try:
        verified_gate = load_verified_anchor_gate_artifact(ANCHOR_DIAGNOSTICS_DIRECTORY)
        load_anchor_confirmatory_handoff(ANCHOR_DIAGNOSTICS_DIRECTORY, verified_gate=verified_gate)
    except AnchorReproductionError as error:
        raise MissingPrerequisiteError(
            ErrorMessage(f"experiment {experiment_id.value} is blocked by the anchor equivalence gate: {error}"),
            subject=experiment_id,
            reason=MissingPrerequisiteReason.ANCHOR_GATE,
        ) from error


def run_experiment(
    experiment_id: ExperimentId,
    *,
    overwrite: OverwriteMode,
    mode: ProgrammeExecutionMode,
) -> ExperimentRunResult:
    return _dispatch_experiment(experiment_id, overwrite=overwrite, mode=mode, require_anchor=True)


def _dispatch_experiment(
    experiment_id: ExperimentId,
    *,
    overwrite: OverwriteMode,
    mode: ProgrammeExecutionMode,
    require_anchor: bool,
) -> ExperimentRunResult:
    reject_anchor_as_experiment(experiment_id)
    require_experiment_execution_ready(experiment_id)
    recipe = recipe_for(experiment_id)
    if require_anchor and mode is ProgrammeExecutionMode.FULL:
        _enforce_anchor_gate(experiment_id, recipe.anchor_requirement)
    output_root = _output_root(mode)
    if overwrite.requested and mode is ProgrammeExecutionMode.SMOKE:
        scoped = output_root / experiment_id.value
        if scoped.exists():
            rmtree(scoped)
    if overwrite.requested and mode is ProgrammeExecutionMode.FULL:
        purge_experiment_artifacts(experiment_id, output_root=output_root)
    if mode is ProgrammeExecutionMode.FULL and not overwrite.requested:
        existing = inspect_experiment_evidence(experiment_id, output_root=output_root)
        if existing.passed:
            return _experiment_result(
                experiment_id=experiment_id,
                seeds=seed_cohort_for(experiment_id).values,
                mode=mode,
                output_root=output_root,
                detail=DetailText(f"experiment={experiment_id.value} status=already_passed"),
                method_outcomes=(),
                disposition=ExperimentRunDisposition.ALREADY_PASSED,
                evidence=existing,
            )
    cohort = seed_cohort_for(experiment_id)
    seeds = (canonical_smoke_seed(experiment_id),) if mode is ProgrammeExecutionMode.SMOKE else cohort.values
    hook = progress_hook(sys.stdout, progress_log_path(output_root, experiment_id.value))
    outcome = recipe.dispatch(seeds, output_root, overwrite, progress=hook)
    if mode is ProgrammeExecutionMode.FULL:
        recipe.report(experiment_id)
        evidence = require_experiment_passed(experiment_id, output_root=output_root)
        return _experiment_result(
            experiment_id=experiment_id,
            seeds=seeds,
            mode=mode,
            output_root=output_root,
            detail=outcome.detail,
            method_outcomes=outcome.method_outcomes,
            disposition=ExperimentRunDisposition.COMPLETED,
            evidence=evidence,
        )
    return ExperimentRunResult(
        experiment=experiment_id,
        seeds=seeds,
        mode=mode,
        output_root=output_root,
        detail=outcome.detail,
        method_outcomes=outcome.method_outcomes,
        disposition=ExperimentRunDisposition.COMPLETED,
    )


def _experiment_result(
    *,
    experiment_id: ExperimentId,
    seeds: tuple[Seed, ...],
    mode: ProgrammeExecutionMode,
    output_root: Path,
    detail: DetailText,
    method_outcomes: tuple[ThresholdMethodOutcome, ...],
    disposition: ExperimentRunDisposition,
    evidence: ExperimentEvidence,
) -> ExperimentRunResult:
    return ExperimentRunResult(
        experiment=experiment_id,
        seeds=seeds,
        mode=mode,
        output_root=output_root,
        detail=detail,
        method_outcomes=method_outcomes,
        disposition=disposition,
        json_paths=evidence.paths_for(ArtifactKind.JSON),
        csv_paths=evidence.paths_for(ArtifactKind.CSV),
        figure_paths=evidence.paths_for(ArtifactKind.FIGURE),
        report_paths=evidence.paths_for(ArtifactKind.REPORT),
    )


def run_smoke(
    experiment_id: ExperimentId | None,
    *,
    overwrite: OverwriteMode,
) -> CampaignRunResult:
    if experiment_id is not None:
        reject_anchor_as_experiment(experiment_id)
    if overwrite.requested and SMOKE_OUTPUT_ROOT.exists():
        rmtree(SMOKE_OUTPUT_ROOT)
    if experiment_id is not None:
        result = run_experiment(
            experiment_id,
            overwrite=overwrite,
            mode=ProgrammeExecutionMode.SMOKE,
        )
        _publish_smoke_summary((result,))
        return CampaignRunResult(
            experiments=(result,),
            detail=DetailText("smoke single experiment"),
            anchor_failure=None,
        )
    anchor_failure: DetailText | None = None
    try:
        reproduced = reproduce_anchor(
            overwrite=overwrite,
            mode=ProgrammeExecutionMode.SMOKE,
            progress=progress_hook(sys.stdout, progress_log_path(SMOKE_OUTPUT_ROOT, "anchor")),
        )
        verified = verify_anchor_programme(mode=ProgrammeExecutionMode.SMOKE)
        non_pass = tuple(
            result.gate_status
            for result in (reproduced, verified)
            if result.gate_status not in {AnchorGateStatus.PASS, AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY}
        )
        if non_pass:
            anchor_failure = DetailText("anchor gate " + ",".join(status.value for status in non_pass))
    except (AnchorReproductionError, MissingPrerequisiteError, ScientificContractError) as error:
        anchor_failure = DetailText(str(error))
    results = tuple(
        run_experiment(
            recipe.experiment,
            overwrite=overwrite,
            mode=ProgrammeExecutionMode.SMOKE,
        )
        for recipe in EXPERIMENT_RECIPES
    )
    _publish_smoke_summary(results)
    return CampaignRunResult(
        experiments=results,
        detail=DetailText(f"smoke experiments={len(results)}"),
        anchor_failure=anchor_failure,
    )


def _publish_smoke_summary(results: tuple[ExperimentRunResult, ...]) -> None:
    SMOKE_SUMMARY_DIRECTORY.mkdir(parents=True, exist_ok=True)
    lines = (
        "smoke_summary",
        *(f"{item.experiment.value}:seeds={','.join(str(seed.value) for seed in item.seeds)}" for item in results),
    )
    write_text_atomically(
        SMOKE_SUMMARY_DIRECTORY / ResearchArtifact.SMOKE_SUMMARY,
        FileContentText("\n".join(lines) + "\n"),
    )


def _run_centralized_reference(overwrite: OverwriteMode) -> None:
    for scope in (NBAIOT_CENTRALIZED_REFERENCE, CIC_CENTRALIZED_REFERENCE):
        for seed in scope.seed_cohort.values:
            directory = centralized_reference_directory(scope, seed)
            if overwrite.requested and directory.exists():
                rmtree(directory)
            run_centralized_reference_seed(scope, seed)


def run_campaign(*, overwrite: OverwriteMode) -> CampaignRunResult:
    validate_programme(None)
    for recipe in EXPERIMENT_RECIPES:
        require_experiment_execution_ready(recipe.experiment)
    preprocess_datasets(None, overwrite=OverwriteMode.KEEP_EXISTING)
    _run_centralized_reference(overwrite)
    results = tuple(
        _dispatch_experiment(
            recipe.experiment,
            overwrite=overwrite,
            mode=ProgrammeExecutionMode.FULL,
            require_anchor=False,
        )
        for recipe in EXPERIMENT_RECIPES
    )
    from datp_core.app.campaign import build_programme_plan

    completeness_plan = restrict_plan_to_experiments(
        build_programme_plan(None).plan,
        frozenset(evaluation_document_experiment_ids()).intersection(result.experiment for result in results),
    )
    require_materialized_execution_completeness(completeness_plan, OUTPUTS_ROOT)
    for recipe in EXPERIMENT_RECIPES:
        if recipe.campaign_role is CampaignRole.OPTIONAL:
            continue
        require_experiment_passed(recipe.experiment, output_root=OUTPUTS_ROOT)
    execution_marker_lines = "\n".join(item.experiment.value for item in results) + "\n"
    CAMPAIGN_EXECUTION_MARKER.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomically(CAMPAIGN_EXECUTION_MARKER, FileContentText(execution_marker_lines))
    report = _generate_campaign_report(require_anchor=False)
    _require_report_publication(report)
    for recipe in EXPERIMENT_RECIPES:
        if recipe.campaign_role is CampaignRole.OPTIONAL:
            continue
        require_experiment_passed(recipe.experiment, output_root=OUTPUTS_ROOT)
    CAMPAIGN_PUBLICATION_MARKER.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomically(CAMPAIGN_PUBLICATION_MARKER, FileContentText(execution_marker_lines))
    delivery = generate_delivery_bundle(overwrite=False, output_root=OUTPUTS_ROOT, results_root=RESULTS_ROOT)
    return CampaignRunResult(
        experiments=results,
        detail=DetailText(f"campaign experiments={len(results)} report={report.detail} results={delivery.root}"),
        anchor_failure=None,
    )


def _require_report_publication(report: ReportResult) -> None:
    """Prevent a campaign publication marker from certifying an empty report.

    Recipe reports are evidence-bearing files or directories.  A successful
    dispatch alone is not publication completion: every report must identify
    at least one nonempty materialized artifact and each reported artifact
    must exist.
    """

    if not report.paths:
        raise ReportEvidenceError(ErrorMessage("campaign report produced no publication artifacts"))
    missing = tuple(path for path in report.paths if not path.exists())
    if missing:
        detail = ", ".join(str(path) for path in missing)
        raise ReportEvidenceError(ErrorMessage(f"campaign report references missing publication artifacts: {detail}"))
    empty = tuple(path for path in report.paths if not _has_materialized_report_content(path))
    if empty:
        detail = ", ".join(str(path) for path in empty)
        raise ReportEvidenceError(ErrorMessage(f"campaign report references empty publication artifacts: {detail}"))


def _has_materialized_report_content(path: Path) -> bool:
    if path.is_file():
        return path.stat().st_size > 0
    if not path.is_dir():
        return False
    return any(child.is_file() and child.stat().st_size > 0 for child in path.rglob("*"))


def generate_report(experiment_id: ExperimentId | None) -> ReportResult:
    if experiment_id is None:
        return _generate_campaign_report(require_anchor=False)
    reject_anchor_as_experiment(experiment_id)
    require_experiment_declaration(experiment_id)
    recipe = recipe_for(experiment_id)
    _enforce_anchor_gate(experiment_id, recipe.anchor_requirement)
    report = recipe.report(experiment_id)
    require_experiment_passed(experiment_id)
    return report


def _generate_campaign_report(*, require_anchor: bool) -> ReportResult:
    paths: list[Path] = []
    details: list[str] = []
    for recipe in EXPERIMENT_RECIPES:
        try:
            if require_anchor:
                _enforce_anchor_gate(recipe.experiment, recipe.anchor_requirement)
            evidence = inspect_experiment_evidence(recipe.experiment)
            if evidence.passed:
                paths.extend(_evidence_publication_paths(evidence))
                details.append(f"{recipe.experiment.value}:ok")
                continue
            report = recipe.report(recipe.experiment)
        except (
            AnchorReproductionError,
            MissingPrerequisiteError,
            ReportEvidenceError,
            ScientificContractError,
            ArtifactIntegrityError,
        ) as error:
            if recipe.campaign_role is CampaignRole.OPTIONAL:
                details.append(f"{recipe.experiment.value}:optional_missing({error})")
                continue
            raise
        paths.extend(report.paths)
        details.append(f"{recipe.experiment.value}:ok")
    return ReportResult(
        experiment=None,
        paths=tuple(paths),
        detail=DetailText(";".join(details) if details else "no reportable experiment evidence"),
    )


def _evidence_publication_paths(evidence: ExperimentEvidence) -> tuple[Path, ...]:
    return (
        *evidence.paths_for(ArtifactKind.JSON),
        *evidence.paths_for(ArtifactKind.CSV),
        *evidence.paths_for(ArtifactKind.FIGURE),
        *evidence.paths_for(ArtifactKind.REPORT),
    )


def programme_status(experiment_id: ExperimentId | None) -> ProgrammeStatusReport:
    graph = validate_protocol_graph(CANONICAL_PROTOCOL_GRAPH)
    if experiment_id is None:
        target_ids = tuple(
            item.id for item in graph.experiments if item.id is not ExperimentId.HISTORICAL_DATP_REPRODUCTION
        )
    else:
        reject_anchor_as_experiment(experiment_id)
        require_experiment_declaration(experiment_id)
        target_ids = (experiment_id,)
    anchor = anchor_status()
    return ProgrammeStatusReport(
        records=tuple(_status_for_experiment(item, anchor.gate_status) for item in target_ids),
        anchor_gate=anchor.gate_status,
        campaign_completion=(
            ArtifactPresence.PRESENT if _campaign_publication_marker_present() else ArtifactPresence.ABSENT
        ),
    )


def _campaign_publication_marker_present() -> bool:
    return CAMPAIGN_PUBLICATION_MARKER.is_file() and CAMPAIGN_PUBLICATION_MARKER.stat().st_size > 0


def _status_for_experiment(
    experiment_id: ExperimentId,
    anchor_gate: AnchorGateStatus,
) -> ExperimentStatusRecord:
    declaration = require_experiment_declaration(experiment_id)
    if declaration.readiness is ExperimentReadiness.SUPPRESSED:
        return ExperimentStatusRecord(
            experiment=experiment_id,
            status=ProgrammeStatus.BLOCKED_BY_DEPENDENCY,
            role=declaration.role,
            readiness=declaration.readiness,
            registration=RecipeRegistration.SUPPRESSED,
            detail=DetailText("suppressed by protocol declaration"),
        )
    try:
        require_experiment_execution_ready(experiment_id)
    except UnresolvedScientificValueError as error:
        return ExperimentStatusRecord(
            experiment=experiment_id,
            status=ProgrammeStatus.BLOCKED_BY_DEPENDENCY,
            role=declaration.role,
            readiness=declaration.readiness,
            registration=RecipeRegistration.REGISTERED,
            detail=DetailText(str(error)),
        )
    recipe = recipe_for(experiment_id)
    if recipe.anchor_requirement is AnchorRequirement.REQUIRED and anchor_gate not in {
        AnchorGateStatus.PASS,
        AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY,
    }:
        return ExperimentStatusRecord(
            experiment=experiment_id,
            status=ProgrammeStatus.BLOCKED_BY_ANCHOR,
            role=declaration.role,
            readiness=declaration.readiness,
            registration=RecipeRegistration.REGISTERED,
            detail=DetailText(f"anchor_gate={anchor_gate.value}"),
        )
    population = next(item for item in POPULATIONS if item.id is declaration.population)
    canonical = canonical_root_under(DATA_ROOT, population.dataset)
    if not canonical_dataset_is_materialized(canonical, population.dataset):
        return ExperimentStatusRecord(
            experiment=experiment_id,
            status=ProgrammeStatus.NOT_STARTED,
            role=declaration.role,
            readiness=declaration.readiness,
            registration=RecipeRegistration.REGISTERED,
            detail=DetailText("canonical dataset incomplete"),
        )
    evidence = inspect_experiment_evidence(experiment_id)
    return ExperimentStatusRecord(
        experiment=experiment_id,
        status=_programme_status(evidence.completion),
        role=declaration.role,
        readiness=declaration.readiness,
        registration=RecipeRegistration.REGISTERED,
        detail=DetailText(f"evidence={evidence.completion.value}"),
    )


def _programme_status(completion: EvidenceCompletion) -> ProgrammeStatus:
    if completion is EvidenceCompletion.PASSED:
        return ProgrammeStatus.PASSED
    if completion is EvidenceCompletion.ANALYSIS_COMPLETE:
        return ProgrammeStatus.ANALYSIS_COMPLETE
    if completion is EvidenceCompletion.EXECUTION_COMPLETE:
        return ProgrammeStatus.EXECUTION_COMPLETE
    if completion is EvidenceCompletion.INVALID:
        return ProgrammeStatus.INVALID
    if completion is EvidenceCompletion.INCOMPLETE:
        return ProgrammeStatus.INCOMPLETE
    return ProgrammeStatus.DATASET_READY


def generate_delivery_results(*, overwrite: OverwriteMode) -> DetailText:
    result = generate_delivery_bundle(
        overwrite=overwrite.requested,
        output_root=OUTPUTS_ROOT,
        results_root=RESULTS_ROOT,
    )
    return DetailText(
        f"results status={result.disposition.value} root={result.root} "
        f"experiments={result.summary.passed_count.value} artifacts={len(result.manifest.artifacts)}"
    )


def format_experiment_completion(result: ExperimentRunResult) -> DetailText:
    if result.disposition is ExperimentRunDisposition.ALREADY_PASSED:
        return DetailText(f"experiment={result.experiment.value} status=already_passed")
    lines = (
        f"experiment={result.experiment.value}",
        f"status={result.disposition.value}",
        f"json={_join_paths(result.json_paths)}",
        f"csv={_join_paths(result.csv_paths)}",
        f"figures={_join_paths(result.figure_paths)}",
        f"reports={_join_paths(result.report_paths)}",
        f"output_root={result.output_root}",
    )
    return DetailText("\n".join(lines))


def _join_paths(paths: tuple[Path, ...]) -> str:
    if not paths:
        return "none"
    return ",".join(path.as_posix() for path in paths)


def format_status(report: ProgrammeStatusReport) -> DetailText:
    lines = [
        f"anchor_gate={report.anchor_gate.value}",
        f"campaign_completion={report.campaign_completion.value}",
    ]
    lines.extend(
        f"{record.experiment.value} status={record.status.value} role={record.role.value} "
        f"readiness={record.readiness.value} registration={record.registration.value} detail={record.detail}"
        for record in report.records
    )
    return DetailText("\n".join(lines))

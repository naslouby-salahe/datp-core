"""Programme execution, campaign lifecycle, reporting orchestration, and status."""

from __future__ import annotations

from pathlib import Path
from shutil import rmtree

from datp_core.anchor.models import AnchorGateStatus
from datp_core.app.anchor_service import (
    anchor_gate_permits_dependents,
    anchor_status,
    reproduce_anchor,
    verify_anchor_programme,
)
from datp_core.app.contracts import (
    AnchorRequirement,
    ArtifactPresence,
    OverwriteMode,
    ProgrammeExecutionMode,
    RecipeRegistration,
)
from datp_core.app.layout import (
    CAMPAIGN_COMPLETION_MARKER,
    CENTRALIZED_REFERENCE_COMPLETION_MARKER,
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
)
from datp_core.app.recipes import (
    EXPERIMENT_RECIPES,
    anchor_gated_experiment_ids,
    recipe_for,
    registered_experiment_ids,
)
from datp_core.datasets.paths import canonical_root_under
from datp_core.domain.enums import ExperimentId, ExperimentReadiness, ProgrammeStatus
from datp_core.domain.errors import (
    AnchorReproductionError,
    MissingPrerequisiteError,
    ReportEvidenceError,
    ScientificContractError,
)
from datp_core.domain.values.counts import Seed
from datp_core.protocols.populations import POPULATIONS
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT
from datp_core.runtime.configuration import DATA_ROOT, OUTPUTS_ROOT
from datp_core.runtime.filesystem import write_text_atomically


__all__ = (
    "anchor_gated_experiment_ids",
    "anchor_status",
    "format_status",
    "generate_report",
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


def canonical_smoke_seed(experiment_id: ExperimentId) -> Seed:
    from datp_core.app.programme import seed_cohort_for

    return seed_cohort_for(experiment_id).values[0]


def _enforce_anchor_gate(experiment_id: ExperimentId, requirement: AnchorRequirement) -> None:
    if requirement is AnchorRequirement.NOT_REQUIRED:
        return
    if not anchor_gate_permits_dependents():
        raise MissingPrerequisiteError(
            f"experiment {experiment_id.value} is blocked by the anchor equivalence gate",
            subject=experiment_id,
            reason="anchor_gate",
        )


def run_experiment(
    experiment_id: ExperimentId,
    *,
    overwrite: OverwriteMode,
    mode: ProgrammeExecutionMode,
) -> ExperimentRunResult:
    from datp_core.app.programme import reject_anchor_as_experiment, seed_cohort_for

    reject_anchor_as_experiment(experiment_id)
    recipe = recipe_for(experiment_id)
    if mode is ProgrammeExecutionMode.FULL:
        _enforce_anchor_gate(experiment_id, recipe.anchor_requirement)
    output_root = _output_root(mode)
    if overwrite.requested and mode is ProgrammeExecutionMode.SMOKE:
        scoped = output_root / experiment_id.value
        if scoped.exists():
            rmtree(scoped)
    cohort = seed_cohort_for(experiment_id)
    seeds = (canonical_smoke_seed(experiment_id),) if mode is ProgrammeExecutionMode.SMOKE else cohort.values
    outcome = recipe.dispatch(seeds, output_root, overwrite)
    return ExperimentRunResult(
        experiment=experiment_id,
        seeds=seeds,
        mode=mode,
        output_root=output_root,
        detail=outcome.detail,
        method_outcomes=outcome.method_outcomes,
    )


def run_smoke(
    experiment_id: ExperimentId | None,
    *,
    overwrite: OverwriteMode,
) -> CampaignRunResult:
    from datp_core.app.programme import reject_anchor_as_experiment

    if experiment_id is not None:
        reject_anchor_as_experiment(experiment_id)
    if overwrite.requested and SMOKE_OUTPUT_ROOT.exists():
        if experiment_id is None:
            rmtree(SMOKE_OUTPUT_ROOT)
        else:
            scoped = SMOKE_OUTPUT_ROOT / experiment_id.value
            if scoped.exists():
                rmtree(scoped)
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
        reproduced = reproduce_anchor(overwrite=overwrite, mode=ProgrammeExecutionMode.SMOKE)
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
        SMOKE_SUMMARY_DIRECTORY / ResearchArtifact.COMPLETE,
        "\n".join(lines) + "\n",
    )


def _run_centralized_reference(overwrite: OverwriteMode) -> None:
    from datp_core.experiments.centralized_reference import centralized_reference_directory, run_centralized_reference_seed

    if CENTRALIZED_REFERENCE_COMPLETION_MARKER.is_file() and not overwrite.requested:
        return
    for seed in CONFIRMATORY_SEED_COHORT.values:
        directory = centralized_reference_directory(seed)
        if overwrite.requested and directory.exists():
            rmtree(directory)
        run_centralized_reference_seed(seed)
    CENTRALIZED_REFERENCE_COMPLETION_MARKER.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomically(
        CENTRALIZED_REFERENCE_COMPLETION_MARKER,
        "\n".join(str(seed.value) for seed in CONFIRMATORY_SEED_COHORT.values) + "\n",
    )


def run_campaign(*, overwrite: OverwriteMode) -> CampaignRunResult:
    from datp_core.app.programme import preprocess_datasets, validate_programme

    validate_programme(None)
    preprocess_datasets(None, overwrite=OverwriteMode.KEEP_EXISTING)
    reproduced = reproduce_anchor(overwrite=overwrite, mode=ProgrammeExecutionMode.FULL)
    verified = verify_anchor_programme(mode=ProgrammeExecutionMode.FULL)
    for result in (reproduced, verified):
        if result.gate_status not in {AnchorGateStatus.PASS, AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY}:
            raise MissingPrerequisiteError(
                f"campaign blocked by anchor gate: {result.gate_status.value}",
                subject=ExperimentId.HISTORICAL_DATP_REPRODUCTION,
                reason="anchor_gate",
            )
    _run_centralized_reference(overwrite)
    results = tuple(
        run_experiment(
            recipe.experiment,
            overwrite=overwrite,
            mode=ProgrammeExecutionMode.FULL,
        )
        for recipe in EXPERIMENT_RECIPES
    )
    CAMPAIGN_COMPLETION_MARKER.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomically(
        CAMPAIGN_COMPLETION_MARKER,
        "\n".join(item.experiment.value for item in results) + "\n",
    )
    report = generate_report(None, overwrite=overwrite)
    return CampaignRunResult(
        experiments=results,
        detail=DetailText(f"campaign experiments={len(results)} report={report.detail}"),
        anchor_failure=None,
    )


def generate_report(
    experiment_id: ExperimentId | None,
    *,
    overwrite: OverwriteMode,
) -> ReportResult:
    if experiment_id is None:
        return _generate_campaign_report(overwrite)
    recipe = recipe_for(experiment_id)
    paths, detail = recipe.report(experiment_id, overwrite)
    return ReportResult(experiment=experiment_id, paths=paths, detail=detail)


def _generate_campaign_report(overwrite: OverwriteMode) -> ReportResult:
    paths: list[Path] = []
    details: list[str] = []
    for recipe in EXPERIMENT_RECIPES:
        try:
            report = generate_report(recipe.experiment, overwrite=overwrite)
        except (AnchorReproductionError, MissingPrerequisiteError, ReportEvidenceError, ScientificContractError) as error:
            details.append(f"{recipe.experiment.value}:missing({error})")
            continue
        paths.extend(report.paths)
        details.append(f"{recipe.experiment.value}:ok")
    return ReportResult(
        experiment=None,
        paths=tuple(paths),
        detail=DetailText(";".join(details) if details else "no reportable experiment evidence"),
    )


def programme_status(experiment_id: ExperimentId | None) -> ProgrammeStatusReport:
    from datp_core.app.programme import reject_anchor_as_experiment, require_experiment_declaration
    from datp_core.protocols.validation import CANONICAL_PROTOCOL_GRAPH, validate_protocol_graph

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
            ArtifactPresence.PRESENT if CAMPAIGN_COMPLETION_MARKER.is_file() else ArtifactPresence.ABSENT
        ),
    )


def _status_for_experiment(
    experiment_id: ExperimentId,
    anchor_gate: AnchorGateStatus,
) -> ExperimentStatusRecord:
    from datp_core.app.programme import require_experiment_declaration

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
    if not (canonical / ResearchArtifact.COMPLETE).is_file():
        return ExperimentStatusRecord(
            experiment=experiment_id,
            status=ProgrammeStatus.NOT_STARTED,
            role=declaration.role,
            readiness=declaration.readiness,
            registration=RecipeRegistration.REGISTERED,
            detail=DetailText("canonical dataset incomplete"),
        )
    if recipe.analysis_marker(experiment_id):
        return ExperimentStatusRecord(
            experiment=experiment_id,
            status=ProgrammeStatus.ANALYSIS_COMPLETE,
            role=declaration.role,
            readiness=declaration.readiness,
            registration=RecipeRegistration.REGISTERED,
            detail=DetailText("analysis or report artifacts present"),
        )
    return ExperimentStatusRecord(
        experiment=experiment_id,
        status=ProgrammeStatus.DATASET_READY,
        role=declaration.role,
        readiness=declaration.readiness,
        registration=RecipeRegistration.REGISTERED,
        detail=DetailText("registered recipe ready for execution"),
    )


def format_status(report: ProgrammeStatusReport) -> str:
    lines = [
        f"anchor_gate={report.anchor_gate.value}",
        f"campaign_completion={report.campaign_completion.value}",
    ]
    lines.extend(
        f"{record.experiment.value} status={record.status.value} role={record.role.value} "
        f"readiness={record.readiness.value} registration={record.registration.value} detail={record.detail}"
        for record in report.records
    )
    return "\n".join(lines)

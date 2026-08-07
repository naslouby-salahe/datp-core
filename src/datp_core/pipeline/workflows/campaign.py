"""Campaign dispatch, smoke isolation, anchor commands, reporting, and status derivation.

Generic protocol validation, planning, and seed-cohort selection live in
:mod:`datp_core.pipeline.workflows` (the package root); this module owns the
downstream orchestration built on top of it: running one or every registered
experiment, the independent anchor-reproduction commands, report generation
from completed evidence, and programme status derivation for the CLI.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from typing import TYPE_CHECKING

from datp_core.anchor.gate import AnchorGateStatus, load_anchor_gate_decision
from datp_core.datasets.paths import canonical_root_under
from datp_core.domain.enums import (
    DatasetId,
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    PopulationId,
    ProgrammeStatus,
)
from datp_core.domain.errors import (
    AnchorReproductionError,
    MissingPrerequisiteError,
    ReportEvidenceError,
    ScientificContractError,
)
from datp_core.domain.values.counts import Seed
from datp_core.protocols.anchor import ANCHOR_DECISION_PROTOCOL, HISTORICAL_ANCHOR_SEED_COHORT
from datp_core.protocols.populations import POPULATIONS
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.protocols.training import DITTO_PRIMARY_REGULARIZATION, FEDPROX_COEFFICIENTS
from datp_core.protocols.validation import CANONICAL_PROTOCOL_GRAPH, validate_protocol_graph
from datp_core.runtime.configuration import DATA_ROOT, OUTPUTS_ROOT

if TYPE_CHECKING:
    from datp_core.pipeline.workflows import PlanPresentation

SMOKE_OUTPUT_ROOT = OUTPUTS_ROOT / "smoke"
ANCHOR_DIAGNOSTICS_DIRECTORY = OUTPUTS_ROOT / "anchor" / "diagnostics"
CAMPAIGN_COMPLETION_MARKER = OUTPUTS_ROOT / "campaign" / "COMPLETE"
SMOKE_SUMMARY_DIRECTORY = SMOKE_OUTPUT_ROOT / "summary"

_CAMPAIGN_ORDER: tuple[ExperimentId, ...] = (
    ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
    ExperimentId.FAMILY_AND_GROUPED_GRANULARITY,
    ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
    ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
    ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
    ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
    ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentRunResult:
    experiment: ExperimentId
    seeds: tuple[int, ...]
    smoke: bool
    output_root: Path
    detail: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CampaignRunResult:
    experiments: tuple[ExperimentRunResult, ...]
    detail: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportResult:
    experiment: ExperimentId | None
    paths: tuple[Path, ...]
    detail: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentStatusRecord:
    experiment: ExperimentId
    status: ProgrammeStatus
    role: EvidenceRole
    readiness: ExperimentReadiness
    registered_workflow: bool
    detail: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ProgrammeStatusReport:
    records: tuple[ExperimentStatusRecord, ...]
    anchor_gate: str
    campaign_complete: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class AnchorCommandResult:
    gate_status: str
    dependent_readiness: str
    detail: str


def canonical_smoke_seed(experiment_id: ExperimentId) -> Seed:
    """Typed smoke seed rule: first declared cohort member in deterministic order."""
    from datp_core.pipeline.workflows import seed_cohort_for

    cohort = seed_cohort_for(experiment_id)
    return cohort.values[0]


def _require_registered_workflow(experiment_id: ExperimentId) -> None:
    from datp_core.pipeline.workflows import (
        REGISTERED_WORKFLOW_EXPERIMENTS,
        reject_anchor_as_experiment,
        require_experiment_declaration,
    )

    reject_anchor_as_experiment(experiment_id)
    require_experiment_declaration(experiment_id)
    if experiment_id not in REGISTERED_WORKFLOW_EXPERIMENTS:
        raise ScientificContractError(
            f"no registered complete workflow for experiment {experiment_id.value}",
            subject=experiment_id,
        )


def _anchor_gate_permits_dependents() -> bool:
    try:
        decision = load_anchor_gate_decision(ANCHOR_DIAGNOSTICS_DIRECTORY)
    except AnchorReproductionError:
        return False
    return decision.status in {AnchorGateStatus.PASS, AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY}


def _enforce_anchor_gate(experiment_id: ExperimentId) -> None:
    from datp_core.pipeline.workflows import ANCHOR_GATED_EXPERIMENTS

    if experiment_id not in ANCHOR_GATED_EXPERIMENTS:
        return
    if not _anchor_gate_permits_dependents():
        raise MissingPrerequisiteError(
            f"experiment {experiment_id.value} is blocked by the anchor equivalence gate",
            subject=experiment_id,
            reason="anchor_gate",
        )


def _output_root(*, smoke: bool) -> Path:
    return SMOKE_OUTPUT_ROOT if smoke else OUTPUTS_ROOT


def run_experiment(
    experiment_id: ExperimentId,
    *,
    overwrite: bool = False,
    smoke: bool = False,
) -> ExperimentRunResult:
    from datp_core.pipeline.workflows import reject_anchor_as_experiment, seed_cohort_for

    reject_anchor_as_experiment(experiment_id)
    _require_registered_workflow(experiment_id)
    if not smoke:
        _enforce_anchor_gate(experiment_id)
    output_root = _output_root(smoke=smoke)
    if overwrite and smoke and output_root.exists():
        scoped = output_root / experiment_id.value
        if scoped.exists():
            rmtree(scoped)
    cohort = seed_cohort_for(experiment_id)
    seeds = (canonical_smoke_seed(experiment_id),) if smoke else cohort.values
    seed_values = tuple(seed.value for seed in seeds)
    detail = _dispatch_experiment(
        experiment_id,
        seeds=seeds,
        output_root=output_root,
        overwrite=overwrite,
    )
    return ExperimentRunResult(
        experiment=experiment_id,
        seeds=seed_values,
        smoke=smoke,
        output_root=output_root,
        detail=detail,
    )


def _dispatch_experiment(
    experiment_id: ExperimentId,
    *,
    seeds: tuple[Seed, ...],
    output_root: Path,
    overwrite: bool,
) -> str:
    from datp_core.pipeline.workflows.confirmatory import (
        run_confirmatory_seed,
        run_family_grouped_mechanism_seed,
    )
    from datp_core.pipeline.workflows.external import (
        run_ciciot_boundary_seed,
        run_external_validation_seed,
    )
    from datp_core.pipeline.workflows.personalization import (
        run_ditto_stress_test_seed,
        run_fedprox_stress_test_seed,
    )
    from datp_core.pipeline.workflows.temporal import run_temporal_seed

    detail: str
    match experiment_id:
        case ExperimentId.SHARED_VS_LOCAL_CONFIRMATION:
            for seed in seeds:
                run_confirmatory_seed(seed, output_root=output_root, overwrite=overwrite)
            detail = f"confirmatory seeds={len(seeds)}"
        case ExperimentId.FAMILY_AND_GROUPED_GRANULARITY:
            for seed in seeds:
                run_family_grouped_mechanism_seed(seed, output_root=output_root, overwrite=overwrite)
            detail = f"family_grouped seeds={len(seeds)}"
        case ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION:
            for seed in seeds:
                run_external_validation_seed(seed)
            detail = f"edge_benign_equity seeds={len(seeds)}"
        case ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY:
            for seed in seeds:
                run_ciciot_boundary_seed(seed)
            detail = f"ciciot_boundary seeds={len(seeds)}"
        case ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST:
            for seed in seeds:
                for coefficient in FEDPROX_COEFFICIENTS:
                    run_fedprox_stress_test_seed(
                        training_seed=seed,
                        coefficient=coefficient,
                        output_root=output_root,
                        overwrite=overwrite,
                    )
            detail = f"fedprox seeds={len(seeds)} coefficients={len(FEDPROX_COEFFICIENTS)}"
        case ExperimentId.DITTO_ABSORPTION_STRESS_TEST:
            for seed in seeds:
                run_ditto_stress_test_seed(
                    training_seed=seed,
                    regularization=DITTO_PRIMARY_REGULARIZATION,
                )
            detail = f"ditto seeds={len(seeds)} regularization={DITTO_PRIMARY_REGULARIZATION.value}"
        case ExperimentId.EDGE_ONE_SHOT_RECALIBRATION:
            for seed in seeds:
                run_temporal_seed(seed)
            detail = f"temporal seeds={len(seeds)}"
        case _:
            raise ScientificContractError(
                f"no registered complete workflow for experiment {experiment_id.value}",
                subject=experiment_id,
            )
    return detail


def run_smoke(experiment_id: ExperimentId | None = None, *, overwrite: bool = False) -> CampaignRunResult:
    from datp_core.pipeline.workflows import reject_anchor_as_experiment

    if experiment_id is not None:
        reject_anchor_as_experiment(experiment_id)
    if overwrite and SMOKE_OUTPUT_ROOT.exists():
        if experiment_id is None:
            rmtree(SMOKE_OUTPUT_ROOT)
        else:
            scoped = SMOKE_OUTPUT_ROOT / experiment_id.value
            if scoped.exists():
                rmtree(scoped)
    if experiment_id is not None:
        result = run_experiment(experiment_id, overwrite=overwrite, smoke=True)
        _publish_smoke_summary((result,))
        return CampaignRunResult(experiments=(result,), detail="smoke single experiment")
    results: list[ExperimentRunResult] = []
    try:
        reproduce_anchor(overwrite=overwrite, smoke=True)
        verify_anchor_programme(smoke=True)
    except (AnchorReproductionError, ScientificContractError, MissingPrerequisiteError) as error:
        # Smoke still exercises journal workflows when the independent anchor path is blocked.
        _ = error
    for item in _CAMPAIGN_ORDER:
        results.append(run_experiment(item, overwrite=overwrite, smoke=True))
    _publish_smoke_summary(tuple(results))
    return CampaignRunResult(experiments=tuple(results), detail=f"smoke experiments={len(results)}")


def _publish_smoke_summary(results: tuple[ExperimentRunResult, ...]) -> None:
    SMOKE_SUMMARY_DIRECTORY.mkdir(parents=True, exist_ok=True)
    lines = [
        "smoke_summary",
        *[f"{item.experiment.value}:seeds={','.join(str(seed) for seed in item.seeds)}" for item in results],
    ]
    (SMOKE_SUMMARY_DIRECTORY / "COMPLETE").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_campaign(*, overwrite: bool = False) -> CampaignRunResult:
    from datp_core.pipeline.workflows import preprocess_datasets, validate_programme

    validate_programme()
    preprocess_datasets(overwrite=False)
    reproduce_anchor(overwrite=overwrite)
    verify_anchor_programme()
    results: list[ExperimentRunResult] = []
    for experiment_id in _CAMPAIGN_ORDER:
        results.append(run_experiment(experiment_id, overwrite=overwrite, smoke=False))
        generate_report(experiment_id, overwrite=overwrite)
    CAMPAIGN_COMPLETION_MARKER.parent.mkdir(parents=True, exist_ok=True)
    CAMPAIGN_COMPLETION_MARKER.write_text(
        "\n".join(item.experiment.value for item in results) + "\n",
        encoding="utf-8",
    )
    campaign_report = generate_report(None, overwrite=overwrite)
    return CampaignRunResult(
        experiments=tuple(results),
        detail=f"campaign experiments={len(results)} report={campaign_report.detail}",
    )


def reproduce_anchor(*, overwrite: bool = False, smoke: bool = False) -> AnchorCommandResult:
    """Run independent anchor reproduction for the declared historical seed cohort.

    Executes HISTORICAL_DATP_REPRODUCTION for the locked five-seed cohort (or one
    smoke seed), publishes independent observations from completed evaluations, and
    applies the equivalence gate against locked historical references.
    """
    from datp_core.pipeline.workflows import preprocess_datasets, require_experiment_declaration
    from datp_core.pipeline.workflows.anchor import (
        VerifyAnchorStageRequest,
        clear_independent_package,
        collect_independent_observations_from_evaluations,
        default_anchor_diagnostics_directory,
        independent_package_directory,
        publish_independent_observations,
        verify_anchor,
    )
    from datp_core.pipeline.workflows.execution import execute_declared_experiment_seed

    output_root = SMOKE_OUTPUT_ROOT if smoke else OUTPUTS_ROOT
    diagnostics = default_anchor_diagnostics_directory(output_root)
    package_directory = independent_package_directory(output_root)
    if overwrite:
        if diagnostics.exists():
            rmtree(diagnostics)
        clear_independent_package(package_directory)
    preprocess_datasets(DatasetId.NBAIOT, overwrite=False)
    seed_cohort = (
        SeedCohort(values=(HISTORICAL_ANCHOR_SEED_COHORT.values[0],)) if smoke else HISTORICAL_ANCHOR_SEED_COHORT
    )
    declaration = require_experiment_declaration(ExperimentId.HISTORICAL_DATP_REPRODUCTION)
    execute_declared_experiment_seed(
        declaration=declaration,
        seed_cohort=seed_cohort,
        reason="independent anchor reproduction supplies locked historical-seed execution prerequisites",
        output_root=output_root,
        overwrite=overwrite,
    )
    try:
        observations = collect_independent_observations_from_evaluations(
            output_root=output_root,
            seed_cohort=seed_cohort,
        )
        if observations:
            publish_independent_observations(package_directory, observations)
        result = verify_anchor(
            VerifyAnchorStageRequest(
                protocol=ANCHOR_DECISION_PROTOCOL,
                diagnostics_directory=diagnostics,
                independent_package_directory=package_directory,
                request_independent_reproduction=True,
            )
        )
    except AnchorReproductionError as error:
        return AnchorCommandResult(
            gate_status=AnchorGateStatus.BLOCKED.value,
            dependent_readiness=ExperimentReadiness.BLOCKED.value,
            detail=str(error),
        )
    return AnchorCommandResult(
        gate_status=result.status.gate_status.value,
        dependent_readiness=result.status.dependent_readiness.value,
        detail=(
            f"seeds={seed_cohort.member_count.value} observations={result.status.observation_count.value} smoke={smoke}"
        ),
    )


def verify_anchor_programme(*, smoke: bool = False) -> AnchorCommandResult:
    """Verify the independent package against locked references without re-running training."""
    from datp_core.pipeline.workflows.anchor import (
        VerifyAnchorStageRequest,
        default_anchor_diagnostics_directory,
        independent_package_directory,
        verify_anchor,
    )

    output_root = SMOKE_OUTPUT_ROOT if smoke else OUTPUTS_ROOT
    diagnostics = default_anchor_diagnostics_directory(output_root)
    package_directory = independent_package_directory(output_root)
    result = verify_anchor(
        VerifyAnchorStageRequest(
            protocol=ANCHOR_DECISION_PROTOCOL,
            diagnostics_directory=diagnostics,
            independent_package_directory=package_directory,
            request_independent_reproduction=True,
        )
    )
    return AnchorCommandResult(
        gate_status=result.status.gate_status.value,
        dependent_readiness=result.status.dependent_readiness.value,
        detail=(
            f"observations={result.status.observation_count.value} "
            f"discrepancies={result.status.discrepancy_count.value}"
        ),
    )


def anchor_status() -> AnchorCommandResult:
    diagnostics = ANCHOR_DIAGNOSTICS_DIRECTORY
    try:
        decision = load_anchor_gate_decision(diagnostics)
    except AnchorReproductionError as error:
        return AnchorCommandResult(
            gate_status=AnchorGateStatus.BLOCKED.value,
            dependent_readiness=ExperimentReadiness.BLOCKED.value,
            detail=str(error),
        )
    blocker = (
        None if decision.reproduction.dependency_blocker is None else decision.reproduction.dependency_blocker.detail
    )
    unblocked = decision.status in {AnchorGateStatus.PASS, AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY}
    return AnchorCommandResult(
        gate_status=decision.status.value,
        dependent_readiness=decision.dependent_readiness.value,
        detail=(
            f"discrepancies={len(decision.reproduction.discrepancies)} "
            f"blocker={blocker} dependents_unblocked={unblocked}"
        ),
    )


def generate_report(experiment_id: ExperimentId | None = None, *, overwrite: bool = False) -> ReportResult:
    """Generate report packages from existing validated evidence only (no training)."""
    from datp_core.pipeline.workflows import reject_anchor_as_experiment, require_experiment_declaration

    if experiment_id is None:
        return _generate_campaign_report(overwrite=overwrite)
    reject_anchor_as_experiment(experiment_id)
    require_experiment_declaration(experiment_id)
    return _generate_experiment_report(experiment_id, overwrite=overwrite)


def _generate_campaign_report(*, overwrite: bool) -> ReportResult:
    paths: list[Path] = []
    details: list[str] = []
    for item in _CAMPAIGN_ORDER:
        try:
            report = generate_report(item, overwrite=overwrite)
        except (ReportEvidenceError, ScientificContractError, MissingPrerequisiteError) as error:
            details.append(f"{item.value}:missing({error})")
            continue
        paths.extend(report.paths)
        details.append(f"{item.value}:ok")
    return ReportResult(experiment=None, paths=tuple(paths), detail=";".join(details))


def _generate_experiment_report(experiment_id: ExperimentId, *, overwrite: bool) -> ReportResult:
    from datp_core.pipeline.workflows.confirmatory import analyze_confirmatory_campaign
    from datp_core.pipeline.workflows.external import (
        analyze_ciciot_boundary_campaign,
        analyze_external_validation_campaign,
    )

    paths: tuple[Path, ...]
    detail: str
    match experiment_id:
        case ExperimentId.SHARED_VS_LOCAL_CONFIRMATION | ExperimentId.FAMILY_AND_GROUPED_GRANULARITY:
            path = analyze_confirmatory_campaign()
            paths = (path,)
            if experiment_id is ExperimentId.SHARED_VS_LOCAL_CONFIRMATION:
                detail = str(path)
            else:
                detail = f"mechanism_via_confirmatory:{path}"
        case ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION:
            result = analyze_external_validation_campaign()
            paths = (result.output_directory,)
            detail = str(result.output_directory)
        case ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY:
            result = analyze_ciciot_boundary_campaign()
            paths = (result.output_directory,)
            detail = str(result.output_directory)
        case ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST:
            paths = _report_fedprox_absorption(overwrite=overwrite)
            detail = f"coefficients={len(paths)}"
        case ExperimentId.DITTO_ABSORPTION_STRESS_TEST:
            analysis_root = (
                OUTPUTS_ROOT
                / "ditto_stress_test"
                / PopulationId.NBAIOT_NATURAL_DEVICES.value
                / "analysis"
                / str(DITTO_PRIMARY_REGULARIZATION.value)
            )
            if not analysis_root.exists():
                raise ReportEvidenceError(
                    "ditto absorption analysis artifacts are missing; run the experiment before reporting",
                    subject=experiment_id,
                )
            paths = (analysis_root,)
            detail = f"reuse_existing_analysis={analysis_root}"
        case ExperimentId.EDGE_ONE_SHOT_RECALIBRATION:
            analysis_root = OUTPUTS_ROOT / "temporal"
            if not analysis_root.exists():
                raise ReportEvidenceError(
                    "temporal analysis artifacts are missing; run the experiment before reporting",
                    subject=experiment_id,
                )
            paths = (analysis_root,)
            detail = f"reuse_existing_analysis={analysis_root}"
        case _:
            raise ReportEvidenceError(
                f"no report package is declared for experiment {experiment_id.value}",
                subject=experiment_id,
            )
    return ReportResult(experiment=experiment_id, paths=paths, detail=detail)


def _report_fedprox_absorption(*, overwrite: bool) -> tuple[Path, ...]:
    from datp_core.pipeline.workflows.confirmatory import load_fedavg_cv_fpr_effect
    from datp_core.pipeline.workflows.personalization import (
        analyze_fedprox_absorption,
        build_fedprox_absorption_observation,
        select_primary_fedprox_coefficient_from_artifacts,
        write_fedprox_primary_coefficient_decision,
    )

    paths: list[Path] = []
    try:
        primary = select_primary_fedprox_coefficient_from_artifacts(output_root=OUTPUTS_ROOT)
        root = OUTPUTS_ROOT / "fedprox_stress_test" / PopulationId.NBAIOT_NATURAL_DEVICES.value
        decision_path = write_fedprox_primary_coefficient_decision(
            primary,
            root / "primary_coefficient_decision.json",
        )
        paths.append(decision_path)
        for coefficient in FEDPROX_COEFFICIENTS:
            observations = tuple(
                build_fedprox_absorption_observation(
                    training_seed=seed,
                    coefficient=coefficient,
                    reference=load_fedavg_cv_fpr_effect(
                        seed,
                        experiment=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
                    ),
                )
                for seed in CONFIRMATORY_SEED_COHORT.values
            )
            role = "primary" if coefficient == primary.primary_coefficient else "sensitivity"
            output = root / "analysis" / role / str(coefficient.value)
            if overwrite and output.exists():
                rmtree(output)
            analyze_fedprox_absorption(observations, output_directory=output)
            paths.append(output)
    except ScientificContractError as error:
        raise ReportEvidenceError(
            str(error),
            subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        ) from error
    return tuple(paths)


def programme_status(experiment_id: ExperimentId | None = None) -> ProgrammeStatusReport:
    from datp_core.pipeline.workflows import reject_anchor_as_experiment, require_experiment_declaration

    graph = validate_protocol_graph(CANONICAL_PROTOCOL_GRAPH)
    target_ids = (
        tuple(item.id for item in graph.experiments if item.id is not ExperimentId.HISTORICAL_DATP_REPRODUCTION)
        if experiment_id is None
        else (experiment_id,)
    )
    if experiment_id is not None:
        reject_anchor_as_experiment(experiment_id)
        require_experiment_declaration(experiment_id)
    anchor = anchor_status()
    records = tuple(_status_for_experiment(item, anchor_gate=anchor.gate_status) for item in target_ids)
    return ProgrammeStatusReport(
        records=records,
        anchor_gate=anchor.gate_status,
        campaign_complete=CAMPAIGN_COMPLETION_MARKER.is_file(),
    )


def _status_for_experiment(experiment_id: ExperimentId, *, anchor_gate: str) -> ExperimentStatusRecord:
    from datp_core.pipeline.workflows import (
        ANCHOR_GATED_EXPERIMENTS,
        REGISTERED_WORKFLOW_EXPERIMENTS,
        require_experiment_declaration,
    )

    declaration = require_experiment_declaration(experiment_id)
    registered = experiment_id in REGISTERED_WORKFLOW_EXPERIMENTS
    if declaration.readiness is ExperimentReadiness.SUPPRESSED:
        return ExperimentStatusRecord(
            experiment=experiment_id,
            status=ProgrammeStatus.BLOCKED_BY_DEPENDENCY,
            role=declaration.role,
            readiness=declaration.readiness,
            registered_workflow=registered,
            detail="suppressed",
        )
    if experiment_id in ANCHOR_GATED_EXPERIMENTS and anchor_gate not in {
        AnchorGateStatus.PASS.value,
        AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY.value,
    }:
        return ExperimentStatusRecord(
            experiment=experiment_id,
            status=ProgrammeStatus.BLOCKED_BY_ANCHOR,
            role=declaration.role,
            readiness=declaration.readiness,
            registered_workflow=registered,
            detail=f"anchor_gate={anchor_gate}",
        )
    population = next(item for item in POPULATIONS if item.id is declaration.population)
    canonical = canonical_root_under(DATA_ROOT, population.dataset)
    if not (canonical / "COMPLETE").is_file():
        return ExperimentStatusRecord(
            experiment=experiment_id,
            status=ProgrammeStatus.NOT_STARTED,
            role=declaration.role,
            readiness=declaration.readiness,
            registered_workflow=registered,
            detail="canonical dataset incomplete",
        )
    if not registered:
        return ExperimentStatusRecord(
            experiment=experiment_id,
            status=ProgrammeStatus.DATASET_READY,
            role=declaration.role,
            readiness=declaration.readiness,
            registered_workflow=False,
            detail="declared without registered complete workflow",
        )
    analysis_complete = _analysis_marker_present(experiment_id)
    if analysis_complete:
        return ExperimentStatusRecord(
            experiment=experiment_id,
            status=ProgrammeStatus.ANALYSIS_COMPLETE,
            role=declaration.role,
            readiness=declaration.readiness,
            registered_workflow=True,
            detail="analysis artifacts present",
        )
    return ExperimentStatusRecord(
        experiment=experiment_id,
        status=ProgrammeStatus.DATASET_READY,
        role=declaration.role,
        readiness=declaration.readiness,
        registered_workflow=True,
        detail="registered workflow ready for execution",
    )


def _analysis_marker_present(experiment_id: ExperimentId) -> bool:
    match experiment_id:
        case ExperimentId.SHARED_VS_LOCAL_CONFIRMATION | ExperimentId.FAMILY_AND_GROUPED_GRANULARITY:
            return (
                OUTPUTS_ROOT / "confirmatory" / PopulationId.NBAIOT_NATURAL_DEVICES.value / "analysis" / "COMPLETE"
            ).is_file()
        case ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION:
            return (OUTPUTS_ROOT / "analysis" / experiment_id.value).exists()
        case ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY:
            return (OUTPUTS_ROOT / "analysis" / experiment_id.value).exists()
        case _:
            return False


def format_plan(presentation: PlanPresentation) -> str:
    lines = [
        f"plan_digest={presentation.plan.digest.value}",
        f"entries={len(presentation.plan.entries)}",
        f"executable={len(presentation.plan.executable)}",
        f"experiments={','.join(item.value for item in presentation.experiment_ids)}",
        f"registered={','.join(item.value for item in presentation.registered_workflows)}",
        f"anchor_required={','.join(item.value for item in presentation.anchor_required)}",
    ]
    for experiment_id, seeds in presentation.seed_cohorts:
        lines.append(f"seeds[{experiment_id.value}]={','.join(str(seed) for seed in seeds)}")
    disposition_counts: dict[str, int] = {}
    for entry in presentation.plan.entries:
        disposition_counts[entry.disposition.value] = disposition_counts.get(entry.disposition.value, 0) + 1
    for name, count in sorted(disposition_counts.items()):
        lines.append(f"disposition[{name}]={count}")
    return "\n".join(lines)


def format_status(report: ProgrammeStatusReport) -> str:
    lines = [
        f"anchor_gate={report.anchor_gate}",
        f"campaign_complete={report.campaign_complete}",
    ]
    for record in report.records:
        lines.append(
            f"{record.experiment.value} status={record.status.value} "
            f"role={record.role.value} readiness={record.readiness.value} "
            f"workflow={record.registered_workflow} detail={record.detail}"
        )
    return "\n".join(lines)

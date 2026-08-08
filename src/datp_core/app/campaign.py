"""Application-level campaign orchestration over typed scientific experiment families."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from shutil import rmtree
from typing import TYPE_CHECKING

from datp_core.anchor.gate import load_anchor_gate_decision
from datp_core.anchor.models import AnchorGateStatus
from datp_core.app.planning import PlanDisposition
from datp_core.datasets.paths import canonical_root_under
from datp_core.domain.enums import (
    DatasetId,
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    FedProxRoleDirectory,
    PopulationId,
    ProgrammeStatus,
    ThresholdMethodExecutionStatus,
)
from datp_core.domain.errors import (
    AnchorReproductionError,
    MissingPrerequisiteError,
    ReportEvidenceError,
    ScientificContractError,
)
from datp_core.domain.values.base import NonEmptyString
from datp_core.domain.values.counts import Seed
from datp_core.experiments.confirmatory import (
    ConfirmatoryAssetDirectory,
    analyze_confirmatory_campaign,
    load_fedavg_cv_fpr_effect,
    run_confirmatory_seed,
    run_family_grouped_mechanism_seed,
)
from datp_core.experiments.external import (
    BoundedExternalAssetDirectory,
    analyze_ciciot_boundary_campaign,
    analyze_external_validation_campaign,
    run_ciciot_boundary_seed,
    run_external_validation_seed,
)
from datp_core.experiments.federated_threshold import (
    federated_benign_statistics_comparison_analysis_marker_present,
    federated_quantile_estimation_analysis_marker_present,
    fixed_coefficient_statistics_sensitivity_analysis_marker_present,
    report_federated_benign_statistics_comparison,
    report_federated_quantile_estimation,
    report_fixed_coefficient_statistics_sensitivity,
    run_federated_benign_statistics_comparison_seed,
    run_federated_quantile_estimation_seed,
    run_fixed_coefficient_statistics_sensitivity_seed,
)
from datp_core.experiments.heterogeneity import (
    MechanismAnalysisDirectory,
    analyze_controlled_heterogeneity_sweep,
    analyze_heterogeneity_benefit_association,
    analyze_per_client_score_geometry,
    analyze_threshold_movement_tradeoff,
    run_controlled_heterogeneity_sweep_seed,
)
from datp_core.experiments.threshold_robustness import (
    ThresholdRobustnessSeedResult,
    calibration_size_ablation_analysis_marker_present,
    fixed_shrinkage_curve_analysis_marker_present,
    local_conformal_coverage_analysis_marker_present,
    quantile_sensitivity_analysis_marker_present,
    report_calibration_size_ablation,
    report_fixed_shrinkage_curve,
    report_local_conformal_coverage,
    report_quantile_sensitivity,
    report_shared_construction_sensitivity,
    report_size_aware_shrinkage,
    run_calibration_size_ablation_seed,
    run_fixed_shrinkage_curve_seed,
    run_local_conformal_coverage_seed,
    run_quantile_sensitivity_seed,
    run_shared_construction_sensitivity_seed,
    run_size_aware_shrinkage_seed,
    shared_construction_sensitivity_analysis_marker_present,
    size_aware_shrinkage_analysis_marker_present,
)
from datp_core.pipeline.decision.evidence import AnalysisAssetName
from datp_core.pipeline.execution.layout import ExecutionRootDirectory
from datp_core.presentation.export import MECHANISM_REPORT_FILENAME, PUBLICATION_FILENAME
from datp_core.protocols.anchor import ANCHOR_DECISION_PROTOCOL, HISTORICAL_ANCHOR_SEED_COHORT
from datp_core.protocols.populations import POPULATIONS
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.protocols.training import DITTO_PRIMARY_REGULARIZATION, FEDPROX_COEFFICIENTS
from datp_core.protocols.validation import CANONICAL_PROTOCOL_GRAPH, validate_protocol_graph
from datp_core.runtime.configuration import DATA_ROOT, OUTPUTS_ROOT

if TYPE_CHECKING:
    from datp_core.app.programme import PlanPresentation
    from datp_core.experiments.temporal import TemporalSeedResult


class CampaignPath(StrEnum):
    SMOKE = "smoke"
    SUMMARY = "summary"
    ANCHOR = "anchor"
    DIAGNOSTICS = "diagnostics"
    CAMPAIGN = "campaign"
    CENTRALIZED_REFERENCE = "centralized_reference"
    COMPLETE = "COMPLETE"


class DetailText(NonEmptyString):
    validation_name = "detail text"


SMOKE_OUTPUT_ROOT = OUTPUTS_ROOT / CampaignPath.SMOKE.value
ANCHOR_DIAGNOSTICS_DIRECTORY = OUTPUTS_ROOT / CampaignPath.ANCHOR.value / CampaignPath.DIAGNOSTICS.value
CAMPAIGN_COMPLETION_MARKER = OUTPUTS_ROOT / CampaignPath.CAMPAIGN.value / CampaignPath.COMPLETE.value
SMOKE_SUMMARY_DIRECTORY = SMOKE_OUTPUT_ROOT / CampaignPath.SUMMARY.value
CENTRALIZED_REFERENCE_COMPLETION_MARKER = (
    OUTPUTS_ROOT / CampaignPath.CENTRALIZED_REFERENCE.value / CampaignPath.COMPLETE.value
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdMethodOutcome:
    method: FederatedThresholdMethod
    status: ThresholdMethodExecutionStatus
    detail: DetailText


@dataclass(frozen=True, slots=True, kw_only=True)
class DispatchOutcome:
    detail: DetailText
    method_outcomes: tuple[ThresholdMethodOutcome, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentRunResult:
    experiment: ExperimentId
    seeds: tuple[Seed, ...]
    smoke: bool
    output_root: Path
    detail: DetailText
    method_outcomes: tuple[ThresholdMethodOutcome, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class CampaignRunResult:
    experiments: tuple[ExperimentRunResult, ...]
    detail: DetailText
    anchor_failure: DetailText | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportResult:
    experiment: ExperimentId | None
    paths: tuple[Path, ...]
    detail: DetailText


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentStatusRecord:
    experiment: ExperimentId
    status: ProgrammeStatus
    role: EvidenceRole
    readiness: ExperimentReadiness
    registered_workflow: bool
    detail: DetailText


@dataclass(frozen=True, slots=True, kw_only=True)
class ProgrammeStatusReport:
    records: tuple[ExperimentStatusRecord, ...]
    anchor_gate: AnchorGateStatus
    campaign_complete: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class AnchorCommandResult:
    gate_status: AnchorGateStatus
    dependent_readiness: ExperimentReadiness
    detail: DetailText


type DispatchHandler = Callable[[tuple[Seed, ...], Path, bool], DispatchOutcome]
type ReportHandler = Callable[[ExperimentId, bool], tuple[tuple[Path, ...], DetailText]]
type AnalysisMarker = Callable[[ExperimentId], bool]


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentWorkflow:
    experiment: ExperimentId
    anchor_gated: bool
    dispatch: DispatchHandler
    report: ReportHandler
    analysis_marker: AnalysisMarker


def canonical_smoke_seed(experiment_id: ExperimentId) -> Seed:
    from datp_core.app.programme import seed_cohort_for

    return seed_cohort_for(experiment_id).values[0]


def _require_registered_workflow(experiment_id: ExperimentId) -> ExperimentWorkflow:
    from datp_core.app.programme import reject_anchor_as_experiment, require_experiment_declaration

    reject_anchor_as_experiment(experiment_id)
    require_experiment_declaration(experiment_id)
    matches = tuple(item for item in EXPERIMENT_WORKFLOWS if item.experiment is experiment_id)
    if len(matches) != 1:
        raise ScientificContractError(
            f"experiment must have exactly one registered workflow: {experiment_id.value}",
            subject=experiment_id,
        )
    return matches[0]


def _anchor_gate_permits_dependents() -> bool:
    try:
        decision = load_anchor_gate_decision(ANCHOR_DIAGNOSTICS_DIRECTORY)
    except AnchorReproductionError:
        return False
    return decision.status in {AnchorGateStatus.PASS, AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY}


def _enforce_anchor_gate(workflow: ExperimentWorkflow) -> None:
    if workflow.anchor_gated and not _anchor_gate_permits_dependents():
        raise MissingPrerequisiteError(
            f"experiment {workflow.experiment.value} is blocked by the anchor equivalence gate",
            subject=workflow.experiment,
            reason="anchor_gate",
        )


def _output_root(smoke: bool) -> Path:
    return SMOKE_OUTPUT_ROOT if smoke else OUTPUTS_ROOT


def run_experiment(
    experiment_id: ExperimentId,
    *,
    overwrite: bool,
    smoke: bool,
) -> ExperimentRunResult:
    from datp_core.app.programme import seed_cohort_for

    workflow = _require_registered_workflow(experiment_id)
    if not smoke:
        _enforce_anchor_gate(workflow)
    output_root = _output_root(smoke)
    if overwrite and smoke:
        scoped = output_root / experiment_id.value
        if scoped.exists():
            rmtree(scoped)
    cohort = seed_cohort_for(experiment_id)
    seeds = (canonical_smoke_seed(experiment_id),) if smoke else cohort.values
    outcome = workflow.dispatch(seeds, output_root, overwrite)
    return ExperimentRunResult(
        experiment=experiment_id,
        seeds=seeds,
        smoke=smoke,
        output_root=output_root,
        detail=outcome.detail,
        method_outcomes=outcome.method_outcomes,
    )


def _declared_threshold_methods(experiment_id: ExperimentId) -> tuple[FederatedThresholdMethod, ...]:
    from datp_core.app.programme import require_experiment_declaration

    return require_experiment_declaration(experiment_id).federated_thresholds


def _seed_completion_outcomes(
    *,
    experiment_id: ExperimentId,
    completed_by_seed: tuple[tuple[FederatedThresholdMethod, ...], ...],
) -> tuple[ThresholdMethodOutcome, ...]:
    declared = _declared_threshold_methods(experiment_id)
    completed_across_runs = frozenset(declared)
    for methods in completed_by_seed:
        completed_across_runs = completed_across_runs.intersection(methods)
    run_count = len(completed_by_seed)
    return tuple(
        ThresholdMethodOutcome(
            method=method,
            status=(
                ThresholdMethodExecutionStatus.COMPLETED
                if method in completed_across_runs
                else ThresholdMethodExecutionStatus.INFEASIBLE
            ),
            detail=DetailText(
                f"executed across all {run_count} runs"
                if method in completed_across_runs
                else "declared but not completed in this execution"
            ),
        )
        for method in declared
    )


def _dispatch_confirmatory(seeds: tuple[Seed, ...], output_root: Path, overwrite: bool) -> DispatchOutcome:
    results = tuple(run_confirmatory_seed(seed, output_root=output_root, overwrite=overwrite) for seed in seeds)
    return DispatchOutcome(
        detail=DetailText(f"confirmatory seeds={len(seeds)}"),
        method_outcomes=_seed_completion_outcomes(
            experiment_id=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
            completed_by_seed=tuple(item.completed_threshold_methods for item in results),
        ),
    )


def _dispatch_family_grouped(seeds: tuple[Seed, ...], output_root: Path, overwrite: bool) -> DispatchOutcome:
    results = tuple(
        run_family_grouped_mechanism_seed(seed, output_root=output_root, overwrite=overwrite) for seed in seeds
    )
    return DispatchOutcome(
        detail=DetailText(f"family_grouped seeds={len(seeds)}"),
        method_outcomes=_seed_completion_outcomes(
            experiment_id=ExperimentId.FAMILY_AND_GROUPED_GRANULARITY,
            completed_by_seed=tuple(item.completed_threshold_methods for item in results),
        ),
    )


def _dispatch_external_validation(seeds: tuple[Seed, ...], output_root: Path, overwrite: bool) -> DispatchOutcome:
    results = tuple(
        run_external_validation_seed(seed, output_root=output_root, overwrite=overwrite) for seed in seeds
    )
    return DispatchOutcome(
        detail=DetailText(f"edge_benign_equity seeds={len(seeds)}"),
        method_outcomes=_seed_completion_outcomes(
            experiment_id=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
            completed_by_seed=tuple(item.completed_threshold_methods for item in results),
        ),
    )


def _dispatch_applicability_boundary(seeds: tuple[Seed, ...], output_root: Path, overwrite: bool) -> DispatchOutcome:
    results = tuple(run_ciciot_boundary_seed(seed, output_root=output_root, overwrite=overwrite) for seed in seeds)
    return DispatchOutcome(
        detail=DetailText(f"ciciot_boundary seeds={len(seeds)}"),
        method_outcomes=_seed_completion_outcomes(
            experiment_id=ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
            completed_by_seed=tuple(item.completed_threshold_methods for item in results),
        ),
    )


def _dispatch_fedprox(seeds: tuple[Seed, ...], output_root: Path, overwrite: bool) -> DispatchOutcome:
    from datp_core.experiments.training_stress import run_fedprox_stress_test_seed

    results = tuple(
        run_fedprox_stress_test_seed(
            training_seed=seed,
            coefficient=coefficient,
            output_root=output_root,
            overwrite=overwrite,
        )
        for seed in seeds
        for coefficient in FEDPROX_COEFFICIENTS
    )
    return DispatchOutcome(
        detail=DetailText(
            f"fedprox seeds={len(seeds)} coefficients={len(FEDPROX_COEFFICIENTS)} executions={len(results)}"
        ),
        method_outcomes=_seed_completion_outcomes(
            experiment_id=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
            completed_by_seed=tuple(item.completed_threshold_methods for item in results),
        ),
    )


def _dispatch_ditto(seeds: tuple[Seed, ...], output_root: Path, overwrite: bool) -> DispatchOutcome:
    from datp_core.experiments.training_stress import run_ditto_stress_test_seed

    results = tuple(
        run_ditto_stress_test_seed(
            training_seed=seed,
            regularization=DITTO_PRIMARY_REGULARIZATION,
            output_root=output_root,
            overwrite=overwrite,
        )
        for seed in seeds
    )
    return DispatchOutcome(
        detail=DetailText(
            f"ditto seeds={len(seeds)} regularization={DITTO_PRIMARY_REGULARIZATION.value}"
        ),
        method_outcomes=_seed_completion_outcomes(
            experiment_id=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
            completed_by_seed=tuple(
                (result.shared_threshold.method, result.local_threshold.method) for result in results
            ),
        ),
    )


def _dispatch_temporal(seeds: tuple[Seed, ...], output_root: Path, overwrite: bool) -> DispatchOutcome:
    from datp_core.experiments.temporal import run_temporal_seed

    results = tuple(run_temporal_seed(seed, output_root=output_root, overwrite=overwrite) for seed in seeds)
    return DispatchOutcome(
        detail=DetailText(f"temporal seeds={len(seeds)}"),
        method_outcomes=_temporal_method_outcomes(results),
    )


def _dispatch_threshold_robustness(
    experiment: ExperimentId,
    runner: Callable[..., ThresholdRobustnessSeedResult],
    seeds: tuple[Seed, ...],
    output_root: Path,
    overwrite: bool,
) -> DispatchOutcome:
    results = tuple(runner(seed, output_root=output_root, overwrite=overwrite) for seed in seeds)
    method_outcomes = (
        _size_aware_shrinkage_outcomes(results)
        if experiment is ExperimentId.SIZE_AWARE_SHRINKAGE
        else _seed_completion_outcomes(
            experiment_id=experiment,
            completed_by_seed=tuple(item.completed_threshold_methods for item in results),
        )
    )
    return DispatchOutcome(
        detail=DetailText(f"{experiment.value} seeds={len(seeds)}"),
        method_outcomes=method_outcomes,
    )


def _size_aware_shrinkage_outcomes(
    results: tuple[ThresholdRobustnessSeedResult, ...],
) -> tuple[ThresholdMethodOutcome, ...]:
    declared = _declared_threshold_methods(ExperimentId.SIZE_AWARE_SHRINKAGE)
    completed = frozenset(declared)
    for result in results:
        completed = completed.intersection(result.completed_threshold_methods)
    return tuple(
        ThresholdMethodOutcome(
            method=method,
            status=(
                ThresholdMethodExecutionStatus.UNAVAILABLE
                if method is FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE
                else (
                    ThresholdMethodExecutionStatus.COMPLETED
                    if method in completed
                    else ThresholdMethodExecutionStatus.INFEASIBLE
                )
            ),
            detail=DetailText(
                "no lambda(n_k) function is declared by the roadmap; inventing one is scientifically forbidden"
                if method is FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE
                else (
                    f"executed across all {len(results)} runs"
                    if method in completed
                    else "declared but not completed in this execution"
                )
            ),
        )
        for method in declared
    )


def _dispatch_federated_estimation(
    experiment: ExperimentId,
    runner: Callable[..., object],
    seeds: tuple[Seed, ...],
    output_root: Path,
    overwrite: bool,
) -> DispatchOutcome:
    results = tuple(runner(seed, output_root=output_root, overwrite=overwrite) for seed in seeds)
    completed = tuple(getattr(item, "completed_threshold_methods") for item in results)
    return DispatchOutcome(
        detail=DetailText(f"{experiment.value} seeds={len(seeds)}"),
        method_outcomes=_seed_completion_outcomes(experiment_id=experiment, completed_by_seed=completed),
    )


def _dispatch_controlled_heterogeneity(
    seeds: tuple[Seed, ...], output_root: Path, overwrite: bool
) -> DispatchOutcome:
    results = tuple(
        run_controlled_heterogeneity_sweep_seed(seed, output_root=output_root, overwrite=overwrite) for seed in seeds
    )
    return DispatchOutcome(
        detail=DetailText(f"controlled_heterogeneity_sweep seeds={len(seeds)}"),
        method_outcomes=_seed_completion_outcomes(
            experiment_id=ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
            completed_by_seed=tuple(item.completed_threshold_methods for item in results),
        ),
    )


def _dispatch_analysis_only(experiment: ExperimentId) -> DispatchOutcome:
    return DispatchOutcome(
        detail=DetailText(f"analysis-only experiment {experiment.value} reuses frozen confirmatory scores"),
        method_outcomes=tuple(
            ThresholdMethodOutcome(
                method=method,
                status=ThresholdMethodExecutionStatus.COMPLETED,
                detail=DetailText("analysis-only experiment reuses frozen confirmatory score artifacts"),
            )
            for method in _declared_threshold_methods(experiment)
        ),
    )


def _temporal_method_outcomes(results: tuple[TemporalSeedResult, ...]) -> tuple[ThresholdMethodOutcome, ...]:
    declared = _declared_threshold_methods(ExperimentId.EDGE_ONE_SHOT_RECALIBRATION)
    completed = frozenset(declared)
    for seed_result in results:
        for state in (seed_result.static_reference, seed_result.frozen_future, seed_result.recalibrated_future):
            completed = completed.intersection(state.completed_threshold_methods)
    outcomes: list[ThresholdMethodOutcome] = []
    for method in declared:
        unavailable = next(
            (
                item
                for seed_result in results
                for state in (seed_result.static_reference, seed_result.frozen_future, seed_result.recalibrated_future)
                for item in state.unavailable_methods
                if item.method is method
            ),
            None,
        )
        if method in completed:
            status = ThresholdMethodExecutionStatus.COMPLETED
            detail = DetailText("executed across all temporal states and seeds")
        elif unavailable is not None:
            status = ThresholdMethodExecutionStatus.UNAVAILABLE
            detail = DetailText(f"{unavailable.reason.value}: {unavailable.detail}")
        else:
            status = ThresholdMethodExecutionStatus.INFEASIBLE
            detail = DetailText("declared but not completed in this execution")
        outcomes.append(ThresholdMethodOutcome(method=method, status=status, detail=detail))
    return tuple(outcomes)


def run_smoke(experiment_id: ExperimentId | None, *, overwrite: bool) -> CampaignRunResult:
    from datp_core.app.programme import reject_anchor_as_experiment

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
        return CampaignRunResult(
            experiments=(result,),
            detail=DetailText("smoke single experiment"),
            anchor_failure=None,
        )
    results: list[ExperimentRunResult] = []
    anchor_failure: DetailText | None = None
    try:
        reproduced = reproduce_anchor(overwrite=overwrite, smoke=True)
        verified = verify_anchor_programme(smoke=True)
        non_pass = tuple(
            item.gate_status
            for item in (reproduced, verified)
            if item.gate_status not in {AnchorGateStatus.PASS, AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY}
        )
        if non_pass:
            anchor_failure = DetailText("anchor gate " + ",".join(item.value for item in non_pass))
    except (AnchorReproductionError, ScientificContractError, MissingPrerequisiteError) as error:
        anchor_failure = DetailText(str(error))
    for workflow in EXPERIMENT_WORKFLOWS:
        results.append(run_experiment(workflow.experiment, overwrite=overwrite, smoke=True))
    _publish_smoke_summary(tuple(results))
    return CampaignRunResult(
        experiments=tuple(results),
        detail=DetailText(f"smoke experiments={len(results)}"),
        anchor_failure=anchor_failure,
    )


def _publish_smoke_summary(results: tuple[ExperimentRunResult, ...]) -> None:
    SMOKE_SUMMARY_DIRECTORY.mkdir(parents=True, exist_ok=True)
    lines = (
        "smoke_summary",
        *(f"{item.experiment.value}:seeds={','.join(str(seed.value) for seed in item.seeds)}" for item in results),
    )
    (SMOKE_SUMMARY_DIRECTORY / CampaignPath.COMPLETE.value).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_centralized_reference(*, overwrite: bool) -> None:
    from datp_core.experiments.centralized_reference import centralized_reference_directory, run_centralized_reference_seed

    if CENTRALIZED_REFERENCE_COMPLETION_MARKER.is_file() and not overwrite:
        return
    for seed in CONFIRMATORY_SEED_COHORT.values:
        directory = centralized_reference_directory(seed)
        if overwrite and directory.exists():
            rmtree(directory)
        run_centralized_reference_seed(seed)
    CENTRALIZED_REFERENCE_COMPLETION_MARKER.parent.mkdir(parents=True, exist_ok=True)
    CENTRALIZED_REFERENCE_COMPLETION_MARKER.write_text(
        "\n".join(str(seed.value) for seed in CONFIRMATORY_SEED_COHORT.values) + "\n",
        encoding="utf-8",
    )


def run_campaign(*, overwrite: bool) -> CampaignRunResult:
    from datp_core.app.programme import preprocess_datasets, validate_programme

    validate_programme(None)
    preprocess_datasets(None, overwrite=False)
    reproduce_anchor(overwrite=overwrite, smoke=False)
    verify_anchor_programme(smoke=False)
    _run_centralized_reference(overwrite=overwrite)
    results = tuple(
        run_experiment(workflow.experiment, overwrite=overwrite, smoke=False) for workflow in EXPERIMENT_WORKFLOWS
    )
    CAMPAIGN_COMPLETION_MARKER.parent.mkdir(parents=True, exist_ok=True)
    CAMPAIGN_COMPLETION_MARKER.write_text(
        "\n".join(item.experiment.value for item in results) + "\n",
        encoding="utf-8",
    )
    report = generate_report(None, overwrite=overwrite)
    return CampaignRunResult(
        experiments=results,
        detail=DetailText(f"campaign experiments={len(results)} report={report.detail}"),
        anchor_failure=None,
    )


def reproduce_anchor(*, overwrite: bool, smoke: bool) -> AnchorCommandResult:
    from datp_core.app.programme import preprocess_datasets, require_experiment_declaration
    from datp_core.experiments.anchor import (
        VerifyAnchorStageRequest,
        clear_independent_package,
        collect_independent_observations_from_evaluations,
        default_anchor_diagnostics_directory,
        independent_package_directory,
        publish_independent_observations,
        verify_anchor,
    )
    from datp_core.experiments.execution import execute_declared_experiment_seed

    preprocess_datasets(DatasetId.NBAIOT, overwrite=False)
    output_root = _output_root(smoke)
    diagnostics = default_anchor_diagnostics_directory(output_root)
    package_directory = independent_package_directory(output_root)
    if overwrite:
        if diagnostics.exists():
            rmtree(diagnostics)
        clear_independent_package(package_directory)
    seed_cohort = (
        SeedCohort(values=(HISTORICAL_ANCHOR_SEED_COHORT.values[0],)) if smoke else HISTORICAL_ANCHOR_SEED_COHORT
    )
    execute_declared_experiment_seed(
        declaration=require_experiment_declaration(ExperimentId.HISTORICAL_DATP_REPRODUCTION),
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
            gate_status=AnchorGateStatus.BLOCKED,
            dependent_readiness=ExperimentReadiness.BLOCKED,
            detail=DetailText(str(error)),
        )
    return AnchorCommandResult(
        gate_status=result.status.gate_status,
        dependent_readiness=result.status.dependent_readiness,
        detail=DetailText(
            f"seeds={seed_cohort.member_count.value} observations={result.status.observation_count.value} smoke={smoke}"
        ),
    )


def verify_anchor_programme(*, smoke: bool) -> AnchorCommandResult:
    from datp_core.experiments.anchor import (
        VerifyAnchorStageRequest,
        default_anchor_diagnostics_directory,
        independent_package_directory,
        verify_anchor,
    )

    output_root = _output_root(smoke)
    result = verify_anchor(
        VerifyAnchorStageRequest(
            protocol=ANCHOR_DECISION_PROTOCOL,
            diagnostics_directory=default_anchor_diagnostics_directory(output_root),
            independent_package_directory=independent_package_directory(output_root),
            request_independent_reproduction=True,
        )
    )
    return AnchorCommandResult(
        gate_status=result.status.gate_status,
        dependent_readiness=result.status.dependent_readiness,
        detail=DetailText(
            f"observations={result.status.observation_count.value} discrepancies={result.status.discrepancy_count.value}"
        ),
    )


def anchor_status() -> AnchorCommandResult:
    try:
        decision = load_anchor_gate_decision(ANCHOR_DIAGNOSTICS_DIRECTORY)
    except AnchorReproductionError as error:
        return AnchorCommandResult(
            gate_status=AnchorGateStatus.BLOCKED,
            dependent_readiness=ExperimentReadiness.BLOCKED,
            detail=DetailText(str(error)),
        )
    blocker = (
        None if decision.reproduction.dependency_blocker is None else decision.reproduction.dependency_blocker.detail
    )
    unblocked = decision.status in {AnchorGateStatus.PASS, AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY}
    return AnchorCommandResult(
        gate_status=decision.status,
        dependent_readiness=decision.dependent_readiness,
        detail=DetailText(
            f"discrepancies={len(decision.reproduction.discrepancies)} blocker={blocker} dependents_unblocked={unblocked}"
        ),
    )


def generate_report(experiment_id: ExperimentId | None, *, overwrite: bool) -> ReportResult:
    from datp_core.app.programme import reject_anchor_as_experiment, require_experiment_declaration

    if experiment_id is None:
        return _generate_campaign_report(overwrite)
    reject_anchor_as_experiment(experiment_id)
    require_experiment_declaration(experiment_id)
    workflow = _require_registered_workflow(experiment_id)
    paths, detail = workflow.report(experiment_id, overwrite)
    return ReportResult(experiment=experiment_id, paths=paths, detail=detail)


def _generate_campaign_report(overwrite: bool) -> ReportResult:
    paths: list[Path] = []
    details: list[str] = []
    for workflow in EXPERIMENT_WORKFLOWS:
        try:
            report = generate_report(workflow.experiment, overwrite=overwrite)
        except (AnchorReproductionError, MissingPrerequisiteError, ReportEvidenceError, ScientificContractError) as error:
            details.append(f"{workflow.experiment.value}:missing({error})")
            continue
        paths.extend(report.paths)
        details.append(f"{workflow.experiment.value}:ok")
    return ReportResult(
        experiment=None,
        paths=tuple(paths),
        detail=DetailText(";".join(details) if details else "no reportable experiment evidence"),
    )


def _report_confirmatory(experiment_id: ExperimentId, overwrite: bool) -> tuple[tuple[Path, ...], DetailText]:
    del overwrite
    path = analyze_confirmatory_campaign()
    detail = (
        str(path)
        if experiment_id is ExperimentId.SHARED_VS_LOCAL_CONFIRMATION
        else f"mechanism_via_confirmatory:{path}"
    )
    return (path,), DetailText(detail)


def _report_external(experiment_id: ExperimentId, overwrite: bool) -> tuple[tuple[Path, ...], DetailText]:
    del overwrite
    result = (
        analyze_external_validation_campaign(output_root=OUTPUTS_ROOT)
        if experiment_id is ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION
        else analyze_ciciot_boundary_campaign(output_root=OUTPUTS_ROOT)
    )
    return (result.output_directory,), DetailText(str(result.output_directory))


def _report_heterogeneity(experiment_id: ExperimentId, overwrite: bool) -> tuple[tuple[Path, ...], DetailText]:
    if experiment_id is ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP:
        path = analyze_controlled_heterogeneity_sweep(overwrite=overwrite)
    elif experiment_id is ExperimentId.PER_CLIENT_SCORE_GEOMETRY:
        path = analyze_per_client_score_geometry(overwrite=overwrite)
    elif experiment_id is ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION:
        path = analyze_heterogeneity_benefit_association(overwrite=overwrite)
    elif experiment_id is ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF:
        path = analyze_threshold_movement_tradeoff(overwrite=overwrite)
    else:
        raise ReportEvidenceError(f"unsupported heterogeneity report: {experiment_id.value}", subject=experiment_id)
    return (path,), DetailText(str(path))


def _report_fedprox(experiment_id: ExperimentId, overwrite: bool) -> tuple[tuple[Path, ...], DetailText]:
    del experiment_id
    from datp_core.experiments.training_stress import (
        TrainingStressArtifactName,
        analyze_fedprox_absorption,
        build_fedprox_absorption_observation,
        fedprox_analysis_directory,
        fedprox_stress_test_root,
        select_primary_fedprox_coefficient_from_artifacts,
        write_fedprox_primary_coefficient_decision,
    )

    try:
        primary = select_primary_fedprox_coefficient_from_artifacts(
            output_root=OUTPUTS_ROOT,
            seed_cohort=CONFIRMATORY_SEED_COHORT,
        )
        root = fedprox_stress_test_root(output_root=OUTPUTS_ROOT)
        paths: list[Path] = [
            write_fedprox_primary_coefficient_decision(
                primary,
                root / TrainingStressArtifactName.PRIMARY_COEFFICIENT_DECISION.value,
            )
        ]
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
            output = fedprox_analysis_directory(
                coefficient,
                FedProxRoleDirectory.PRIMARY
                if coefficient == primary.primary_coefficient
                else FedProxRoleDirectory.SENSITIVITY,
                output_root=OUTPUTS_ROOT,
            )
            if overwrite and output.exists():
                rmtree(output)
            analyze_fedprox_absorption(observations, output_directory=output)
            paths.append(output)
    except ScientificContractError as error:
        raise ReportEvidenceError(str(error), subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST) from error
    return tuple(paths), DetailText(f"coefficients={len(paths) - 1}")


def _report_ditto(experiment_id: ExperimentId, overwrite: bool) -> tuple[tuple[Path, ...], DetailText]:
    del experiment_id
    from datp_core.experiments.training_stress import (
        analyze_ditto_absorption,
        ditto_analysis_directory,
        load_ditto_stress_test_evidence,
    )

    analysis_root = ditto_analysis_directory(DITTO_PRIMARY_REGULARIZATION, output_root=OUTPUTS_ROOT)
    if overwrite and analysis_root.exists():
        rmtree(analysis_root)
    results = tuple(
        load_ditto_stress_test_evidence(
            training_seed=seed,
            regularization=DITTO_PRIMARY_REGULARIZATION,
            output_root=OUTPUTS_ROOT,
        )
        for seed in CONFIRMATORY_SEED_COHORT.values
    )
    references = tuple(
        load_fedavg_cv_fpr_effect(
            result.personalized_coordinate.training_seed,
            experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        )
        for result in results
    )
    analyze_ditto_absorption(results, reference_evidence=references, output_directory=analysis_root)
    return (analysis_root,), DetailText(f"analysis={analysis_root}")


def _report_temporal(experiment_id: ExperimentId, overwrite: bool) -> tuple[tuple[Path, ...], DetailText]:
    del experiment_id, overwrite
    from datp_core.experiments.temporal import TemporalCampaignResult, analyze_temporal_campaign, load_temporal_campaign_seeds

    seeds = load_temporal_campaign_seeds(output_root=OUTPUTS_ROOT)
    analyses = analyze_temporal_campaign(TemporalCampaignResult(seeds=seeds), output_root=OUTPUTS_ROOT)
    paths = tuple(item.output_directory for item in analyses)
    return paths, DetailText(f"temporal_methods={len(paths)}")


def _report_threshold_robustness(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> tuple[tuple[Path, ...], DetailText]:
    if experiment_id is ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY:
        paths, detail = report_shared_construction_sensitivity(experiment_id, overwrite)
    elif experiment_id is ExperimentId.QUANTILE_SENSITIVITY:
        paths, detail = report_quantile_sensitivity(experiment_id, overwrite)
    elif experiment_id is ExperimentId.CALIBRATION_SIZE_ABLATION:
        paths, detail = report_calibration_size_ablation(experiment_id, overwrite)
    elif experiment_id is ExperimentId.FIXED_SHRINKAGE_CURVE:
        paths, detail = report_fixed_shrinkage_curve(experiment_id, overwrite)
    elif experiment_id is ExperimentId.SIZE_AWARE_SHRINKAGE:
        paths, detail = report_size_aware_shrinkage(experiment_id, overwrite)
    elif experiment_id is ExperimentId.LOCAL_CONFORMAL_COVERAGE:
        paths, detail = report_local_conformal_coverage(experiment_id, overwrite)
    else:
        raise ReportEvidenceError(f"unsupported threshold robustness report: {experiment_id.value}", subject=experiment_id)
    return paths, DetailText(detail)


def _report_federated_estimation(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> tuple[tuple[Path, ...], DetailText]:
    if experiment_id is ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON:
        paths, detail = report_federated_benign_statistics_comparison(experiment_id, overwrite)
    elif experiment_id is ExperimentId.FEDERATED_QUANTILE_ESTIMATION:
        paths, detail = report_federated_quantile_estimation(experiment_id, overwrite)
    elif experiment_id is ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY:
        paths, detail = report_fixed_coefficient_statistics_sensitivity(experiment_id, overwrite)
    else:
        raise ReportEvidenceError(f"unsupported federated estimation report: {experiment_id.value}", subject=experiment_id)
    return paths, DetailText(detail)


def programme_status(experiment_id: ExperimentId | None) -> ProgrammeStatusReport:
    from datp_core.app.programme import reject_anchor_as_experiment, require_experiment_declaration

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
        campaign_complete=CAMPAIGN_COMPLETION_MARKER.is_file(),
    )


def _status_for_experiment(experiment_id: ExperimentId, anchor_gate: AnchorGateStatus) -> ExperimentStatusRecord:
    from datp_core.app.programme import require_experiment_declaration

    declaration = require_experiment_declaration(experiment_id)
    workflow = next((item for item in EXPERIMENT_WORKFLOWS if item.experiment is experiment_id), None)
    registered = workflow is not None
    if declaration.readiness is ExperimentReadiness.SUPPRESSED:
        return ExperimentStatusRecord(
            experiment=experiment_id,
            status=ProgrammeStatus.BLOCKED_BY_DEPENDENCY,
            role=declaration.role,
            readiness=declaration.readiness,
            registered_workflow=registered,
            detail=DetailText("suppressed"),
        )
    if workflow is not None and workflow.anchor_gated and anchor_gate not in {
        AnchorGateStatus.PASS,
        AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY,
    }:
        return ExperimentStatusRecord(
            experiment=experiment_id,
            status=ProgrammeStatus.BLOCKED_BY_ANCHOR,
            role=declaration.role,
            readiness=declaration.readiness,
            registered_workflow=True,
            detail=DetailText(f"anchor_gate={anchor_gate.value}"),
        )
    population = next(item for item in POPULATIONS if item.id is declaration.population)
    canonical = canonical_root_under(DATA_ROOT, population.dataset)
    if not (canonical / CampaignPath.COMPLETE.value).is_file():
        return ExperimentStatusRecord(
            experiment=experiment_id,
            status=ProgrammeStatus.NOT_STARTED,
            role=declaration.role,
            readiness=declaration.readiness,
            registered_workflow=registered,
            detail=DetailText("canonical dataset incomplete"),
        )
    if workflow is None:
        return ExperimentStatusRecord(
            experiment=experiment_id,
            status=ProgrammeStatus.DATASET_READY,
            role=declaration.role,
            readiness=declaration.readiness,
            registered_workflow=False,
            detail=DetailText("declared without registered workflow"),
        )
    if workflow.analysis_marker(experiment_id):
        return ExperimentStatusRecord(
            experiment=experiment_id,
            status=ProgrammeStatus.ANALYSIS_COMPLETE,
            role=declaration.role,
            readiness=declaration.readiness,
            registered_workflow=True,
            detail=DetailText("analysis artifacts present"),
        )
    return ExperimentStatusRecord(
        experiment=experiment_id,
        status=ProgrammeStatus.DATASET_READY,
        role=declaration.role,
        readiness=declaration.readiness,
        registered_workflow=True,
        detail=DetailText("registered workflow ready for execution"),
    )


def _confirmatory_marker(experiment_id: ExperimentId) -> bool:
    del experiment_id
    return (
        OUTPUTS_ROOT
        / ConfirmatoryAssetDirectory.ROOT.value
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / ConfirmatoryAssetDirectory.ANALYSIS.value
        / AnalysisAssetName.COMPLETE.value
    ).is_file()


def _external_marker(experiment_id: ExperimentId) -> bool:
    from datp_core.app.programme import require_experiment_declaration

    declaration = require_experiment_declaration(experiment_id)
    return (
        OUTPUTS_ROOT
        / BoundedExternalAssetDirectory.ANALYSIS.value
        / experiment_id.value
        / declaration.population.value
        / AnalysisAssetName.COMPLETE.value
    ).is_file()


def _fedprox_marker(experiment_id: ExperimentId) -> bool:
    del experiment_id
    from datp_core.experiments.training_stress import (
        TrainingStressArtifactName,
        fedprox_analysis_directory,
        fedprox_stress_test_root,
        load_fedprox_primary_coefficient_decision,
    )

    decision_path = (
        fedprox_stress_test_root(output_root=OUTPUTS_ROOT)
        / TrainingStressArtifactName.PRIMARY_COEFFICIENT_DECISION.value
    )
    if not decision_path.is_file():
        return False
    decision = load_fedprox_primary_coefficient_decision(decision_path)
    return all(
        (
            fedprox_analysis_directory(
                coefficient,
                FedProxRoleDirectory.PRIMARY
                if coefficient == decision.primary_coefficient
                else FedProxRoleDirectory.SENSITIVITY,
                output_root=OUTPUTS_ROOT,
            )
            / PUBLICATION_FILENAME
        ).is_file()
        for coefficient in FEDPROX_COEFFICIENTS
    )


def _ditto_marker(experiment_id: ExperimentId) -> bool:
    del experiment_id
    from datp_core.experiments.training_stress import ditto_analysis_directory

    root = ditto_analysis_directory(DITTO_PRIMARY_REGULARIZATION, output_root=OUTPUTS_ROOT)
    return (root / PUBLICATION_FILENAME).is_file() and (root / MECHANISM_REPORT_FILENAME).is_file()


def _temporal_marker(experiment_id: ExperimentId) -> bool:
    from datp_core.app.programme import require_experiment_declaration
    from datp_core.experiments.temporal import TemporalArtifactDirectory

    declaration = require_experiment_declaration(experiment_id)
    return all(
        (
            OUTPUTS_ROOT
            / ExecutionRootDirectory.BOUNDED_EVIDENCE.value
            / experiment_id.value
            / declaration.population.value
            / declaration.role.value
            / TemporalArtifactDirectory.ANALYSIS.value
            / method.value
            / AnalysisAssetName.COMPLETE.value
        ).is_file()
        for method in declaration.federated_thresholds
    )


def _heterogeneity_marker(experiment_id: ExperimentId) -> bool:
    population = (
        PopulationId.NBAIOT_DIRICHLET_CLIENTS
        if experiment_id is ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP
        else PopulationId.NBAIOT_NATURAL_DEVICES
    )
    directory = (
        OUTPUTS_ROOT
        / MechanismAnalysisDirectory.ROOT.value
        / experiment_id.value
        / population.value
        / MechanismAnalysisDirectory.ANALYSIS.value
    )
    return (directory / PUBLICATION_FILENAME).is_file() and (directory / MECHANISM_REPORT_FILENAME).is_file()


def _threshold_marker(experiment_id: ExperimentId) -> bool:
    if experiment_id is ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY:
        return shared_construction_sensitivity_analysis_marker_present(experiment_id)
    if experiment_id is ExperimentId.QUANTILE_SENSITIVITY:
        return quantile_sensitivity_analysis_marker_present(experiment_id)
    if experiment_id is ExperimentId.CALIBRATION_SIZE_ABLATION:
        return calibration_size_ablation_analysis_marker_present(experiment_id)
    if experiment_id is ExperimentId.FIXED_SHRINKAGE_CURVE:
        return fixed_shrinkage_curve_analysis_marker_present(experiment_id)
    if experiment_id is ExperimentId.SIZE_AWARE_SHRINKAGE:
        return size_aware_shrinkage_analysis_marker_present(experiment_id)
    if experiment_id is ExperimentId.LOCAL_CONFORMAL_COVERAGE:
        return local_conformal_coverage_analysis_marker_present(experiment_id)
    raise ScientificContractError(f"unknown threshold robustness experiment: {experiment_id.value}")


def _federated_estimation_marker(experiment_id: ExperimentId) -> bool:
    if experiment_id is ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON:
        return federated_benign_statistics_comparison_analysis_marker_present(experiment_id)
    if experiment_id is ExperimentId.FEDERATED_QUANTILE_ESTIMATION:
        return federated_quantile_estimation_analysis_marker_present(experiment_id)
    if experiment_id is ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY:
        return fixed_coefficient_statistics_sensitivity_analysis_marker_present(experiment_id)
    raise ScientificContractError(f"unknown federated threshold-estimation experiment: {experiment_id.value}")


def _threshold_dispatch(
    experiment: ExperimentId,
    runner: Callable[..., ThresholdRobustnessSeedResult],
) -> DispatchHandler:
    return lambda seeds, output_root, overwrite: _dispatch_threshold_robustness(
        experiment,
        runner,
        seeds,
        output_root,
        overwrite,
    )


def _federated_dispatch(experiment: ExperimentId, runner: Callable[..., object]) -> DispatchHandler:
    return lambda seeds, output_root, overwrite: _dispatch_federated_estimation(
        experiment,
        runner,
        seeds,
        output_root,
        overwrite,
    )


def _analysis_dispatch(experiment: ExperimentId) -> DispatchHandler:
    return lambda _seeds, _output_root, _overwrite: _dispatch_analysis_only(experiment)


EXPERIMENT_WORKFLOWS: tuple[ExperimentWorkflow, ...] = (
    ExperimentWorkflow(
        experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        anchor_gated=True,
        dispatch=_dispatch_confirmatory,
        report=_report_confirmatory,
        analysis_marker=_confirmatory_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.FAMILY_AND_GROUPED_GRANULARITY,
        anchor_gated=True,
        dispatch=_dispatch_family_grouped,
        report=_report_confirmatory,
        analysis_marker=_confirmatory_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        anchor_gated=True,
        dispatch=_dispatch_fedprox,
        report=_report_fedprox,
        analysis_marker=_fedprox_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        anchor_gated=True,
        dispatch=_dispatch_ditto,
        report=_report_ditto,
        analysis_marker=_ditto_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON,
        anchor_gated=True,
        dispatch=_federated_dispatch(
            ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON,
            run_federated_benign_statistics_comparison_seed,
        ),
        report=_report_federated_estimation,
        analysis_marker=_federated_estimation_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.FEDERATED_QUANTILE_ESTIMATION,
        anchor_gated=True,
        dispatch=_federated_dispatch(
            ExperimentId.FEDERATED_QUANTILE_ESTIMATION,
            run_federated_quantile_estimation_seed,
        ),
        report=_report_federated_estimation,
        analysis_marker=_federated_estimation_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY,
        anchor_gated=True,
        dispatch=_federated_dispatch(
            ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY,
            run_fixed_coefficient_statistics_sensitivity_seed,
        ),
        report=_report_federated_estimation,
        analysis_marker=_federated_estimation_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        anchor_gated=False,
        dispatch=_dispatch_external_validation,
        report=_report_external,
        analysis_marker=_external_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
        anchor_gated=False,
        dispatch=_dispatch_applicability_boundary,
        report=_report_external,
        analysis_marker=_external_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        anchor_gated=False,
        dispatch=_dispatch_temporal,
        report=_report_temporal,
        analysis_marker=_temporal_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY,
        anchor_gated=True,
        dispatch=_threshold_dispatch(
            ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY,
            run_shared_construction_sensitivity_seed,
        ),
        report=_report_threshold_robustness,
        analysis_marker=_threshold_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.QUANTILE_SENSITIVITY,
        anchor_gated=True,
        dispatch=_threshold_dispatch(ExperimentId.QUANTILE_SENSITIVITY, run_quantile_sensitivity_seed),
        report=_report_threshold_robustness,
        analysis_marker=_threshold_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.CALIBRATION_SIZE_ABLATION,
        anchor_gated=True,
        dispatch=_threshold_dispatch(ExperimentId.CALIBRATION_SIZE_ABLATION, run_calibration_size_ablation_seed),
        report=_report_threshold_robustness,
        analysis_marker=_threshold_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.FIXED_SHRINKAGE_CURVE,
        anchor_gated=True,
        dispatch=_threshold_dispatch(ExperimentId.FIXED_SHRINKAGE_CURVE, run_fixed_shrinkage_curve_seed),
        report=_report_threshold_robustness,
        analysis_marker=_threshold_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.SIZE_AWARE_SHRINKAGE,
        anchor_gated=True,
        dispatch=_threshold_dispatch(ExperimentId.SIZE_AWARE_SHRINKAGE, run_size_aware_shrinkage_seed),
        report=_report_threshold_robustness,
        analysis_marker=_threshold_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.LOCAL_CONFORMAL_COVERAGE,
        anchor_gated=True,
        dispatch=_threshold_dispatch(ExperimentId.LOCAL_CONFORMAL_COVERAGE, run_local_conformal_coverage_seed),
        report=_report_threshold_robustness,
        analysis_marker=_threshold_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
        anchor_gated=True,
        dispatch=_dispatch_controlled_heterogeneity,
        report=_report_heterogeneity,
        analysis_marker=_heterogeneity_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.PER_CLIENT_SCORE_GEOMETRY,
        anchor_gated=True,
        dispatch=_analysis_dispatch(ExperimentId.PER_CLIENT_SCORE_GEOMETRY),
        report=_report_heterogeneity,
        analysis_marker=_heterogeneity_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
        anchor_gated=True,
        dispatch=_analysis_dispatch(ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION),
        report=_report_heterogeneity,
        analysis_marker=_heterogeneity_marker,
    ),
    ExperimentWorkflow(
        experiment=ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF,
        anchor_gated=True,
        dispatch=_analysis_dispatch(ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF),
        report=_report_heterogeneity,
        analysis_marker=_heterogeneity_marker,
    ),
)

REGISTERED_WORKFLOW_EXPERIMENTS = frozenset(item.experiment for item in EXPERIMENT_WORKFLOWS)
ANCHOR_GATED_EXPERIMENTS = frozenset(item.experiment for item in EXPERIMENT_WORKFLOWS if item.anchor_gated)


def _validate_workflow_registry() -> None:
    ordered = tuple(item.experiment for item in EXPERIMENT_WORKFLOWS)
    if len(ordered) != len(frozenset(ordered)):
        raise ScientificContractError("experiment workflow registry contains duplicate experiment identities")


_validate_workflow_registry()


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
        lines.append(f"seeds[{experiment_id.value}]={','.join(str(seed.value) for seed in seeds)}")
    for disposition in PlanDisposition:
        count = sum(1 for entry in presentation.plan.entries if entry.disposition is disposition)
        if count:
            lines.append(f"disposition[{disposition.value}]={count}")
    return "\n".join(lines)


def format_status(report: ProgrammeStatusReport) -> str:
    lines = [
        f"anchor_gate={report.anchor_gate.value}",
        f"campaign_complete={report.campaign_complete}",
    ]
    lines.extend(
        f"{record.experiment.value} status={record.status.value} role={record.role.value} "
        f"readiness={record.readiness.value} workflow={record.registered_workflow} detail={record.detail}"
        for record in report.records
    )
    return "\n".join(lines)

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from typing import Protocol

from datp_core.analysis.evidence import ExperimentMetricResults, MetricObservation
from datp_core.analysis.mechanisms import AbsorptionSeedObservation, MechanismEvidence
from datp_core.analysis.mechanisms.model_alignment import (
    AlignmentReductionOutcome,
    ModelAlignmentMetric,
    ModelAlignmentResult,
    summarize_alignment_activation,
)
from datp_core.analysis.metrics.models import AvailableMetric, metric_by_id
from datp_core.app.contracts import AnchorRequirement, CampaignRole, OverwriteMode
from datp_core.app.layout import ResearchArtifact, ResearchDirectory
from datp_core.app.models import DetailText, DispatchOutcome, ReportResult, ThresholdMethodOutcome
from datp_core.app.planning import (
    PlanDisposition,
    PlanningEvidence,
    PlanReason,
    expand_experiment_plan,
    seed_cohort_for,
)
from datp_core.artifacts.layout import evaluation_run_directory
from datp_core.artifacts.repositories.evaluations import FederatedEvaluationAssetName
from datp_core.core.errors import (
    ErrorMessage,
    ReportEvidenceError,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    FileContentText,
    MetricId,
    PopulationId,
    ThresholdMethodExecutionStatus,
)
from datp_core.core.numeric import MetricValue, ProximalCoefficient, Seed
from datp_core.detector.training.protocols import (
    DITTO_REGULARIZATION_GRID,
    FEDPROX_COEFFICIENTS,
)
from datp_core.experiments.centralized_reference import (
    CIC_CENTRALIZED_REFERENCE,
    NBAIOT_CENTRALIZED_REFERENCE,
    report_centralized_reference,
)
from datp_core.experiments.common.reports import persist_result_document
from datp_core.experiments.common.seeds import BOUNDED_EVIDENCE_SEED_COHORT, CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.experiments.confirmatory.run import (
    analyze_calibration_support_burden,
    analyze_confirmatory_campaign,
    analyze_equity_utility_pareto,
    analyze_malware_family_sensitivity,
    analyze_natural_device_client_impact,
    analyze_physical_family_adequacy,
    load_fedavg_cv_fpr_effect,
    run_confirmatory_seed,
    run_family_grouped_mechanism_seed,
)
from datp_core.experiments.execution import execute_declared_experiment_seed
from datp_core.experiments.execution.evidence import load_evaluation_document
from datp_core.experiments.execution.layout import EvaluationRunAssetDirectory, ExecutionRootDirectory
from datp_core.experiments.execution.models import ProgressHook
from datp_core.experiments.external import (
    analyze_ciciot_boundary_campaign,
    analyze_ciciot_boundary_evidence,
    analyze_external_benign_statistics,
    analyze_external_validation_campaign,
    run_ciciot_boundary_seed,
    run_external_validation_seed,
)
from datp_core.experiments.federated_threshold import (
    FederatedEstimationSeedResult,
    report_federated_benign_statistics_comparison,
    report_federated_quantile_estimation,
    report_fixed_coefficient_statistics_sensitivity,
    run_federated_benign_statistics_comparison_seed,
    run_federated_quantile_estimation_seed,
    run_fixed_coefficient_statistics_sensitivity_seed,
)
from datp_core.experiments.heterogeneity import (
    analyze_controlled_heterogeneity_sweep,
    analyze_heterogeneity_benefit_association,
    analyze_heterogeneity_support_interaction,
    analyze_per_client_score_geometry,
    analyze_threshold_movement_tradeoff,
    run_controlled_heterogeneity_sweep_seed,
)
from datp_core.experiments.registry import ExperimentDeclaration, require_experiment_declaration
from datp_core.experiments.temporal import (
    TemporalCampaignResult,
    TemporalSeedResult,
    analyze_temporal_campaign,
    load_temporal_seed_result,
    run_temporal_seed,
)
from datp_core.experiments.threshold_robustness import (
    ThresholdRobustnessSeedResult,
    report_calibration_cold_start_onboarding,
    report_calibration_size_ablation,
    report_fixed_shrinkage_curve,
    report_local_conformal_coverage,
    report_preprocessing_geometry_sensitivity,
    report_quantile_sensitivity,
    report_shared_calibration_contributor_availability,
    report_shared_construction_sensitivity,
    report_size_aware_shrinkage,
    report_threshold_estimator_scope_sensitivity,
    run_calibration_cold_start_onboarding_seed,
    run_calibration_size_ablation_seed,
    run_fixed_shrinkage_curve_seed,
    run_local_conformal_coverage_seed,
    run_preprocessing_geometry_sensitivity_seed,
    run_quantile_sensitivity_seed,
    run_shared_calibration_contributor_availability_seed,
    run_shared_construction_sensitivity_seed,
    run_size_aware_shrinkage_seed,
    run_threshold_estimator_scope_sensitivity_seed,
)
from datp_core.experiments.training_stress import (
    FedProxAlignmentEvidence,
    FineTuningArtifactBranch,
    analyze_ditto_absorption,
    analyze_fedprox_absorption,
    analyze_fine_tuning_absorption,
    build_fedprox_absorption_observation,
    ditto_analysis_directory,
    fedprox_activation_report,
    fedprox_analysis_directory,
    load_ditto_stress_test_evidence,
    load_fedprox_alignment_evidence,
    load_fine_tuning_stress_test_evidence,
    run_ditto_stress_test_seed,
    run_fedavg_local_fine_tuning_stress_test_seed,
    run_fedprox_stress_test_seed,
)
from datp_core.presentation.export import MechanismPublicationDocument
from datp_core.runtime.configuration import OUTPUTS_ROOT
from datp_core.runtime.filesystem import write_text_atomically


class RobustnessRunner(Protocol):
    def __call__(
        self,
        training_seed: Seed,
        *,
        output_root: Path,
        overwrite: bool,
        progress: ProgressHook | None = None,
    ) -> ThresholdRobustnessSeedResult: ...


class FederatedEstimationRunner(Protocol):
    def __call__(
        self,
        training_seed: Seed,
        *,
        output_root: Path,
        overwrite: bool,
        progress: ProgressHook | None = None,
    ) -> FederatedEstimationSeedResult: ...


class DispatchHandler(Protocol):
    def __call__(
        self,
        seeds: tuple[Seed, ...],
        output_root: Path,
        overwrite: OverwriteMode,
        *,
        progress: ProgressHook | None = None,
    ) -> DispatchOutcome: ...


class ReportHandler(Protocol):
    def __call__(self, experiment_id: ExperimentId) -> ReportResult: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentRecipe:
    experiment: ExperimentId
    anchor_requirement: AnchorRequirement
    campaign_role: CampaignRole
    dispatch: DispatchHandler
    report: ReportHandler


_METHOD_NOT_COMPLETED_DETAIL = "declared but not completed in this execution"

_ANALYSIS_ONLY_EXPERIMENTS = frozenset(
    (
        ExperimentId.PHYSICAL_FAMILY_ADEQUACY,
        ExperimentId.CALIBRATION_SUPPORT_BURDEN,
        ExperimentId.NATURAL_DEVICE_CLIENT_IMPACT,
        ExperimentId.MALWARE_FAMILY_SENSITIVITY,
        ExperimentId.EQUITY_UTILITY_PARETO,
        ExperimentId.PER_CLIENT_SCORE_GEOMETRY,
        ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
        ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF,
    )
)


def _declaration(experiment_id: ExperimentId) -> ExperimentDeclaration:
    return require_experiment_declaration(experiment_id)


def _declared_methods(experiment_id: ExperimentId) -> tuple[FederatedThresholdMethod, ...]:
    return _declaration(experiment_id).federated_thresholds


def _method_outcomes(
    experiment_id: ExperimentId,
    completed_by_run: tuple[tuple[FederatedThresholdMethod, ...], ...],
) -> tuple[ThresholdMethodOutcome, ...]:
    declared = _declared_methods(experiment_id)
    completed = frozenset(declared)
    for methods in completed_by_run:
        completed = completed.intersection(methods)
    return tuple(
        ThresholdMethodOutcome(
            method=method,
            status=(
                ThresholdMethodExecutionStatus.COMPLETED
                if method in completed
                else ThresholdMethodExecutionStatus.INFEASIBLE
            ),
            detail=DetailText(
                f"executed across all {len(completed_by_run)} runs"
                if method in completed
                else _METHOD_NOT_COMPLETED_DETAIL
            ),
        )
        for method in declared
    )


def _dispatch_confirmatory(
    seeds: tuple[Seed, ...],
    output_root: Path,
    overwrite: OverwriteMode,
    *,
    progress: ProgressHook | None = None,
) -> DispatchOutcome:
    results = tuple(
        run_confirmatory_seed(seed, output_root=output_root, overwrite=overwrite.requested, progress=progress)
        for seed in seeds
    )
    return DispatchOutcome(
        detail=DetailText(f"confirmatory seeds={len(seeds)}"),
        method_outcomes=_method_outcomes(
            ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
            tuple(item.completed_threshold_methods for item in results),
        ),
    )


def _dispatch_family(
    seeds: tuple[Seed, ...],
    output_root: Path,
    overwrite: OverwriteMode,
    *,
    progress: ProgressHook | None = None,
) -> DispatchOutcome:
    results = tuple(
        run_family_grouped_mechanism_seed(
            seed,
            output_root=output_root,
            overwrite=overwrite.requested,
            progress=progress,
        )
        for seed in seeds
    )
    return DispatchOutcome(
        detail=DetailText(f"family_grouped seeds={len(seeds)}"),
        method_outcomes=_method_outcomes(
            ExperimentId.FAMILY_AND_GROUPED_GRANULARITY,
            tuple(item.completed_threshold_methods for item in results),
        ),
    )


def _dispatch_external(
    experiment_id: ExperimentId,
    seeds: tuple[Seed, ...],
    output_root: Path,
    overwrite: OverwriteMode,
    *,
    progress: ProgressHook | None = None,
) -> DispatchOutcome:
    if experiment_id is ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION:
        results = tuple(
            run_external_validation_seed(
                seed, output_root=output_root, overwrite=overwrite.requested, progress=progress
            )
            for seed in seeds
        )
    elif experiment_id is ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY:
        results = tuple(
            run_ciciot_boundary_seed(seed, output_root=output_root, overwrite=overwrite.requested, progress=progress)
            for seed in seeds
        )
    else:
        raise ScientificContractError(ErrorMessage(f"unsupported external experiment: {experiment_id.value}"))
    return DispatchOutcome(
        detail=DetailText(f"{experiment_id.value} seeds={len(seeds)}"),
        method_outcomes=_method_outcomes(experiment_id, tuple(item.completed_threshold_methods for item in results)),
    )


def _dispatch_fedprox(
    seeds: tuple[Seed, ...],
    output_root: Path,
    overwrite: OverwriteMode,
    *,
    progress: ProgressHook | None = None,
) -> DispatchOutcome:
    results = tuple(
        run_fedprox_stress_test_seed(
            training_seed=seed,
            coefficient=coefficient,
            output_root=output_root,
            overwrite=overwrite.requested,
            progress=progress,
        )
        for seed in seeds
        for coefficient in FEDPROX_COEFFICIENTS
    )
    return DispatchOutcome(
        detail=DetailText(
            f"fedprox seeds={len(seeds)} coefficients={len(FEDPROX_COEFFICIENTS)} executions={len(results)}"
        ),
        method_outcomes=_method_outcomes(
            ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
            tuple(item.completed_threshold_methods for item in results),
        ),
    )


def _dispatch_ditto(
    seeds: tuple[Seed, ...],
    output_root: Path,
    overwrite: OverwriteMode,
    *,
    progress: ProgressHook | None = None,
) -> DispatchOutcome:
    results = tuple(
        run_ditto_stress_test_seed(
            training_seed=seed,
            regularization=regularization,
            output_root=output_root,
            overwrite=overwrite.requested,
            progress=progress,
        )
        for seed in seeds
        for regularization in DITTO_REGULARIZATION_GRID
    )
    return DispatchOutcome(
        detail=DetailText(
            f"ditto seeds={len(seeds)} regularizations={len(DITTO_REGULARIZATION_GRID)} executions={len(results)}"
        ),
        method_outcomes=_method_outcomes(
            ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
            tuple((item.shared_threshold.method, item.local_threshold.method) for item in results),
        ),
    )


def _dispatch_fine_tuning(
    seeds: tuple[Seed, ...],
    output_root: Path,
    overwrite: OverwriteMode,
    *,
    progress: ProgressHook | None = None,
) -> DispatchOutcome:
    del progress
    results = tuple(
        run_fedavg_local_fine_tuning_stress_test_seed(
            training_seed=seed,
            output_root=output_root,
            overwrite=overwrite.requested,
        )
        for seed in seeds
    )
    return DispatchOutcome(
        detail=DetailText(f"fedavg_local_fine_tuning seeds={len(seeds)}"),
        method_outcomes=_method_outcomes(
            ExperimentId.FEDAVG_LOCAL_FINE_TUNING,
            tuple((item.shared_threshold.method, item.local_threshold.method) for item in results),
        ),
    )


def _temporal_unavailable(
    results: tuple[TemporalSeedResult, ...], method: FederatedThresholdMethod
) -> DetailText | None:
    for seed_result in results:
        for state in (seed_result.static_reference, seed_result.frozen_future, seed_result.recalibrated_future):
            for unavailable in state.unavailable_methods:
                if unavailable.method is method:
                    return DetailText(f"{unavailable.reason.value}: {unavailable.detail}")
    return None


def _dispatch_temporal(
    seeds: tuple[Seed, ...],
    output_root: Path,
    overwrite: OverwriteMode,
    *,
    progress: ProgressHook | None = None,
) -> DispatchOutcome:
    results = tuple(
        run_temporal_seed(
            seed,
            output_root=output_root,
            overwrite=overwrite.requested,
            progress=progress,
        )
        for seed in seeds
    )
    declared = _declared_methods(ExperimentId.EDGE_ONE_SHOT_RECALIBRATION)
    # A temporal result is only complete if its method was evaluated in every
    # declared state.  Taking the union of the state-level completions would
    # incorrectly report a method as complete when, for example, only the
    # static reference was materialized.
    completed = frozenset(declared)
    for result in results:
        state_methods: tuple[frozenset[FederatedThresholdMethod], ...] = tuple(
            frozenset(state.completed_threshold_methods)
            for state in (result.static_reference, result.frozen_future, result.recalibrated_future)
        )
        per_seed = state_methods[0].intersection(*state_methods[1:])
        completed = completed.intersection(per_seed)
    outcomes: list[ThresholdMethodOutcome] = []
    for method in declared:
        unavailable = _temporal_unavailable(results, method)
        if method in completed:
            status = ThresholdMethodExecutionStatus.COMPLETED
            detail = DetailText("executed across all temporal states and seeds")
        elif unavailable is not None:
            status = ThresholdMethodExecutionStatus.UNAVAILABLE
            detail = unavailable
        else:
            status = ThresholdMethodExecutionStatus.INFEASIBLE
            detail = DetailText(_METHOD_NOT_COMPLETED_DETAIL)
        outcomes.append(ThresholdMethodOutcome(method=method, status=status, detail=detail))
    return DispatchOutcome(detail=DetailText(f"temporal seeds={len(seeds)}"), method_outcomes=tuple(outcomes))


def _dispatch_robustness(
    experiment_id: ExperimentId,
    runner: RobustnessRunner,
    seeds: tuple[Seed, ...],
    output_root: Path,
    overwrite: OverwriteMode,
    *,
    progress: ProgressHook | None = None,
) -> DispatchOutcome:
    results = tuple(
        runner(seed, output_root=output_root, overwrite=overwrite.requested, progress=progress) for seed in seeds
    )
    outcomes = _method_outcomes(experiment_id, tuple(item.completed_threshold_methods for item in results))
    return DispatchOutcome(detail=DetailText(f"{experiment_id.value} seeds={len(seeds)}"), method_outcomes=outcomes)


def _dispatch_estimation(
    experiment_id: ExperimentId,
    runner: FederatedEstimationRunner,
    seeds: tuple[Seed, ...],
    output_root: Path,
    overwrite: OverwriteMode,
    *,
    progress: ProgressHook | None = None,
) -> DispatchOutcome:
    results = tuple(
        runner(seed, output_root=output_root, overwrite=overwrite.requested, progress=progress) for seed in seeds
    )
    return DispatchOutcome(
        detail=DetailText(f"{experiment_id.value} seeds={len(seeds)}"),
        method_outcomes=_method_outcomes(experiment_id, tuple(item.completed_threshold_methods for item in results)),
    )


def _dispatch_heterogeneity(
    seeds: tuple[Seed, ...],
    output_root: Path,
    overwrite: OverwriteMode,
    *,
    progress: ProgressHook | None = None,
) -> DispatchOutcome:
    results = tuple(
        run_controlled_heterogeneity_sweep_seed(
            seed, output_root=output_root, overwrite=overwrite.requested, progress=progress
        )
        for seed in seeds
    )
    return DispatchOutcome(
        detail=DetailText(f"controlled_heterogeneity_sweep seeds={len(seeds)}"),
        method_outcomes=_method_outcomes(
            ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
            tuple(item.completed_threshold_methods for item in results),
        ),
    )


def _dispatch_declared(
    experiment_id: ExperimentId,
    seeds: tuple[Seed, ...],
    output_root: Path,
    overwrite: OverwriteMode,
    *,
    progress: ProgressHook | None = None,
) -> DispatchOutcome:
    declaration = _declaration(experiment_id)
    results = tuple(
        execute_declared_experiment_seed(
            declaration=declaration,
            seed_cohort=SeedCohort(values=(seed,)),
            reason=PlanReason(f"registered supplementary recipe for {experiment_id.value}"),
            output_root=output_root,
            overwrite=overwrite.requested,
            progress=progress,
        )
        for seed in seeds
    )
    return DispatchOutcome(
        detail=DetailText(f"{experiment_id.value} seeds={len(seeds)}"),
        method_outcomes=_method_outcomes(experiment_id, tuple(item.completed_threshold_methods for item in results)),
    )


def _dispatch_analysis(experiment_id: ExperimentId, output_root: Path) -> DispatchOutcome:
    if output_root != OUTPUTS_ROOT:
        raise ScientificContractError(
            ErrorMessage("analysis-only experiments require full confirmatory evidence and cannot run in smoke mode"),
            subject=experiment_id,
        )
    report = _report_heterogeneity(experiment_id)
    return DispatchOutcome(
        detail=DetailText(f"analysis experiment rendered current scientific evidence: {report.detail}"),
        method_outcomes=tuple(
            ThresholdMethodOutcome(
                method=method,
                status=ThresholdMethodExecutionStatus.COMPLETED,
                detail=DetailText("analysis artifact generated from its declared scientific evidence"),
            )
            for method in _declared_methods(experiment_id)
        ),
    )


def _report_confirmatory(experiment_id: ExperimentId) -> ReportResult:
    centralized = report_centralized_reference(NBAIOT_CENTRALIZED_REFERENCE, output_root=OUTPUTS_ROOT, overwrite=True)
    path = analyze_confirmatory_campaign()
    return ReportResult(
        experiment=experiment_id,
        paths=(centralized, path),
        detail=DetailText(f"centralized_reference={centralized} confirmatory={path}"),
    )


def _report_external(experiment_id: ExperimentId) -> ReportResult:
    if experiment_id is ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION:
        result = analyze_external_validation_campaign(output_root=OUTPUTS_ROOT, overwrite=True)
        benign = analyze_external_benign_statistics(output_root=OUTPUTS_ROOT, overwrite=True)
        return ReportResult(
            experiment=experiment_id,
            paths=(result.output_directory, benign.output_directory),
            detail=DetailText(f"paired={result.output_directory} benign_statistics={benign.output_directory}"),
        )
    if experiment_id is ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY:
        result = analyze_ciciot_boundary_campaign(output_root=OUTPUTS_ROOT, overwrite=True)
        boundary = analyze_ciciot_boundary_evidence(output_root=OUTPUTS_ROOT, overwrite=True)
        centralized = report_centralized_reference(CIC_CENTRALIZED_REFERENCE, output_root=OUTPUTS_ROOT, overwrite=True)
        return ReportResult(
            experiment=experiment_id,
            paths=(result.output_directory, boundary, centralized),
            detail=DetailText(
                f"boundary={boundary} paired={result.output_directory} centralized_reference={centralized}"
            ),
        )
    raise ReportEvidenceError(ErrorMessage(f"unsupported external report: {experiment_id.value}"))


def _report_heterogeneity(experiment_id: ExperimentId) -> ReportResult:
    if experiment_id is ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP:
        path = analyze_controlled_heterogeneity_sweep(overwrite=True)
    elif experiment_id is ExperimentId.PHYSICAL_FAMILY_ADEQUACY:
        path = analyze_physical_family_adequacy(overwrite=True)
    elif experiment_id is ExperimentId.CALIBRATION_SUPPORT_BURDEN:
        path = analyze_calibration_support_burden(overwrite=True)
    elif experiment_id is ExperimentId.NATURAL_DEVICE_CLIENT_IMPACT:
        path = analyze_natural_device_client_impact(overwrite=True)
    elif experiment_id is ExperimentId.MALWARE_FAMILY_SENSITIVITY:
        path = analyze_malware_family_sensitivity(overwrite=True)
    elif experiment_id is ExperimentId.EQUITY_UTILITY_PARETO:
        path = analyze_equity_utility_pareto(overwrite=True)
    elif experiment_id is ExperimentId.PER_CLIENT_SCORE_GEOMETRY:
        path = analyze_per_client_score_geometry(overwrite=True)
    elif experiment_id is ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION:
        path = analyze_heterogeneity_benefit_association(overwrite=True)
    elif experiment_id is ExperimentId.HETEROGENEITY_CALIBRATION_SUPPORT_INTERACTION:
        path = analyze_heterogeneity_support_interaction(overwrite=True)
    elif experiment_id is ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF:
        path = analyze_threshold_movement_tradeoff(overwrite=True)
    else:
        raise ReportEvidenceError(ErrorMessage(f"unsupported heterogeneity report: {experiment_id.value}"))
    return ReportResult(experiment=experiment_id, paths=(path,), detail=DetailText(str(path)))


def _report_fedprox(experiment_id: ExperimentId) -> ReportResult:
    try:
        paths: list[Path] = []
        activation_evidence: list[
            tuple[
                ProximalCoefficient,
                tuple[FedProxAlignmentEvidence, ...],
                tuple[AbsorptionSeedObservation, ...],
            ]
        ] = []
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
                output_root=OUTPUTS_ROOT,
            )
            if output.exists():
                rmtree(output)
            analyze_fedprox_absorption(observations, output_directory=output)
            alignment = tuple(
                load_fedprox_alignment_evidence(seed, coefficient) for seed in CONFIRMATORY_SEED_COHORT.values
            )
            write_text_atomically(
                output / ResearchArtifact.EVIDENCE_REPORT,
                FileContentText(
                    _alignment_report(
                        title=f"FedProx alignment evidence (coefficient={coefficient.value:.12g})",
                        condition_name="FedProx",
                        observations=tuple(
                            (
                                item.training_seed,
                                item.reference_alignment,
                                item.alignment,
                                item.alignment_reductions,
                                next(
                                    observation
                                    for observation in observations
                                    if observation.seed == item.training_seed
                                ),
                            )
                            for item in alignment
                        ),
                    )
                ),
            )
            paths.append(output)
            activation_evidence.append((coefficient, alignment, observations))
        activation_path = fedprox_analysis_directory(FEDPROX_COEFFICIENTS[0], output_root=OUTPUTS_ROOT).parent / (
            "fedprox_activation_report.md"
        )
        write_text_atomically(
            activation_path,
            FileContentText(fedprox_activation_report(tuple(activation_evidence))),
        )
        paths.append(activation_path)
        _write_stress_results(
            experiment_id,
            activation_path.parent / ResearchArtifact.RESULTS,
            tuple(item.alignment for _, alignment, _ in activation_evidence for item in alignment),
        )
    except ScientificContractError as error:
        raise ReportEvidenceError(
            ErrorMessage(str(error)), subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST
        ) from error
    return ReportResult(
        experiment=experiment_id,
        paths=tuple(paths),
        detail=DetailText(f"coefficients={len(FEDPROX_COEFFICIENTS)} activation={paths[-1]}"),
    )


def _report_ditto(experiment_id: ExperimentId) -> ReportResult:
    outputs: list[Path] = []
    mechanisms: list[MechanismEvidence] = []
    for regularization in DITTO_REGULARIZATION_GRID:
        output = ditto_analysis_directory(regularization, output_root=OUTPUTS_ROOT)
        if output.exists():
            rmtree(output)
        results = tuple(
            load_ditto_stress_test_evidence(
                training_seed=seed,
                regularization=regularization,
                output_root=OUTPUTS_ROOT,
            )
            for seed in CONFIRMATORY_SEED_COHORT.values
        )
        references = tuple(
            load_fedavg_cv_fpr_effect(
                item.personalized_coordinate.training_seed,
                experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
            )
            for item in results
        )
        absorption = analyze_ditto_absorption(results, reference_evidence=references, output_directory=output)
        write_text_atomically(
            output / ResearchArtifact.EVIDENCE_REPORT,
            FileContentText(
                _alignment_report(
                    title=f"Ditto alignment evidence (regularization={regularization.value:.12g})",
                    condition_name="Ditto",
                    observations=tuple(
                        (
                            item.personalized_coordinate.training_seed,
                            item.reference_alignment,
                            item.alignment,
                            item.alignment_reductions,
                            next(
                                observation
                                for observation in absorption.observations
                                if observation.seed == item.personalized_coordinate.training_seed
                            ),
                        )
                        for item in results
                    ),
                )
            ),
        )
        outputs.append(output)
        mechanisms.extend(item.alignment for item in results)
    _write_stress_results(
        experiment_id,
        outputs[0].parent / ResearchArtifact.RESULTS,
        tuple(mechanisms),
    )
    return ReportResult(experiment=experiment_id, paths=tuple(outputs), detail=DetailText(f"analyses={len(outputs)}"))


def _fine_tuning_analysis_path() -> Path:
    return (
        OUTPUTS_ROOT
        / ExecutionRootDirectory.FEDAVG_LOCAL_FINE_TUNING
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / FineTuningArtifactBranch.ANALYSIS
        / ResearchArtifact.EVIDENCE_REPORT
    )


def _report_fine_tuning(experiment_id: ExperimentId) -> ReportResult:
    rows = [
        "# FedAvg local fine-tuning execution evidence",
        "",
        "This is a bounded simple model-personalization stress condition, not confirmatory evidence, "
        "a new personalized-federated-learning contribution, or a replacement for the locked Ditto experiment.",
        "",
        "| Seed | Client | Serialized bytes | Fine-tuning wall time (s) |",
        "|---:|---|---:|---:|",
    ]
    evidence_by_seed = tuple(
        load_fine_tuning_stress_test_evidence(training_seed=seed, output_root=OUTPUTS_ROOT)
        for seed in CONFIRMATORY_SEED_COHORT.values
    )
    for seed, evidence in zip(CONFIRMATORY_SEED_COHORT.values, evidence_by_seed, strict=True):
        for model in evidence.model_evidence:
            rows.append(
                f"| {seed.value} | {model.client.client_id.value} | "
                f"{model.serialized_state_evidence.byte_count.value} | {model.wall_time.value:.12g} |"
            )
    activation = summarize_alignment_activation(tuple(item.alignment_reductions for item in evidence_by_seed))
    rows.extend(
        (
            "",
            "## Per-seed alignment reductions",
            "",
            "| Seed | Alignment quantity | FedAvg reference | Fine-tuned model | Alignment reduction | Availability |",
            "|---:|---|---:|---:|---:|---|",
        )
    )
    for seed, evidence in zip(CONFIRMATORY_SEED_COHORT.values, evidence_by_seed, strict=True):
        reference = {item.metric: item for item in evidence.reference_alignment.metrics}
        condition = {item.metric: item for item in evidence.alignment.metrics}
        for reduction in evidence.alignment_reductions:
            reference_value = reference[reduction.metric].value
            condition_value = condition[reduction.metric].value
            availability = (
                reduction.unavailable_reason.value if reduction.unavailable_reason is not None else "available"
            )
            rows.append(
                f"| {seed.value} | {reduction.metric.value} | "
                f"{_alignment_value(reference_value)} | {_alignment_value(condition_value)} | "
                f"{_alignment_value(reduction.value)} | {availability} |"
            )
    rows.extend(
        (
            "",
            "## Campaign alignment activation",
            "",
            "This descriptive sign-based label is not a significance or materiality test; "
            "raw seed-level quantities above remain primary.",
            "",
            "| Alignment quantity | Valid seeds | Mean alignment reduction |",
            "|---|---:|---:|",
            *(
                f"| {item.metric.value} | {item.valid_seed_count.value} | {_alignment_value(item.value)} |"
                for item in activation.reductions
            ),
            "",
            f"Campaign activation label: `{activation.label.value}`.",
        )
    )
    output = _fine_tuning_analysis_path()
    if output.parent.exists():
        rmtree(output.parent)
    output.parent.mkdir(parents=True, exist_ok=True)
    references = tuple(
        load_fedavg_cv_fpr_effect(seed, experiment=ExperimentId.FEDAVG_LOCAL_FINE_TUNING)
        for seed in CONFIRMATORY_SEED_COHORT.values
    )
    absorption = analyze_fine_tuning_absorption(
        evidence_by_seed,
        reference_evidence=references,
        output_directory=output.parent,
    )
    rows.extend(
        (
            "",
            "## Common model-side score-alignment and threshold-absorption tuple",
            "",
            *_common_alignment_tuple_rows(
                tuple(
                    (
                        evidence.personalized_coordinate.training_seed,
                        evidence.alignment,
                        next(
                            observation
                            for observation in absorption.observations
                            if observation.seed == evidence.personalized_coordinate.training_seed
                        ),
                    )
                    for evidence in evidence_by_seed
                )
            ),
        )
    )
    write_text_atomically(output, FileContentText("\n".join(rows) + "\n"))
    _write_stress_results(
        experiment_id,
        output.parent / ResearchArtifact.RESULTS,
        tuple(item.alignment for item in evidence_by_seed),
    )
    return ReportResult(
        experiment=experiment_id,
        paths=(output.parent,),
        detail=DetailText(f"analysis={output.parent}"),
    )


def _alignment_value(value: MetricValue | None) -> str:
    if value is None:
        return "—"
    return f"{value.value:.12g}"


def _alignment_report(
    *,
    title: str,
    condition_name: str,
    observations: tuple[
        tuple[
            Seed,
            ModelAlignmentResult,
            ModelAlignmentResult,
            tuple[AlignmentReductionOutcome, ...],
            AbsorptionSeedObservation,
        ],
        ...,
    ],
) -> str:
    activation = summarize_alignment_activation(tuple(item[3] for item in observations))
    rows = [f"# {title}", "", "## Per-seed alignment reductions", ""]
    rows.extend(
        (
            "| Seed | Alignment quantity | FedAvg reference | "
            f"{condition_name} model | Alignment reduction | Availability |",
            "|---:|---|---:|---:|---:|---|",
        )
    )
    for seed, reference_alignment, condition_alignment, reductions, _ in observations:
        reference = {item.metric: item for item in reference_alignment.metrics}
        condition = {item.metric: item for item in condition_alignment.metrics}
        for reduction in reductions:
            availability = (
                reduction.unavailable_reason.value if reduction.unavailable_reason is not None else "available"
            )
            rows.append(
                f"| {seed.value} | {reduction.metric.value} | "
                f"{_alignment_value(reference[reduction.metric].value)} | "
                f"{_alignment_value(condition[reduction.metric].value)} | "
                f"{_alignment_value(reduction.value)} | {availability} |"
            )
    rows.extend(
        (
            "",
            "## Campaign alignment activation",
            "",
            "| Alignment quantity | Valid seeds | Mean alignment reduction |",
            "|---|---:|---:|",
        )
    )
    rows.extend(
        f"| {item.metric.value} | {item.valid_seed_count.value} | {_alignment_value(item.value)} |"
        for item in activation.reductions
    )
    rows.extend(
        (
            "",
            "## Common model-side score-alignment and threshold-absorption tuple",
            "",
            *_common_alignment_tuple_rows(
                tuple(
                    (seed, condition_alignment, absorption)
                    for seed, _, condition_alignment, _, absorption in observations
                )
            ),
        )
    )
    rows.extend(("", f"Campaign activation label: `{activation.label.value}`.", ""))
    return "\n".join(rows)


def _common_alignment_tuple_rows(
    observations: tuple[tuple[Seed, ModelAlignmentResult, AbsorptionSeedObservation], ...],
) -> tuple[str, ...]:
    """Render the §7.2B per-seed tuple without deriving a policy recommendation."""

    rows = (
        "| Seed | ModelAlignmentH | LocationDispersion | ScaleDispersion | LocalThresholdDispersion | "
        "NormalizedSharedLocalThresholdDistance | DeltaScope | ScopeAbsorption |",
        "|---:|---:|---:|---:|---:|---:|---:|---|",
    )
    rendered: list[str] = list(rows)
    for seed, alignment, absorption in observations:
        metrics = {item.metric: item.value for item in alignment.metrics}
        scope_absorption = (
            MetricValue(1.0 - absorption.personalized_effect.value / absorption.reference_effect.value)
            if absorption.reference_effect.value > 1e-12
            else None
        )
        scope_absorption_text = (
            _alignment_value(scope_absorption) if scope_absorption is not None else "UNAVAILABLE_NO_POSITIVE_FEDAVG_GAP"
        )
        rendered.append(
            f"| {seed.value} | "
            f"{_alignment_value(metrics[ModelAlignmentMetric.MODEL_ALIGNMENT_HETEROGENEITY])} | "
            f"{_alignment_value(metrics[ModelAlignmentMetric.LOCATION_DISPERSION])} | "
            f"{_alignment_value(metrics[ModelAlignmentMetric.SCALE_DISPERSION])} | "
            f"{_alignment_value(metrics[ModelAlignmentMetric.LOCAL_THRESHOLD_DISPERSION])} | "
            f"{_alignment_value(metrics[ModelAlignmentMetric.NORMALIZED_SHARED_LOCAL_THRESHOLD_DISTANCE])} | "
            f"{_alignment_value(absorption.personalized_effect)} | {scope_absorption_text} |"
        )
    return tuple(rendered)


def _report_temporal(experiment_id: ExperimentId) -> ReportResult:
    seeds = tuple(
        load_temporal_seed_result(seed, output_root=OUTPUTS_ROOT) for seed in BOUNDED_EVIDENCE_SEED_COHORT.values
    )
    campaign = TemporalCampaignResult(seeds=seeds, analyses=())
    analyses = analyze_temporal_campaign(campaign, output_root=OUTPUTS_ROOT, overwrite=True)
    paths = tuple(item.output_directory for item in analyses)
    return ReportResult(
        experiment=experiment_id,
        paths=paths,
        detail=DetailText(f"temporal_methods={len(paths)}"),
    )


def _report_robustness(experiment_id: ExperimentId) -> ReportResult:
    if experiment_id is ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY:
        result = report_shared_construction_sensitivity(experiment_id, True)
    elif experiment_id is ExperimentId.QUANTILE_SENSITIVITY:
        result = report_quantile_sensitivity(experiment_id, True)
    elif experiment_id is ExperimentId.THRESHOLD_ESTIMATOR_SCOPE_SENSITIVITY:
        result = report_threshold_estimator_scope_sensitivity(experiment_id, True)
    elif experiment_id is ExperimentId.CALIBRATION_SIZE_ABLATION:
        result = report_calibration_size_ablation(experiment_id, True)
    elif experiment_id is ExperimentId.CALIBRATION_COLD_START_ONBOARDING:
        result = report_calibration_cold_start_onboarding(experiment_id, True)
    elif experiment_id is ExperimentId.SHARED_CALIBRATION_CONTRIBUTOR_AVAILABILITY:
        result = report_shared_calibration_contributor_availability(experiment_id, True)
    elif experiment_id is ExperimentId.FIXED_SHRINKAGE_CURVE:
        result = report_fixed_shrinkage_curve(experiment_id, True)
    elif experiment_id is ExperimentId.SIZE_AWARE_SHRINKAGE:
        result = report_size_aware_shrinkage(experiment_id, True)
    elif experiment_id is ExperimentId.LOCAL_CONFORMAL_COVERAGE:
        result = report_local_conformal_coverage(experiment_id, True)
    elif experiment_id is ExperimentId.PREPROCESSING_GEOMETRY_SENSITIVITY:
        result = report_preprocessing_geometry_sensitivity(experiment_id, True)
    else:
        raise ReportEvidenceError(ErrorMessage(f"unsupported threshold robustness report: {experiment_id.value}"))
    return ReportResult(experiment=experiment_id, paths=result.directories, detail=DetailText(result.detail))


def _report_estimation(experiment_id: ExperimentId) -> ReportResult:
    if experiment_id is ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON:
        result = report_federated_benign_statistics_comparison(experiment_id, True)
    elif experiment_id is ExperimentId.FEDERATED_QUANTILE_ESTIMATION:
        result = report_federated_quantile_estimation(experiment_id, True)
    elif experiment_id is ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY:
        result = report_fixed_coefficient_statistics_sensitivity(experiment_id, True)
    else:
        raise ReportEvidenceError(ErrorMessage(f"unsupported federated estimation report: {experiment_id.value}"))
    return ReportResult(experiment=experiment_id, paths=result.directories, detail=DetailText(result.detail))


def _write_stress_results(
    experiment_id: ExperimentId,
    destination: Path,
    mechanisms: tuple[MechanismEvidence, ...],
) -> Path:
    persist_result_document(
        MechanismPublicationDocument(
            experiment=experiment_id,
            population=_declaration(experiment_id).population,
            evidence_role=_declaration(experiment_id).role,
            mechanisms=mechanisms,
        ),
        destination,
    )
    return destination


def _supplementary_directory(experiment_id: ExperimentId) -> Path:
    return OUTPUTS_ROOT / ResearchDirectory.SUPPLEMENTARY / experiment_id.value


def _report_supplementary(experiment_id: ExperimentId) -> ReportResult:
    declaration = _declaration(experiment_id)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=seed_cohort_for(experiment_id),
        evidence=(
            PlanningEvidence(
                experiment=experiment_id,
                disposition=PlanDisposition.EXECUTABLE,
                reason=PlanReason("supplementary evidence report consumes the registered experiment recipe"),
            ),
        ),
    )
    report_path = _supplementary_directory(experiment_id) / ResearchArtifact.EVIDENCE_REPORT
    lines = [
        "# DATP-Core Supplementary Evidence",
        "",
        f"Experiment: `{experiment_id.value}`",
        f"Evidence role: `{declaration.role.value}`",
        f"Population: `{declaration.population.value}`",
        "",
        "| Seed | Threshold method | Metric | Status | Value | Reason | Denominator |",
        "|---:|---|---|---|---:|---|---:|",
    ]
    seen: set[tuple[Seed, FederatedThresholdMethod, MetricId]] = set()
    observations: list[MetricObservation] = []
    for entry in plan.executable:
        coordinate = entry.coordinate
        key = (coordinate.training_seed, coordinate.threshold_method, coordinate.metric)
        if key in seen:
            continue
        seen.add(key)
        document_path = (
            evaluation_run_directory(OUTPUTS_ROOT, coordinate)
            / EvaluationRunAssetDirectory.EVALUATION
            / FederatedEvaluationAssetName.DOCUMENT
        )
        if not document_path.is_file():
            raise ReportEvidenceError(
                ErrorMessage(f"missing evaluation evidence for {coordinate.stable_key}: {document_path}"),
                subject=experiment_id,
            )
        document = load_evaluation_document(document_path)
        metric = metric_by_id(document.population.metrics, coordinate.metric)
        observations.append(
            MetricObservation(
                seed=coordinate.training_seed,
                threshold_method=coordinate.threshold_method,
                metric=coordinate.metric,
                status=metric.status,
                value=metric.value if isinstance(metric, AvailableMetric) else None,
                reason=metric.reason,
                denominator=metric.denominator,
            )
        )
        value = f"{metric.value.value:.12g}" if isinstance(metric, AvailableMetric) else "—"
        reason = "—" if metric.reason is None else metric.reason.value
        denominator = "—" if metric.denominator is None else str(metric.denominator.value)
        lines.append(
            f"| {coordinate.training_seed.value} | {coordinate.threshold_method.value} | "
            f"{coordinate.metric.value} | {metric.status.value} | {value} | {reason} | {denominator} |"
        )
    if not observations:
        raise ReportEvidenceError(
            ErrorMessage(f"supplementary report produced no metric observations: {experiment_id.value}"),
            subject=experiment_id,
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    persist_result_document(
        ExperimentMetricResults(
            experiment=experiment_id,
            population=declaration.population,
            evidence_role=declaration.role,
            observations=tuple(observations),
        ),
        report_path.parent / ResearchArtifact.RESULTS,
    )
    write_text_atomically(report_path, FileContentText("\n".join(lines) + "\n"))
    return ReportResult(
        experiment=experiment_id,
        paths=(report_path, report_path.parent / ResearchArtifact.RESULTS),
        detail=DetailText(f"generated {report_path}"),
    )


def _external_recipe(experiment_id: ExperimentId) -> DispatchHandler:
    def dispatch(
        seeds: tuple[Seed, ...],
        output_root: Path,
        overwrite: OverwriteMode,
        *,
        progress: ProgressHook | None = None,
    ) -> DispatchOutcome:
        return _dispatch_external(experiment_id, seeds, output_root, overwrite, progress=progress)

    return dispatch


def _robustness_recipe(experiment_id: ExperimentId, runner: RobustnessRunner) -> DispatchHandler:
    def dispatch(
        seeds: tuple[Seed, ...],
        output_root: Path,
        overwrite: OverwriteMode,
        *,
        progress: ProgressHook | None = None,
    ) -> DispatchOutcome:
        return _dispatch_robustness(experiment_id, runner, seeds, output_root, overwrite, progress=progress)

    return dispatch


def _estimation_recipe(experiment_id: ExperimentId, runner: FederatedEstimationRunner) -> DispatchHandler:
    def dispatch(
        seeds: tuple[Seed, ...],
        output_root: Path,
        overwrite: OverwriteMode,
        *,
        progress: ProgressHook | None = None,
    ) -> DispatchOutcome:
        return _dispatch_estimation(experiment_id, runner, seeds, output_root, overwrite, progress=progress)

    return dispatch


def _declared_recipe(experiment_id: ExperimentId) -> DispatchHandler:
    def dispatch(
        seeds: tuple[Seed, ...],
        output_root: Path,
        overwrite: OverwriteMode,
        *,
        progress: ProgressHook | None = None,
    ) -> DispatchOutcome:
        return _dispatch_declared(experiment_id, seeds, output_root, overwrite, progress=progress)

    return dispatch


def _analysis_recipe(experiment_id: ExperimentId) -> DispatchHandler:
    def dispatch(
        seeds: tuple[Seed, ...],
        output_root: Path,
        overwrite: OverwriteMode,
        *,
        progress: ProgressHook | None = None,
    ) -> DispatchOutcome:
        del seeds, overwrite, progress
        return _dispatch_analysis(experiment_id, output_root)

    return dispatch


EXPERIMENT_RECIPES: tuple[ExperimentRecipe, ...] = (
    ExperimentRecipe(
        experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_dispatch_confirmatory,
        report=_report_confirmatory,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.FAMILY_AND_GROUPED_GRANULARITY,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_dispatch_family,
        report=_report_supplementary,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_dispatch_fedprox,
        report=_report_fedprox,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.FEDAVG_LOCAL_FINE_TUNING,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_dispatch_fine_tuning,
        report=_report_fine_tuning,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_dispatch_ditto,
        report=_report_ditto,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_estimation_recipe(
            ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON, run_federated_benign_statistics_comparison_seed
        ),
        report=_report_estimation,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.FEDERATED_QUANTILE_ESTIMATION,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_estimation_recipe(ExperimentId.FEDERATED_QUANTILE_ESTIMATION, run_federated_quantile_estimation_seed),
        report=_report_estimation,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_estimation_recipe(
            ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY, run_fixed_coefficient_statistics_sensitivity_seed
        ),
        report=_report_estimation,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_external_recipe(ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION),
        report=_report_external,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_external_recipe(ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY),
        report=_report_external,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_dispatch_temporal,
        report=_report_temporal,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_robustness_recipe(
            ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY, run_shared_construction_sensitivity_seed
        ),
        report=_report_robustness,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.QUANTILE_SENSITIVITY,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_robustness_recipe(ExperimentId.QUANTILE_SENSITIVITY, run_quantile_sensitivity_seed),
        report=_report_robustness,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.THRESHOLD_ESTIMATOR_SCOPE_SENSITIVITY,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_robustness_recipe(
            ExperimentId.THRESHOLD_ESTIMATOR_SCOPE_SENSITIVITY,
            run_threshold_estimator_scope_sensitivity_seed,
        ),
        report=_report_robustness,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.CALIBRATION_SIZE_ABLATION,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_robustness_recipe(ExperimentId.CALIBRATION_SIZE_ABLATION, run_calibration_size_ablation_seed),
        report=_report_robustness,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.CALIBRATION_COLD_START_ONBOARDING,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_robustness_recipe(
            ExperimentId.CALIBRATION_COLD_START_ONBOARDING,
            run_calibration_cold_start_onboarding_seed,
        ),
        report=_report_robustness,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.SHARED_CALIBRATION_CONTRIBUTOR_AVAILABILITY,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_robustness_recipe(
            ExperimentId.SHARED_CALIBRATION_CONTRIBUTOR_AVAILABILITY,
            run_shared_calibration_contributor_availability_seed,
        ),
        report=_report_robustness,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.FIXED_SHRINKAGE_CURVE,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_robustness_recipe(ExperimentId.FIXED_SHRINKAGE_CURVE, run_fixed_shrinkage_curve_seed),
        report=_report_robustness,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.SIZE_AWARE_SHRINKAGE,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_robustness_recipe(ExperimentId.SIZE_AWARE_SHRINKAGE, run_size_aware_shrinkage_seed),
        report=_report_robustness,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.LOCAL_CONFORMAL_COVERAGE,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_robustness_recipe(ExperimentId.LOCAL_CONFORMAL_COVERAGE, run_local_conformal_coverage_seed),
        report=_report_robustness,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.PREPROCESSING_GEOMETRY_SENSITIVITY,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_robustness_recipe(
            ExperimentId.PREPROCESSING_GEOMETRY_SENSITIVITY,
            run_preprocessing_geometry_sensitivity_seed,
        ),
        report=_report_robustness,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_dispatch_heterogeneity,
        report=_report_heterogeneity,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.HETEROGENEITY_CALIBRATION_SUPPORT_INTERACTION,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_declared_recipe(ExperimentId.HETEROGENEITY_CALIBRATION_SUPPORT_INTERACTION),
        report=_report_heterogeneity,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.PHYSICAL_FAMILY_ADEQUACY,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_analysis_recipe(ExperimentId.PHYSICAL_FAMILY_ADEQUACY),
        report=_report_heterogeneity,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.CALIBRATION_SUPPORT_BURDEN,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_analysis_recipe(ExperimentId.CALIBRATION_SUPPORT_BURDEN),
        report=_report_heterogeneity,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.NATURAL_DEVICE_CLIENT_IMPACT,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_analysis_recipe(ExperimentId.NATURAL_DEVICE_CLIENT_IMPACT),
        report=_report_heterogeneity,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.MALWARE_FAMILY_SENSITIVITY,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_analysis_recipe(ExperimentId.MALWARE_FAMILY_SENSITIVITY),
        report=_report_heterogeneity,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.EQUITY_UTILITY_PARETO,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_analysis_recipe(ExperimentId.EQUITY_UTILITY_PARETO),
        report=_report_heterogeneity,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.PER_CLIENT_SCORE_GEOMETRY,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_analysis_recipe(ExperimentId.PER_CLIENT_SCORE_GEOMETRY),
        report=_report_heterogeneity,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_analysis_recipe(ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION),
        report=_report_heterogeneity,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.MANDATORY,
        dispatch=_analysis_recipe(ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF),
        report=_report_heterogeneity,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.GROUP_MEDIAN_SUPPLEMENT,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.OPTIONAL,
        dispatch=_declared_recipe(ExperimentId.GROUP_MEDIAN_SUPPLEMENT),
        report=_report_supplementary,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.OPTIONAL_EQUITY_INDICES,
        anchor_requirement=AnchorRequirement.REQUIRED,
        campaign_role=CampaignRole.OPTIONAL,
        dispatch=_declared_recipe(ExperimentId.OPTIONAL_EQUITY_INDICES),
        report=_report_supplementary,
    ),
)


def registered_experiment_ids() -> tuple[ExperimentId, ...]:
    return tuple(recipe.experiment for recipe in EXPERIMENT_RECIPES)


def evaluation_document_experiment_ids() -> tuple[ExperimentId, ...]:
    return tuple(
        recipe.experiment for recipe in EXPERIMENT_RECIPES if recipe.experiment not in _ANALYSIS_ONLY_EXPERIMENTS
    )


def mandatory_experiment_ids() -> tuple[ExperimentId, ...]:
    return tuple(recipe.experiment for recipe in EXPERIMENT_RECIPES if recipe.campaign_role is CampaignRole.MANDATORY)


def anchor_gated_experiment_ids() -> tuple[ExperimentId, ...]:
    return tuple(
        recipe.experiment for recipe in EXPERIMENT_RECIPES if recipe.anchor_requirement is AnchorRequirement.REQUIRED
    )


def recipe_for(experiment_id: ExperimentId) -> ExperimentRecipe:
    declaration = _declaration(experiment_id)
    if declaration.readiness is ExperimentReadiness.SUPPRESSED:
        raise ScientificContractError(
            ErrorMessage(f"experiment is intentionally suppressed: {experiment_id.value}"), subject=experiment_id
        )
    matches = tuple(recipe for recipe in EXPERIMENT_RECIPES if recipe.experiment is experiment_id)
    if len(matches) != 1:
        raise ScientificContractError(
            ErrorMessage(f"experiment recipe must resolve exactly once: {experiment_id.value}"), subject=experiment_id
        )
    return matches[0]

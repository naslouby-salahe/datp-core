"""Exact experiment recipe registry, dispatch, reporting, and evidence markers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from typing import Protocol

from datp_core.app.contracts import AnchorRequirement, OverwriteMode
from datp_core.app.layout import ANCHOR_DIAGNOSTICS_DIRECTORY, ResearchArtifact, ResearchDirectory
from datp_core.app.models import DetailText, DispatchOutcome, ThresholdMethodOutcome
from datp_core.core.identifiers import (
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    FedProxRoleDirectory,
    PopulationId,
    ThresholdMethodExecutionStatus,
)
from datp_core.artifacts.serializers.json import canonical_checksum
from datp_core.core.errors import ReportEvidenceError, ScientificContractError
from datp_core.core.numeric import Seed
from datp_core.evaluation.federated.publication import FederatedEvaluationAssetName
from datp_core.analysis.metrics.models import AvailableMetric, metric_by_id
from datp_core.experiments.confirmatory import (
    ConfirmatoryAssetDirectory,
    analyze_confirmatory_campaign,
    load_fedavg_cv_fpr_effect,
    run_confirmatory_seed,
    run_family_grouped_mechanism_seed,
)
from datp_core.experiments.execution import execute_declared_experiment_seed
from datp_core.experiments.external import (
    BoundedExternalAssetDirectory,
    analyze_ciciot_boundary_campaign,
    analyze_external_validation_campaign,
    run_ciciot_boundary_seed,
    run_external_validation_seed,
)
from datp_core.experiments.federated_threshold import (
    FederatedEstimationSeedResult,
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
from datp_core.experiments.planning import PlanDisposition, PlanningEvidence, expand_experiment_plan
from datp_core.experiments.temporal import (
    TemporalArtifactDirectory,
    TemporalCampaignResult,
    TemporalSeedResult,
    analyze_temporal_campaign,
    load_temporal_campaign_seeds,
    run_temporal_seed,
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
from datp_core.pipeline.execution.evidence import load_evaluation_document
from datp_core.pipeline.execution.layout import EvaluationRunAssetDirectory, ExecutionRootDirectory
from datp_core.artifacts.layout import evaluation_run_directory
from datp_core.presentation.export import MECHANISM_REPORT_FILENAME, PUBLICATION_FILENAME
from datp_core.experiments.common.seeds import CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.protocols.training import DITTO_PRIMARY_REGULARIZATION, FEDPROX_COEFFICIENTS
from datp_core.runtime.configuration import OUTPUTS_ROOT
from datp_core.runtime.filesystem import write_text_atomically


class RobustnessRunner(Protocol):
    def __call__(
        self,
        training_seed: Seed,
        *,
        output_root: Path,
        overwrite: bool,
    ) -> ThresholdRobustnessSeedResult: ...


class FederatedEstimationRunner(Protocol):
    def __call__(
        self,
        training_seed: Seed,
        *,
        output_root: Path,
        overwrite: bool,
    ) -> FederatedEstimationSeedResult: ...


class DispatchHandler(Protocol):
    def __call__(
        self,
        seeds: tuple[Seed, ...],
        output_root: Path,
        overwrite: OverwriteMode,
    ) -> DispatchOutcome: ...


class ReportHandler(Protocol):
    def __call__(
        self,
        experiment_id: ExperimentId,
        overwrite: OverwriteMode,
    ) -> tuple[tuple[Path, ...], DetailText]: ...


class AnalysisMarker(Protocol):
    def __call__(self, experiment_id: ExperimentId) -> bool: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentRecipe:
    experiment: ExperimentId
    anchor_requirement: AnchorRequirement
    dispatch: DispatchHandler
    report: ReportHandler
    analysis_marker: AnalysisMarker


def _declaration(experiment_id: ExperimentId):
    from datp_core.app.campaign import require_experiment_declaration

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
                else "declared but not completed in this execution"
            ),
        )
        for method in declared
    )


def _dispatch_confirmatory(seeds: tuple[Seed, ...], output_root: Path, overwrite: OverwriteMode) -> DispatchOutcome:
    results = tuple(
        run_confirmatory_seed(seed, output_root=output_root, overwrite=overwrite.requested) for seed in seeds
    )
    return DispatchOutcome(
        detail=DetailText(f"confirmatory seeds={len(seeds)}"),
        method_outcomes=_method_outcomes(
            ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
            tuple(item.completed_threshold_methods for item in results),
        ),
    )


def _dispatch_family(seeds: tuple[Seed, ...], output_root: Path, overwrite: OverwriteMode) -> DispatchOutcome:
    results = tuple(
        run_family_grouped_mechanism_seed(seed, output_root=output_root, overwrite=overwrite.requested)
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
) -> DispatchOutcome:
    if experiment_id is ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION:
        results = tuple(
            run_external_validation_seed(seed, output_root=output_root, overwrite=overwrite.requested) for seed in seeds
        )
    elif experiment_id is ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY:
        results = tuple(
            run_ciciot_boundary_seed(seed, output_root=output_root, overwrite=overwrite.requested) for seed in seeds
        )
    else:
        raise ScientificContractError(f"unsupported external experiment: {experiment_id.value}")
    return DispatchOutcome(
        detail=DetailText(f"{experiment_id.value} seeds={len(seeds)}"),
        method_outcomes=_method_outcomes(experiment_id, tuple(item.completed_threshold_methods for item in results)),
    )


def _dispatch_fedprox(seeds: tuple[Seed, ...], output_root: Path, overwrite: OverwriteMode) -> DispatchOutcome:
    from datp_core.experiments.training_stress import run_fedprox_stress_test_seed

    results = tuple(
        run_fedprox_stress_test_seed(
            training_seed=seed,
            coefficient=coefficient,
            output_root=output_root,
            overwrite=overwrite.requested,
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


def _dispatch_ditto(seeds: tuple[Seed, ...], output_root: Path, overwrite: OverwriteMode) -> DispatchOutcome:
    from datp_core.experiments.training_stress import run_ditto_stress_test_seed

    results = tuple(
        run_ditto_stress_test_seed(
            training_seed=seed,
            regularization=DITTO_PRIMARY_REGULARIZATION,
            output_root=output_root,
            overwrite=overwrite.requested,
        )
        for seed in seeds
    )
    return DispatchOutcome(
        detail=DetailText(f"ditto seeds={len(seeds)} regularization={DITTO_PRIMARY_REGULARIZATION.value}"),
        method_outcomes=_method_outcomes(
            ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
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


def _dispatch_temporal(seeds: tuple[Seed, ...], output_root: Path, overwrite: OverwriteMode) -> DispatchOutcome:
    results = tuple(run_temporal_seed(seed, output_root=output_root, overwrite=overwrite.requested) for seed in seeds)
    declared = _declared_methods(ExperimentId.EDGE_ONE_SHOT_RECALIBRATION)
    completed = frozenset(declared)
    for result in results:
        per_seed: set[FederatedThresholdMethod] = set()
        for state in (result.static_reference, result.frozen_future, result.recalibrated_future):
            per_seed.update(state.completed_threshold_methods)
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
            detail = DetailText("declared but not completed in this execution")
        outcomes.append(ThresholdMethodOutcome(method=method, status=status, detail=detail))
    return DispatchOutcome(detail=DetailText(f"temporal seeds={len(seeds)}"), method_outcomes=tuple(outcomes))


def _dispatch_robustness(
    experiment_id: ExperimentId,
    runner: RobustnessRunner,
    seeds: tuple[Seed, ...],
    output_root: Path,
    overwrite: OverwriteMode,
) -> DispatchOutcome:
    results = tuple(runner(seed, output_root=output_root, overwrite=overwrite.requested) for seed in seeds)
    if experiment_id is ExperimentId.SIZE_AWARE_SHRINKAGE:
        declared = _declared_methods(experiment_id)
        completed = frozenset(declared)
        for result in results:
            completed = completed.intersection(result.completed_threshold_methods)
        outcomes = tuple(
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
    else:
        outcomes = _method_outcomes(experiment_id, tuple(item.completed_threshold_methods for item in results))
    return DispatchOutcome(detail=DetailText(f"{experiment_id.value} seeds={len(seeds)}"), method_outcomes=outcomes)


def _dispatch_estimation(
    experiment_id: ExperimentId,
    runner: FederatedEstimationRunner,
    seeds: tuple[Seed, ...],
    output_root: Path,
    overwrite: OverwriteMode,
) -> DispatchOutcome:
    results = tuple(runner(seed, output_root=output_root, overwrite=overwrite.requested) for seed in seeds)
    return DispatchOutcome(
        detail=DetailText(f"{experiment_id.value} seeds={len(seeds)}"),
        method_outcomes=_method_outcomes(experiment_id, tuple(item.completed_threshold_methods for item in results)),
    )


def _dispatch_heterogeneity(seeds: tuple[Seed, ...], output_root: Path, overwrite: OverwriteMode) -> DispatchOutcome:
    results = tuple(
        run_controlled_heterogeneity_sweep_seed(seed, output_root=output_root, overwrite=overwrite.requested)
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
) -> DispatchOutcome:
    declaration = _declaration(experiment_id)
    results = tuple(
        execute_declared_experiment_seed(
            declaration=declaration,
            seed_cohort=SeedCohort(values=(seed,)),
            reason=f"registered supplementary recipe for {experiment_id.value}",
            output_root=output_root,
            overwrite=overwrite.requested,
        )
        for seed in seeds
    )
    return DispatchOutcome(
        detail=DetailText(f"{experiment_id.value} seeds={len(seeds)}"),
        method_outcomes=_method_outcomes(experiment_id, tuple(item.completed_threshold_methods for item in results)),
    )


def _dispatch_analysis(experiment_id: ExperimentId) -> DispatchOutcome:
    return DispatchOutcome(
        detail=DetailText(f"analysis-only experiment {experiment_id.value} reuses frozen confirmatory scores"),
        method_outcomes=tuple(
            ThresholdMethodOutcome(
                method=method,
                status=ThresholdMethodExecutionStatus.COMPLETED,
                detail=DetailText("analysis-only experiment reuses frozen confirmatory score artifacts"),
            )
            for method in _declared_methods(experiment_id)
        ),
    )


def _report_confirmatory(experiment_id: ExperimentId, overwrite: OverwriteMode) -> tuple[tuple[Path, ...], DetailText]:
    del experiment_id, overwrite
    path = analyze_confirmatory_campaign(anchor_gate_diagnostics_directory=ANCHOR_DIAGNOSTICS_DIRECTORY)
    return (path,), DetailText(str(path))


def _report_external(experiment_id: ExperimentId, overwrite: OverwriteMode) -> tuple[tuple[Path, ...], DetailText]:
    if experiment_id is ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION:
        result = analyze_external_validation_campaign(output_root=OUTPUTS_ROOT, overwrite=overwrite.requested)
    elif experiment_id is ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY:
        result = analyze_ciciot_boundary_campaign(output_root=OUTPUTS_ROOT, overwrite=overwrite.requested)
    else:
        raise ReportEvidenceError(f"unsupported external report: {experiment_id.value}")
    return (result.output_directory,), DetailText(str(result.output_directory))


def _report_heterogeneity(experiment_id: ExperimentId, overwrite: OverwriteMode) -> tuple[tuple[Path, ...], DetailText]:
    if experiment_id is ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP:
        path = analyze_controlled_heterogeneity_sweep(overwrite=overwrite.requested)
    elif experiment_id is ExperimentId.PER_CLIENT_SCORE_GEOMETRY:
        path = analyze_per_client_score_geometry(overwrite=overwrite.requested)
    elif experiment_id is ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION:
        path = analyze_heterogeneity_benefit_association(overwrite=overwrite.requested)
    elif experiment_id is ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF:
        path = analyze_threshold_movement_tradeoff(overwrite=overwrite.requested)
    else:
        raise ReportEvidenceError(f"unsupported heterogeneity report: {experiment_id.value}")
    return (path,), DetailText(str(path))


def _report_fedprox(experiment_id: ExperimentId, overwrite: OverwriteMode) -> tuple[tuple[Path, ...], DetailText]:
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
                root / TrainingStressArtifactName.PRIMARY_COEFFICIENT_DECISION,
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
            if overwrite.requested and output.exists():
                rmtree(output)
            analyze_fedprox_absorption(observations, output_directory=output)
            paths.append(output)
    except ScientificContractError as error:
        raise ReportEvidenceError(str(error), subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST) from error
    return tuple(paths), DetailText(f"coefficients={len(paths) - 1}")


def _report_ditto(experiment_id: ExperimentId, overwrite: OverwriteMode) -> tuple[tuple[Path, ...], DetailText]:
    del experiment_id
    from datp_core.experiments.training_stress import (
        analyze_ditto_absorption,
        ditto_analysis_directory,
        load_ditto_stress_test_evidence,
    )

    output = ditto_analysis_directory(DITTO_PRIMARY_REGULARIZATION, output_root=OUTPUTS_ROOT)
    if overwrite.requested and output.exists():
        rmtree(output)
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
            item.personalized_coordinate.training_seed,
            experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        )
        for item in results
    )
    analyze_ditto_absorption(results, reference_evidence=references, output_directory=output)
    return (output,), DetailText(f"analysis={output}")


def _report_temporal(experiment_id: ExperimentId, overwrite: OverwriteMode) -> tuple[tuple[Path, ...], DetailText]:
    del experiment_id
    seeds = load_temporal_campaign_seeds(output_root=OUTPUTS_ROOT)
    campaign = TemporalCampaignResult(seeds=seeds, analyses=())
    analyses = analyze_temporal_campaign(campaign, output_root=OUTPUTS_ROOT, overwrite=overwrite.requested)
    paths = tuple(item.output_directory for item in analyses)
    return paths, DetailText(f"temporal_methods={len(paths)}")


def _report_robustness(experiment_id: ExperimentId, overwrite: OverwriteMode) -> tuple[tuple[Path, ...], DetailText]:
    if experiment_id is ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY:
        paths, detail = report_shared_construction_sensitivity(experiment_id, overwrite.requested)
    elif experiment_id is ExperimentId.QUANTILE_SENSITIVITY:
        paths, detail = report_quantile_sensitivity(experiment_id, overwrite.requested)
    elif experiment_id is ExperimentId.CALIBRATION_SIZE_ABLATION:
        paths, detail = report_calibration_size_ablation(experiment_id, overwrite.requested)
    elif experiment_id is ExperimentId.FIXED_SHRINKAGE_CURVE:
        paths, detail = report_fixed_shrinkage_curve(experiment_id, overwrite.requested)
    elif experiment_id is ExperimentId.SIZE_AWARE_SHRINKAGE:
        paths, detail = report_size_aware_shrinkage(experiment_id, overwrite.requested)
    elif experiment_id is ExperimentId.LOCAL_CONFORMAL_COVERAGE:
        paths, detail = report_local_conformal_coverage(experiment_id, overwrite.requested)
    else:
        raise ReportEvidenceError(f"unsupported threshold robustness report: {experiment_id.value}")
    return paths, DetailText(detail)


def _report_estimation(experiment_id: ExperimentId, overwrite: OverwriteMode) -> tuple[tuple[Path, ...], DetailText]:
    if experiment_id is ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON:
        paths, detail = report_federated_benign_statistics_comparison(experiment_id, overwrite.requested)
    elif experiment_id is ExperimentId.FEDERATED_QUANTILE_ESTIMATION:
        paths, detail = report_federated_quantile_estimation(experiment_id, overwrite.requested)
    elif experiment_id is ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY:
        paths, detail = report_fixed_coefficient_statistics_sensitivity(experiment_id, overwrite.requested)
    else:
        raise ReportEvidenceError(f"unsupported federated estimation report: {experiment_id.value}")
    return paths, DetailText(detail)


def _supplementary_directory(experiment_id: ExperimentId) -> Path:
    return OUTPUTS_ROOT / ResearchDirectory.SUPPLEMENTARY / experiment_id.value


def _report_supplementary(experiment_id: ExperimentId, overwrite: OverwriteMode) -> tuple[tuple[Path, ...], DetailText]:
    from datp_core.app.campaign import seed_cohort_for

    declaration = _declaration(experiment_id)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=seed_cohort_for(experiment_id),
        evidence=(
            PlanningEvidence(
                experiment=experiment_id,
                disposition=PlanDisposition.EXECUTABLE,
                reason="supplementary evidence report consumes the registered experiment recipe",
            ),
        ),
    )
    report_path = _supplementary_directory(experiment_id) / ResearchArtifact.EVIDENCE_REPORT
    if report_path.is_file() and not overwrite.requested:
        return (report_path,), DetailText(f"reused {report_path}")
    lines = [
        "# DATP-Core Supplementary Evidence",
        "",
        f"Experiment: `{experiment_id.value}`",
        f"Evidence role: `{declaration.role.value}`",
        f"Population: `{declaration.population.value}`",
        "",
        "| Seed | Threshold method | Metric | Status | Value | Evidence checksum |",
        "|---:|---|---|---|---:|---|",
    ]
    seen: set[tuple[Seed, FederatedThresholdMethod, str]] = set()
    for entry in plan.executable:
        coordinate = entry.coordinate
        key = (coordinate.training_seed, coordinate.threshold_method, coordinate.metric.value)
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
                f"missing evaluation evidence for {coordinate.stable_key}: {document_path}",
                subject=experiment_id,
            )
        document = load_evaluation_document(document_path)
        metric = metric_by_id(document.population.metrics, coordinate.metric)
        value = f"{metric.value.value:.12g}" if isinstance(metric, AvailableMetric) else "—"
        lines.append(
            f"| {coordinate.training_seed.value} | {coordinate.threshold_method.value} | "
            f"{coordinate.metric.value} | {metric.status.value} | {value} | {canonical_checksum(document).value} |"
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomically(report_path, "\n".join(lines) + "\n")
    return (report_path,), DetailText(f"generated {report_path}")


def _confirmatory_marker(experiment_id: ExperimentId) -> bool:
    del experiment_id
    return (
        OUTPUTS_ROOT
        / ConfirmatoryAssetDirectory.ROOT
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / ConfirmatoryAssetDirectory.ANALYSIS
        / AnalysisAssetName.COMPLETE
    ).is_file()


def _external_marker(experiment_id: ExperimentId) -> bool:
    declaration = _declaration(experiment_id)
    return (
        OUTPUTS_ROOT
        / BoundedExternalAssetDirectory.ANALYSIS
        / experiment_id.value
        / declaration.population.value
        / AnalysisAssetName.COMPLETE
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
        fedprox_stress_test_root(output_root=OUTPUTS_ROOT) / TrainingStressArtifactName.PRIMARY_COEFFICIENT_DECISION
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

    output = ditto_analysis_directory(DITTO_PRIMARY_REGULARIZATION, output_root=OUTPUTS_ROOT)
    return (output / PUBLICATION_FILENAME).is_file() and (output / MECHANISM_REPORT_FILENAME).is_file()


def _temporal_marker(experiment_id: ExperimentId) -> bool:
    declaration = _declaration(experiment_id)
    return all(
        (
            OUTPUTS_ROOT
            / ExecutionRootDirectory.BOUNDED_EVIDENCE
            / experiment_id.value
            / declaration.population.value
            / declaration.role.value
            / TemporalArtifactDirectory.ANALYSIS
            / method.value
            / AnalysisAssetName.COMPLETE
        ).is_file()
        for method in declaration.federated_thresholds
    )


def _heterogeneity_marker(experiment_id: ExperimentId) -> bool:
    population = (
        PopulationId.NBAIOT_DIRICHLET_CLIENTS
        if experiment_id is ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP
        else PopulationId.NBAIOT_NATURAL_DEVICES
    )
    output = (
        OUTPUTS_ROOT
        / MechanismAnalysisDirectory.ROOT
        / experiment_id.value
        / population.value
        / MechanismAnalysisDirectory.ANALYSIS
    )
    return (output / PUBLICATION_FILENAME).is_file() and (output / MECHANISM_REPORT_FILENAME).is_file()


def _robustness_marker(experiment_id: ExperimentId) -> bool:
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
    raise ScientificContractError(f"unknown threshold-robustness experiment: {experiment_id.value}")


def _estimation_marker(experiment_id: ExperimentId) -> bool:
    if experiment_id is ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON:
        return federated_benign_statistics_comparison_analysis_marker_present(experiment_id)
    if experiment_id is ExperimentId.FEDERATED_QUANTILE_ESTIMATION:
        return federated_quantile_estimation_analysis_marker_present(experiment_id)
    if experiment_id is ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY:
        return fixed_coefficient_statistics_sensitivity_analysis_marker_present(experiment_id)
    raise ScientificContractError(f"unknown federated threshold-estimation experiment: {experiment_id.value}")


def _supplementary_marker(experiment_id: ExperimentId) -> bool:
    return (_supplementary_directory(experiment_id) / ResearchArtifact.EVIDENCE_REPORT).is_file()


def _external_recipe(experiment_id: ExperimentId) -> DispatchHandler:
    def dispatch(seeds: tuple[Seed, ...], output_root: Path, overwrite: OverwriteMode) -> DispatchOutcome:
        return _dispatch_external(experiment_id, seeds, output_root, overwrite)

    return dispatch


def _robustness_recipe(experiment_id: ExperimentId, runner: RobustnessRunner) -> DispatchHandler:
    def dispatch(seeds: tuple[Seed, ...], output_root: Path, overwrite: OverwriteMode) -> DispatchOutcome:
        return _dispatch_robustness(experiment_id, runner, seeds, output_root, overwrite)

    return dispatch


def _estimation_recipe(experiment_id: ExperimentId, runner: FederatedEstimationRunner) -> DispatchHandler:
    def dispatch(seeds: tuple[Seed, ...], output_root: Path, overwrite: OverwriteMode) -> DispatchOutcome:
        return _dispatch_estimation(experiment_id, runner, seeds, output_root, overwrite)

    return dispatch


def _declared_recipe(experiment_id: ExperimentId) -> DispatchHandler:
    def dispatch(seeds: tuple[Seed, ...], output_root: Path, overwrite: OverwriteMode) -> DispatchOutcome:
        return _dispatch_declared(experiment_id, seeds, output_root, overwrite)

    return dispatch


def _analysis_recipe(experiment_id: ExperimentId) -> DispatchHandler:
    def dispatch(seeds: tuple[Seed, ...], output_root: Path, overwrite: OverwriteMode) -> DispatchOutcome:
        del seeds, output_root, overwrite
        return _dispatch_analysis(experiment_id)

    return dispatch


EXPERIMENT_RECIPES: tuple[ExperimentRecipe, ...] = (
    ExperimentRecipe(
        experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_dispatch_confirmatory,
        report=_report_confirmatory,
        analysis_marker=_confirmatory_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.FAMILY_AND_GROUPED_GRANULARITY,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_dispatch_family,
        report=_report_supplementary,
        analysis_marker=_supplementary_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_dispatch_fedprox,
        report=_report_fedprox,
        analysis_marker=_fedprox_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_dispatch_ditto,
        report=_report_ditto,
        analysis_marker=_ditto_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_estimation_recipe(
            ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON, run_federated_benign_statistics_comparison_seed
        ),
        report=_report_estimation,
        analysis_marker=_estimation_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.FEDERATED_QUANTILE_ESTIMATION,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_estimation_recipe(ExperimentId.FEDERATED_QUANTILE_ESTIMATION, run_federated_quantile_estimation_seed),
        report=_report_estimation,
        analysis_marker=_estimation_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_estimation_recipe(
            ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY, run_fixed_coefficient_statistics_sensitivity_seed
        ),
        report=_report_estimation,
        analysis_marker=_estimation_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        anchor_requirement=AnchorRequirement.NOT_REQUIRED,
        dispatch=_external_recipe(ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION),
        report=_report_external,
        analysis_marker=_external_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
        anchor_requirement=AnchorRequirement.NOT_REQUIRED,
        dispatch=_external_recipe(ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY),
        report=_report_external,
        analysis_marker=_external_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        anchor_requirement=AnchorRequirement.NOT_REQUIRED,
        dispatch=_dispatch_temporal,
        report=_report_temporal,
        analysis_marker=_temporal_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_robustness_recipe(
            ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY, run_shared_construction_sensitivity_seed
        ),
        report=_report_robustness,
        analysis_marker=_robustness_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.QUANTILE_SENSITIVITY,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_robustness_recipe(ExperimentId.QUANTILE_SENSITIVITY, run_quantile_sensitivity_seed),
        report=_report_robustness,
        analysis_marker=_robustness_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.CALIBRATION_SIZE_ABLATION,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_robustness_recipe(ExperimentId.CALIBRATION_SIZE_ABLATION, run_calibration_size_ablation_seed),
        report=_report_robustness,
        analysis_marker=_robustness_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.FIXED_SHRINKAGE_CURVE,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_robustness_recipe(ExperimentId.FIXED_SHRINKAGE_CURVE, run_fixed_shrinkage_curve_seed),
        report=_report_robustness,
        analysis_marker=_robustness_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.SIZE_AWARE_SHRINKAGE,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_robustness_recipe(ExperimentId.SIZE_AWARE_SHRINKAGE, run_size_aware_shrinkage_seed),
        report=_report_robustness,
        analysis_marker=_robustness_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.LOCAL_CONFORMAL_COVERAGE,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_robustness_recipe(ExperimentId.LOCAL_CONFORMAL_COVERAGE, run_local_conformal_coverage_seed),
        report=_report_robustness,
        analysis_marker=_robustness_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_dispatch_heterogeneity,
        report=_report_heterogeneity,
        analysis_marker=_heterogeneity_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.PER_CLIENT_SCORE_GEOMETRY,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_analysis_recipe(ExperimentId.PER_CLIENT_SCORE_GEOMETRY),
        report=_report_heterogeneity,
        analysis_marker=_heterogeneity_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_analysis_recipe(ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION),
        report=_report_heterogeneity,
        analysis_marker=_heterogeneity_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_analysis_recipe(ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF),
        report=_report_heterogeneity,
        analysis_marker=_heterogeneity_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.GROUP_MEDIAN_SUPPLEMENT,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_declared_recipe(ExperimentId.GROUP_MEDIAN_SUPPLEMENT),
        report=_report_supplementary,
        analysis_marker=_supplementary_marker,
    ),
    ExperimentRecipe(
        experiment=ExperimentId.OPTIONAL_EQUITY_INDICES,
        anchor_requirement=AnchorRequirement.REQUIRED,
        dispatch=_declared_recipe(ExperimentId.OPTIONAL_EQUITY_INDICES),
        report=_report_supplementary,
        analysis_marker=_supplementary_marker,
    ),
)


def registered_experiment_ids() -> tuple[ExperimentId, ...]:
    return tuple(recipe.experiment for recipe in EXPERIMENT_RECIPES)


def anchor_gated_experiment_ids() -> tuple[ExperimentId, ...]:
    return tuple(
        recipe.experiment for recipe in EXPERIMENT_RECIPES if recipe.anchor_requirement is AnchorRequirement.REQUIRED
    )


def recipe_for(experiment_id: ExperimentId) -> ExperimentRecipe:
    declaration = _declaration(experiment_id)
    if declaration.readiness is ExperimentReadiness.SUPPRESSED:
        raise ScientificContractError(
            f"experiment is intentionally suppressed: {experiment_id.value}", subject=experiment_id
        )
    matches = tuple(recipe for recipe in EXPERIMENT_RECIPES if recipe.experiment is experiment_id)
    if len(matches) != 1:
        raise ScientificContractError(
            f"experiment recipe must resolve exactly once: {experiment_id.value}", subject=experiment_id
        )
    return matches[0]

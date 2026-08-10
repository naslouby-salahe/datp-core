"""Threshold-robustness experiment runners and typed evidence summaries."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from datp_core.analysis.descriptive import summarize_cross_seed_metric_values
from datp_core.analysis.metrics.models import metric_by_id
from datp_core.analysis.metrics.population import calculate_population_metrics
from datp_core.analysis.metrics.semantics import metric_value
from datp_core.app.planning import PlanReason, expand_experiment_plan
from datp_core.artifacts.layout import evaluation_run_directory
from datp_core.artifacts.repositories.evaluations import FederatedEvaluationAssetName
from datp_core.artifacts.serializers.json import serialize_json_model
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    AnalysisMarkerText,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
)
from datp_core.core.numeric import (
    CalibrationSize,
    ClientCount,
    MetricDelta,
    MetricValue,
    Quantile,
    Ratio,
    ReplicateIndex,
    Seed,
    SeedCount,
    SeedObservationCount,
    ShrinkageWeight,
)
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.experiments.common.coordinates import ExperimentCoordinate
from datp_core.experiments.common.reports import (
    AnalysisReportFinalizationInput,
    AnalysisReportPublication,
    finalize_analysis_report,
)
from datp_core.experiments.common.seeds import CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.experiments.execution import execute_declared_experiment_seed
from datp_core.experiments.execution.evidence import load_evaluation_document, population_metric
from datp_core.experiments.execution.layout import EvaluationRunAssetDirectory
from datp_core.experiments.execution.models import ProgressHook
from datp_core.experiments.registry import require_experiment_declaration
from datp_core.experiments.threshold_robustness.cohorts import (
    compute_intersection_cohort,
    extract_feasible_clients_by_size,
)
from datp_core.runtime.configuration import OUTPUTS_ROOT
from datp_core.thresholds.contracts import ThresholdInfeasibilityReason
from datp_core.thresholds.protocols import (
    CALIBRATION_SIZES,
    QUANTILE_GRID,
    CalibrationSizeClassification,
    classify_calibration_size,
    require_calibration_subsample_replicate_count,
)

if TYPE_CHECKING:
    from datp_core.analysis.metrics.federated import CalibrationSizeAblationCell, FederatedEvaluationDocument


class ThresholdRobustnessArtifactName(StrEnum):
    ROOT = "threshold_robustness"
    ANALYSIS = "analysis"
    SUMMARY = "summary.json"


class ThresholdRobustnessAnalysisMarker(StrEnum):
    SHARED_CONSTRUCTION_SENSITIVITY = "shared_construction_sensitivity_analysis_complete"
    QUANTILE_SENSITIVITY = "quantile_sensitivity_analysis_complete"
    FIXED_SHRINKAGE_CURVE = "fixed_shrinkage_curve_analysis_complete"
    SIZE_AWARE_SHRINKAGE = "size_aware_shrinkage_analysis_complete"
    LOCAL_CONFORMAL_COVERAGE = "local_conformal_coverage_analysis_complete"


class ThresholdRobustnessSeedResult(StrictModel):
    training_seed: Seed
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


class MethodCvSummary(StrictModel):
    method: FederatedThresholdMethod
    seed_count: SeedCount
    mean_cv_fpr: MetricValue | None
    mean_worst_client_fpr: MetricValue | None
    cv_fpr_across_seeds: MetricValue | None


class MethodCvSummaryReport(StrictModel):
    experiment: ExperimentId
    rows: tuple[MethodCvSummary, ...]


class QuantileSummary(StrictModel):
    method: FederatedThresholdMethod
    quantile: Quantile
    summary: MethodCvSummary


class QuantileSummaryReport(StrictModel):
    experiment: ExperimentId
    rows: tuple[QuantileSummary, ...]


class CalibrationSizeAblationRow(StrictModel):
    seed: Seed
    method: FederatedThresholdMethod
    calibration_size: CalibrationSize
    size_classification: CalibrationSizeClassification
    replicate: ReplicateIndex
    cv_fpr: MetricValue | None
    worst_client_fpr: MetricValue | None
    p10_macro_f1: MetricValue | None


class CalibrationSizeFixedCohortRow(StrictModel):
    """Population-level cross-size row restricted to the intersection of feasible clients.

    Descriptive per-size rows (`CalibrationSizeAblationRow`) independently include every client
    feasible at that one size and must never be mixed with this fixed-cohort comparison.
    """

    seed: Seed
    method: FederatedThresholdMethod
    calibration_size: CalibrationSize
    replicate: ReplicateIndex
    intersection_client_count: ClientCount
    coverage: Ratio
    cv_fpr: MetricValue | None
    worst_client_fpr: MetricValue | None
    p10_macro_f1: MetricValue | None


class CalibrationSizeAblationReport(StrictModel):
    experiment: ExperimentId
    rows: tuple[CalibrationSizeAblationRow, ...]
    fixed_cohort_rows: tuple[CalibrationSizeFixedCohortRow, ...] = ()


class ShrinkageCurveRow(StrictModel):
    seed: Seed
    lambda_weight: ShrinkageWeight
    cv_fpr: MetricValue | None
    worst_client_fpr: MetricValue | None


class ShrinkageCurveReport(StrictModel):
    experiment: ExperimentId
    rows: tuple[ShrinkageCurveRow, ...]


class ConformalCoverageRow(StrictModel):
    seed: Seed
    client: ClientIdentity
    target_coverage: Ratio
    achieved_coverage: Ratio | None
    signed_coverage_error: MetricDelta | None
    absolute_coverage_error: MetricValue | None
    client_fpr: MetricValue | None


class ConformalCoverageReport(StrictModel):
    experiment: ExperimentId
    rows: tuple[ConformalCoverageRow, ...]


class SizeAwareShrinkageReport(StrictModel):
    experiment: ExperimentId
    unavailable_reason: ThresholdInfeasibilityReason
    shared_threshold: MethodCvSummary
    local_threshold: MethodCvSummary


def _analysis_directory(experiment_id: ExperimentId, population: PopulationId) -> Path:
    return (
        OUTPUTS_ROOT
        / ThresholdRobustnessArtifactName.ROOT
        / experiment_id.value
        / population.value
        / ThresholdRobustnessArtifactName.ANALYSIS
    )


def _complete_marker(experiment_id: ExperimentId, population: PopulationId) -> Path:
    return _summary_path(experiment_id, population)


def _summary_path(experiment_id: ExperimentId, population: PopulationId) -> Path:
    return _analysis_directory(experiment_id, population) / ThresholdRobustnessArtifactName.SUMMARY


def _evaluation_document_path(output_root: Path, coordinate: ExperimentCoordinate) -> Path:
    return (
        evaluation_run_directory(output_root, coordinate)
        / EvaluationRunAssetDirectory.EVALUATION
        / FederatedEvaluationAssetName.DOCUMENT
    )


def _evaluation_document_for_seed(
    seed: Seed,
    method: FederatedThresholdMethod,
    experiment_id: ExperimentId,
    output_root: Path,
    *,
    quantile: Quantile | None = None,
) -> FederatedEvaluationDocument:
    declaration = require_experiment_declaration(experiment_id)
    plan = expand_experiment_plan(declarations=(declaration,), seed_cohort=SeedCohort(values=(seed,)))
    matches = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.coordinate.threshold_method is method
        and entry.coordinate.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION
        and (quantile is None or entry.coordinate.threshold_quantile == quantile)
    )
    if len(matches) != 1:
        quantile_suffix = f" q={quantile.value}" if quantile is not None else ""
        raise ScientificContractError(
            ErrorMessage(f"evaluation coordinate for {method.value}{quantile_suffix} must resolve exactly once")
        )
    path = _evaluation_document_path(output_root, matches[0])
    if not path.is_file():
        raise ScientificContractError(ErrorMessage(f"missing evaluation document: {path}"))
    return load_evaluation_document(path)


def _run_robustness_seed(
    experiment_id: ExperimentId,
    training_seed: Seed,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None,
) -> ThresholdRobustnessSeedResult:
    declaration = require_experiment_declaration(experiment_id)
    result = execute_declared_experiment_seed(
        declaration=declaration,
        seed_cohort=SeedCohort(values=(training_seed,)),
        reason=PlanReason(f"threshold robustness entry point for {experiment_id.value}"),
        output_root=output_root,
        overwrite=overwrite,
        progress=progress,
    )
    return ThresholdRobustnessSeedResult(
        training_seed=training_seed,
        completed_threshold_methods=result.completed_threshold_methods,
    )


def _method_summary(
    method: FederatedThresholdMethod, documents: tuple[FederatedEvaluationDocument, ...]
) -> MethodCvSummary:
    cv_values = tuple(population_metric(document, MetricId.FPR_COEFFICIENT_OF_VARIATION) for document in documents)
    worst_values = tuple(population_metric(document, MetricId.WORST_CLIENT_FPR) for document in documents)
    cv_summary = summarize_cross_seed_metric_values(cv_values)
    worst_summary = summarize_cross_seed_metric_values(worst_values)
    return MethodCvSummary(
        method=method,
        seed_count=SeedCount(len(documents)),
        mean_cv_fpr=cv_summary.mean,
        mean_worst_client_fpr=worst_summary.mean,
        cv_fpr_across_seeds=cv_summary.coefficient_of_variation,
    )


def run_shared_construction_sensitivity_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(
        ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY,
        training_seed,
        output_root,
        overwrite,
        progress,
    )


def report_shared_construction_sensitivity(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> AnalysisReportPublication:
    del overwrite
    declaration = require_experiment_declaration(experiment_id)
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    rows: list[MethodCvSummary] = []
    missing = 0
    for method in declaration.federated_thresholds:
        documents: list[FederatedEvaluationDocument] = []
        for seed in CONFIRMATORY_SEED_COHORT.values:
            try:
                documents.append(_evaluation_document_for_seed(seed, method, experiment_id, OUTPUTS_ROOT))
            except ScientificContractError:
                missing += 1
        if documents:
            rows.append(_method_summary(method, tuple(documents)))
    serialize_json_model(
        MethodCvSummaryReport(experiment=experiment_id, rows=tuple(rows)),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            marker=_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(ThresholdRobustnessAnalysisMarker.SHARED_CONSTRUCTION_SENSITIVITY),
        )
    )


def shared_construction_sensitivity_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


def run_quantile_sensitivity_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(ExperimentId.QUANTILE_SENSITIVITY, training_seed, output_root, overwrite, progress)


def report_quantile_sensitivity(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> AnalysisReportPublication:
    del overwrite
    declaration = require_experiment_declaration(experiment_id)
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    rows: list[QuantileSummary] = []
    missing = 0
    for method in declaration.federated_thresholds:
        for quantile in QUANTILE_GRID:
            documents: list[FederatedEvaluationDocument] = []
            for seed in CONFIRMATORY_SEED_COHORT.values:
                try:
                    documents.append(
                        _evaluation_document_for_seed(
                            seed,
                            method,
                            experiment_id,
                            OUTPUTS_ROOT,
                            quantile=quantile,
                        )
                    )
                except ScientificContractError:
                    missing += 1
            if documents:
                rows.append(
                    QuantileSummary(
                        method=method,
                        quantile=quantile,
                        summary=_method_summary(method, tuple(documents)),
                    )
                )
    serialize_json_model(
        QuantileSummaryReport(experiment=experiment_id, rows=tuple(rows)),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            marker=_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(ThresholdRobustnessAnalysisMarker.QUANTILE_SENSITIVITY),
        )
    )


def quantile_sensitivity_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


def run_calibration_size_ablation_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> ThresholdRobustnessSeedResult:
    require_calibration_subsample_replicate_count()
    return _run_robustness_seed(ExperimentId.CALIBRATION_SIZE_ABLATION, training_seed, output_root, overwrite, progress)


def report_calibration_size_ablation(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> AnalysisReportPublication:
    del overwrite
    replicate_count = require_calibration_subsample_replicate_count()
    declaration = require_experiment_declaration(experiment_id)
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    rows: list[CalibrationSizeAblationRow] = []
    fixed_cohort_rows: list[CalibrationSizeFixedCohortRow] = []
    missing = 0
    for method in declaration.federated_thresholds:
        for seed in CONFIRMATORY_SEED_COHORT.values:
            try:
                document = _evaluation_document_for_seed(seed, method, experiment_id, OUTPUTS_ROOT)
            except ScientificContractError:
                missing += 1
                continue
            cells = document.diagnostics.calibration_size_ablation
            for cell in cells:
                metrics = cell.population.metrics
                rows.append(
                    CalibrationSizeAblationRow(
                        seed=seed,
                        method=method,
                        calibration_size=cell.calibration_size,
                        size_classification=classify_calibration_size(cell.calibration_size),
                        replicate=cell.replicate_index,
                        cv_fpr=metric_value(metric_by_id(metrics, MetricId.FPR_COEFFICIENT_OF_VARIATION)),
                        worst_client_fpr=metric_value(metric_by_id(metrics, MetricId.WORST_CLIENT_FPR)),
                        p10_macro_f1=metric_value(metric_by_id(metrics, MetricId.P10_BINARY_MACRO_F1)),
                    )
                )
            fixed_cohort_rows.extend(_fixed_cohort_rows_for_seed(seed, method, cells))
    serialize_json_model(
        CalibrationSizeAblationReport(
            experiment=experiment_id,
            rows=tuple(rows),
            fixed_cohort_rows=tuple(fixed_cohort_rows),
        ),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            marker=_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(
                "calibration_size_ablation_analysis_complete "
                f"sizes={len(CALIBRATION_SIZES)} replicates={replicate_count.value}"
            ),
        )
    )


def _fixed_cohort_rows_for_seed(
    seed: Seed,
    method: FederatedThresholdMethod,
    cells: tuple[CalibrationSizeAblationCell, ...],
) -> tuple[CalibrationSizeFixedCohortRow, ...]:
    """Restrict each replicate's cells to the intersection of clients feasible at every locked size."""
    by_replicate: dict[ReplicateIndex, list[CalibrationSizeAblationCell]] = {}
    for cell in cells:
        by_replicate.setdefault(cell.replicate_index, []).append(cell)

    def _generate():
        for replicate_index, replicate_cells in by_replicate.items():
            sizes = tuple(cell.calibration_size for cell in replicate_cells)
            feasible_by_size = extract_feasible_clients_by_size(tuple(replicate_cells))
            union_clients = frozenset(client for clients in feasible_by_size.values() for client in clients)
            total_eligible = ClientCount(len(union_clients))
            intersection_cohort = compute_intersection_cohort(sizes, feasible_by_size, total_eligible)
            for cell in replicate_cells:
                intersection_results = tuple(
                    result for result in cell.clients if result.client in intersection_cohort.intersection_clients
                )
                if not intersection_results:
                    continue
                population = calculate_population_metrics(intersection_results)
                yield CalibrationSizeFixedCohortRow(
                    seed=seed,
                    method=method,
                    calibration_size=cell.calibration_size,
                    replicate=replicate_index,
                    intersection_client_count=ClientCount(intersection_cohort.intersection_count.value),
                    coverage=Ratio(intersection_cohort.intersection_count.value / total_eligible.value),
                    cv_fpr=metric_value(metric_by_id(population.metrics, MetricId.FPR_COEFFICIENT_OF_VARIATION)),
                    worst_client_fpr=metric_value(metric_by_id(population.metrics, MetricId.WORST_CLIENT_FPR)),
                    p10_macro_f1=metric_value(metric_by_id(population.metrics, MetricId.P10_BINARY_MACRO_F1)),
                )

    return tuple(_generate())


def calibration_size_ablation_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


def run_fixed_shrinkage_curve_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(ExperimentId.FIXED_SHRINKAGE_CURVE, training_seed, output_root, overwrite, progress)


def report_fixed_shrinkage_curve(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> AnalysisReportPublication:
    del overwrite
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    rows: list[ShrinkageCurveRow] = []
    missing = 0
    for seed in CONFIRMATORY_SEED_COHORT.values:
        try:
            document = _evaluation_document_for_seed(
                seed,
                FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,
                experiment_id,
                OUTPUTS_ROOT,
            )
        except ScientificContractError:
            missing += 1
            continue
        for evaluation in document.diagnostics.shrinkage_curve:
            rows.append(
                ShrinkageCurveRow(
                    seed=seed,
                    lambda_weight=evaluation.lambda_weight,
                    cv_fpr=metric_value(
                        metric_by_id(evaluation.population.metrics, MetricId.FPR_COEFFICIENT_OF_VARIATION)
                    ),
                    worst_client_fpr=metric_value(
                        metric_by_id(evaluation.population.metrics, MetricId.WORST_CLIENT_FPR)
                    ),
                )
            )
    serialize_json_model(
        ShrinkageCurveReport(experiment=experiment_id, rows=tuple(rows)),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            marker=_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(ThresholdRobustnessAnalysisMarker.FIXED_SHRINKAGE_CURVE),
        )
    )


def fixed_shrinkage_curve_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


def run_size_aware_shrinkage_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> ThresholdRobustnessSeedResult:
    declaration = require_experiment_declaration(ExperimentId.SIZE_AWARE_SHRINKAGE)
    filtered = declaration.model_copy(
        update={
            "federated_thresholds": (
                FederatedThresholdMethod.SHARED_THRESHOLD,
                FederatedThresholdMethod.LOCAL_THRESHOLD,
            )
        }
    )
    result = execute_declared_experiment_seed(
        declaration=filtered,
        seed_cohort=SeedCohort(values=(training_seed,)),
        reason=PlanReason(
            "size-aware shrinkage executes its declared reference corners only because "
            "no lambda(n_k) function is declared"
        ),
        output_root=output_root,
        overwrite=overwrite,
        progress=progress,
    )
    return ThresholdRobustnessSeedResult(
        training_seed=training_seed,
        completed_threshold_methods=result.completed_threshold_methods,
    )


def report_size_aware_shrinkage(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> AnalysisReportPublication:
    del overwrite
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    missing = 0
    summaries: list[MethodCvSummary] = []
    for method in (FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD):
        documents: list[FederatedEvaluationDocument] = []
        for seed in CONFIRMATORY_SEED_COHORT.values:
            try:
                documents.append(_evaluation_document_for_seed(seed, method, experiment_id, OUTPUTS_ROOT))
            except ScientificContractError:
                missing += 1
        if documents:
            summaries.append(_method_summary(method, tuple(documents)))
    summary_by_method = {summary.method: summary for summary in summaries}
    if set(summary_by_method) != {
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    }:
        raise ScientificContractError(
            ErrorMessage("size-aware shrinkage report requires both executable reference corners")
        )
    serialize_json_model(
        SizeAwareShrinkageReport(
            experiment=experiment_id,
            unavailable_reason=ThresholdInfeasibilityReason.SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED,
            shared_threshold=summary_by_method[FederatedThresholdMethod.SHARED_THRESHOLD],
            local_threshold=summary_by_method[FederatedThresholdMethod.LOCAL_THRESHOLD],
        ),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            marker=_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(ThresholdRobustnessAnalysisMarker.SIZE_AWARE_SHRINKAGE),
        )
    )


def size_aware_shrinkage_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


def run_local_conformal_coverage_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(ExperimentId.LOCAL_CONFORMAL_COVERAGE, training_seed, output_root, overwrite, progress)


def _client_fpr_for(document: FederatedEvaluationDocument, client: ClientIdentity) -> MetricValue | None:
    for client_result in document.clients:
        if client_result.client == client:
            return metric_value(metric_by_id(client_result.metrics, MetricId.FALSE_POSITIVE_RATE))
    return None


def report_local_conformal_coverage(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> AnalysisReportPublication:
    del overwrite
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    rows: list[ConformalCoverageRow] = []
    missing = 0
    for seed in CONFIRMATORY_SEED_COHORT.values:
        try:
            document = _evaluation_document_for_seed(
                seed,
                FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD,
                experiment_id,
                OUTPUTS_ROOT,
            )
        except ScientificContractError:
            missing += 1
            continue
        for diagnostic in document.diagnostics.conformal_coverage:
            rows.append(
                ConformalCoverageRow(
                    seed=seed,
                    client=diagnostic.client,
                    target_coverage=Ratio(diagnostic.target_coverage.value),
                    achieved_coverage=(
                        None
                        if diagnostic.achieved_held_out_benign_coverage is None
                        else Ratio(diagnostic.achieved_held_out_benign_coverage.value)
                    ),
                    signed_coverage_error=(
                        None
                        if diagnostic.signed_coverage_error is None
                        else MetricDelta(diagnostic.signed_coverage_error.value)
                    ),
                    absolute_coverage_error=diagnostic.absolute_coverage_error,
                    client_fpr=_client_fpr_for(document, diagnostic.client),
                )
            )
    serialize_json_model(
        ConformalCoverageReport(experiment=experiment_id, rows=tuple(rows)),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            marker=_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(ThresholdRobustnessAnalysisMarker.LOCAL_CONFORMAL_COVERAGE),
        )
    )


def local_conformal_coverage_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()

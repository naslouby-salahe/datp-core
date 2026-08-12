from __future__ import annotations

from enum import StrEnum
from math import sqrt
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
    ThresholdEstimator,
)
from datp_core.core.numeric import (
    CalibrationSize,
    ClientCount,
    MetricDelta,
    MetricValue,
    NonNegativeIntegerValue,
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
from datp_core.thresholds.protocols import (
    CALIBRATION_SIZES,
    MINIMUM_BENIGN_SUPPORT,
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
    COMPLETE = "complete.marker"


class ThresholdRobustnessAnalysisMarker(StrEnum):
    SHARED_CONSTRUCTION_SENSITIVITY = "shared_construction_sensitivity_analysis_complete"
    QUANTILE_SENSITIVITY = "quantile_sensitivity_analysis_complete"
    FIXED_SHRINKAGE_CURVE = "fixed_shrinkage_curve_analysis_complete"
    SIZE_AWARE_SHRINKAGE = "size_aware_shrinkage_analysis_complete"
    LOCAL_CONFORMAL_COVERAGE = "local_conformal_coverage_analysis_complete"
    THRESHOLD_ESTIMATOR_SCOPE_SENSITIVITY = "threshold_estimator_scope_sensitivity_analysis_complete"


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


class EstimatorScopeSummary(StrictModel):
    estimator: ThresholdEstimator
    method: FederatedThresholdMethod
    summary: MethodCvSummary


class EstimatorScopeSummaryReport(StrictModel):
    experiment: ExperimentId
    rows: tuple[EstimatorScopeSummary, ...]


class CalibrationSizeAblationRow(StrictModel):
    seed: Seed
    method: FederatedThresholdMethod
    calibration_size: CalibrationSize
    size_classification: CalibrationSizeClassification
    replicate: ReplicateIndex
    cv_fpr: MetricValue | None
    worst_client_fpr: MetricValue | None
    p10_macro_f1: MetricValue | None
    mean_absolute_target_error: MetricValue | None
    worst_absolute_target_error: MetricValue | None
    mean_absolute_calibration_generalization_gap: MetricValue | None


class CalibrationSizeFixedCohortRow(StrictModel):
    seed: Seed
    method: FederatedThresholdMethod
    calibration_size: CalibrationSize
    replicate: ReplicateIndex
    intersection_client_count: ClientCount
    coverage: Ratio
    cv_fpr: MetricValue | None
    worst_client_fpr: MetricValue | None
    p10_macro_f1: MetricValue | None


class CalibrationThresholdStabilityRow(StrictModel):
    seed: Seed
    method: FederatedThresholdMethod
    calibration_size: CalibrationSize
    client: ClientIdentity
    full_calibration_local_threshold: MetricValue
    bias_threshold: MetricValue
    rmse_threshold: MetricValue


class CalibrationThresholdOrderRow(StrictModel):
    seed: Seed
    method: FederatedThresholdMethod
    calibration_size: CalibrationSize
    replicate: ReplicateIndex
    inverted_pair_count: NonNegativeIntegerValue
    comparable_pair_count: NonNegativeIntegerValue
    tied_pair_count: NonNegativeIntegerValue


class CalibrationSizeAblationReport(StrictModel):
    experiment: ExperimentId
    rows: tuple[CalibrationSizeAblationRow, ...]
    fixed_cohort_rows: tuple[CalibrationSizeFixedCohortRow, ...] = ()
    threshold_stability_rows: tuple[CalibrationThresholdStabilityRow, ...] = ()
    threshold_order_rows: tuple[CalibrationThresholdOrderRow, ...] = ()


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
    methods: tuple[MethodCvSummary, ...]
    clients: tuple[SizeAwareShrinkageClientRow, ...]


class SizeAwareShrinkageClientRow(StrictModel):
    seed: Seed
    client: ClientIdentity
    source_support: CalibrationSize
    used_support: CalibrationSize
    lambda_weight: ShrinkageWeight
    shared_threshold: MetricValue
    local_threshold: MetricValue
    size_aware_threshold: MetricValue
    fpr: MetricValue | None
    tpr: MetricValue | None
    macro_f1: MetricValue | None
    balanced_accuracy: MetricValue | None


def _analysis_directory(experiment_id: ExperimentId, population: PopulationId) -> Path:
    return (
        OUTPUTS_ROOT
        / ThresholdRobustnessArtifactName.ROOT
        / experiment_id.value
        / population.value
        / ThresholdRobustnessArtifactName.ANALYSIS
    )


def _complete_marker(experiment_id: ExperimentId, population: PopulationId) -> Path:
    return _analysis_directory(experiment_id, population) / ThresholdRobustnessArtifactName.COMPLETE


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
    estimator: ThresholdEstimator | None = None,
) -> FederatedEvaluationDocument:
    declaration = require_experiment_declaration(experiment_id)
    plan = expand_experiment_plan(declarations=(declaration,), seed_cohort=SeedCohort(values=(seed,)))
    matches = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.coordinate.threshold_method is method
        and entry.coordinate.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION
        and (quantile is None or entry.coordinate.threshold_quantile == quantile)
        and (estimator is None or entry.coordinate.threshold_estimator is estimator)
    )
    if len(matches) != 1:
        quantile_suffix = f" q={quantile.value}" if quantile is not None else ""
        estimator_suffix = f" estimator={estimator.value}" if estimator is not None else ""
        raise ScientificContractError(
            ErrorMessage(
                f"evaluation coordinate for {method.value}{quantile_suffix}{estimator_suffix} must resolve exactly once"
            )
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


def run_threshold_estimator_scope_sensitivity_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(
        ExperimentId.THRESHOLD_ESTIMATOR_SCOPE_SENSITIVITY,
        training_seed,
        output_root,
        overwrite,
        progress,
    )


def report_threshold_estimator_scope_sensitivity(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> AnalysisReportPublication:
    del overwrite
    declaration = require_experiment_declaration(experiment_id)
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    rows: list[EstimatorScopeSummary] = []
    missing = 0
    for estimator in ThresholdEstimator:
        for method in declaration.federated_thresholds:
            documents: list[FederatedEvaluationDocument] = []
            for seed in CONFIRMATORY_SEED_COHORT.values:
                try:
                    documents.append(
                        _evaluation_document_for_seed(
                            seed,
                            method,
                            experiment_id,
                            OUTPUTS_ROOT,
                            estimator=estimator,
                        )
                    )
                except ScientificContractError:
                    missing += 1
            if documents:
                rows.append(
                    EstimatorScopeSummary(
                        estimator=estimator,
                        method=method,
                        summary=_method_summary(method, tuple(documents)),
                    )
                )
    serialize_json_model(
        EstimatorScopeSummaryReport(experiment=experiment_id, rows=tuple(rows)),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            marker=_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(ThresholdRobustnessAnalysisMarker.THRESHOLD_ESTIMATOR_SCOPE_SENSITIVITY),
        )
    )


def threshold_estimator_scope_sensitivity_analysis_marker_present(experiment_id: ExperimentId) -> bool:
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
    threshold_stability_rows: list[CalibrationThresholdStabilityRow] = []
    threshold_order_rows: list[CalibrationThresholdOrderRow] = []
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
                operating_summary = cell.held_out_operating_point_summary
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
                        mean_absolute_target_error=(
                            None if operating_summary is None else operating_summary.mean_absolute_target_error
                        ),
                        worst_absolute_target_error=(
                            None if operating_summary is None else operating_summary.worst_absolute_target_error
                        ),
                        mean_absolute_calibration_generalization_gap=(
                            None
                            if operating_summary is None
                            else operating_summary.mean_absolute_calibration_generalization_gap
                        ),
                    )
                )
            fixed_cohort_rows.extend(_fixed_cohort_rows_for_seed(seed, method, cells))
            local_reference = _evaluation_document_for_seed(
                seed, FederatedThresholdMethod.LOCAL_THRESHOLD, experiment_id, OUTPUTS_ROOT
            )
            threshold_stability_rows.extend(
                _threshold_stability_rows_for_seed(seed, method, cells, local_reference)
            )
            threshold_order_rows.extend(_threshold_order_rows_for_seed(seed, method, cells, local_reference))
    serialize_json_model(
        CalibrationSizeAblationReport(
            experiment=experiment_id,
            rows=tuple(rows),
            fixed_cohort_rows=tuple(fixed_cohort_rows),
            threshold_stability_rows=tuple(threshold_stability_rows),
            threshold_order_rows=tuple(threshold_order_rows),
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


def _threshold_stability_rows_for_seed(
    seed: Seed,
    method: FederatedThresholdMethod,
    cells: tuple[CalibrationSizeAblationCell, ...],
    local_reference: FederatedEvaluationDocument,
) -> tuple[CalibrationThresholdStabilityRow, ...]:
    reference = {item.client: item.threshold for item in local_reference.clients}
    grouped: dict[tuple[CalibrationSize, ClientIdentity], list[MetricValue]] = {}
    for cell in cells:
        for client in cell.clients:
            if client.client not in reference:
                raise ScientificContractError(ErrorMessage("full-calibration local reference omits an ablation client"))
            grouped.setdefault((cell.calibration_size, client.client), []).append(MetricValue(client.threshold.value))
    rows: list[CalibrationThresholdStabilityRow] = []
    for (size, client), thresholds in sorted(grouped.items()):
        full = MetricValue(reference[client].value)
        differences = tuple(value.value - full.value for value in thresholds)
        rows.append(
            CalibrationThresholdStabilityRow(
                seed=seed,
                method=method,
                calibration_size=size,
                client=client,
                full_calibration_local_threshold=full,
                bias_threshold=MetricValue(sum(differences) / len(differences)),
                rmse_threshold=MetricValue(sqrt(sum(value**2 for value in differences) / len(differences))),
            )
        )
    return tuple(rows)


def _threshold_order_rows_for_seed(
    seed: Seed,
    method: FederatedThresholdMethod,
    cells: tuple[CalibrationSizeAblationCell, ...],
    local_reference: FederatedEvaluationDocument,
) -> tuple[CalibrationThresholdOrderRow, ...]:
    reference = {item.client: item.threshold.value for item in local_reference.clients}
    rows: list[CalibrationThresholdOrderRow] = []
    for cell in cells:
        clients = tuple(sorted(cell.clients, key=lambda item: item.client))
        inverted = comparable = tied = 0
        for index, left in enumerate(clients):
            for right in clients[index + 1 :]:
                if left.client not in reference or right.client not in reference:
                    raise ScientificContractError(
                        ErrorMessage("full-calibration local reference omits an ablation client")
                    )
                full_difference = reference[left.client] - reference[right.client]
                replicate_difference = left.threshold.value - right.threshold.value
                if full_difference == 0.0 or replicate_difference == 0.0:
                    tied += 1
                else:
                    comparable += 1
                    if full_difference * replicate_difference < 0.0:
                        inverted += 1
        rows.append(
            CalibrationThresholdOrderRow(
                seed=seed,
                method=method,
                calibration_size=cell.calibration_size,
                replicate=cell.replicate_index,
                inverted_pair_count=NonNegativeIntegerValue(inverted),
                comparable_pair_count=NonNegativeIntegerValue(comparable),
                tied_pair_count=NonNegativeIntegerValue(tied),
            )
        )
    return tuple(rows)


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
    result = execute_declared_experiment_seed(
        declaration=require_experiment_declaration(ExperimentId.SIZE_AWARE_SHRINKAGE),
        seed_cohort=SeedCohort(values=(training_seed,)),
        reason=PlanReason("execute the declared prospective size-aware shrinkage comparison"),
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
    documents_by_method: dict[FederatedThresholdMethod, tuple[FederatedEvaluationDocument, ...]] = {}
    for method in (
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,
    ):
        documents: list[FederatedEvaluationDocument] = []
        for seed in CONFIRMATORY_SEED_COHORT.values:
            try:
                documents.append(_evaluation_document_for_seed(seed, method, experiment_id, OUTPUTS_ROOT))
            except ScientificContractError:
                missing += 1
        if documents:
            documents_by_method[method] = tuple(documents)
            summaries.append(_method_summary(method, tuple(documents)))
    summary_by_method = {summary.method: summary for summary in summaries}
    if set(summary_by_method) != {
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,
    }:
        raise ScientificContractError(
            ErrorMessage("size-aware shrinkage report requires all declared comparison methods")
        )
    rows: list[SizeAwareShrinkageClientRow] = []
    shared_by_seed = {
        document.score_coordinate.training_seed: document
        for document in documents_by_method[FederatedThresholdMethod.SHARED_THRESHOLD]
    }
    local_by_seed = {
        document.score_coordinate.training_seed: document
        for document in documents_by_method[FederatedThresholdMethod.LOCAL_THRESHOLD]
    }
    for document in documents_by_method[FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE]:
        seed = document.score_coordinate.training_seed
        shared_clients = {client.client: client for client in shared_by_seed[seed].clients}
        local_clients = {client.client: client for client in local_by_seed[seed].clients}
        cohort_records = {record.client: record for record in document.cohort.records}
        for client in document.clients:
            local = local_clients[client.client]
            shared = shared_clients[client.client]
            used_support = CalibrationSize(cohort_records[client.client].benign_calibration_count.value)
            rows.append(
                SizeAwareShrinkageClientRow(
                    seed=seed,
                    client=client.client,
                    source_support=used_support,
                    used_support=used_support,
                    lambda_weight=ShrinkageWeight(
                        used_support.value / (used_support.value + MINIMUM_BENIGN_SUPPORT.value)
                    ),
                    shared_threshold=MetricValue(shared.threshold.value),
                    local_threshold=MetricValue(local.threshold.value),
                    size_aware_threshold=MetricValue(client.threshold.value),
                    fpr=metric_value(metric_by_id(client.metrics, MetricId.FALSE_POSITIVE_RATE)),
                    tpr=metric_value(metric_by_id(client.metrics, MetricId.TRUE_POSITIVE_RATE)),
                    macro_f1=metric_value(metric_by_id(client.metrics, MetricId.BINARY_MACRO_F1)),
                    balanced_accuracy=metric_value(metric_by_id(client.metrics, MetricId.BALANCED_ACCURACY)),
                )
            )
    serialize_json_model(
        SizeAwareShrinkageReport(
            experiment=experiment_id,
            methods=tuple(summaries),
            clients=tuple(rows),
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

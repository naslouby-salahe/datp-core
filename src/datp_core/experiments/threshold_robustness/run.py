from __future__ import annotations

from enum import StrEnum
from math import sqrt
from pathlib import Path
from statistics import fmean, median
from typing import TYPE_CHECKING

import polars as pl

from datp_core.analysis.descriptive import summarize_cross_seed_metric_values
from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
from datp_core.analysis.inference.bootstrap.estimation import seed_level_bca_interval
from datp_core.analysis.mechanisms import ClientScoreVector, jensen_shannon_from_client_scores
from datp_core.analysis.metrics.models import metric_by_id
from datp_core.analysis.metrics.population import calculate_population_metrics
from datp_core.analysis.metrics.semantics import metric_value
from datp_core.app.planning import PlanReason, expand_experiment_plan
from datp_core.artifacts.layout import evaluation_run_directory
from datp_core.artifacts.repositories.evaluations import FederatedEvaluationAssetName
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    AnalysisMarkerText,
    ExperimentId,
    FederatedThresholdMethod,
    FileContentText,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    ScoreFrameColumn,
    ThresholdEstimator,
    ValidationReasonText,
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
    ThresholdVariance,
)
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.scoring.models import FederatedScoreAssetName
from datp_core.experiments.common.coordinates import ExperimentCoordinate
from datp_core.experiments.common.reports import (
    AnalysisReportFinalizationInput,
    AnalysisReportPublication,
    finalize_analysis_report,
    persist_result_document,
)
from datp_core.experiments.common.seeds import (
    CONFIRMATORY_ANALYSIS_SEED,
    CONFIRMATORY_SEED_COHORT,
    SeedCohort,
)
from datp_core.experiments.confirmatory.spec import CONFIRMATORY_INFERENCE_PROTOCOL
from datp_core.experiments.execution import execute_declared_experiment_seed
from datp_core.experiments.execution.evidence import load_evaluation_document, population_metric
from datp_core.experiments.execution.layout import (
    EvaluationRunAssetDirectory,
    ExecutionArtifactDirectory,
    federated_training_directory,
)
from datp_core.experiments.execution.models import ProgressHook
from datp_core.experiments.registry import require_experiment_declaration
from datp_core.experiments.threshold_robustness.cohorts import (
    compute_intersection_cohort,
    extract_feasible_clients_by_size,
)
from datp_core.runtime.configuration import OUTPUTS_ROOT
from datp_core.runtime.filesystem import write_text_atomically
from datp_core.thresholds.contracts import ThresholdInfeasibilityReason
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
    SHARED_CONSTRUCTION_PANEL = "shared_construction_robustness.md"


class ThresholdRobustnessAnalysisMarker(StrEnum):
    SHARED_CONSTRUCTION_SENSITIVITY = "shared_construction_sensitivity_analysis_complete"
    QUANTILE_SENSITIVITY = "quantile_sensitivity_analysis_complete"
    FIXED_SHRINKAGE_CURVE = "fixed_shrinkage_curve_analysis_complete"
    SIZE_AWARE_SHRINKAGE = "size_aware_shrinkage_analysis_complete"
    LOCAL_CONFORMAL_COVERAGE = "local_conformal_coverage_analysis_complete"
    THRESHOLD_ESTIMATOR_SCOPE_SENSITIVITY = "threshold_estimator_scope_sensitivity_analysis_complete"
    PREPROCESSING_GEOMETRY_SENSITIVITY = "preprocessing_geometry_sensitivity_analysis_complete"
    SHARED_CALIBRATION_CONTRIBUTOR_AVAILABILITY = "shared_calibration_contributor_availability_analysis_complete"


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


class EstimatorScopeContrast(StrictModel):
    seed: Seed
    q95_scope_gain: MetricDelta
    moment_scope_gain: MetricDelta
    estimator_sensitivity: MetricDelta


class EstimatorScopeSignCounts(StrictModel):
    estimator: ThresholdEstimator
    positive: NonNegativeIntegerValue
    zero: NonNegativeIntegerValue
    negative: NonNegativeIntegerValue


class EstimatorScopeSummaryReport(StrictModel):
    experiment: ExperimentId
    comparison_role: ValidationReasonText
    claim_boundary: ValidationReasonText
    rows: tuple[EstimatorScopeSummary, ...]
    contrasts: tuple[EstimatorScopeContrast, ...]
    sign_counts: tuple[EstimatorScopeSignCounts, ...]
    secondary_moment_scope_gain_interval: BootstrapInterval


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


class OnboardingCalibrationRow(StrictModel):
    seed: Seed
    target_client: ClientIdentity
    calibration_size: NonNegativeIntegerValue
    replicate: ReplicateIndex
    method: FederatedThresholdMethod
    target_threshold: MetricValue | None
    threshold_delta_from_full_local: MetricDelta | None
    target_fpr: MetricValue | None
    target_tpr: MetricValue | None
    target_macro_f1: MetricValue | None
    unavailable_reason: str | None
    family_fallback: bool


class OnboardingCalibrationReport(StrictModel):
    experiment: ExperimentId
    rows: tuple[OnboardingCalibrationRow, ...]


class ContributorAvailabilitySeedSummary(StrictModel):
    seed: Seed
    omitted_count: NonNegativeIntegerValue
    median_delta_cv: MetricDelta
    worst_shared_cv: MetricValue
    max_absolute_threshold_shift: MetricValue
    positive_scope_gain_retention: Ratio
    worst_shared_cv_omission: tuple[ClientIdentity, ...]
    max_threshold_shift_omission: tuple[ClientIdentity, ...]


class ContributorAvailabilityRow(StrictModel):
    seed: Seed
    omitted_clients: tuple[ClientIdentity, ...]
    shared_threshold: MetricValue
    shared_cv_fpr: MetricValue
    local_cv_fpr: MetricValue
    delta_cv_fpr: MetricDelta
    shared_threshold_shift: MetricDelta
    mean_fpr: MetricValue | None
    fpr_iqr: MetricValue | None
    fpr_range: MetricValue | None
    worst_client_fpr: MetricValue | None
    mean_absolute_target_error: MetricValue | None
    worst_absolute_target_error: MetricValue | None
    p10_macro_f1: MetricValue | None
    worst_client_balanced_accuracy: MetricValue | None


class ContributorAvailabilityCampaignSummary(StrictModel):
    omitted_count: NonNegativeIntegerValue
    mean_median_delta_cv: MetricDelta
    median_median_delta_cv: MetricDelta
    minimum_median_delta_cv: MetricDelta
    maximum_median_delta_cv: MetricDelta


class ContributorAvailabilityUnavailableRow(StrictModel):
    seed: Seed
    omitted_count: NonNegativeIntegerValue
    unavailable_reason: ThresholdInfeasibilityReason


class ContributorAvailabilityReport(StrictModel):
    experiment: ExperimentId
    rows: tuple[ContributorAvailabilityRow, ...]
    seed_summaries: tuple[ContributorAvailabilitySeedSummary, ...]
    campaign_summaries: tuple[ContributorAvailabilityCampaignSummary, ...]
    unavailable_rows: tuple[ContributorAvailabilityUnavailableRow, ...]


class ShrinkageCurveRow(StrictModel):
    seed: Seed
    lambda_weight: ShrinkageWeight
    cv_fpr: MetricValue | None
    worst_client_fpr: MetricValue | None
    fpr_iqr: MetricValue | None
    fpr_range: MetricValue | None
    true_positive_rate: MetricValue | None
    p10_macro_f1: MetricValue | None
    threshold_variance_across_clients: ThresholdVariance | None


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
    local_client_fpr: MetricValue | None
    shared_client_fpr: MetricValue | None
    threshold_difference_from_local: MetricDelta | None
    auroc: MetricValue | None
    average_precision: MetricValue | None


class ConformalCoverageReport(StrictModel):
    experiment: ExperimentId
    interpretation: ValidationReasonText
    claim_boundary: ValidationReasonText
    rows: tuple[ConformalCoverageRow, ...]


class PreprocessingGeometryRow(StrictModel):
    seed: Seed
    preprocessing_protocol: PreprocessingProtocolId
    method: FederatedThresholdMethod
    cv_fpr: MetricValue
    fpr_iqr: MetricValue
    fpr_range: MetricValue
    worst_client_fpr: MetricValue
    mean_absolute_target_error: MetricValue | None
    auroc: MetricValue
    average_precision: MetricValue
    mean_pairwise_benign_score_jsd: MetricValue | None


class PreprocessingAbsorptionReason(StrEnum):
    UNAVAILABLE_NO_POSITIVE_LOCAL_STANDARD_GAP = "unavailable_no_positive_local_standard_gap"


class PreprocessingAbsorptionRow(StrictModel):
    seed: Seed
    local_standard_scope_gain: MetricDelta
    pooled_min_max_scope_gain: MetricDelta
    absorption: MetricDelta | None
    unavailable_reason: PreprocessingAbsorptionReason | None


class PreprocessingGeometrySensitivityReport(StrictModel):
    experiment: ExperimentId
    rows: tuple[PreprocessingGeometryRow, ...]
    absorption_rows: tuple[PreprocessingAbsorptionRow, ...]


class SizeAwareShrinkageReport(StrictModel):
    experiment: ExperimentId
    methods: tuple[MethodCvSummary, ...]
    rows: tuple[SizeAwareShrinkageClientRow, ...]


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


def _summary_path(experiment_id: ExperimentId, population: PopulationId) -> Path:
    return _analysis_directory(experiment_id, population) / ThresholdRobustnessArtifactName.SUMMARY


def _shared_construction_panel_path(population: PopulationId) -> Path:
    return (
        _analysis_directory(ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY, population)
        / ThresholdRobustnessArtifactName.SHARED_CONSTRUCTION_PANEL
    )


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
    preprocessing_protocol: PreprocessingProtocolId | None = None,
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
        and (preprocessing_protocol is None or entry.coordinate.preprocessing_protocol is preprocessing_protocol)
    )
    if len(matches) != 1:
        quantile_suffix = f" q={quantile.value}" if quantile is not None else ""
        estimator_suffix = f" estimator={estimator.value}" if estimator is not None else ""
        preprocessing_suffix = (
            f" preprocessing={preprocessing_protocol.value}" if preprocessing_protocol is not None else ""
        )
        raise ScientificContractError(
            ErrorMessage(
                "evaluation coordinate for "
                f"{method.value}{quantile_suffix}{estimator_suffix}{preprocessing_suffix} must resolve exactly once"
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
    report = MethodCvSummaryReport(experiment=experiment_id, rows=tuple(rows))
    persist_result_document(
        report,
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    write_text_atomically(
        _shared_construction_panel_path(PopulationId.NBAIOT_NATURAL_DEVICES),
        FileContentText(_render_shared_construction_panel(report)),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(ThresholdRobustnessAnalysisMarker.SHARED_CONSTRUCTION_SENSITIVITY),
        )
    )


def _render_shared_construction_panel(report: MethodCvSummaryReport) -> str:
    local = next(
        (item for item in report.rows if item.method is FederatedThresholdMethod.LOCAL_THRESHOLD),
        None,
    )
    rows = [
        "# Shared-threshold robustness panel",
        "",
        "All shared constructions are compared against the same LOCAL_THRESHOLD baseline. "
        "Values are arithmetic means over available seed-level CV(FPR) outcomes; unavailable evidence is retained.",
        "",
        "| Threshold construction | Seeds | Mean CV(FPR) | LOCAL minus construction CV(FPR) | "
        "Mean worst-client FPR | CV(FPR) across seeds |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in report.rows:
        difference = (
            None
            if local is None or local.mean_cv_fpr is None or item.mean_cv_fpr is None
            else local.mean_cv_fpr.value - item.mean_cv_fpr.value
        )
        rows.append(
            f"| `{item.method.value}` | {item.seed_count.value} | {_panel_value(item.mean_cv_fpr)} | "
            f"{_panel_value(difference)} | {_panel_value(item.mean_worst_client_fpr)} | "
            f"{_panel_value(item.cv_fpr_across_seeds)} |"
        )
    return "\n".join(rows) + "\n"


def _panel_value(value: MetricValue | float | None) -> str:
    if value is None:
        return "UNAVAILABLE"
    numeric = value.value if isinstance(value, MetricValue) else value
    return f"{numeric:.12g}"


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
    persist_result_document(
        QuantileSummaryReport(experiment=experiment_id, rows=tuple(rows)),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(ThresholdRobustnessAnalysisMarker.QUANTILE_SENSITIVITY),
        )
    )


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
    contrasts: list[EstimatorScopeContrast] = []
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
    for seed in CONFIRMATORY_SEED_COHORT.values:
        seed_documents: dict[tuple[ThresholdEstimator, FederatedThresholdMethod], FederatedEvaluationDocument] = {}
        for estimator in ThresholdEstimator:
            for method in declaration.federated_thresholds:
                try:
                    seed_documents[(estimator, method)] = _evaluation_document_for_seed(
                        seed, method, experiment_id, OUTPUTS_ROOT, estimator=estimator
                    )
                except ScientificContractError:
                    continue
        if len(seed_documents) != len(ThresholdEstimator) * len(declaration.federated_thresholds):
            continue
        contrasts.append(
            estimator_scope_contrast(
                seed=seed,
                q95_shared=population_metric(
                    seed_documents[(ThresholdEstimator.TYPE7_Q95, FederatedThresholdMethod.SHARED_THRESHOLD)],
                    MetricId.FPR_COEFFICIENT_OF_VARIATION,
                ),
                q95_local=population_metric(
                    seed_documents[(ThresholdEstimator.TYPE7_Q95, FederatedThresholdMethod.LOCAL_THRESHOLD)],
                    MetricId.FPR_COEFFICIENT_OF_VARIATION,
                ),
                moment_shared=population_metric(
                    seed_documents[
                        (
                            ThresholdEstimator.MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR,
                            FederatedThresholdMethod.SHARED_THRESHOLD,
                        )
                    ],
                    MetricId.FPR_COEFFICIENT_OF_VARIATION,
                ),
                moment_local=population_metric(
                    seed_documents[
                        (
                            ThresholdEstimator.MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR,
                            FederatedThresholdMethod.LOCAL_THRESHOLD,
                        )
                    ],
                    MetricId.FPR_COEFFICIENT_OF_VARIATION,
                ),
            )
        )
    persist_result_document(
        EstimatorScopeSummaryReport(
            experiment=experiment_id,
            comparison_role=ValidationReasonText(
                "The mean-plus-sample-standard-deviation estimator is a fixed-score scope sensitivity control."
            ),
            claim_boundary=ValidationReasonText(
                "It does not reproduce or make fidelity claims about Meidan et al.'s complete detector."
            ),
            rows=tuple(rows),
            contrasts=tuple(contrasts),
            sign_counts=_estimator_scope_sign_counts(tuple(contrasts)),
            secondary_moment_scope_gain_interval=_moment_scope_gain_interval(tuple(contrasts)),
        ),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(ThresholdRobustnessAnalysisMarker.THRESHOLD_ESTIMATOR_SCOPE_SENSITIVITY),
        )
    )


def estimator_scope_contrast(
    *,
    seed: Seed,
    q95_shared: MetricValue,
    q95_local: MetricValue,
    moment_shared: MetricValue,
    moment_local: MetricValue,
) -> EstimatorScopeContrast:
    q95_gain = MetricDelta(q95_shared.value - q95_local.value)
    moment_gain = MetricDelta(moment_shared.value - moment_local.value)
    return EstimatorScopeContrast(
        seed=seed,
        q95_scope_gain=q95_gain,
        moment_scope_gain=moment_gain,
        estimator_sensitivity=MetricDelta(moment_gain.value - q95_gain.value),
    )


def _estimator_scope_sign_counts(
    contrasts: tuple[EstimatorScopeContrast, ...],
) -> tuple[EstimatorScopeSignCounts, ...]:
    return tuple(
        EstimatorScopeSignCounts(
            estimator=estimator,
            positive=NonNegativeIntegerValue(sum(value > 0.0 for value in gains)),
            zero=NonNegativeIntegerValue(sum(value == 0.0 for value in gains)),
            negative=NonNegativeIntegerValue(sum(value < 0.0 for value in gains)),
        )
        for estimator, gains in (
            (ThresholdEstimator.TYPE7_Q95, tuple(item.q95_scope_gain.value for item in contrasts)),
            (
                ThresholdEstimator.MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR,
                tuple(item.moment_scope_gain.value for item in contrasts),
            ),
        )
    )


def _moment_scope_gain_interval(contrasts: tuple[EstimatorScopeContrast, ...]) -> BootstrapInterval:
    return seed_level_bca_interval(
        tuple(MetricValue(item.moment_scope_gain.value) for item in contrasts),
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=CONFIRMATORY_ANALYSIS_SEED,
        require_full_cohort=True,
    )


def run_calibration_size_ablation_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> ThresholdRobustnessSeedResult:
    require_calibration_subsample_replicate_count()
    return _run_robustness_seed(ExperimentId.CALIBRATION_SIZE_ABLATION, training_seed, output_root, overwrite, progress)


def run_calibration_cold_start_onboarding_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(
        ExperimentId.CALIBRATION_COLD_START_ONBOARDING,
        training_seed,
        output_root,
        overwrite,
        progress,
    )


def report_calibration_cold_start_onboarding(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> AnalysisReportPublication:
    del overwrite
    declaration = require_experiment_declaration(experiment_id)
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    rows: list[OnboardingCalibrationRow] = []
    missing = 0
    for seed in CONFIRMATORY_SEED_COHORT.values:
        for method in declaration.federated_thresholds:
            try:
                document = _evaluation_document_for_seed(seed, method, experiment_id, OUTPUTS_ROOT)
            except ScientificContractError:
                missing += 1
                continue
            for cell in document.diagnostics.onboarding_calibration:
                metrics = cell.target_metrics
                rows.append(
                    OnboardingCalibrationRow(
                        seed=seed,
                        target_client=cell.target_client,
                        calibration_size=NonNegativeIntegerValue(cell.calibration_size.value),
                        replicate=cell.replicate_index,
                        method=cell.method,
                        target_threshold=(
                            None if cell.target_threshold is None else MetricValue(cell.target_threshold.value)
                        ),
                        threshold_delta_from_full_local=(
                            None
                            if cell.target_threshold is None
                            else MetricDelta(cell.target_threshold.value - cell.full_calibration_local_threshold.value)
                        ),
                        target_fpr=(
                            None
                            if metrics is None
                            else metric_value(metric_by_id(metrics.metrics, MetricId.FALSE_POSITIVE_RATE))
                        ),
                        target_tpr=(
                            None
                            if metrics is None
                            else metric_value(metric_by_id(metrics.metrics, MetricId.TRUE_POSITIVE_RATE))
                        ),
                        target_macro_f1=(
                            None
                            if metrics is None
                            else metric_value(metric_by_id(metrics.metrics, MetricId.BINARY_MACRO_F1))
                        ),
                        unavailable_reason=None if cell.unavailable_reason is None else cell.unavailable_reason.value,
                        family_fallback=cell.family_fallback,
                    )
                )
    persist_result_document(
        OnboardingCalibrationReport(experiment=experiment_id, rows=tuple(rows)),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText("calibration_cold_start_onboarding_analysis_complete"),
        )
    )


def run_shared_calibration_contributor_availability_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(
        ExperimentId.SHARED_CALIBRATION_CONTRIBUTOR_AVAILABILITY,
        training_seed,
        output_root,
        overwrite,
        progress,
    )


def report_shared_calibration_contributor_availability(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> AnalysisReportPublication:
    del overwrite
    declaration = require_experiment_declaration(experiment_id)
    if declaration.federated_thresholds != (
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    ):
        raise ScientificContractError(ErrorMessage("contributor availability requires locked shared/local methods"))
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    rows: list[ContributorAvailabilityRow] = []
    seed_summaries: list[ContributorAvailabilitySeedSummary] = []
    unavailable_rows: list[ContributorAvailabilityUnavailableRow] = []
    missing = 0
    for seed in CONFIRMATORY_SEED_COHORT.values:
        try:
            local = _evaluation_document_for_seed(
                seed, FederatedThresholdMethod.LOCAL_THRESHOLD, experiment_id, OUTPUTS_ROOT
            )
            shared = _evaluation_document_for_seed(
                seed, FederatedThresholdMethod.SHARED_THRESHOLD, experiment_id, OUTPUTS_ROOT
            )
        except ScientificContractError:
            missing += 1
            continue
        local_cv = population_metric(local, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        eligible_count = len(local.clients)
        unavailable_rows.extend(
            ContributorAvailabilityUnavailableRow(
                seed=seed,
                omitted_count=NonNegativeIntegerValue(omitted_count),
                unavailable_reason=ThresholdInfeasibilityReason.UNAVAILABLE_TOO_FEW_REMAINING_CONTRIBUTORS,
            )
            for omitted_count in range(5)
            if eligible_count - omitted_count < 5
        )
        cells = shared.diagnostics.contributor_omission
        baseline = next((cell for cell in cells if not cell.omitted_clients), None)
        if baseline is None:
            raise ScientificContractError(ErrorMessage("contributor availability lacks its m=0 shared baseline"))
        by_omitted_count: dict[int, list[tuple[ContributorAvailabilityRow, tuple[ClientIdentity, ...]]]] = {}
        for cell in cells:
            population = cell.population.metrics
            shared_cv = metric_value(metric_by_id(population, MetricId.FPR_COEFFICIENT_OF_VARIATION))
            if shared_cv is None:
                raise ScientificContractError(ErrorMessage("contributor omission cell lacks FPR CV"))
            operating = cell.held_out_operating_point_summary
            row = ContributorAvailabilityRow(
                seed=seed,
                omitted_clients=cell.omitted_clients,
                shared_threshold=MetricValue(cell.shared_threshold.value),
                shared_cv_fpr=shared_cv,
                local_cv_fpr=local_cv,
                delta_cv_fpr=MetricDelta(shared_cv.value - local_cv.value),
                shared_threshold_shift=MetricDelta(cell.shared_threshold.value - baseline.shared_threshold.value),
                mean_fpr=metric_value(metric_by_id(population, MetricId.MEAN_FPR)),
                fpr_iqr=metric_value(metric_by_id(population, MetricId.FPR_IQR)),
                fpr_range=metric_value(metric_by_id(population, MetricId.FPR_RANGE)),
                worst_client_fpr=metric_value(metric_by_id(population, MetricId.WORST_CLIENT_FPR)),
                mean_absolute_target_error=None if operating is None else operating.mean_absolute_target_error,
                worst_absolute_target_error=None if operating is None else operating.worst_absolute_target_error,
                p10_macro_f1=metric_value(metric_by_id(population, MetricId.P10_BINARY_MACRO_F1)),
                worst_client_balanced_accuracy=metric_value(
                    metric_by_id(population, MetricId.WORST_CLIENT_BALANCED_ACCURACY)
                ),
            )
            rows.append(row)
            by_omitted_count.setdefault(len(cell.omitted_clients), []).append((row, cell.omitted_clients))
        for omitted_count, group in sorted(by_omitted_count.items()):
            worst = max(group, key=lambda item: item[0].shared_cv_fpr.value)
            largest_shift = max(group, key=lambda item: abs(item[0].shared_threshold_shift.value))
            deltas = [item[0].delta_cv_fpr.value for item in group]
            seed_summaries.append(
                ContributorAvailabilitySeedSummary(
                    seed=seed,
                    omitted_count=NonNegativeIntegerValue(omitted_count),
                    median_delta_cv=MetricDelta(median(deltas)),
                    worst_shared_cv=worst[0].shared_cv_fpr,
                    max_absolute_threshold_shift=MetricValue(abs(largest_shift[0].shared_threshold_shift.value)),
                    positive_scope_gain_retention=Ratio(
                        sum(item[0].delta_cv_fpr.value > 0.0 for item in group) / len(group)
                    ),
                    worst_shared_cv_omission=worst[1],
                    max_threshold_shift_omission=largest_shift[1],
                )
            )
    campaign_summaries: list[ContributorAvailabilityCampaignSummary] = []
    for omitted_count in sorted({item.omitted_count.value for item in seed_summaries}):
        values = [item.median_delta_cv.value for item in seed_summaries if item.omitted_count.value == omitted_count]
        campaign_summaries.append(
            ContributorAvailabilityCampaignSummary(
                omitted_count=NonNegativeIntegerValue(omitted_count),
                mean_median_delta_cv=MetricDelta(fmean(values)),
                median_median_delta_cv=MetricDelta(median(values)),
                minimum_median_delta_cv=MetricDelta(min(values)),
                maximum_median_delta_cv=MetricDelta(max(values)),
            )
        )
    persist_result_document(
        ContributorAvailabilityReport(
            experiment=experiment_id,
            rows=tuple(rows),
            seed_summaries=tuple(seed_summaries),
            campaign_summaries=tuple(campaign_summaries),
            unavailable_rows=tuple(unavailable_rows),
        ),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(
                ThresholdRobustnessAnalysisMarker.SHARED_CALIBRATION_CONTRIBUTOR_AVAILABILITY
            ),
        )
    )


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
            threshold_stability_rows.extend(_threshold_stability_rows_for_seed(seed, method, cells, local_reference))
            threshold_order_rows.extend(_threshold_order_rows_for_seed(seed, method, cells, local_reference))
    persist_result_document(
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
            thresholds = tuple(client.threshold.value for client in evaluation.clients)
            threshold_variance = (
                None
                if len(thresholds) < 2
                else ThresholdVariance(
                    sum((value - sum(thresholds) / len(thresholds)) ** 2 for value in thresholds)
                    / (len(thresholds) - 1)
                )
            )
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
                    fpr_iqr=metric_value(metric_by_id(evaluation.population.metrics, MetricId.FPR_IQR)),
                    fpr_range=metric_value(metric_by_id(evaluation.population.metrics, MetricId.FPR_RANGE)),
                    true_positive_rate=metric_value(
                        metric_by_id(evaluation.population.metrics, MetricId.TRUE_POSITIVE_RATE)
                    ),
                    p10_macro_f1=metric_value(
                        metric_by_id(evaluation.population.metrics, MetricId.P10_BINARY_MACRO_F1)
                    ),
                    threshold_variance_across_clients=threshold_variance,
                )
            )
    persist_result_document(
        ShrinkageCurveReport(experiment=experiment_id, rows=tuple(rows)),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(ThresholdRobustnessAnalysisMarker.FIXED_SHRINKAGE_CURVE),
        )
    )


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
    persist_result_document(
        SizeAwareShrinkageReport(
            experiment=experiment_id,
            methods=tuple(summaries),
            rows=tuple(rows),
        ),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(ThresholdRobustnessAnalysisMarker.SIZE_AWARE_SHRINKAGE),
        )
    )


def run_local_conformal_coverage_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(ExperimentId.LOCAL_CONFORMAL_COVERAGE, training_seed, output_root, overwrite, progress)


def _client_fpr_for(document: FederatedEvaluationDocument, client: ClientIdentity) -> MetricValue | None:
    return _client_metric_for(document, client, MetricId.FALSE_POSITIVE_RATE)


def _client_metric_for(
    document: FederatedEvaluationDocument, client: ClientIdentity, metric: MetricId
) -> MetricValue | None:
    for client_result in document.clients:
        if client_result.client == client:
            return metric_value(metric_by_id(client_result.metrics, metric))
    return None


def _client_threshold_for(document: FederatedEvaluationDocument, client: ClientIdentity) -> MetricValue | None:
    for client_result in document.clients:
        if client_result.client == client:
            return MetricValue(client_result.threshold.value)
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
        local = _evaluation_document_for_seed(
            seed, FederatedThresholdMethod.LOCAL_THRESHOLD, experiment_id, OUTPUTS_ROOT
        )
        shared = _evaluation_document_for_seed(
            seed, FederatedThresholdMethod.SHARED_THRESHOLD, experiment_id, OUTPUTS_ROOT
        )
        for diagnostic in document.diagnostics.conformal_coverage:
            conformal_threshold = _client_threshold_for(document, diagnostic.client)
            local_threshold = _client_threshold_for(local, diagnostic.client)
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
                    local_client_fpr=_client_fpr_for(local, diagnostic.client),
                    shared_client_fpr=_client_fpr_for(shared, diagnostic.client),
                    threshold_difference_from_local=(
                        None
                        if conformal_threshold is None or local_threshold is None
                        else MetricDelta(conformal_threshold.value - local_threshold.value)
                    ),
                    auroc=_client_metric_for(document, diagnostic.client, MetricId.AUROC),
                    average_precision=_client_metric_for(document, diagnostic.client, MetricId.AVERAGE_PRECISION),
                )
            )
    persist_result_document(
        ConformalCoverageReport(
            experiment=experiment_id,
            interpretation=ValidationReasonText(
                "Held-out benign coverage is a supportive finite-sample diagnostic for the local conformal threshold."
            ),
            claim_boundary=ValidationReasonText(
                "This diagnostic does not establish arbitrary client-conditional validity beyond the retained client "
                "calibration and held-out benign evidence."
            ),
            rows=tuple(rows),
        ),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(ThresholdRobustnessAnalysisMarker.LOCAL_CONFORMAL_COVERAGE),
        )
    )


def run_preprocessing_geometry_sensitivity_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(
        ExperimentId.PREPROCESSING_GEOMETRY_SENSITIVITY,
        training_seed,
        output_root,
        overwrite,
        progress,
    )


def _mean_pairwise_benign_score_jsd(document: FederatedEvaluationDocument) -> MetricValue | None:
    score_root = (
        federated_training_directory(document.score_coordinate, OUTPUTS_ROOT) / ExecutionArtifactDirectory.SCORES
    )
    vectors: list[ClientScoreVector] = []
    for client_result in sorted(document.clients, key=lambda item: item.client):
        path = score_root / client_result.client.client_id.value / FederatedScoreAssetName.CALIBRATION
        if not path.is_file():
            raise ScientificContractError(ErrorMessage(f"missing persisted benign calibration scores: {path}"))
        values = pl.read_parquet(path)[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list()
        if not values:
            raise ScientificContractError(ErrorMessage(f"empty benign calibration scores: {path}"))
        vectors.append(
            ClientScoreVector(
                client=client_result.client,
                scores=tuple(MetricValue(float(value)) for value in values),
            )
        )
    return jensen_shannon_from_client_scores(tuple(vectors)).aggregate


def _preprocessing_geometry_row(
    seed: Seed,
    preprocessing_protocol: PreprocessingProtocolId,
    method: FederatedThresholdMethod,
    document: FederatedEvaluationDocument,
) -> PreprocessingGeometryRow:
    operating = document.diagnostics.held_out_operating_point_summary
    return PreprocessingGeometryRow(
        seed=seed,
        preprocessing_protocol=preprocessing_protocol,
        method=method,
        cv_fpr=population_metric(document, MetricId.FPR_COEFFICIENT_OF_VARIATION),
        fpr_iqr=population_metric(document, MetricId.FPR_IQR),
        fpr_range=population_metric(document, MetricId.FPR_RANGE),
        worst_client_fpr=population_metric(document, MetricId.WORST_CLIENT_FPR),
        mean_absolute_target_error=None if operating is None else operating.mean_absolute_target_error,
        auroc=population_metric(document, MetricId.AUROC),
        average_precision=population_metric(document, MetricId.AVERAGE_PRECISION),
        mean_pairwise_benign_score_jsd=_mean_pairwise_benign_score_jsd(document),
    )


def report_preprocessing_geometry_sensitivity(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> AnalysisReportPublication:
    del overwrite
    declaration = require_experiment_declaration(experiment_id)
    expected_protocols = (
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
    )
    if declaration.preprocessing_protocols != expected_protocols:
        raise ScientificContractError(
            ErrorMessage("preprocessing geometry sensitivity requires the two locked protocols")
        )
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    rows: list[PreprocessingGeometryRow] = []
    absorption_rows: list[PreprocessingAbsorptionRow] = []
    missing = 0
    for seed in CONFIRMATORY_SEED_COHORT.values:
        documents: dict[tuple[PreprocessingProtocolId, FederatedThresholdMethod], FederatedEvaluationDocument] = {}
        for protocol in expected_protocols:
            for method in declaration.federated_thresholds:
                try:
                    document = _evaluation_document_for_seed(
                        seed, method, experiment_id, OUTPUTS_ROOT, preprocessing_protocol=protocol
                    )
                except ScientificContractError:
                    missing += 1
                    continue
                documents[(protocol, method)] = document
                rows.append(_preprocessing_geometry_row(seed, protocol, method, document))
        local_standard_shared = documents.get(
            (PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD, FederatedThresholdMethod.SHARED_THRESHOLD)
        )
        local_standard_local = documents.get(
            (PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD, FederatedThresholdMethod.LOCAL_THRESHOLD)
        )
        pooled_shared = documents.get(
            (PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX, FederatedThresholdMethod.SHARED_THRESHOLD)
        )
        pooled_local = documents.get(
            (PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX, FederatedThresholdMethod.LOCAL_THRESHOLD)
        )
        if (
            local_standard_shared is None
            or local_standard_local is None
            or pooled_shared is None
            or pooled_local is None
        ):
            continue
        local_standard_gain = MetricDelta(
            population_metric(local_standard_shared, MetricId.FPR_COEFFICIENT_OF_VARIATION).value
            - population_metric(local_standard_local, MetricId.FPR_COEFFICIENT_OF_VARIATION).value
        )
        pooled_gain = MetricDelta(
            population_metric(pooled_shared, MetricId.FPR_COEFFICIENT_OF_VARIATION).value
            - population_metric(pooled_local, MetricId.FPR_COEFFICIENT_OF_VARIATION).value
        )
        absorption_rows.append(
            PreprocessingAbsorptionRow(
                seed=seed,
                local_standard_scope_gain=local_standard_gain,
                pooled_min_max_scope_gain=pooled_gain,
                absorption=(
                    None
                    if local_standard_gain.value <= 1e-12
                    else MetricDelta(1.0 - (pooled_gain.value / local_standard_gain.value))
                ),
                unavailable_reason=(
                    PreprocessingAbsorptionReason.UNAVAILABLE_NO_POSITIVE_LOCAL_STANDARD_GAP
                    if local_standard_gain.value <= 1e-12
                    else None
                ),
            )
        )
    persist_result_document(
        PreprocessingGeometrySensitivityReport(
            experiment=experiment_id,
            rows=tuple(rows),
            absorption_rows=tuple(absorption_rows),
        ),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(ThresholdRobustnessAnalysisMarker.PREPROCESSING_GEOMETRY_SENSITIVITY),
        )
    )

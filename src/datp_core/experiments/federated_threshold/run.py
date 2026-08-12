from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from importlib.metadata import version
from pathlib import Path
from platform import machine, platform, processor
from sys import version as python_version
from typing import TYPE_CHECKING, ClassVar

import numpy as np
from pydantic import TypeAdapter

from datp_core.analysis.descriptive import summarize_cross_seed_metric_values
from datp_core.analysis.metrics.models import metric_by_id
from datp_core.analysis.metrics.semantics import metric_value
from datp_core.app.planning import PlanReason, expand_experiment_plan
from datp_core.artifacts.layout import evaluation_run_directory
from datp_core.artifacts.repositories.evaluations import FederatedEvaluationAssetName
from datp_core.artifacts.repositories.thresholds import FederatedThresholdAssetName
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
    ValidationReasonText,
)
from datp_core.core.numeric import (
    AbsoluteThresholdError,
    ByteCount,
    ElapsedSeconds,
    MetricValue,
    NonNegativeFiniteFloatValue,
    NonNegativeIntegerValue,
    Ratio,
    RelativeThresholdError,
    Seed,
    SeedCount,
    SeedObservationCount,
    SummaryCoefficient,
    ThresholdValue,
    ThresholdVariance,
)
from datp_core.experiments.common.coordinates import ExperimentCoordinate
from datp_core.experiments.common.reports import (
    AnalysisReportFinalizationInput,
    AnalysisReportPublication,
    finalize_analysis_report,
)
from datp_core.experiments.common.seeds import CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.experiments.execution import execute_declared_experiment_seed
from datp_core.experiments.execution.evidence import load_evaluation_document
from datp_core.experiments.execution.layout import EvaluationRunAssetDirectory
from datp_core.experiments.execution.models import ProgressHook
from datp_core.experiments.registry import require_experiment_declaration
from datp_core.runtime.configuration import OUTPUTS_ROOT

if TYPE_CHECKING:
    from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
    from datp_core.thresholds.dispatch import ThresholdConstructionResult


class AverageByteCount(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "average byte count"


class FederatedEstimationArtifactName(StrEnum):
    ROOT = "federated_threshold_estimation"
    ANALYSIS = "analysis"
    SUMMARY = "summary.json"


class FederatedEstimationAnalysisMarker(StrEnum):
    FEDERATED_BENIGN_STATISTICS_COMPARISON = "federated_benign_statistics_comparison_analysis_complete"
    FEDERATED_QUANTILE_ESTIMATION = "federated_quantile_estimation_analysis_complete"
    FIXED_COEFFICIENT_STATISTICS_SENSITIVITY = "fixed_coefficient_statistics_sensitivity_analysis_complete"


class FederatedEstimationSeedResult(StrictModel):
    training_seed: Seed
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


class EstimationSummary(StrictModel):
    method: FederatedThresholdMethod
    seed_count: SeedCount
    mean_cv_fpr: MetricValue | None
    mean_worst_client_fpr: MetricValue | None
    cv_fpr_across_seeds: MetricValue | None
    mean_absolute_threshold_error: AbsoluteThresholdError | None
    mean_relative_threshold_error: RelativeThresholdError | None
    mean_kll_empirical_rank_error: Ratio | None
    mean_absolute_attainment_error: MetricValue | None
    mean_achieved_exceedance: Ratio | None
    mean_threshold_variance: ThresholdVariance | None
    mean_estimated_communication_bytes: AverageByteCount | None
    mean_threshold_stage_logical_elements: NonNegativeIntegerValue | None
    kll_client_build_serialization_timing: RuntimeTimingSummary | None
    kll_server_deserialize_merge_query_timing: RuntimeTimingSummary | None


class RuntimeTimingSummary(StrictModel):
    median_milliseconds: MetricValue
    interquartile_range_milliseconds: MetricValue
    p95_milliseconds: MetricValue
    observation_count: SeedObservationCount
    environment: RuntimeEnvironmentEvidence
    peak_server_rss: MetricValue | None = None
    peak_server_rss_unavailable_reason: ValidationReasonText = ValidationReasonText(
        "UNAVAILABLE_MEASUREMENT_NOT_SUPPORTED"
    )


class RuntimeEnvironmentEvidence(StrictModel):
    hardware: ValidationReasonText
    operating_system: ValidationReasonText
    python: ValidationReasonText
    datasketches: ValidationReasonText


class EstimationSummaryReport(StrictModel):
    experiment: ExperimentId
    rows: tuple[EstimationSummary, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class EstimationSummaryLoad:
    summary: EstimationSummary | None
    missing_count: SeedObservationCount


class FixedCoefficientSummary(StrictModel):
    seed: Seed
    coefficient: SummaryCoefficient | None
    method: FederatedThresholdMethod
    threshold_value: ThresholdValue | None
    cv_fpr: MetricValue | None
    worst_client_fpr: MetricValue | None


class FixedCoefficientSummaryReport(StrictModel):
    experiment: ExperimentId
    rows: tuple[FixedCoefficientSummary, ...]


def _analysis_directory(experiment_id: ExperimentId, population: PopulationId) -> Path:
    return (
        OUTPUTS_ROOT
        / FederatedEstimationArtifactName.ROOT
        / experiment_id.value
        / population.value
        / FederatedEstimationArtifactName.ANALYSIS
    )


def _summary_path(experiment_id: ExperimentId, population: PopulationId) -> Path:
    return _analysis_directory(experiment_id, population) / FederatedEstimationArtifactName.SUMMARY


def _complete_marker(experiment_id: ExperimentId, population: PopulationId) -> Path:
    return _summary_path(experiment_id, population)


def _evaluation_document_path(output_root: Path, coordinate: ExperimentCoordinate) -> Path:
    return (
        evaluation_run_directory(output_root, coordinate)
        / EvaluationRunAssetDirectory.EVALUATION
        / FederatedEvaluationAssetName.DOCUMENT
    )


def _threshold_result_path(output_root: Path, coordinate: ExperimentCoordinate) -> Path:
    return (
        evaluation_run_directory(output_root, coordinate)
        / EvaluationRunAssetDirectory.THRESHOLD
        / FederatedThresholdAssetName.RESULT
    )


def _load_threshold_result(path: Path) -> ThresholdConstructionResult:
    from datp_core.thresholds.dispatch import ThresholdConstructionResult

    adapter: TypeAdapter[ThresholdConstructionResult] = TypeAdapter(ThresholdConstructionResult)
    return adapter.validate_json(path.read_text(encoding="utf-8"))


def _evaluation_document_for_seed(
    seed: Seed,
    method: FederatedThresholdMethod,
    experiment_id: ExperimentId,
    output_root: Path,
) -> FederatedEvaluationDocument:
    declaration = require_experiment_declaration(experiment_id)
    plan = expand_experiment_plan(declarations=(declaration,), seed_cohort=SeedCohort(values=(seed,)))
    matches = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.coordinate.threshold_method is method
        and entry.coordinate.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION
    )
    if len(matches) != 1:
        raise ScientificContractError(
            ErrorMessage(f"evaluation coordinate for {method.value} must resolve exactly once in {experiment_id.value}")
        )
    path = _evaluation_document_path(output_root, matches[0])
    if not path.is_file():
        raise ScientificContractError(ErrorMessage(f"missing evaluation document: {path}"))
    return load_evaluation_document(path)


def _threshold_coordinate_for_seed(
    seed: Seed,
    method: FederatedThresholdMethod,
    experiment_id: ExperimentId,
) -> ExperimentCoordinate:
    declaration = require_experiment_declaration(experiment_id)
    plan = expand_experiment_plan(declarations=(declaration,), seed_cohort=SeedCohort(values=(seed,)))
    matches = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.coordinate.threshold_method is method
        and entry.coordinate.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION
    )
    if len(matches) != 1:
        raise ScientificContractError(
            ErrorMessage(f"threshold coordinate for {method.value} must resolve exactly once in {experiment_id.value}")
        )
    return matches[0]


def _mean_absolute_threshold_error(values: list[AbsoluteThresholdError]) -> AbsoluteThresholdError | None:
    return AbsoluteThresholdError(sum(item.value for item in values) / len(values)) if values else None


def _mean_relative_threshold_error(values: list[RelativeThresholdError]) -> RelativeThresholdError | None:
    return RelativeThresholdError(sum(item.value for item in values) / len(values)) if values else None


def _mean_ratio(values: list[Ratio]) -> Ratio | None:
    return Ratio(sum(value.value for value in values) / len(values)) if values else None


def _mean_threshold_variance(values: list[ThresholdVariance]) -> ThresholdVariance | None:
    return ThresholdVariance(sum(value.value for value in values) / len(values)) if values else None


def _mean_bytes(values: list[ByteCount]) -> AverageByteCount | None:
    return AverageByteCount(sum(value.value for value in values) / len(values)) if values else None


def _constant_logical_element_count(
    values: list[NonNegativeIntegerValue],
) -> NonNegativeIntegerValue | None:
    if not values:
        return None
    if any(item != values[0] for item in values[1:]):
        raise ScientificContractError(
            ErrorMessage("threshold-stage logical field count must remain fixed across seeds")
        )
    return values[0]


def _run_estimation_seed(
    experiment_id: ExperimentId,
    training_seed: Seed,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None,
) -> FederatedEstimationSeedResult:
    declaration = require_experiment_declaration(experiment_id)
    result = execute_declared_experiment_seed(
        declaration=declaration,
        seed_cohort=SeedCohort(values=(training_seed,)),
        reason=PlanReason(f"federated threshold estimation entry point for {experiment_id.value}"),
        output_root=output_root,
        overwrite=overwrite,
        progress=progress,
    )
    return FederatedEstimationSeedResult(
        training_seed=training_seed,
        completed_threshold_methods=result.completed_threshold_methods,
    )


class EstimationDiagnosticFamily(StrEnum):
    THRESHOLD_ERROR = "threshold_error"
    EXCEEDANCE_AND_VARIANCE = "exceedance_and_variance"


@dataclass(frozen=True, slots=True, kw_only=True)
class _EstimationDiagnostics:
    threshold_errors: list[AbsoluteThresholdError]
    relative_threshold_errors: list[RelativeThresholdError]
    attainment_errors: list[MetricValue]
    exceedances: list[Ratio]
    variances: list[ThresholdVariance]
    communication: list[ByteCount]
    logical_elements: list[NonNegativeIntegerValue]


def _collect_threshold_error_diagnostics(
    documents: tuple[FederatedEvaluationDocument, ...],
) -> tuple[list[AbsoluteThresholdError], list[RelativeThresholdError], list[MetricValue]]:
    threshold_errors: list[AbsoluteThresholdError] = []
    relative_threshold_errors: list[RelativeThresholdError] = []
    attainment_errors: list[MetricValue] = []
    for document in documents:
        for diagnostic in document.diagnostics.threshold_estimation:
            threshold_errors.append(diagnostic.absolute_threshold_error)
            if diagnostic.relative_threshold_error is not None:
                relative_threshold_errors.append(diagnostic.relative_threshold_error)
            attainment_errors.append(diagnostic.absolute_attainment_error)
    return threshold_errors, relative_threshold_errors, attainment_errors


def _collect_exceedance_and_variance_diagnostics(
    documents: tuple[FederatedEvaluationDocument, ...],
) -> tuple[list[Ratio], list[ThresholdVariance]]:
    exceedances: list[Ratio] = []
    variances: list[ThresholdVariance] = []
    for document in documents:
        for diagnostic in document.diagnostics.threshold_estimation:
            exceedances.append(diagnostic.achieved_benign_exceedance)
        for point in document.diagnostics.sample_efficiency:
            variances.append(point.threshold_variance_across_nested_replicates)
    return exceedances, variances


def _collect_communication_diagnostics(
    documents: tuple[FederatedEvaluationDocument, ...],
) -> tuple[list[ByteCount], list[NonNegativeIntegerValue]]:
    communication: list[ByteCount] = []
    logical_elements: list[NonNegativeIntegerValue] = []
    for document in documents:
        if document.diagnostics.threshold_stage_communication is not None:
            communication.append(document.diagnostics.threshold_stage_communication.total_serialized_bytes)
            logical_elements.append(document.diagnostics.threshold_stage_communication.total_logical_element_count)
    return communication, logical_elements


def _collect_estimation_diagnostics(
    documents: tuple[FederatedEvaluationDocument, ...],
    *,
    families: frozenset[EstimationDiagnosticFamily],
) -> _EstimationDiagnostics:
    threshold_errors: list[AbsoluteThresholdError] = []
    relative_threshold_errors: list[RelativeThresholdError] = []
    attainment_errors: list[MetricValue] = []
    exceedances: list[Ratio] = []
    variances: list[ThresholdVariance] = []
    if EstimationDiagnosticFamily.THRESHOLD_ERROR in families:
        threshold_errors, relative_threshold_errors, attainment_errors = _collect_threshold_error_diagnostics(documents)
    if EstimationDiagnosticFamily.EXCEEDANCE_AND_VARIANCE in families:
        exceedances, variances = _collect_exceedance_and_variance_diagnostics(documents)
    communication, logical_elements = _collect_communication_diagnostics(documents)
    return _EstimationDiagnostics(
        threshold_errors=threshold_errors,
        relative_threshold_errors=relative_threshold_errors,
        attainment_errors=attainment_errors,
        exceedances=exceedances,
        variances=variances,
        communication=communication,
        logical_elements=logical_elements,
    )


def _estimation_summary(
    *,
    experiment_id: ExperimentId,
    method: FederatedThresholdMethod,
    families: frozenset[EstimationDiagnosticFamily],
) -> EstimationSummaryLoad:
    documents: list[FederatedEvaluationDocument] = []
    missing = 0
    for seed in CONFIRMATORY_SEED_COHORT.values:
        try:
            documents.append(_evaluation_document_for_seed(seed, method, experiment_id, OUTPUTS_ROOT))
        except ScientificContractError:
            missing += 1
    if not documents:
        return EstimationSummaryLoad(summary=None, missing_count=SeedObservationCount(missing))

    cv_values = tuple(
        value
        for document in documents
        if (value := metric_value(metric_by_id(document.population.metrics, MetricId.FPR_COEFFICIENT_OF_VARIATION)))
    )
    worst_values = tuple(
        value
        for document in documents
        if (value := metric_value(metric_by_id(document.population.metrics, MetricId.WORST_CLIENT_FPR)))
    )
    cv_summary = summarize_cross_seed_metric_values(cv_values)
    worst_summary = summarize_cross_seed_metric_values(worst_values)
    diagnostics = _collect_estimation_diagnostics(
        tuple(documents),
        families=families,
    )

    client_timings, server_timings = _kll_endpoint_timings(experiment_id, method, tuple(documents))
    return EstimationSummaryLoad(
        summary=EstimationSummary(
            method=method,
            seed_count=SeedCount(len(documents)),
            mean_cv_fpr=cv_summary.mean,
            mean_worst_client_fpr=worst_summary.mean,
            cv_fpr_across_seeds=cv_summary.coefficient_of_variation,
            mean_absolute_threshold_error=_mean_absolute_threshold_error(diagnostics.threshold_errors),
            mean_relative_threshold_error=_mean_relative_threshold_error(diagnostics.relative_threshold_errors),
            mean_kll_empirical_rank_error=_kll_mean_empirical_rank_error(
                experiment_id, method, tuple(documents)
            ),
            mean_absolute_attainment_error=(
                MetricValue(
                    sum(item.value for item in diagnostics.attainment_errors) / len(diagnostics.attainment_errors)
                )
                if diagnostics.attainment_errors
                else None
            ),
            mean_achieved_exceedance=_mean_ratio(diagnostics.exceedances),
            mean_threshold_variance=_mean_threshold_variance(diagnostics.variances),
            mean_estimated_communication_bytes=_mean_bytes(diagnostics.communication),
            mean_threshold_stage_logical_elements=_constant_logical_element_count(diagnostics.logical_elements),
            kll_client_build_serialization_timing=_runtime_timing_summary(client_timings),
            kll_server_deserialize_merge_query_timing=_runtime_timing_summary(server_timings),
        ),
        missing_count=SeedObservationCount(missing),
    )


def _kll_endpoint_timings(
    experiment_id: ExperimentId,
    method: FederatedThresholdMethod,
    documents: tuple[FederatedEvaluationDocument, ...],
) -> tuple[tuple[ElapsedSeconds, ...], tuple[ElapsedSeconds, ...]]:
    if method is not FederatedThresholdMethod.FEDERATED_KLL_SHARED_THRESHOLD:
        return (), ()
    from datp_core.thresholds.variants.kll import FederatedKllSharedThresholdResult

    client: list[ElapsedSeconds] = []
    server: list[ElapsedSeconds] = []
    for document in documents:
        coordinate = _threshold_coordinate_for_seed(document.score_coordinate.training_seed, method, experiment_id)
        threshold_result = _load_threshold_result(_threshold_result_path(OUTPUTS_ROOT, coordinate))
        if not isinstance(threshold_result, FederatedKllSharedThresholdResult):
            raise ScientificContractError(ErrorMessage("KLL evaluation has a non-KLL threshold result"))
        for reconstruction in threshold_result.reconstructions:
            client.extend(item.build_serialization_elapsed for item in reconstruction.client_sketches)
            server.append(reconstruction.server_deserialize_merge_query_elapsed)
    return tuple(client), tuple(server)


def _kll_mean_empirical_rank_error(
    experiment_id: ExperimentId,
    method: FederatedThresholdMethod,
    documents: tuple[FederatedEvaluationDocument, ...],
) -> Ratio | None:
    if method is not FederatedThresholdMethod.FEDERATED_KLL_SHARED_THRESHOLD:
        return None
    from datp_core.thresholds.variants.kll import FederatedKllSharedThresholdResult

    values: list[Ratio] = []
    for document in documents:
        coordinate = _threshold_coordinate_for_seed(document.score_coordinate.training_seed, method, experiment_id)
        threshold_result = _load_threshold_result(_threshold_result_path(OUTPUTS_ROOT, coordinate))
        if not isinstance(threshold_result, FederatedKllSharedThresholdResult):
            raise ScientificContractError(ErrorMessage("KLL evaluation has a non-KLL threshold result"))
        values.extend(item.empirical_rank_error for item in threshold_result.reconstructions)
    return _mean_ratio(values)


def _runtime_timing_summary(values: tuple[ElapsedSeconds, ...]) -> RuntimeTimingSummary | None:
    if not values:
        return None
    milliseconds = np.asarray(tuple(item.value * 1000.0 for item in values), dtype=np.float64)
    lower, upper = np.quantile(milliseconds, (0.25, 0.75), method="linear")
    return RuntimeTimingSummary(
        median_milliseconds=MetricValue(float(np.quantile(milliseconds, 0.5, method="linear"))),
        interquartile_range_milliseconds=MetricValue(float(upper - lower)),
        p95_milliseconds=MetricValue(float(np.quantile(milliseconds, 0.95, method="linear"))),
        observation_count=SeedObservationCount(len(values)),
        environment=RuntimeEnvironmentEvidence(
            hardware=_hardware_identity(),
            operating_system=ValidationReasonText(platform()),
            python=ValidationReasonText(python_version),
            datasketches=ValidationReasonText(version("datasketches")),
        ),
    )


def _hardware_identity() -> ValidationReasonText:
    return ValidationReasonText(processor() or machine() or "UNAVAILABLE_HARDWARE_IDENTITY")


def run_federated_benign_statistics_comparison_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> FederatedEstimationSeedResult:
    return _run_estimation_seed(
        ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON,
        training_seed,
        output_root,
        overwrite,
        progress,
    )


def report_federated_benign_statistics_comparison(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> AnalysisReportPublication:
    del overwrite
    declaration = require_experiment_declaration(experiment_id)
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    rows: list[EstimationSummary] = []
    missing = 0
    for method in declaration.federated_thresholds:
        loaded = _estimation_summary(
            experiment_id=experiment_id,
            method=method,
            families=frozenset(
                (
                    EstimationDiagnosticFamily.THRESHOLD_ERROR,
                    EstimationDiagnosticFamily.EXCEEDANCE_AND_VARIANCE,
                )
            ),
        )
        missing += loaded.missing_count.value
        if loaded.summary is not None:
            rows.append(loaded.summary)
    serialize_json_model(
        EstimationSummaryReport(experiment=experiment_id, rows=tuple(rows)),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            marker=_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(FederatedEstimationAnalysisMarker.FEDERATED_BENIGN_STATISTICS_COMPARISON),
        )
    )


def federated_benign_statistics_comparison_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


def run_federated_quantile_estimation_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> FederatedEstimationSeedResult:
    return _run_estimation_seed(
        ExperimentId.FEDERATED_QUANTILE_ESTIMATION,
        training_seed,
        output_root,
        overwrite,
        progress,
    )


def report_federated_quantile_estimation(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> AnalysisReportPublication:
    del overwrite
    declaration = require_experiment_declaration(experiment_id)
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    rows: list[EstimationSummary] = []
    missing = 0
    for method in declaration.federated_thresholds:
        loaded = _estimation_summary(
            experiment_id=experiment_id,
            method=method,
            families=frozenset(
                (
                    EstimationDiagnosticFamily.THRESHOLD_ERROR,
                    EstimationDiagnosticFamily.EXCEEDANCE_AND_VARIANCE,
                )
            ),
        )
        missing += loaded.missing_count.value
        if loaded.summary is not None:
            rows.append(loaded.summary)
    serialize_json_model(
        EstimationSummaryReport(experiment=experiment_id, rows=tuple(rows)),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            marker=_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(FederatedEstimationAnalysisMarker.FEDERATED_QUANTILE_ESTIMATION),
        )
    )


def federated_quantile_estimation_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


def run_fixed_coefficient_statistics_sensitivity_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> FederatedEstimationSeedResult:
    return _run_estimation_seed(
        ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY,
        training_seed,
        output_root,
        overwrite,
        progress,
    )


def _fixed_coefficient_rows_for_seed(
    *,
    seed: Seed,
    method: FederatedThresholdMethod,
    experiment_id: ExperimentId,
) -> tuple[FixedCoefficientSummary, ...]:
    rows: list[FixedCoefficientSummary] = []
    document = _evaluation_document_for_seed(seed, method, experiment_id, OUTPUTS_ROOT)
    cv_fpr = metric_value(metric_by_id(document.population.metrics, MetricId.FPR_COEFFICIENT_OF_VARIATION))
    worst_fpr = metric_value(metric_by_id(document.population.metrics, MetricId.WORST_CLIENT_FPR))
    if method is FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS:
        rows.extend(
            FixedCoefficientSummary(
                seed=seed,
                coefficient=evaluation.coefficient,
                method=method,
                threshold_value=evaluation.threshold,
                cv_fpr=metric_value(metric_by_id(evaluation.population.metrics, MetricId.FPR_COEFFICIENT_OF_VARIATION)),
                worst_client_fpr=metric_value(metric_by_id(evaluation.population.metrics, MetricId.WORST_CLIENT_FPR)),
            )
            for evaluation in document.diagnostics.fixed_coefficient_curve
        )
        if rows:
            return tuple(rows)
        raise ScientificContractError(ErrorMessage("fixed-coefficient statistics evaluation is missing its curve"))
    rows.append(
        FixedCoefficientSummary(
            seed=seed,
            coefficient=None,
            method=method,
            threshold_value=None,
            cv_fpr=cv_fpr,
            worst_client_fpr=worst_fpr,
        )
    )
    return tuple(rows)


def report_fixed_coefficient_statistics_sensitivity(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> AnalysisReportPublication:
    del overwrite
    declaration = require_experiment_declaration(experiment_id)
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    rows: list[FixedCoefficientSummary] = []
    missing = 0
    for method in declaration.federated_thresholds:
        for seed in CONFIRMATORY_SEED_COHORT.values:
            try:
                rows.extend(_fixed_coefficient_rows_for_seed(seed=seed, method=method, experiment_id=experiment_id))
            except ScientificContractError:
                missing += 1
    serialize_json_model(
        FixedCoefficientSummaryReport(experiment=experiment_id, rows=tuple(rows)),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return finalize_analysis_report(
        AnalysisReportFinalizationInput(
            directory=directory,
            marker=_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
            missing_count=SeedObservationCount(missing),
            marker_text=AnalysisMarkerText(FederatedEstimationAnalysisMarker.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY),
        )
    )


def fixed_coefficient_statistics_sensitivity_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()

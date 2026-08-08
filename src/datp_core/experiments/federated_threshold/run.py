"""Federated threshold-estimation experiment runners and typed reports."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from pydantic import TypeAdapter

from datp_core.analysis.metrics.models import MetricStatus, metric_by_id
from datp_core.app.planning import expand_experiment_plan
from datp_core.artifacts.layout import evaluation_run_directory
from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.repositories.evaluations import FederatedEvaluationAssetName
from datp_core.artifacts.repositories.thresholds import FederatedThresholdAssetName
from datp_core.artifacts.serializers.json import serialize_json_model
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import ExperimentId, FederatedThresholdMethod, MetricId, PopulationId
from datp_core.core.numeric import (
    AbsoluteThresholdError,
    ByteCount,
    MetricValue,
    NonNegativeFiniteFloatValue,
    Ratio,
    Seed,
    SeedCount,
    SummaryCoefficient,
    ThresholdValue,
    ThresholdVariance,
)
from datp_core.experiments.common.coordinates import ExperimentCoordinate
from datp_core.experiments.common.seeds import CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.experiments.execution import execute_declared_experiment_seed
from datp_core.experiments.execution.evidence import load_evaluation_document
from datp_core.experiments.execution.layout import EvaluationRunAssetDirectory
from datp_core.experiments.registry import EXPERIMENTS, ExperimentDeclaration
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


class FederatedEstimationSeedResult(StrictModel):
    training_seed: Seed
    campaign_digest: Checksum
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


class EstimationSummary(StrictModel):
    method: FederatedThresholdMethod
    seed_count: SeedCount
    mean_cv_fpr: MetricValue | None
    mean_worst_client_fpr: MetricValue | None
    cv_fpr_across_seeds: MetricValue | None
    mean_absolute_threshold_error: AbsoluteThresholdError | None
    mean_absolute_attainment_error: MetricValue | None
    mean_achieved_exceedance: Ratio | None
    mean_threshold_variance: ThresholdVariance | None
    mean_estimated_communication_bytes: AverageByteCount | None


class EstimationSummaryReport(StrictModel):
    experiment: ExperimentId
    rows: tuple[EstimationSummary, ...]


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
    from datp_core.analysis.evidence import AnalysisAssetName

    return _analysis_directory(experiment_id, population) / AnalysisAssetName.COMPLETE


def _declaration_for(experiment_id: ExperimentId) -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is experiment_id)
    if len(matches) != 1:
        raise ScientificContractError(
            f"experiment must be declared exactly once: {experiment_id.value}",
            subject=experiment_id,
        )
    return matches[0]


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
    declaration = _declaration_for(experiment_id)
    plan = expand_experiment_plan(declarations=(declaration,), seed_cohort=SeedCohort(values=(seed,)))
    matches = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.coordinate.threshold_method is method
        and entry.coordinate.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION
    )
    if len(matches) != 1:
        raise ScientificContractError(
            f"evaluation coordinate for {method.value} must resolve exactly once in {experiment_id.value}"
        )
    path = _evaluation_document_path(output_root, matches[0])
    if not path.is_file():
        raise ScientificContractError(f"missing evaluation document: {path}")
    return load_evaluation_document(path)


def _threshold_coordinate_for_seed(
    seed: Seed,
    method: FederatedThresholdMethod,
    experiment_id: ExperimentId,
) -> ExperimentCoordinate:
    declaration = _declaration_for(experiment_id)
    plan = expand_experiment_plan(declarations=(declaration,), seed_cohort=SeedCohort(values=(seed,)))
    matches = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.coordinate.threshold_method is method
        and entry.coordinate.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION
    )
    if len(matches) != 1:
        raise ScientificContractError(
            f"threshold coordinate for {method.value} must resolve exactly once in {experiment_id.value}"
        )
    return matches[0]


def _try_metric_value(document: FederatedEvaluationDocument, metric: MetricId) -> MetricValue | None:
    result = metric_by_id(document.population.metrics, metric)
    return result.value if result.status is MetricStatus.AVAILABLE else None


def _mean_metric(values: list[MetricValue]) -> MetricValue | None:
    return MetricValue(sum(value.value for value in values) / len(values)) if values else None


def _cv(values: list[MetricValue]) -> MetricValue | None:
    if len(values) < 2:
        return None
    mean = sum(value.value for value in values) / len(values)
    if mean == 0:
        return None
    variance = sum((value.value - mean) ** 2 for value in values) / len(values)
    return MetricValue(variance**0.5 / mean)


def _mean_absolute_threshold_error(values: list[float]) -> AbsoluteThresholdError | None:
    return AbsoluteThresholdError(sum(values) / len(values)) if values else None


def _mean_ratio(values: list[float]) -> Ratio | None:
    return Ratio(sum(values) / len(values)) if values else None


def _mean_threshold_variance(values: list[float]) -> ThresholdVariance | None:
    return ThresholdVariance(sum(values) / len(values)) if values else None


def _mean_bytes(values: list[ByteCount]) -> AverageByteCount | None:
    return AverageByteCount(sum(value.value for value in values) / len(values)) if values else None


def _finalize_report(
    directory: Path,
    marker: Path,
    missing_count: int,
    *,
    marker_text: str,
) -> tuple[tuple[Path, ...], str]:
    if missing_count == 0:
        marker.write_text(marker_text, encoding="utf-8")
        return (directory,), marker_text.strip().split("\n", 1)[0]
    return (directory,), f"{marker_text.strip().split(chr(10), 1)[0]} ({missing_count} seed(s) missing)"


def _run_estimation_seed(
    experiment_id: ExperimentId,
    training_seed: Seed,
    output_root: Path,
    overwrite: bool,
) -> FederatedEstimationSeedResult:
    declaration = _declaration_for(experiment_id)
    result = execute_declared_experiment_seed(
        declaration=declaration,
        seed_cohort=SeedCohort(values=(training_seed,)),
        reason=f"federated threshold estimation entry point for {experiment_id.value}",
        output_root=output_root,
        overwrite=overwrite,
    )
    return FederatedEstimationSeedResult(
        training_seed=training_seed,
        campaign_digest=result.campaign_digest,
        completed_threshold_methods=result.completed_threshold_methods,
    )


def _estimation_summary(
    *,
    experiment_id: ExperimentId,
    method: FederatedThresholdMethod,
    include_threshold_error: bool,
    include_exceedance_and_variance: bool,
) -> tuple[EstimationSummary | None, int]:
    documents: list[FederatedEvaluationDocument] = []
    missing = 0
    for seed in CONFIRMATORY_SEED_COHORT.values:
        try:
            documents.append(_evaluation_document_for_seed(seed, method, experiment_id, OUTPUTS_ROOT))
        except ScientificContractError:
            missing += 1
    if not documents:
        return None, missing

    cv_values = [
        value for document in documents if (value := _try_metric_value(document, MetricId.FPR_COEFFICIENT_OF_VARIATION))
    ]
    worst_values = [
        value for document in documents if (value := _try_metric_value(document, MetricId.WORST_CLIENT_FPR))
    ]
    threshold_errors: list[float] = []
    attainment_errors: list[float] = []
    exceedances: list[float] = []
    variances: list[float] = []
    communication: list[ByteCount] = []
    for document in documents:
        if include_threshold_error:
            for diagnostic in document.diagnostics.threshold_estimation:
                threshold_errors.append(diagnostic.absolute_threshold_error)
                attainment_errors.append(diagnostic.absolute_attainment_error)
        if include_exceedance_and_variance:
            for diagnostic in document.diagnostics.threshold_estimation:
                exceedances.append(diagnostic.achieved_benign_exceedance.value)
            for point in document.diagnostics.sample_efficiency:
                variances.append(point.threshold_variance_across_nested_replicates.value)
        if document.diagnostics.communication is not None:
            communication.append(document.diagnostics.communication.total_estimated_serialized_bytes)

    return (
        EstimationSummary(
            method=method,
            seed_count=SeedCount(len(documents)),
            mean_cv_fpr=_mean_metric(cv_values),
            mean_worst_client_fpr=_mean_metric(worst_values),
            cv_fpr_across_seeds=_cv(cv_values),
            mean_absolute_threshold_error=_mean_absolute_threshold_error(threshold_errors),
            mean_absolute_attainment_error=(
                MetricValue(sum(attainment_errors) / len(attainment_errors)) if attainment_errors else None
            ),
            mean_achieved_exceedance=_mean_ratio(exceedances),
            mean_threshold_variance=_mean_threshold_variance(variances),
            mean_estimated_communication_bytes=_mean_bytes(communication),
        ),
        missing,
    )


def run_federated_benign_statistics_comparison_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
) -> FederatedEstimationSeedResult:
    return _run_estimation_seed(
        ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON,
        training_seed,
        output_root,
        overwrite,
    )


def report_federated_benign_statistics_comparison(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> tuple[tuple[Path, ...], str]:
    del overwrite
    declaration = _declaration_for(experiment_id)
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    rows: list[EstimationSummary] = []
    missing = 0
    for method in declaration.federated_thresholds:
        summary, missing_for_method = _estimation_summary(
            experiment_id=experiment_id,
            method=method,
            include_threshold_error=True,
            include_exceedance_and_variance=False,
        )
        missing += missing_for_method
        if summary is not None:
            rows.append(summary)
    serialize_json_model(
        EstimationSummaryReport(experiment=experiment_id, rows=tuple(rows)),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return _finalize_report(
        directory,
        _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text="federated_benign_statistics_comparison_analysis_complete\n",
    )


def federated_benign_statistics_comparison_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


def run_federated_quantile_estimation_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
) -> FederatedEstimationSeedResult:
    return _run_estimation_seed(ExperimentId.FEDERATED_QUANTILE_ESTIMATION, training_seed, output_root, overwrite)


def report_federated_quantile_estimation(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> tuple[tuple[Path, ...], str]:
    del overwrite
    declaration = _declaration_for(experiment_id)
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    rows: list[EstimationSummary] = []
    missing = 0
    for method in declaration.federated_thresholds:
        summary, missing_for_method = _estimation_summary(
            experiment_id=experiment_id,
            method=method,
            include_threshold_error=False,
            include_exceedance_and_variance=True,
        )
        missing += missing_for_method
        if summary is not None:
            rows.append(summary)
    serialize_json_model(
        EstimationSummaryReport(experiment=experiment_id, rows=tuple(rows)),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return _finalize_report(
        directory,
        _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text="federated_quantile_estimation_analysis_complete\n",
    )


def federated_quantile_estimation_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


def run_fixed_coefficient_statistics_sensitivity_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
) -> FederatedEstimationSeedResult:
    return _run_estimation_seed(
        ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY,
        training_seed,
        output_root,
        overwrite,
    )


def report_fixed_coefficient_statistics_sensitivity(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> tuple[tuple[Path, ...], str]:
    del overwrite
    declaration = _declaration_for(experiment_id)
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    rows: list[FixedCoefficientSummary] = []
    missing = 0
    for method in declaration.federated_thresholds:
        for seed in CONFIRMATORY_SEED_COHORT.values:
            try:
                document = _evaluation_document_for_seed(seed, method, experiment_id, OUTPUTS_ROOT)
            except ScientificContractError:
                missing += 1
                continue
            cv_fpr = _try_metric_value(document, MetricId.FPR_COEFFICIENT_OF_VARIATION)
            worst_fpr = _try_metric_value(document, MetricId.WORST_CLIENT_FPR)
            if method is FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS:
                coordinate = _threshold_coordinate_for_seed(seed, method, experiment_id)
                threshold_path = _threshold_result_path(OUTPUTS_ROOT, coordinate)
                if threshold_path.is_file():
                    threshold_result = _load_threshold_result(threshold_path)
                    from datp_core.thresholds.variants.federated_statistics import FederatedStatisticsThresholdResult

                    if isinstance(threshold_result, FederatedStatisticsThresholdResult):
                        rows.extend(
                            FixedCoefficientSummary(
                                seed=seed,
                                coefficient=entry.coefficient,
                                method=method,
                                threshold_value=entry.threshold,
                                cv_fpr=cv_fpr,
                                worst_client_fpr=worst_fpr,
                            )
                            for entry in threshold_result.fixed_coefficient_curve
                        )
                        continue
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
    serialize_json_model(
        FixedCoefficientSummaryReport(experiment=experiment_id, rows=tuple(rows)),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return _finalize_report(
        directory,
        _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text="fixed_coefficient_statistics_sensitivity_analysis_complete\n",
    )


def fixed_coefficient_statistics_sensitivity_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()

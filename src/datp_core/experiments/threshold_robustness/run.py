"""Threshold-robustness experiment runners and typed evidence summaries."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from datp_core.data.populations.contracts import ClientIdentity
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import ExperimentId, FederatedThresholdMethod, MetricId, PopulationId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import serialize_json_model
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import CalibrationSize, ReplicateIndex, Seed, SeedCount
from datp_core.domain.values.ratios import MetricDelta, MetricValue, Quantile, Ratio, ShrinkageWeight
from datp_core.evaluation.federated.publication import FederatedEvaluationAssetName
from datp_core.evaluation.models import MetricStatus, metric_by_id
from datp_core.experiments.execution import execute_declared_experiment_seed
from datp_core.experiments.planning import expand_experiment_plan
from datp_core.pipeline.coordinates import ExperimentCoordinate
from datp_core.pipeline.execution.evidence import load_evaluation_document, population_metric
from datp_core.pipeline.execution.layout import EvaluationRunAssetDirectory
from datp_core.pipeline.publication.layout import evaluation_run_directory
from datp_core.protocols.calibration import (
    CALIBRATION_SIZES,
    QUANTILE_GRID,
    require_calibration_subsample_replicate_count,
)
from datp_core.protocols.experiments import EXPERIMENTS, ExperimentDeclaration
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.runtime.configuration import OUTPUTS_ROOT
from datp_core.thresholding.identities import ThresholdInfeasibilityReason

if TYPE_CHECKING:
    from datp_core.evaluation.federated.contracts import FederatedEvaluationDocument
    from datp_core.evaluation.models import MetricAvailability


class ThresholdRobustnessArtifactName(StrEnum):
    ROOT = "threshold_robustness"
    ANALYSIS = "analysis"
    SUMMARY = "summary.json"


class ThresholdRobustnessSeedResult(StrictModel):
    training_seed: Seed
    campaign_digest: Checksum
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
    replicate: ReplicateIndex
    cv_fpr: MetricValue | None
    worst_client_fpr: MetricValue | None
    p10_macro_f1: MetricValue | None


class CalibrationSizeAblationReport(StrictModel):
    experiment: ExperimentId
    rows: tuple[CalibrationSizeAblationRow, ...]


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
    from datp_core.pipeline.decision.evidence import AnalysisAssetName

    return _analysis_directory(experiment_id, population) / AnalysisAssetName.COMPLETE.value


def _summary_path(experiment_id: ExperimentId, population: PopulationId) -> Path:
    return _analysis_directory(experiment_id, population) / ThresholdRobustnessArtifactName.SUMMARY


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


def _evaluation_document_for_seed(
    seed: Seed,
    method: FederatedThresholdMethod,
    experiment_id: ExperimentId,
    output_root: Path,
    *,
    quantile: Quantile | None = None,
) -> FederatedEvaluationDocument:
    declaration = _declaration_for(experiment_id)
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
            f"evaluation coordinate for {method.value}{quantile_suffix} must resolve exactly once"
        )
    path = _evaluation_document_path(output_root, matches[0])
    if not path.is_file():
        raise ScientificContractError(f"missing evaluation document: {path}")
    return load_evaluation_document(path)


def _run_robustness_seed(
    experiment_id: ExperimentId,
    training_seed: Seed,
    output_root: Path,
    overwrite: bool,
) -> ThresholdRobustnessSeedResult:
    declaration = _declaration_for(experiment_id)
    result = execute_declared_experiment_seed(
        declaration=declaration,
        seed_cohort=SeedCohort(values=(training_seed,)),
        reason=f"threshold robustness entry point for {experiment_id.value}",
        output_root=output_root,
        overwrite=overwrite,
    )
    return ThresholdRobustnessSeedResult(
        training_seed=training_seed,
        campaign_digest=result.campaign_digest,
        completed_threshold_methods=result.completed_threshold_methods,
    )


def _available_metric_value(metrics: tuple[MetricAvailability, ...], metric_id: MetricId) -> MetricValue | None:
    result = metric_by_id(metrics, metric_id)
    return result.value if result.status is MetricStatus.AVAILABLE else None


def _mean(values: list[MetricValue]) -> MetricValue | None:
    return MetricValue(sum(value.value for value in values) / len(values)) if values else None


def _coefficient_of_variation(values: list[MetricValue]) -> MetricValue | None:
    if len(values) < 2:
        return None
    mean = sum(value.value for value in values) / len(values)
    if mean == 0:
        return None
    variance = sum((value.value - mean) ** 2 for value in values) / len(values)
    return MetricValue(variance**0.5 / mean)


def _method_summary(
    method: FederatedThresholdMethod, documents: tuple[FederatedEvaluationDocument, ...]
) -> MethodCvSummary:
    cv_values = [population_metric(document, MetricId.FPR_COEFFICIENT_OF_VARIATION) for document in documents]
    worst_values = [population_metric(document, MetricId.WORST_CLIENT_FPR) for document in documents]
    return MethodCvSummary(
        method=method,
        seed_count=SeedCount(len(documents)),
        mean_cv_fpr=_mean(cv_values),
        mean_worst_client_fpr=_mean(worst_values),
        cv_fpr_across_seeds=_coefficient_of_variation(cv_values),
    )


def run_shared_construction_sensitivity_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(
        ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY,
        training_seed,
        output_root,
        overwrite,
    )


def report_shared_construction_sensitivity(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> tuple[tuple[Path, ...], str]:
    del overwrite
    declaration = _declaration_for(experiment_id)
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
    return _finalize_report(
        directory,
        _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text="shared_construction_sensitivity_analysis_complete\n",
    )


def shared_construction_sensitivity_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


def run_quantile_sensitivity_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(ExperimentId.QUANTILE_SENSITIVITY, training_seed, output_root, overwrite)


def report_quantile_sensitivity(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> tuple[tuple[Path, ...], str]:
    del overwrite
    declaration = _declaration_for(experiment_id)
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
    return _finalize_report(
        directory,
        _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text="quantile_sensitivity_analysis_complete\n",
    )


def quantile_sensitivity_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


def run_calibration_size_ablation_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
) -> ThresholdRobustnessSeedResult:
    require_calibration_subsample_replicate_count()
    return _run_robustness_seed(ExperimentId.CALIBRATION_SIZE_ABLATION, training_seed, output_root, overwrite)


def report_calibration_size_ablation(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> tuple[tuple[Path, ...], str]:
    del overwrite
    replicate_count = require_calibration_subsample_replicate_count()
    declaration = _declaration_for(experiment_id)
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    rows: list[CalibrationSizeAblationRow] = []
    missing = 0
    for method in declaration.federated_thresholds:
        for seed in CONFIRMATORY_SEED_COHORT.values:
            try:
                document = _evaluation_document_for_seed(seed, method, experiment_id, OUTPUTS_ROOT)
            except ScientificContractError:
                missing += 1
                continue
            for cell in document.diagnostics.calibration_size_ablation:
                metrics = cell.population.metrics
                rows.append(
                    CalibrationSizeAblationRow(
                        seed=seed,
                        method=method,
                        calibration_size=cell.calibration_size,
                        replicate=cell.replicate_index,
                        cv_fpr=_available_metric_value(metrics, MetricId.FPR_COEFFICIENT_OF_VARIATION),
                        worst_client_fpr=_available_metric_value(metrics, MetricId.WORST_CLIENT_FPR),
                        p10_macro_f1=_available_metric_value(metrics, MetricId.P10_BINARY_MACRO_F1),
                    )
                )
    serialize_json_model(
        CalibrationSizeAblationReport(experiment=experiment_id, rows=tuple(rows)),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    marker = (
        "calibration_size_ablation_analysis_complete "
        f"sizes={len(CALIBRATION_SIZES)} replicates={replicate_count.value}\n"
    )
    return _finalize_report(
        directory,
        _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text=marker,
    )


def calibration_size_ablation_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


def run_fixed_shrinkage_curve_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(ExperimentId.FIXED_SHRINKAGE_CURVE, training_seed, output_root, overwrite)


def report_fixed_shrinkage_curve(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> tuple[tuple[Path, ...], str]:
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
                    cv_fpr=_available_metric_value(
                        evaluation.population.metrics,
                        MetricId.FPR_COEFFICIENT_OF_VARIATION,
                    ),
                    worst_client_fpr=_available_metric_value(
                        evaluation.population.metrics,
                        MetricId.WORST_CLIENT_FPR,
                    ),
                )
            )
    serialize_json_model(
        ShrinkageCurveReport(experiment=experiment_id, rows=tuple(rows)),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return _finalize_report(
        directory,
        _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text="fixed_shrinkage_curve_analysis_complete\n",
    )


def fixed_shrinkage_curve_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


def run_size_aware_shrinkage_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
) -> ThresholdRobustnessSeedResult:
    declaration = _declaration_for(ExperimentId.SIZE_AWARE_SHRINKAGE)
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
        reason=(
            "size-aware shrinkage executes its declared reference corners only because "
            "the roadmap does not declare a lambda(n_k) function"
        ),
        output_root=output_root,
        overwrite=overwrite,
    )
    return ThresholdRobustnessSeedResult(
        training_seed=training_seed,
        campaign_digest=result.campaign_digest,
        completed_threshold_methods=result.completed_threshold_methods,
    )


def report_size_aware_shrinkage(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> tuple[tuple[Path, ...], str]:
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
        raise ScientificContractError("size-aware shrinkage report requires both executable reference corners")
    serialize_json_model(
        SizeAwareShrinkageReport(
            experiment=experiment_id,
            unavailable_reason=ThresholdInfeasibilityReason.SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED,
            shared_threshold=summary_by_method[FederatedThresholdMethod.SHARED_THRESHOLD],
            local_threshold=summary_by_method[FederatedThresholdMethod.LOCAL_THRESHOLD],
        ),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return _finalize_report(
        directory,
        _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text="size_aware_shrinkage_analysis_complete\n",
    )


def size_aware_shrinkage_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


def run_local_conformal_coverage_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(ExperimentId.LOCAL_CONFORMAL_COVERAGE, training_seed, output_root, overwrite)


def report_local_conformal_coverage(
    experiment_id: ExperimentId,
    overwrite: bool,
) -> tuple[tuple[Path, ...], str]:
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
            client_fpr: MetricValue | None = None
            for client_result in document.clients:
                if client_result.client == diagnostic.client:
                    metric = metric_by_id(client_result.metrics, MetricId.FALSE_POSITIVE_RATE)
                    if metric.status is MetricStatus.AVAILABLE:
                        client_fpr = metric.value
                    break
            rows.append(
                ConformalCoverageRow(
                    seed=seed,
                    client=diagnostic.client,
                    target_coverage=Ratio(diagnostic.target_coverage.value),
                    achieved_coverage=(
                        None
                        if diagnostic.achieved_held_out_benign_coverage is None
                        else Ratio(diagnostic.achieved_held_out_benign_coverage)
                    ),
                    signed_coverage_error=(
                        None
                        if diagnostic.signed_coverage_error is None
                        else MetricDelta(diagnostic.signed_coverage_error)
                    ),
                    absolute_coverage_error=(
                        None
                        if diagnostic.absolute_coverage_error is None
                        else MetricValue(diagnostic.absolute_coverage_error)
                    ),
                    client_fpr=client_fpr,
                )
            )
    serialize_json_model(
        ConformalCoverageReport(experiment=experiment_id, rows=tuple(rows)),
        _summary_path(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    return _finalize_report(
        directory,
        _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text="local_conformal_coverage_analysis_complete\n",
    )


def local_conformal_coverage_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()

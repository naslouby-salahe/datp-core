"""Federated threshold-estimation seed runners, reports, and analysis markers.

Covers three threshold-variant experiments:
- FEDERATED_BENIGN_STATISTICS_COMPARISON
- FEDERATED_QUANTILE_ESTIMATION
- FIXED_COEFFICIENT_STATISTICS_SENSITIVITY
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import TypeAdapter

from datp_core.domain.enums import (
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import Seed
from datp_core.evaluation.federated.publication import FederatedEvaluationAssetName
from datp_core.evaluation.models import MetricStatus, metric_by_id
from datp_core.pipeline.coordinates import ExperimentCoordinate
from datp_core.pipeline.execution.evidence import load_evaluation_document
from datp_core.pipeline.execution.layout import EvaluationRunAssetDirectory
from datp_core.pipeline.planning import expand_experiment_plan
from datp_core.pipeline.publication.layout import evaluation_run_directory
from datp_core.protocols.experiments import ExperimentDeclaration
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.runtime.configuration import OUTPUTS_ROOT
from datp_core.thresholding.publication import FederatedThresholdAssetName

if TYPE_CHECKING:
    from datp_core.evaluation.federated.contracts import FederatedEvaluationDocument
    from datp_core.thresholding.models import ThresholdConstructionResult


class FederatedEstimationAssetDirectory(StrEnum):
    ROOT = "federated_threshold_estimation"


_SUMMARY_FILENAME = "summary.json"


@dataclass(frozen=True, slots=True, kw_only=True)
class _EstimationSummaryRow:
    method: str
    seed_count: int
    mean_cv_fpr: float | None
    worst_client_fpr: float | None
    fpr_coefficient_of_variation: float | None
    mean_absolute_threshold_error: float | None = None
    mean_absolute_attainment_error: float | None = None
    mean_achieved_exceedance: float | None = None
    mean_threshold_variance: float | None = None
    estimated_communication_bytes: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class _FixedCoefficientSummaryRow:
    seed: int
    coefficient: float | None
    method: str
    threshold_value: float | None
    cv_fpr: float | None
    worst_client_fpr: float | None


@dataclass(frozen=True, slots=True, kw_only=True)
class FederatedEstimationSeedResult:
    training_seed: Seed
    campaign_digest: Checksum
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


def _analysis_directory(experiment_id: ExperimentId, population: PopulationId) -> Path:
    return (
        OUTPUTS_ROOT
        / FederatedEstimationAssetDirectory.ROOT
        / experiment_id.value
        / population.value
        / "analysis"
    )


def _complete_marker(experiment_id: ExperimentId, population: PopulationId) -> Path:
    from datp_core.pipeline.decision.evidence import AnalysisAssetName

    return _analysis_directory(experiment_id, population) / AnalysisAssetName.COMPLETE


def _declaration_for(experiment_id: ExperimentId) -> ExperimentDeclaration:
    from datp_core.pipeline.workflows import require_experiment_declaration

    return require_experiment_declaration(experiment_id)


def _evaluation_document_path(
    output_root: Path,
    coordinate: ExperimentCoordinate,
) -> Path:
    return (
        evaluation_run_directory(output_root, coordinate)
        / EvaluationRunAssetDirectory.EVALUATION
        / FederatedEvaluationAssetName.DOCUMENT
    )


def _threshold_result_path(
    output_root: Path,
    coordinate: ExperimentCoordinate,
) -> Path:
    return (
        evaluation_run_directory(output_root, coordinate)
        / EvaluationRunAssetDirectory.THRESHOLD
        / FederatedThresholdAssetName.RESULT
    )


def _load_threshold_result(path: Path) -> ThresholdConstructionResult:
    from datp_core.thresholding.models import ThresholdConstructionResult

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


def _try_metric_value(doc: FederatedEvaluationDocument, metric: MetricId) -> float | None:
    result = metric_by_id(doc.population.metrics, metric)
    if result.status is MetricStatus.AVAILABLE and result.value is not None:
        return result.value.value
    return None


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _coefficient_of_variation(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    if mean == 0:
        return None
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return variance**0.5 / mean


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
    from datp_core.pipeline.workflows.execution import execute_declared_experiment_seed

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


# ── FEDERATED_BENIGN_STATISTICS_COMPARISON ─────────────────────────────────


def run_federated_benign_statistics_comparison_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool = False,
) -> FederatedEstimationSeedResult:
    return _run_estimation_seed(
        ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON,
        training_seed,
        output_root=output_root,
        overwrite=overwrite,
    )


def report_federated_benign_statistics_comparison(
    experiment_id: ExperimentId, overwrite: bool,
) -> tuple[tuple[Path, ...], str]:
    del overwrite
    declaration = _declaration_for(experiment_id)
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    summary: dict[str, _EstimationSummaryRow] = {}
    missing = 0
    for method in declaration.federated_thresholds:
        cv_values: list[float] = []
        worst_fpr_values: list[float] = []
        abs_threshold_errors: list[float] = []
        abs_attainment_errors: list[float] = []
        comm_bytes_values: list[int] = []
        for seed in CONFIRMATORY_SEED_COHORT.values:
            try:
                doc = _evaluation_document_for_seed(seed, method, experiment_id, OUTPUTS_ROOT)
            except ScientificContractError:
                missing += 1
                continue
            cv_val = _try_metric_value(doc, MetricId.FPR_COEFFICIENT_OF_VARIATION)
            if cv_val is not None:
                cv_values.append(cv_val)
            worst_val = _try_metric_value(doc, MetricId.WORST_CLIENT_FPR)
            if worst_val is not None:
                worst_fpr_values.append(worst_val)
            for diag in doc.diagnostics.threshold_estimation:
                abs_threshold_errors.append(diag.absolute_threshold_error)
                abs_attainment_errors.append(diag.absolute_attainment_error)
            if doc.diagnostics.communication is not None:
                comm_bytes_values.append(
                    doc.diagnostics.communication.total_estimated_serialized_bytes.value
                )
        summary[method.value] = _EstimationSummaryRow(
            method=method.value,
            seed_count=len(cv_values),
            mean_cv_fpr=_mean(cv_values),
            worst_client_fpr=_mean(worst_fpr_values),
            fpr_coefficient_of_variation=_coefficient_of_variation(cv_values),
            mean_absolute_threshold_error=_mean(abs_threshold_errors),
            mean_absolute_attainment_error=_mean(abs_attainment_errors),
            estimated_communication_bytes=(
                int(mean_bytes) if (mean_bytes := _mean([float(b) for b in comm_bytes_values])) is not None
                else None
            ),
        )
    serialized = {
        key: {k: v for k, v in asdict(row).items()}
        for key, row in summary.items()
    }
    (directory / _SUMMARY_FILENAME).write_text(json.dumps(serialized, indent=2), encoding="utf-8")
    return _finalize_report(
        directory,
        _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text="federated_benign_statistics_comparison_analysis_complete\n",
    )


def federated_benign_statistics_comparison_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


# ── FEDERATED_QUANTILE_ESTIMATION ──────────────────────────────────────────


def run_federated_quantile_estimation_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool = False,
) -> FederatedEstimationSeedResult:
    return _run_estimation_seed(
        ExperimentId.FEDERATED_QUANTILE_ESTIMATION,
        training_seed,
        output_root=output_root,
        overwrite=overwrite,
    )


def report_federated_quantile_estimation(
    experiment_id: ExperimentId, overwrite: bool,
) -> tuple[tuple[Path, ...], str]:
    del overwrite
    declaration = _declaration_for(experiment_id)
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    summary: dict[str, _EstimationSummaryRow] = {}
    missing = 0
    for method in declaration.federated_thresholds:
        cv_values: list[float] = []
        worst_fpr_values: list[float] = []
        achieved_exceedance_values: list[float] = []
        threshold_variances: list[float] = []
        comm_bytes_values: list[int] = []
        for seed in CONFIRMATORY_SEED_COHORT.values:
            try:
                doc = _evaluation_document_for_seed(seed, method, experiment_id, OUTPUTS_ROOT)
            except ScientificContractError:
                missing += 1
                continue
            cv_val = _try_metric_value(doc, MetricId.FPR_COEFFICIENT_OF_VARIATION)
            if cv_val is not None:
                cv_values.append(cv_val)
            worst_val = _try_metric_value(doc, MetricId.WORST_CLIENT_FPR)
            if worst_val is not None:
                worst_fpr_values.append(worst_val)
            for diag in doc.diagnostics.threshold_estimation:
                achieved_exceedance_values.append(diag.achieved_benign_exceedance.value)
            for point in doc.diagnostics.sample_efficiency:
                threshold_variances.append(
                    point.threshold_variance_across_nested_replicates.value
                )
            if doc.diagnostics.communication is not None:
                comm_bytes_values.append(
                    doc.diagnostics.communication.total_estimated_serialized_bytes.value
                )
        summary[method.value] = _EstimationSummaryRow(
            method=method.value,
            seed_count=len(cv_values),
            mean_cv_fpr=_mean(cv_values),
            worst_client_fpr=_mean(worst_fpr_values),
            fpr_coefficient_of_variation=_coefficient_of_variation(cv_values),
            mean_achieved_exceedance=_mean(achieved_exceedance_values),
            mean_threshold_variance=_mean(threshold_variances),
            estimated_communication_bytes=(
                int(mean_bytes) if (mean_bytes := _mean([float(b) for b in comm_bytes_values])) is not None
                else None
            ),
        )
    serialized = {
        key: {k: v for k, v in asdict(row).items()}
        for key, row in summary.items()
    }
    (directory / _SUMMARY_FILENAME).write_text(json.dumps(serialized, indent=2), encoding="utf-8")
    return _finalize_report(
        directory,
        _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text="federated_quantile_estimation_analysis_complete\n",
    )


def federated_quantile_estimation_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


# ── FIXED_COEFFICIENT_STATISTICS_SENSITIVITY ───────────────────────────────


def run_fixed_coefficient_statistics_sensitivity_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool = False,
) -> FederatedEstimationSeedResult:
    return _run_estimation_seed(
        ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY,
        training_seed,
        output_root=output_root,
        overwrite=overwrite,
    )


def report_fixed_coefficient_statistics_sensitivity(
    experiment_id: ExperimentId, overwrite: bool,
) -> tuple[tuple[Path, ...], str]:
    del overwrite
    declaration = _declaration_for(experiment_id)
    directory = _analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    summary: list[_FixedCoefficientSummaryRow] = []
    missing = 0
    for method in declaration.federated_thresholds:
        for seed in CONFIRMATORY_SEED_COHORT.values:
            try:
                doc = _evaluation_document_for_seed(seed, method, experiment_id, OUTPUTS_ROOT)
            except ScientificContractError:
                missing += 1
                continue
            cv_val = _try_metric_value(doc, MetricId.FPR_COEFFICIENT_OF_VARIATION)
            worst_val = _try_metric_value(doc, MetricId.WORST_CLIENT_FPR)
            if method is FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS:
                coordinate = _threshold_coordinate_for_seed(seed, method, experiment_id)
                threshold_path = _threshold_result_path(OUTPUTS_ROOT, coordinate)
                if threshold_path.is_file():
                    thr_result = _load_threshold_result(threshold_path)
                    from datp_core.thresholding.methods.federated_statistics import (
                        FederatedStatisticsThresholdResult,
                    )
                    if isinstance(thr_result, FederatedStatisticsThresholdResult):
                        for entry in thr_result.fixed_coefficient_curve:
                            summary.append(
                                _FixedCoefficientSummaryRow(
                                    seed=seed.value,
                                    coefficient=entry.coefficient.value,
                                    method=method.value,
                                    threshold_value=entry.threshold.value,
                                    cv_fpr=cv_val,
                                    worst_client_fpr=worst_val,
                                )
                            )
                        continue
                summary.append(
                    _FixedCoefficientSummaryRow(
                        seed=seed.value,
                        coefficient=None,
                        method=method.value,
                        threshold_value=None,
                        cv_fpr=cv_val,
                        worst_client_fpr=worst_val,
                    )
                )
            else:
                summary.append(
                    _FixedCoefficientSummaryRow(
                        seed=seed.value,
                        coefficient=None,
                        method=method.value,
                        threshold_value=None,
                        cv_fpr=cv_val,
                        worst_client_fpr=worst_val,
                    )
                )
    serialized = [asdict(row) for row in summary]
    (directory / _SUMMARY_FILENAME).write_text(json.dumps(serialized, indent=2), encoding="utf-8")
    return _finalize_report(
        directory,
        _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text="fixed_coefficient_statistics_sensitivity_analysis_complete\n",
    )


def fixed_coefficient_statistics_sensitivity_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()

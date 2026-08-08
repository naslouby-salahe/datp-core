"""Threshold robustness seed runners, reports, and analysis markers.

Covers six supportive threshold experiments:
- SHARED_CONSTRUCTION_SENSITIVITY
- QUANTILE_SENSITIVITY (planning sweeps quantile grid)
- CALIBRATION_SIZE_ABLATION (dormant workspace wiring)
- FIXED_SHRINKAGE_CURVE (LOCAL_GLOBAL_SHRINKAGE)
- SIZE_AWARE_SHRINKAGE (scientifically unavailable)
- LOCAL_CONFORMAL_COVERAGE (LOCAL_CONFORMAL_THRESHOLD)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from datp_core.domain.enums import (
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import Quantile
from datp_core.evaluation.federated.publication import FederatedEvaluationAssetName
from datp_core.evaluation.models import MetricStatus, metric_by_id
from datp_core.pipeline.coordinates import ExperimentCoordinate
from datp_core.pipeline.execution.evidence import load_evaluation_document, population_metric
from datp_core.pipeline.execution.layout import EvaluationRunAssetDirectory
from datp_core.pipeline.planning import expand_experiment_plan
from datp_core.pipeline.publication.layout import evaluation_run_directory
from datp_core.pipeline.workflows.execution import execute_declared_experiment_seed
from datp_core.protocols.calibration import (
    CALIBRATION_SIZES,
    CALIBRATION_SUBSAMPLE_REPLICATE_COUNT,
    QUANTILE_GRID,
)
from datp_core.protocols.experiments import ExperimentDeclaration
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.runtime.configuration import OUTPUTS_ROOT

if TYPE_CHECKING:
    from datp_core.evaluation.federated.contracts import FederatedEvaluationDocument
    from datp_core.evaluation.models import MetricAvailability

_SUMMARY_FILENAME = "summary.json"


class ThresholdRobustnessAssetDirectory(StrEnum):
    ROOT = "threshold_robustness"


@dataclass(frozen=True, slots=True, kw_only=True)
class _MethodCvSummaryRow:
    seed_count: int
    mean_cv_fpr: float | None
    worst_client_fpr: float | None
    fpr_coefficient_of_variation: float | None


@dataclass(frozen=True, slots=True, kw_only=True)
class _CalibrationSizeAblationRow:
    seed: int
    method: str
    calibration_size: int
    replicate: int
    cv_fpr: float | None
    worst_client_fpr: float | None
    p10_macro_f1: float | None


@dataclass(frozen=True, slots=True, kw_only=True)
class _ShrinkageCurveRow:
    seed: int
    lambda_weight: float
    cv_fpr: float | None
    worst_client_fpr: float | None


@dataclass(frozen=True, slots=True, kw_only=True)
class _ConformalCoverageRow:
    seed: int
    client: str
    target_coverage: float
    achieved_coverage: float | None
    signed_coverage_error: float | None
    absolute_coverage_error: float | None
    client_fpr: float | None


@dataclass(frozen=True, slots=True, kw_only=True)
class _SizeAwareShrinkageSummary:
    unavailable_note: str
    shared_threshold: _MethodCvSummaryRow | None
    local_threshold: _MethodCvSummaryRow | None


def _threshold_robustness_analysis_directory(experiment_id: ExperimentId, population: PopulationId) -> Path:
    return (
        OUTPUTS_ROOT
        / ThresholdRobustnessAssetDirectory.ROOT
        / experiment_id.value
        / population.value
        / "analysis"
    )


def _threshold_robustness_complete_marker(experiment_id: ExperimentId, population: PopulationId) -> Path:
    from datp_core.pipeline.decision.evidence import AnalysisAssetName

    return _threshold_robustness_analysis_directory(experiment_id, population) / AnalysisAssetName.COMPLETE.value


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


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdRobustnessSeedResult:
    training_seed: Seed
    campaign_digest: Checksum
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


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


def _available_metric_value(
    metrics: tuple[MetricAvailability, ...],
    metric_id: MetricId,
) -> float | None:
    """Return the metric value if AVAILABLE, None otherwise."""
    result = metric_by_id(metrics, metric_id)
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


# ── SHARED_CONSTRUCTION_SENSITIVITY ──────────────────────────────────────────


def run_shared_construction_sensitivity_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool = False,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(
        ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY,
        training_seed,
        output_root=output_root,
        overwrite=overwrite,
    )


def report_shared_construction_sensitivity(
    experiment_id: ExperimentId, overwrite: bool,
) -> tuple[tuple[Path, ...], str]:
    del overwrite
    declaration = _declaration_for(experiment_id)
    directory = _threshold_robustness_analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    summary: dict[str, _MethodCvSummaryRow] = {}
    missing = 0
    for method in declaration.federated_thresholds:
        cv_values: list[float] = []
        worst_fpr_values: list[float] = []
        for seed in CONFIRMATORY_SEED_COHORT.values:
            try:
                doc = _evaluation_document_for_seed(seed, method, experiment_id, OUTPUTS_ROOT)
                cv_values.append(population_metric(doc, MetricId.FPR_COEFFICIENT_OF_VARIATION).value)
                worst_fpr_values.append(population_metric(doc, MetricId.WORST_CLIENT_FPR).value)
            except ScientificContractError:
                missing += 1
        summary[method.value] = _MethodCvSummaryRow(
            seed_count=len(cv_values),
            mean_cv_fpr=_mean(cv_values),
            worst_client_fpr=_mean(worst_fpr_values),
            fpr_coefficient_of_variation=_coefficient_of_variation(cv_values),
        )
    serialized = {method: asdict(row) for method, row in summary.items()}
    (directory / _SUMMARY_FILENAME).write_text(json.dumps(serialized, indent=2), encoding="utf-8")
    return _finalize_report(
        directory,
        _threshold_robustness_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text="shared_construction_sensitivity_analysis_complete\n",
    )


def shared_construction_sensitivity_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _threshold_robustness_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


# ── QUANTILE_SENSITIVITY ─────────────────────────────────────────────────────


def run_quantile_sensitivity_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool = False,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(
        ExperimentId.QUANTILE_SENSITIVITY,
        training_seed,
        output_root=output_root,
        overwrite=overwrite,
    )


def report_quantile_sensitivity(experiment_id: ExperimentId, overwrite: bool) -> tuple[tuple[Path, ...], str]:
    del overwrite
    declaration = _declaration_for(experiment_id)
    directory = _threshold_robustness_analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    summary: dict[str, dict[str, _MethodCvSummaryRow]] = {}
    missing = 0
    for method in declaration.federated_thresholds:
        method_summary: dict[str, _MethodCvSummaryRow] = {}
        for quantile in QUANTILE_GRID:
            cv_values: list[float] = []
            worst_fpr_values: list[float] = []
            for seed in CONFIRMATORY_SEED_COHORT.values:
                try:
                    doc = _evaluation_document_for_seed(
                        seed, method, experiment_id, OUTPUTS_ROOT, quantile=quantile
                    )
                    cv_values.append(population_metric(doc, MetricId.FPR_COEFFICIENT_OF_VARIATION).value)
                    worst_fpr_values.append(population_metric(doc, MetricId.WORST_CLIENT_FPR).value)
                except ScientificContractError:
                    missing += 1
            method_summary[str(quantile.value)] = _MethodCvSummaryRow(
                seed_count=len(cv_values),
                mean_cv_fpr=_mean(cv_values),
                worst_client_fpr=_mean(worst_fpr_values),
                fpr_coefficient_of_variation=_coefficient_of_variation(cv_values),
            )
        summary[method.value] = method_summary
    serialized = {
        method: {quantile: asdict(row) for quantile, row in quantile_summary.items()}
        for method, quantile_summary in summary.items()
    }
    (directory / _SUMMARY_FILENAME).write_text(json.dumps(serialized, indent=2), encoding="utf-8")
    return _finalize_report(
        directory,
        _threshold_robustness_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text="quantile_sensitivity_analysis_complete\n",
    )


def quantile_sensitivity_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _threshold_robustness_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


# ── CALIBRATION_SIZE_ABLATION ────────────────────────────────────────────────


def run_calibration_size_ablation_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool = False,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(
        ExperimentId.CALIBRATION_SIZE_ABLATION,
        training_seed,
        output_root=output_root,
        overwrite=overwrite,
    )


def report_calibration_size_ablation(experiment_id: ExperimentId, overwrite: bool) -> tuple[tuple[Path, ...], str]:
    del overwrite
    declaration = _declaration_for(experiment_id)
    directory = _threshold_robustness_analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    summary: list[_CalibrationSizeAblationRow] = []
    missing = 0
    for method in declaration.federated_thresholds:
        for seed in CONFIRMATORY_SEED_COHORT.values:
            try:
                doc = _evaluation_document_for_seed(seed, method, experiment_id, OUTPUTS_ROOT)
                for cell in doc.diagnostics.calibration_size_ablation:
                    pop_metrics = cell.population.metrics
                    summary.append(
                        _CalibrationSizeAblationRow(
                            seed=seed.value,
                            method=method.value,
                            calibration_size=cell.calibration_size.value,
                            replicate=cell.replicate_index.value,
                            cv_fpr=_available_metric_value(pop_metrics, MetricId.FPR_COEFFICIENT_OF_VARIATION),
                            worst_client_fpr=_available_metric_value(pop_metrics, MetricId.WORST_CLIENT_FPR),
                            p10_macro_f1=_available_metric_value(pop_metrics, MetricId.P10_BINARY_MACRO_F1),
                        )
                    )
            except ScientificContractError:
                missing += 1
    serialized = [asdict(row) for row in summary]
    (directory / _SUMMARY_FILENAME).write_text(json.dumps(serialized, indent=2), encoding="utf-8")
    _size = len(CALIBRATION_SIZES)
    _reps = CALIBRATION_SUBSAMPLE_REPLICATE_COUNT
    return _finalize_report(
        directory,
        _threshold_robustness_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text=f"calibration_size_ablation_analysis_complete sizes={_size} replicates={_reps}\n",
    )


def calibration_size_ablation_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _threshold_robustness_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


# ── FIXED_SHRINKAGE_CURVE ────────────────────────────────────────────────────


def run_fixed_shrinkage_curve_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool = False,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(
        ExperimentId.FIXED_SHRINKAGE_CURVE,
        training_seed,
        output_root=output_root,
        overwrite=overwrite,
    )


def report_fixed_shrinkage_curve(experiment_id: ExperimentId, overwrite: bool) -> tuple[tuple[Path, ...], str]:
    del overwrite
    directory = _threshold_robustness_analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    summary: list[_ShrinkageCurveRow] = []
    missing = 0
    for seed in CONFIRMATORY_SEED_COHORT.values:
        try:
            doc = _evaluation_document_for_seed(
                seed, FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE, experiment_id, OUTPUTS_ROOT
            )
            for evaluation in doc.diagnostics.shrinkage_curve:
                pop_metrics = evaluation.population.metrics
                summary.append(
                    _ShrinkageCurveRow(
                        seed=seed.value,
                        lambda_weight=evaluation.lambda_weight.value,
                        cv_fpr=_available_metric_value(pop_metrics, MetricId.FPR_COEFFICIENT_OF_VARIATION),
                        worst_client_fpr=_available_metric_value(pop_metrics, MetricId.WORST_CLIENT_FPR),
                    )
                )
        except ScientificContractError:
            missing += 1
    serialized = [asdict(row) for row in summary]
    (directory / _SUMMARY_FILENAME).write_text(json.dumps(serialized, indent=2), encoding="utf-8")
    return _finalize_report(
        directory,
        _threshold_robustness_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text="fixed_shrinkage_curve_analysis_complete\n",
    )


def fixed_shrinkage_curve_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _threshold_robustness_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


# ── SIZE_AWARE_SHRINKAGE ─────────────────────────────────────────────────────


def run_size_aware_shrinkage_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool = False,
) -> ThresholdRobustnessSeedResult:
    """Execute SHARED_THRESHOLD and LOCAL_THRESHOLD reference corners only.

    SIZE_AWARE_SHRINKAGE returns ThresholdUnavailableResult at construction time
    because no lambda(n_k) formula is declared. The experiment runs the two
    executable threshold methods as reference corners and reports the
    SIZE_AWARE_SHRINKAGE method as scientifically UNAVAILABLE.
    """
    declaration = _declaration_for(ExperimentId.SIZE_AWARE_SHRINKAGE)
    executable_thresholds = (
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    )
    filtered = declaration.model_copy(update={"federated_thresholds": executable_thresholds})
    result = execute_declared_experiment_seed(
        declaration=filtered,
        seed_cohort=SeedCohort(values=(training_seed,)),
        reason=(
            "size-aware shrinkage entry point executes reference corners only; "
            "shrinkage estimator is scientifically unavailable"
        ),
        output_root=output_root,
        overwrite=overwrite,
    )
    return ThresholdRobustnessSeedResult(
        training_seed=training_seed,
        campaign_digest=result.campaign_digest,
        completed_threshold_methods=result.completed_threshold_methods,
    )


def report_size_aware_shrinkage(experiment_id: ExperimentId, overwrite: bool) -> tuple[tuple[Path, ...], str]:
    del overwrite
    declaration = _declaration_for(experiment_id)
    directory = _threshold_robustness_analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    missing = 0
    rows: dict[FederatedThresholdMethod, _MethodCvSummaryRow] = {}
    for method in declaration.federated_thresholds:
        if method is FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE:
            continue
        cv_values: list[float] = []
        worst_fpr_values: list[float] = []
        for seed in CONFIRMATORY_SEED_COHORT.values:
            try:
                doc = _evaluation_document_for_seed(seed, method, experiment_id, OUTPUTS_ROOT)
                cv_values.append(population_metric(doc, MetricId.FPR_COEFFICIENT_OF_VARIATION).value)
                worst_fpr_values.append(population_metric(doc, MetricId.WORST_CLIENT_FPR).value)
            except ScientificContractError:
                missing += 1
        rows[method] = _MethodCvSummaryRow(
            seed_count=len(cv_values),
            mean_cv_fpr=_mean(cv_values),
            worst_client_fpr=_mean(worst_fpr_values),
            fpr_coefficient_of_variation=_coefficient_of_variation(cv_values),
        )
    summary = _SizeAwareShrinkageSummary(
        unavailable_note=(
            "UNAVAILABLE: no lambda(n_k) formula declared; inventing one is scientifically forbidden"
        ),
        shared_threshold=rows[FederatedThresholdMethod.SHARED_THRESHOLD],
        local_threshold=rows[FederatedThresholdMethod.LOCAL_THRESHOLD],
    )
    (directory / _SUMMARY_FILENAME).write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
    return _finalize_report(
        directory,
        _threshold_robustness_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text="size_aware_shrinkage_analysis_complete\n",
    )


def size_aware_shrinkage_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _threshold_robustness_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()


# ── LOCAL_CONFORMAL_COVERAGE ─────────────────────────────────────────────────


def run_local_conformal_coverage_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool = False,
) -> ThresholdRobustnessSeedResult:
    return _run_robustness_seed(
        ExperimentId.LOCAL_CONFORMAL_COVERAGE,
        training_seed,
        output_root=output_root,
        overwrite=overwrite,
    )


def report_local_conformal_coverage(experiment_id: ExperimentId, overwrite: bool) -> tuple[tuple[Path, ...], str]:
    del overwrite
    directory = _threshold_robustness_analysis_directory(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES)
    directory.mkdir(parents=True, exist_ok=True)
    summary: list[_ConformalCoverageRow] = []
    missing = 0
    for seed in CONFIRMATORY_SEED_COHORT.values:
        try:
            doc = _evaluation_document_for_seed(
                seed, FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD, experiment_id, OUTPUTS_ROOT
            )
            for diagnostic in doc.diagnostics.conformal_coverage:
                client_fpr: float | None = None
                for client_result in doc.clients:
                    if client_result.client == diagnostic.client:
                        fpr_metric = metric_by_id(client_result.metrics, MetricId.FALSE_POSITIVE_RATE)
                        if fpr_metric.status is MetricStatus.AVAILABLE and fpr_metric.value is not None:
                            client_fpr = fpr_metric.value.value
                        break
                summary.append(
                    _ConformalCoverageRow(
                        seed=seed.value,
                        client=diagnostic.client.client_id,
                        target_coverage=diagnostic.target_coverage.value,
                        achieved_coverage=diagnostic.achieved_held_out_benign_coverage,
                        signed_coverage_error=diagnostic.signed_coverage_error,
                        absolute_coverage_error=diagnostic.absolute_coverage_error,
                        client_fpr=client_fpr,
                    )
                )
        except ScientificContractError:
            missing += 1
    serialized = [asdict(row) for row in summary]
    (directory / _SUMMARY_FILENAME).write_text(json.dumps(serialized, indent=2), encoding="utf-8")
    return _finalize_report(
        directory,
        _threshold_robustness_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES),
        missing,
        marker_text="local_conformal_coverage_analysis_complete\n",
    )


def local_conformal_coverage_analysis_marker_present(experiment_id: ExperimentId) -> bool:
    return _threshold_robustness_complete_marker(experiment_id, PopulationId.NBAIOT_NATURAL_DEVICES).is_file()

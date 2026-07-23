"""Conformal-coverage analysis and the ratio-based recovery-fraction/absorption analyses that share
its seed-indexed ratio-of-paired-differences machinery.
"""

from __future__ import annotations

import json
from io import BytesIO
from math import ceil

import numpy as np
import polars as pl

from datp_core.analysis.models import (
    AbsorptionAnalysisResult,
    ConformalClientCoverageRecord,
    ConformalCoverageAnalysisResult,
    ConformalSeedCoverageResult,
    PairedThresholdAnalysisResult,
    RecoveryFractionAnalysisResult,
    SeedRatioResult,
)
from datp_core.artifacts.models import ArtifactRepository
from datp_core.configuration.resolution import ResolvedProjectConfiguration
from datp_core.evaluation.models import MetricStatus
from datp_core.experiments.identity import IdentityBuilder, execution_run_id
from datp_core.experiments.models import (
    AbsorptionAnalysisRecord,
    ConformalCoverageAnalysisRecord,
    ExperimentRecord,
    RecoveryFractionAnalysisRecord,
)
from datp_core.experiments.sweeps import score_context
from datp_core.pipeline.frames import validate_calibration_score_frame, validate_client_metric_frame, validate_threshold_frame
from datp_core.pipeline.identifiers import ExperimentId, RunId
from datp_core.pipeline.models import StageJobContext
from datp_core.pipeline.values import Seed
from datp_core.thresholding.models import ConformalAttainabilityStatus, SplitConformalThresholdPolicyRecord


def mean_group_std(groups: list[list[tuple[float, float]]], index: int) -> float | None:
    return float(np.mean([np.std([item[index] for item in group]) for group in groups])) if groups else None


def group_mean_std(groups: list[list[tuple[float, float]]], index: int) -> float | None:
    return float(np.std([np.mean([item[index] for item in group]) for group in groups])) if groups else None


def materiality_threshold(rule: float | str) -> float:
    if isinstance(rule, float):
        return rule
    if rule == "absolute_denominator_at_least_1.0e-6":
        return 1.0e-6
    raise ValueError(f"Unsupported denominator materiality rule: {rule!r}")


def weighted_mean(values: list[tuple[int, int]]) -> float | None:
    denominator = sum(weight for _, weight in values)
    return sum(value for value, _ in values) / denominator if denominator else None


def seed_ratio_result(
    *,
    label: str,
    formula: str,
    numerator_seed_differences: tuple[float, ...],
    denominator_seed_differences: tuple[float, ...],
    materiality_rule: float | str,
    undefined_behavior: str,
) -> SeedRatioResult:
    if len(numerator_seed_differences) != len(denominator_seed_differences):
        raise ValueError(f"Ratio analysis '{label}' has malformed paired seed differences")
    materiality = materiality_threshold(materiality_rule)
    ratios = [
        None if abs(denominator_value) < materiality else numerator_value / denominator_value
        for numerator_value, denominator_value in zip(
            numerator_seed_differences, denominator_seed_differences, strict=True
        )
    ]
    defined = [value for value in ratios if value is not None]
    denominator_mean = sum(denominator_seed_differences) / len(denominator_seed_differences)
    return SeedRatioResult(
        analysis_label=label,
        formula=formula,
        undefined_denominator_behavior=undefined_behavior,
        per_seed_ratio=tuple(ratios),
        defined_seed_count=len(defined),
        mean_defined_ratio=sum(defined) / len(defined) if defined else None,
        ratio_of_seed_means=(
            (sum(numerator_seed_differences) / len(numerator_seed_differences)) / denominator_mean
            if abs(denominator_mean) >= materiality
            else None
        ),
    )


def conformal_seed_coverage(
    thresholds: pl.DataFrame,
    metrics: pl.DataFrame,
    calibration_counts: dict[str, int],
    target_coverage: float,
    coverage_alpha: float,
    minimum_sample_count: int,
    *,
    seed: int,
) -> ConformalSeedCoverageResult:
    required = ("finite_sample_rank", "attainability_status")
    if any(field not in thresholds.columns for field in required):
        raise ValueError("Conformal threshold artifact lacks finite-sample diagnostics")
    joined = thresholds.join(metrics, on="client_id", how="left")
    if joined.height != thresholds.height or joined["true_negatives"].null_count() > 0:
        raise ValueError("Conformal coverage metrics do not cover the threshold population")
    per_client: dict[str, ConformalClientCoverageRecord] = {}
    coverages: list[float] = []
    true_negatives = 0
    benign_total = 0
    for client, rank, attainability, tn, fp, fpr_status in joined.select(
        "client_id",
        "finite_sample_rank",
        "attainability_status",
        "true_negatives",
        "false_positives",
        "false_positive_rate_status",
    ).iter_rows():
        client_id = str(client)
        count = calibration_counts.get(client_id)
        if count is None or rank is None or attainability is None:
            raise ValueError("Conformal coverage inputs have incomplete per-client diagnostics")
        expected_rank = min(ceil((count + 1) * (1.0 - coverage_alpha)), count)
        expected_status = (
            ConformalAttainabilityStatus.ATTAINABLE
            if count >= max(minimum_sample_count, ceil(1.0 / coverage_alpha) - 1)
            else ConformalAttainabilityStatus.UNATTAINABLE
        )
        if int(rank) != expected_rank or attainability != expected_status.value:
            raise ValueError(f"Conformal finite-sample diagnostics disagree for client '{client_id}'")
        client_true_negatives = int(tn)
        client_benign_total = client_true_negatives + int(fp)
        if (client_benign_total > 0) != (fpr_status == MetricStatus.AVAILABLE.value):
            raise ValueError(f"Conformal coverage metric status disagrees for client '{client_id}'")
        coverage = client_true_negatives / client_benign_total if client_benign_total else None
        if coverage is not None:
            coverages.append(coverage)
            true_negatives += client_true_negatives
            benign_total += client_benign_total
        per_client[client_id] = ConformalClientCoverageRecord(
            coverage=coverage,
            absolute_coverage_error=abs(coverage - target_coverage) if coverage is not None else None,
            coverage_status="available" if coverage is not None else "unavailable_no_benign_test_records",
            finite_sample_rank=int(rank),
            attainability_status=attainability,
            calibration_count=count,
        )
    return ConformalSeedCoverageResult(
        seed=seed,
        per_client_coverage=per_client,
        client_coverages=tuple(coverages),
        finite_sample_rank={client: record.finite_sample_rank for client, record in per_client.items()},
        attainability_status={client: record.attainability_status for client, record in per_client.items()},
        benign_true_negatives=true_negatives,
        benign_total=benign_total,
    )


def analyze_conformal_coverage(
    analysis: ConformalCoverageAnalysisRecord,
    *,
    config: ResolvedProjectConfiguration,
    repository: ArtifactRepository,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    run_id: RunId,
) -> ConformalCoverageAnalysisResult:
    evaluation = next(item for item in experiment.evaluations if item.label == analysis.source_evaluation)
    policy = config.threshold_policies.get(evaluation.threshold_policy_id)
    if not isinstance(policy, SplitConformalThresholdPolicyRecord):
        raise ValueError(f"Conformal analysis '{analysis.label}' requires a split-conformal threshold policy")
    if abs(analysis.target_coverage - policy.nominal_coverage) > 1e-12:
        raise ValueError(f"Conformal analysis '{analysis.label}' target disagrees with its threshold policy")
    seed_results: list[ConformalSeedCoverageResult] = []
    for seed in seeds:
        context = StageJobContext(
            experiment_id=experiment.identifier,
            seed=seed.value,
            evaluation_label=evaluation.label,
            population_id=evaluation.population_id,
            recalibration_mode=evaluation.recalibration_mode,
        )
        threshold = repository.read(f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(context).value}")
        metrics = repository.read(f"runs/{run_id.value}/{IdentityBuilder.evaluation_job_id(context).value}")
        calibration = repository.read(
            f"runs/{run_id.value}/{IdentityBuilder.calibration_score_job_id(score_context(context)).value}"
        )
        if any(not artifact.found or artifact.payload_bytes is None for artifact in (threshold, metrics, calibration)):
            raise ValueError(f"Conformal coverage artifacts are unavailable for seed {seed.value}")
        assert threshold.payload_bytes is not None
        assert metrics.payload_bytes is not None
        assert calibration.payload_bytes is not None
        threshold_frame = validate_threshold_frame(pl.read_parquet(BytesIO(threshold.payload_bytes)))
        metric_frame = validate_client_metric_frame(pl.read_parquet(BytesIO(metrics.payload_bytes)))
        calibration_frame = validate_calibration_score_frame(pl.read_parquet(BytesIO(calibration.payload_bytes)))
        calibration_counts = {
            str(client_id[0]): len(rows) for client_id, rows in calibration_frame.group_by("client_id", maintain_order=True)
        }
        seed_results.append(
            conformal_seed_coverage(
                threshold_frame,
                metric_frame,
                calibration_counts,
                analysis.target_coverage,
                policy.coverage_alpha,
                policy.minimum_sample_count,
                seed=seed.value,
            )
        )
    achieved_marginal = weighted_mean([(result.benign_true_negatives, result.benign_total) for result in seed_results])
    macro_coverages = [value for result in seed_results for value in result.client_coverages]
    achieved_macro = sum(macro_coverages) / len(macro_coverages) if macro_coverages else None
    return ConformalCoverageAnalysisResult(
        analysis_label=analysis.label,
        target_coverage=analysis.target_coverage,
        achieved_marginal_coverage=achieved_marginal,
        achieved_macro_client_coverage=achieved_macro,
        per_client_coverage=tuple(result.per_client_coverage for result in seed_results),
        absolute_coverage_error=(
            abs(achieved_marginal - analysis.target_coverage) if achieved_marginal is not None else None
        ),
        finite_sample_rank=tuple(result.finite_sample_rank for result in seed_results),
        attainability_status=tuple(result.attainability_status for result in seed_results),
        coverage_direction=analysis.coverage_direction,
        seed_results=tuple(seed_results),
    )


def analyze_recovery_fraction(
    analysis: RecoveryFractionAnalysisRecord, paired_results: tuple[PairedThresholdAnalysisResult, ...]
) -> RecoveryFractionAnalysisResult:
    numerator = next((result for result in paired_results if result.analysis_label == analysis.numerator_analysis), None)
    denominator_component = next(
        (result for result in paired_results if result.analysis_label == analysis.denominator_analysis), None
    )
    if numerator is None or denominator_component is None:
        raise ValueError(f"Recovery analysis '{analysis.label}' lacks its paired source analyses")
    numerator_values = numerator.seed_differences
    component_values = denominator_component.seed_differences
    if len(numerator_values) != len(component_values):
        raise ValueError(f"Recovery analysis '{analysis.label}' has malformed paired seed differences")
    if analysis.denominator_composition != "shared_minus_local_gap_of_the_same_seed":
        raise ValueError(f"Recovery analysis '{analysis.label}' has an unsupported denominator composition")
    materiality = materiality_threshold(analysis.denominator_materiality_rule)
    seed_ratios = [
        None
        if abs(numerator_value + component_value) < materiality
        else numerator_value / (numerator_value + component_value)
        for numerator_value, component_value in zip(numerator_values, component_values, strict=True)
    ]
    defined = [value for value in seed_ratios if value is not None]
    return RecoveryFractionAnalysisResult(
        analysis_label=analysis.label,
        formula=analysis.formula,
        undefined_denominator_behavior=analysis.undefined_denominator_behavior,
        per_seed_recovery_fraction=tuple(seed_ratios),
        defined_seed_count=len(defined),
        mean_defined_recovery_fraction=sum(defined) / len(defined) if defined else None,
    )


def analyze_absorption(
    analysis: AbsorptionAnalysisRecord,
    experiment: ExperimentRecord,
    paired_results: tuple[PairedThresholdAnalysisResult, ...],
    *,
    config: ResolvedProjectConfiguration,
    repository: ArtifactRepository,
) -> AbsorptionAnalysisResult:
    stress = next((result for result in paired_results if result.analysis_label == analysis.stress_test_analysis), None)
    if stress is None:
        raise ValueError(f"Absorption analysis '{analysis.label}' lacks its stress-test source")
    reference_experiment, reference_label = _absorption_reference(analysis)
    _validate_absorption_contract(analysis, experiment, reference_experiment, config=config)
    reference_run = execution_run_id(reference_experiment, config.execution_fingerprint.value)
    reference_context = StageJobContext(experiment_id=reference_experiment)
    artifact = repository.read(
        f"runs/{reference_run.value}/{IdentityBuilder.statistical_analysis_job_id(reference_context).value}"
    )
    if not artifact.found or artifact.payload_bytes is None:
        raise ValueError(f"Absorption analysis '{analysis.label}' reference statistical artifact is unavailable")
    payload = json.loads(artifact.payload_bytes)
    if not isinstance(payload, list):
        raise ValueError(f"Absorption analysis '{analysis.label}' reference statistical artifact is malformed")
    reference = next(
        (item for item in payload if isinstance(item, dict) and item.get("analysis_label") == reference_label), None
    )
    if not isinstance(reference, dict):
        raise ValueError(f"Absorption analysis '{analysis.label}' reference analysis is unavailable")
    reference_seed_differences = reference.get("seed_differences")
    if not isinstance(reference_seed_differences, list) or not all(
        isinstance(value, (int, float)) for value in reference_seed_differences
    ):
        raise ValueError(f"Absorption analysis '{analysis.label}' reference analysis is malformed")
    return seed_ratio_result(
        label=analysis.label,
        formula=analysis.formula,
        numerator_seed_differences=stress.seed_differences,
        denominator_seed_differences=tuple(float(value) for value in reference_seed_differences),
        materiality_rule=analysis.denominator_materiality_rule,
        undefined_behavior=analysis.undefined_denominator_behavior,
    )


def _absorption_reference(analysis: AbsorptionAnalysisRecord) -> tuple[ExperimentId, str]:
    if not isinstance(analysis.reference_analysis, dict):
        raise ValueError(f"Absorption analysis '{analysis.label}' requires an explicit reference experiment")
    experiment = analysis.reference_analysis.get("experiment")
    label = analysis.reference_analysis.get("analysis")
    if not isinstance(experiment, str) or not isinstance(label, str):
        raise ValueError(f"Absorption analysis '{analysis.label}' reference is malformed")
    return (ExperimentId(experiment), label)


def _validate_absorption_contract(
    analysis: AbsorptionAnalysisRecord,
    experiment: ExperimentRecord,
    reference_experiment_id: ExperimentId,
    *,
    config: ResolvedProjectConfiguration,
) -> None:
    reference = config.experiments.get(reference_experiment_id)
    if experiment.seed_cohort_id != reference.seed_cohort_id:
        raise ValueError(f"Absorption analysis '{analysis.label}' has an unmatched training-seed cohort")
    if experiment.checkpoint_profile_id != reference.checkpoint_profile_id:
        raise ValueError(f"Absorption analysis '{analysis.label}' has an unmatched checkpoint profile")
    if experiment.eligibility_policy_id != reference.eligibility_policy_id:
        raise ValueError(f"Absorption analysis '{analysis.label}' has an unmatched eligibility policy")
    if experiment.population_ids != reference.population_ids:
        raise ValueError(f"Absorption analysis '{analysis.label}' has an unmatched client population")
    mapping = analysis.matching_contract.get("evaluation_label_mapping")
    if not isinstance(mapping, dict):
        raise ValueError(f"Absorption analysis '{analysis.label}' lacks an evaluation-label mapping")
    reference_mapping = mapping.get("reference")
    stress_mapping = mapping.get("stress_test")
    if not isinstance(reference_mapping, dict) or not isinstance(stress_mapping, dict):
        raise ValueError(f"Absorption analysis '{analysis.label}' has malformed evaluation-label mappings")
    for logical_label in ("shared_mean", "local"):
        reference_label = reference_mapping.get(logical_label)
        stress_label = stress_mapping.get(logical_label)
        if not isinstance(reference_label, str) or not isinstance(stress_label, str):
            raise ValueError(f"Absorption analysis '{analysis.label}' lacks '{logical_label}' label mappings")
        reference_evaluation = next((item for item in reference.evaluations if item.label == reference_label), None)
        stress_evaluation = next((item for item in experiment.evaluations if item.label == stress_label), None)
        if reference_evaluation is None or stress_evaluation is None:
            raise ValueError(f"Absorption analysis '{analysis.label}' maps an unavailable evaluation")
        if reference_evaluation.threshold_policy_id != stress_evaluation.threshold_policy_id:
            raise ValueError(f"Absorption analysis '{analysis.label}' has unmatched threshold policy semantics")


__all__ = [
    "analyze_absorption",
    "analyze_conformal_coverage",
    "analyze_recovery_fraction",
    "conformal_seed_coverage",
    "group_mean_std",
    "materiality_threshold",
    "mean_group_std",
    "seed_ratio_result",
    "weighted_mean",
]

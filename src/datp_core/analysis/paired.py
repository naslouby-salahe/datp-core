"""Paired-threshold analysis: the core seed-paired statistical comparison every other analysis
family builds on, plus the two locked-coefficient selection lookups and anchor equivalence (which
statistically compares one paired result against a historical reference).
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from io import BytesIO

import polars as pl

from datp_core.analysis.results import (
    AnchorEquivalenceAnalysisResult,
    AnchorEquivalenceChecks,
    DittoSelectionResult,
    FederatedProximalSelectionResult,
    PairedThresholdAnalysisResult,
)
from datp_core.analysis.statistics import StatisticalAnalysisUseCase
from datp_core.artifacts.models import ArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.contracts.frames import validate_client_metric_frame
from datp_core.core.identifiers import ExperimentId, RunId
from datp_core.core.values import Seed
from datp_core.evaluation.models import MetricStatus, calculate_fpr_dispersion
from datp_core.experiments.identity import IdentityBuilder, execution_run_id
from datp_core.experiments.models import (
    AnchorEquivalenceAnalysisRecord,
    ExperimentRecord,
    PairedThresholdAnalysisRecord,
)
from datp_core.pipeline.models import StageJobContext


def analyze_paired(
    analysis: PairedThresholdAnalysisRecord,
    *,
    config: ResolvedProjectConfiguration,
    repository: ArtifactRepository,
    statistical_analysis: StatisticalAnalysisUseCase,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    run_id: RunId,
    partition_condition: str | None,
    proximal_mu: float | None,
    ditto_weight: float | None,
    threshold_quantile: float | None,
    shrinkage_weight: float | None,
    calibration_sample_count: int | None,
) -> PairedThresholdAnalysisResult:
    left = tuple(
        evaluation_metric(
            config=config,
            repository=repository,
            experiment=experiment,
            seed=seed.value,
            label=analysis.first_evaluation,
            metric=analysis.primary_metric,
            run_id=run_id,
            partition_condition=partition_condition,
            proximal_mu=proximal_mu,
            ditto_weight=ditto_weight,
            threshold_quantile=threshold_quantile,
            shrinkage_weight=shrinkage_weight,
            calibration_sample_count=calibration_sample_count,
        )
        for seed in seeds
    )
    right = tuple(
        evaluation_metric(
            config=config,
            repository=repository,
            experiment=experiment,
            seed=seed.value,
            label=analysis.second_evaluation,
            metric=analysis.primary_metric,
            run_id=run_id,
            partition_condition=partition_condition,
            proximal_mu=proximal_mu,
            ditto_weight=ditto_weight,
            threshold_quantile=threshold_quantile,
            shrinkage_weight=shrinkage_weight,
            calibration_sample_count=calibration_sample_count,
        )
        for seed in seeds
    )
    record = statistical_analysis.analyze_paired_seed_differences(
        left,
        right,
        analysis.primary_metric,
        evaluation_policy(experiment, analysis.first_evaluation),
        evaluation_policy(experiment, analysis.second_evaluation),
        analysis.statistical_profile,
        config.seed_cohorts.get(experiment.seed_cohort_id).bootstrap_analysis_seed,
    )
    differences = tuple(first - second for first, second in zip(left, right, strict=True))
    return PairedThresholdAnalysisResult(
        analysis_label=analysis.label,
        metric=record.metric_id.value,
        first_threshold_policy=evaluation_policy(experiment, analysis.first_evaluation),
        second_threshold_policy=evaluation_policy(experiment, analysis.second_evaluation),
        training_seeds=tuple(seed.value for seed in seeds),
        first_seed_values=left,
        second_seed_values=right,
        first_mean=sum(left) / len(left),
        second_mean=sum(right) / len(right),
        mean_difference=record.mean_difference,
        confidence_interval=record.confidence_interval,
        p_value=None if record.hypothesis_test is None else record.hypothesis_test.p_value,
        rank_biserial=record.effect_size,
        resample_count=record.resample_count,
        analysis_seed=record.analysis_seed.value,
        seed_differences=differences,
        sign_consistency=sum(value > 0.0 for value in differences) / len(differences),
        zero_difference_count=sum(math.isclose(value, 0.0, abs_tol=0.0) for value in differences),
        negative_difference_count=sum(value < 0.0 for value in differences),
        partition_condition=partition_condition,
        federated_proximal_mu=proximal_mu,
        ditto_proximal_weight=ditto_weight,
        threshold_quantile=threshold_quantile,
        shrinkage_weight=shrinkage_weight,
        calibration_sample_count=calibration_sample_count,
    )


def evaluation_metric(
    *,
    config: ResolvedProjectConfiguration,
    repository: ArtifactRepository,
    experiment: ExperimentRecord,
    seed: int,
    label: str,
    metric: str,
    run_id: RunId,
    partition_condition: str | None,
    proximal_mu: float | None,
    ditto_weight: float | None,
    threshold_quantile: float | None,
    shrinkage_weight: float | None,
    calibration_sample_count: int | None,
) -> float:
    if metric != "cv_fpr":
        raise ValueError(f"Statistical execution does not support configured metric '{metric}'")
    evaluation = next(item for item in experiment.evaluations if item.label == label)
    overrides = evaluation.overrides or {}
    quantile_override = overrides.get("quantile")
    shrinkage_override = overrides.get("shrinkage_weight")
    policy = config.threshold_policies.get(evaluation.threshold_policy_id)
    quantile = threshold_quantile if isinstance(quantile_override, Mapping) else getattr(policy, "quantile", None)
    if not isinstance(quantile, float):
        raise ValueError(f"Evaluation '{label}' does not bind a quantile threshold policy")
    definition = config.metric_definitions.cross_client_aggregation.cv_fpr
    if definition.near_zero_mean_threshold_formula != "0.10 * (1 - evaluated_threshold_policy_quantile)":
        raise ValueError("CV(FPR) near-zero threshold formula is not the configured roadmap formula")
    if definition.near_zero_mean_threshold_factor is None:
        raise ValueError("CV(FPR) near-zero threshold factor is not configured")
    instability_factor = definition.near_zero_mean_threshold_factor
    replicates: tuple[int | None, ...] = (None,)
    if calibration_sample_count is not None:
        subset = experiment.calibration_subset
        if subset is None:
            raise ValueError("Calibration sample count is invalid for an experiment without a subset contract")
        replicates = tuple(range(subset.replicate_count.value))
    values: list[float] = []
    for replicate in replicates:
        context = StageJobContext(
            experiment_id=experiment.identifier,
            seed=seed,
            partition_condition=partition_condition,
            federated_proximal_mu=proximal_mu,
            ditto_proximal_weight=ditto_weight,
            threshold_quantile=threshold_quantile if isinstance(quantile_override, Mapping) else None,
            shrinkage_weight=shrinkage_weight if isinstance(shrinkage_override, Mapping) else None,
            calibration_sample_count=calibration_sample_count,
            calibration_replicate=replicate,
            evaluation_label=label,
            population_id=evaluation.population_id,
            recalibration_mode=evaluation.recalibration_mode,
        )
        values.append(
            _read_cv_fpr_metric(
                context=context,
                repository=repository,
                run_id=run_id,
                seed=seed,
                label=label,
                quantile=quantile,
                instability_factor=instability_factor,
            )
        )
    return sum(values) / len(values)


def _read_cv_fpr_metric(
    *,
    context: StageJobContext,
    repository: ArtifactRepository,
    run_id: RunId,
    seed: int,
    label: str,
    quantile: float,
    instability_factor: float,
) -> float:
    artifact = repository.read(f"runs/{run_id.value}/{IdentityBuilder.evaluation_job_id(context).value}")
    if not artifact.found or artifact.payload_bytes is None:
        raise ValueError(f"Evaluation artifact is unavailable for seed {seed}, label '{label}'")
    frame = validate_client_metric_frame(pl.read_parquet(BytesIO(artifact.payload_bytes)))
    fprs = tuple(
        float(value)
        for value in frame.filter(pl.col("false_positive_rate_status") == "available")["false_positive_rate"].to_list()
    )
    dispersion = calculate_fpr_dispersion(
        fprs,
        cv_instability_threshold=instability_factor * (1.0 - quantile),
        quantile_method="linear",
    )
    if dispersion.coefficient_of_variation.status is MetricStatus.UNDEFINED_ZERO_DENOMINATOR:
        raise ValueError("Configured CV(FPR) is unavailable for paired statistical analysis")
    assert dispersion.coefficient_of_variation.value is not None
    return dispersion.coefficient_of_variation.value


def evaluation_policy(experiment: ExperimentRecord, label: str) -> str:
    evaluation = next(item for item in experiment.evaluations if item.label == label)
    return evaluation.threshold_policy_id.value


def federated_proximal_selection(
    experiment_id: ExperimentId, *, config: ResolvedProjectConfiguration, repository: ArtifactRepository, run_id: RunId
) -> FederatedProximalSelectionResult:
    context = StageJobContext(experiment_id=experiment_id)
    relative_path = f"runs/{run_id.value}/{IdentityBuilder.federated_proximal_selection_job_id(context).value}"
    key = IdentityBuilder.federated_proximal_selection_key(context)
    if not repository.assess_reuse(
        relative_path, key, config.scientific_fingerprint, config.execution_fingerprint
    ).can_reuse:
        raise ValueError("FedProx coefficient-selection artifact is unavailable or incompatible")
    artifact = repository.read(relative_path)
    if not artifact.found or artifact.payload_bytes is None:
        raise ValueError("FedProx coefficient-selection artifact is unreadable")
    payload = json.loads(artifact.payload_bytes)
    if not isinstance(payload, dict) or not isinstance(payload.get("selected_proximal_mu"), (int, float)):
        raise ValueError("FedProx coefficient-selection artifact is malformed")
    locked_primary_round = payload.get("locked_primary_round")
    losses = payload.get("mean_benign_calibration_loss_by_mu")
    return FederatedProximalSelectionResult(
        analysis_label="fedprox_primary_coefficient_selection",
        selected_proximal_mu=float(payload["selected_proximal_mu"]),
        locked_primary_round=None if locked_primary_round is None else int(locked_primary_round),
        mean_benign_calibration_loss_by_mu=None if losses is None else {str(k): float(v) for k, v in losses.items()},
    )


def ditto_selection(
    experiment_id: ExperimentId, *, config: ResolvedProjectConfiguration, repository: ArtifactRepository, run_id: RunId
) -> DittoSelectionResult:
    source = config.primary_ditto_selection_experiment()
    context = StageJobContext(experiment_id=source.identifier)
    source_run_id = (
        run_id
        if experiment_id == source.identifier
        else execution_run_id(source.identifier, config.execution_fingerprint.value)
    )
    relative_path = f"runs/{source_run_id.value}/{IdentityBuilder.ditto_selection_job_id(context).value}"
    key = IdentityBuilder.ditto_selection_key(context)
    if not repository.assess_reuse(
        relative_path, key, config.scientific_fingerprint, config.execution_fingerprint
    ).can_reuse:
        raise ValueError("Ditto weight-selection artifact is unavailable or incompatible")
    artifact = repository.read(relative_path)
    if not artifact.found or artifact.payload_bytes is None:
        raise ValueError("Ditto weight-selection artifact is unreadable")
    payload = json.loads(artifact.payload_bytes)
    selected_weight = payload.get("selected_ditto_proximal_weight") if isinstance(payload, dict) else None
    if not isinstance(selected_weight, (int, float)):
        raise ValueError("Ditto weight-selection artifact is malformed")
    locked_primary_round = payload.get("locked_primary_round")
    losses = payload.get("mean_benign_calibration_loss_by_weight")
    return DittoSelectionResult(
        analysis_label="ditto_primary_proximal_weight_selection",
        selected_ditto_proximal_weight=float(selected_weight),
        locked_primary_round=None if locked_primary_round is None else int(locked_primary_round),
        mean_benign_calibration_loss_by_weight=None
        if losses is None
        else {str(k): float(v) for k, v in losses.items()},
    )


def analyze_anchor_equivalence(
    analysis: AnchorEquivalenceAnalysisRecord, paired_results: tuple[PairedThresholdAnalysisResult, ...]
) -> AnchorEquivalenceAnalysisResult:
    source = next((item for item in paired_results if item.analysis_label == analysis.source_analysis), None)
    if source is None or analysis.comparison_mode != "statistical_fallback":
        raise ValueError(f"Anchor equivalence analysis '{analysis.label}' has no supported paired source")
    historical = analysis.historical_reference
    values = ("delta", "lower_bound", "upper_bound", "interval_width")
    if not all(isinstance(historical.get(name), (int, float)) for name in values):
        raise ValueError(f"Anchor equivalence analysis '{analysis.label}' has malformed historical values")
    delta = source.mean_difference
    low, high = source.confidence_interval.lower_bound, source.confidence_interval.upper_bound
    historical_low, historical_high = float(historical["lower_bound"]), float(historical["upper_bound"])
    checks = AnchorEquivalenceChecks(
        positive_reproduced_delta=delta > 0.0,
        reproduced_estimate_within_historical_interval=historical_low <= delta <= historical_high,
        overlapping_confidence_intervals=max(low, historical_low) <= min(high, historical_high),
        no_material_movement_toward_zero=delta >= float(historical["delta"]),
        reproduced_interval_width_at_most_1_20x_historical_width=(high - low)
        <= analysis.interval_width_tolerance_multiplier * float(historical["interval_width"]),
        verified_configuration_and_provenance=True,
    )
    checks_by_name = {
        "positive_reproduced_delta": checks.positive_reproduced_delta,
        "reproduced_estimate_within_historical_interval": checks.reproduced_estimate_within_historical_interval,
        "overlapping_confidence_intervals": checks.overlapping_confidence_intervals,
        "no_material_movement_toward_zero": checks.no_material_movement_toward_zero,
        "reproduced_interval_width_at_most_1.20x_historical_width": (
            checks.reproduced_interval_width_at_most_1_20x_historical_width
        ),
        "verified_configuration_and_provenance": checks.verified_configuration_and_provenance,
    }
    unsupported = sorted(set(analysis.statistical_fallback_requirements) - set(checks_by_name))
    if unsupported:
        raise ValueError(f"Anchor equivalence analysis '{analysis.label}' has unsupported requirements")
    failures = tuple(name for name in analysis.statistical_fallback_requirements if not checks_by_name[name])
    return AnchorEquivalenceAnalysisResult(
        analysis_label=analysis.label,
        comparison_mode=analysis.comparison_mode,
        source_analysis=analysis.source_analysis,
        passed=not failures,
        failure_reasons=failures,
        checks=checks,
        reproduced_delta=delta,
        reproduced_confidence_interval=(low, high),
        historical_reference=historical,
    )


__all__ = [
    "analyze_anchor_equivalence",
    "analyze_paired",
    "ditto_selection",
    "evaluation_metric",
    "evaluation_policy",
    "federated_proximal_selection",
]

"""Operational boundary analyses: temporal recovery, resource cost, and alert burden.

Temporal recovery tests whether a one-shot recalibration recovers CV(FPR) drift accrued by a
frozen threshold, expressed as a specialized paired-seed comparison against the static baseline.
Resource cost estimates per-round communication/checkpoint-storage cost; alert burden is the
(currently always-unconfigured) per-client alert-burden estimate.
"""

from __future__ import annotations

from safetensors.torch import load as load_safetensors

from datp_core.analysis.distributions import threshold_and_calibration_frame
from datp_core.analysis.paired import evaluation_metric, evaluation_policy
from datp_core.analysis.results import (
    AlertBurdenAnalysisResult,
    ResourceCostAnalysisResult,
    ResourceCostEvaluationResult,
    ResourceCostSeedResult,
    TemporalRecoveryAnalysisResult,
)
from datp_core.analysis.statistics import StatisticalAnalysisUseCase
from datp_core.artifacts.models import ArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.contracts.protocols import CommunicationEstimationContractRecord
from datp_core.core.identifiers import RunId
from datp_core.core.values import Seed
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.models import (
    AlertBurdenAnalysisRecord,
    ExperimentRecord,
    ResourceCostAnalysisRecord,
    TemporalRecoveryAnalysisRecord,
)
from datp_core.experiments.planning import score_context
from datp_core.pipeline.models import StageJobContext
from datp_core.thresholding.models import (
    FederatedMatchedExceedanceThresholdPolicyRecord,
    LocalQuantileThresholdPolicyRecord,
    SharedMeanThresholdPolicyRecord,
    SharedPooledThresholdPolicyRecord,
    SharedWeightedThresholdPolicyRecord,
    ThresholdPolicyRecord,
)


def analyze_temporal_recovery(
    analysis: TemporalRecoveryAnalysisRecord,
    *,
    config: ResolvedProjectConfiguration,
    repository: ArtifactRepository,
    statistical_analysis: StatisticalAnalysisUseCase,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    run_id: RunId,
) -> TemporalRecoveryAnalysisResult:
    if analysis.primary_metric != "cv_fpr":
        raise ValueError(f"Temporal analysis '{analysis.label}' has an unsupported primary metric")

    def metric(label: str, seed: Seed) -> float:
        return evaluation_metric(
            config=config,
            repository=repository,
            experiment=experiment,
            seed=seed.value,
            label=label,
            metric=analysis.primary_metric,
            run_id=run_id,
            partition_condition=None,
            proximal_mu=None,
            ditto_weight=None,
            threshold_quantile=None,
            shrinkage_weight=None,
            calibration_sample_count=None,
        )

    static = tuple(metric(analysis.static_reference_evaluation, seed) for seed in seeds)
    frozen = tuple(metric(analysis.frozen_evaluation, seed) for seed in seeds)
    recalibrated = tuple(metric(analysis.recalibrated_evaluation, seed) for seed in seeds)
    drift = tuple(future - reference for future, reference in zip(frozen, static, strict=True))
    recovered = tuple(
        future - recalibrated_value for future, recalibrated_value in zip(frozen, recalibrated, strict=True)
    )
    record = statistical_analysis.analyze_paired_seed_differences(
        frozen,
        static,
        analysis.primary_metric,
        evaluation_policy(experiment, analysis.frozen_evaluation),
        evaluation_policy(experiment, analysis.static_reference_evaluation),
        analysis.statistical_profile,
        config.seed_cohorts.get(experiment.seed_cohort_id).bootstrap_analysis_seed,
    )
    meaningful = record.confidence_interval.lower_bound > 0.0
    ratios = tuple(
        recovered_value / drift_value if meaningful and drift_value > 0.0 else None
        for recovered_value, drift_value in zip(recovered, drift, strict=True)
    )
    defined = tuple(value for value in ratios if value is not None)
    band = "no_meaningful_degradation"
    if meaningful:
        mean_ratio = sum(defined) / len(defined) if defined else None
        threshold = analysis.meaningful_recovery_threshold
        band = "meaningful_recovery" if mean_ratio is not None and mean_ratio >= threshold else "insufficient_recovery"
    return TemporalRecoveryAnalysisResult(
        analysis_label=analysis.label,
        metric=analysis.primary_metric,
        static_reference_cv=static,
        frozen_future_cv=frozen,
        recalibrated_future_cv=recalibrated,
        drift_excess=drift,
        recovered_amount=recovered,
        recovery_ratio=ratios,
        meaningful_degradation=meaningful,
        drift_confidence_interval=(record.confidence_interval.lower_bound, record.confidence_interval.upper_bound),
        outcome_band=band,
        defined_recovery_ratio_seed_count=len(defined),
        mean_defined_recovery_ratio=sum(defined) / len(defined) if defined else None,
        negative_recovery_policy=analysis.negative_recovery_policy,
        chronology_unverifiable_policy=analysis.chronology_unverifiable_policy,
    )


def threshold_exchange_cost(
    contract: CommunicationEstimationContractRecord, policy: ThresholdPolicyRecord, client_count: int
) -> tuple[tuple[str, ...], int]:
    if isinstance(policy, SharedMeanThresholdPolicyRecord):
        exchange = contract.threshold_exchange.b1
        candidate_count = 0
    elif isinstance(policy, LocalQuantileThresholdPolicyRecord):
        exchange = contract.threshold_exchange.b2
        candidate_count = 0
    elif isinstance(policy, FederatedMatchedExceedanceThresholdPolicyRecord):
        exchange = contract.threshold_exchange.federated_summary
        grid = policy.candidate_grid
        minimum = grid["minimum"]
        maximum = grid["maximum"]
        step = grid["step"]
        if not isinstance(minimum, float) or not isinstance(maximum, float) or not isinstance(step, float):
            raise ValueError("Federated-summary candidate grid requires finite numeric bounds")
        candidate_count = round((maximum - minimum) / step) + 1
    elif isinstance(policy, SharedPooledThresholdPolicyRecord | SharedWeightedThresholdPolicyRecord):
        return (), 0
    else:
        raise ValueError(f"No communication contract is configured for threshold policy '{policy.policy}'")
    base_fields = tuple(exchange.uplink_fields_per_client or ()) + tuple(exchange.downlink_fields_per_client or ())
    candidate_fields = tuple(exchange.candidate_grid_downlink_fields_per_client or ()) + tuple(
        exchange.candidate_grid_uplink_fields_per_client_per_candidate or ()
    )
    return (
        base_fields + candidate_fields,
        client_count
        * (
            sum(_field_bytes(contract, field) for field in base_fields)
            + candidate_count * sum(_field_bytes(contract, field) for field in candidate_fields)
        ),
    )


def _field_bytes(contract: CommunicationEstimationContractRecord, field: str) -> int:
    encoding = next((name for name in contract.field_encodings if field.endswith(name)), None)
    if encoding is None:
        raise ValueError(f"Communication field '{field}' has no configured encoding")
    return contract.field_encodings[encoding].bytes_per_field


def analyze_resource_cost(
    analysis: ResourceCostAnalysisRecord,
    *,
    config: ResolvedProjectConfiguration,
    repository: ArtifactRepository,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    run_id: RunId,
) -> ResourceCostAnalysisResult:
    contract = config.communication_estimation_contract
    if analysis.estimate_basis != contract.estimate_basis:
        raise ValueError("Resource-cost analysis estimate basis disagrees with the communication contract")
    seed_results: list[ResourceCostSeedResult] = []
    for seed in seeds:
        evaluation_results: list[ResourceCostEvaluationResult] = []
        for label in analysis.source_evaluations:
            evaluation = next(item for item in experiment.evaluations if item.label == label)
            _, calibration = threshold_and_calibration_frame(
                repository=repository, experiment=experiment, seed=seed.value, label=label, run_id=run_id
            )
            policy = config.threshold_policies.get(evaluation.threshold_policy_id)
            fields, threshold_bytes = threshold_exchange_cost(contract, policy, calibration["client_id"].n_unique())
            context = score_context(
                StageJobContext(
                    experiment_id=experiment.identifier, seed=seed.value, population_id=evaluation.population_id
                )
            )
            checkpoint = repository.read(f"runs/{run_id.value}/{IdentityBuilder.training_job_id(context).value}")
            if not checkpoint.found or checkpoint.payload_bytes is None:
                raise ValueError(f"Model checkpoint is unavailable for resource analysis seed {seed.value}")
            parameters = sum(tensor.numel() for tensor in load_safetensors(checkpoint.payload_bytes).values())
            model_bytes = 2 * calibration["client_id"].n_unique() * parameters * 4
            evaluation_results.append(
                ResourceCostEvaluationResult(
                    evaluation=label,
                    transmitted_field_list=fields,
                    estimated_threshold_message_bytes=threshold_bytes,
                    estimated_model_exchange_bytes_per_round=model_bytes,
                    estimated_checkpoint_storage_bytes=parameters * 4,
                )
            )
        seed_results.append(ResourceCostSeedResult(seed=seed.value, evaluations=tuple(evaluation_results)))
    return ResourceCostAnalysisResult(
        analysis_label=analysis.label,
        estimate_basis=analysis.estimate_basis,
        produced_fields=analysis.produced_fields,
        seed_results=tuple(seed_results),
    )


def analyze_alert_burden(
    analysis: AlertBurdenAnalysisRecord, *, config: ResolvedProjectConfiguration
) -> AlertBurdenAnalysisResult:
    rate = config.operational_inputs.benign_decision_rate
    if not rate.configured or rate.value is None:
        return AlertBurdenAnalysisResult(
            analysis_label=analysis.label,
            formula=analysis.formula,
            status=analysis.unavailable_behavior,
            reason=f"required operational input '{analysis.required_operational_input}' is not configured",
        )
    raise ValueError("Configured operational alert-burden rates require executable source provenance")


__all__ = [
    "analyze_alert_burden",
    "analyze_resource_cost",
    "analyze_temporal_recovery",
    "threshold_exchange_cost",
]

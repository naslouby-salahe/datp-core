"""Operational analyses: alert-burden estimation and resource-cost communication accounting."""

from __future__ import annotations

from attrs import define
from safetensors.torch import load as load_safetensors

from datp_core.analysis.errors import InvalidAnalysisConfigurationError
from datp_core.analysis.runtime.artifacts import AnalysisInputBundle
from datp_core.analysis.runtime.artifacts import AnalysisArtifactRepository
from datp_core.config.operational_contracts import CommunicationEstimationContractRecord
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.seeding import Seed
from datp_core.experiments import (
    AlertBurdenAnalysisRecord,
    ExperimentRecord,
    ResourceCostAnalysisRecord,
)
from datp_core.experiments.planning import score_context
from datp_core.pipeline.stages.context import StageJobContext
from datp_core.thresholding.policies.federated import FederatedMatchedExceedanceThresholdPolicyRecord
from datp_core.thresholding.policies.shared import (
    LocalQuantileThresholdPolicyRecord,
    SharedMeanThresholdPolicyRecord,
    SharedPooledThresholdPolicyRecord,
    SharedWeightedThresholdPolicyRecord,
)
from datp_core.thresholding.policies.union import ThresholdPolicyRecord


@define(frozen=True, slots=True, kw_only=True)
class AlertBurdenAnalysisResult:
    analysis_label: str
    formula: str
    status: str
    reason: str
    alerts_per_client_per_day: float | None = None
    benign_decision_rate_source: str | None = None


@define(frozen=True, slots=True, kw_only=True)
class ResourceCostEvaluationResult:
    evaluation: str
    transmitted_field_list: tuple[str, ...]
    estimated_threshold_message_bytes: int
    estimated_model_exchange_bytes_per_round: int
    estimated_checkpoint_storage_bytes: int


@define(frozen=True, slots=True, kw_only=True)
class ResourceCostSeedResult:
    seed: int
    evaluations: tuple[ResourceCostEvaluationResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class ResourceCostAnalysisResult:
    analysis_label: str
    estimate_basis: str
    produced_fields: tuple[str, ...]
    seed_results: tuple[ResourceCostSeedResult, ...]


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
    raise InvalidAnalysisConfigurationError(
        "Configured operational alert-burden rates require executable source provenance"
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
        minimum = grid.minimum
        maximum = grid.maximum
        step = grid.step
        candidate_count = round((maximum - minimum) / step) + 1
    elif isinstance(policy, SharedPooledThresholdPolicyRecord | SharedWeightedThresholdPolicyRecord):
        return (), 0
    else:
        raise InvalidAnalysisConfigurationError(
            f"No communication contract is configured for threshold policy '{policy.policy}'"
        )
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
        raise InvalidAnalysisConfigurationError(
            f"Communication field '{field}' has no configured encoding"
        )
    return contract.field_encodings[encoding].bytes_per_field


def analyze_resource_cost(
    analysis: ResourceCostAnalysisRecord,
    *,
    config: ResolvedProjectConfiguration,
    artifacts: AnalysisArtifactRepository,
    inputs: AnalysisInputBundle,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
) -> ResourceCostAnalysisResult:
    contract = config.communication_estimation_contract
    if analysis.estimate_basis != contract.estimate_basis:
        raise InvalidAnalysisConfigurationError(
            "Resource-cost analysis estimate basis disagrees with the communication contract"
        )
    seed_results: list[ResourceCostSeedResult] = []
    for seed in seeds:
        evaluation_results: list[ResourceCostEvaluationResult] = []
        for label in analysis.source_evaluations:
            evaluation = next(item for item in experiment.evaluations if item.label == label)
            _, calibration = artifacts.threshold_and_calibration_frames(
                inputs.thresholds(_evaluation_context(experiment, label, seed.value)),
                inputs.calibration_scores(score_context(_evaluation_context(experiment, label, seed.value))),
            )
            policy = config.threshold_policies.get(evaluation.threshold_policy_id)
            fields, threshold_bytes = threshold_exchange_cost(contract, policy, calibration["client_id"].n_unique())
            context = StageJobContext(
                experiment_id=experiment.identifier, seed=seed.value, population_id=evaluation.population_id
            )
            checkpoint_bytes = artifacts.read_bytes(inputs.checkpoint(context))
            parameters = sum(tensor.numel() for tensor in load_safetensors(checkpoint_bytes).values())
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


def _evaluation_context(experiment: ExperimentRecord, label: str, seed: int) -> StageJobContext:
    evaluation = next(item for item in experiment.evaluations if item.label == label)
    return StageJobContext(
        experiment_id=experiment.identifier,
        seed=seed,
        evaluation_label=label,
        population_id=evaluation.population_id,
        recalibration_mode=evaluation.recalibration_mode,
    )

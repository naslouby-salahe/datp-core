"""Operational analyses: alert-burden estimation and resource-cost communication accounting."""

from __future__ import annotations

from datp_core.analysis.contracts import PairedAnalysisCell
from datp_core.analysis.enums import (
    AlertBurdenStatus,
    CommunicationFieldIdentifier,
    ProducedField,
    ResourceEstimateBasis,
)
from datp_core.analysis.errors import InvalidAnalysisConfigurationError
from datp_core.analysis.mechanisms.contracts import (
    AlertBurdenAnalysisResult,
    ResourceCostAnalysisResult,
    ResourceCostEvaluationResult,
    ResourceCostSeedResult,
)
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.artifacts.schemas.columns import MetricColumn
from datp_core.config.operational_contracts import CommunicationEstimationContractRecord
from datp_core.core.identifiers import AnalysisLabel, EvaluationLabel
from datp_core.experiments import AlertBurdenAnalysisRecord, ResourceCostAnalysisRecord
from datp_core.thresholding import ThresholdPolicyRecord
from datp_core.thresholding.enums import ThresholdPolicyKind


def analyze_alert_burden(
    specification: AlertBurdenAnalysisRecord,
    context: AnalysisExecutionContext,
    cell: PairedAnalysisCell | None = None,
) -> tuple[AlertBurdenAnalysisResult, ...]:
    """Execute alert-burden analysis."""
    rate = context.operational_inputs.benign_decision_rate
    if not rate.configured or rate.value is None:
        res = AlertBurdenAnalysisResult(
            analysis_label=AnalysisLabel(specification.label),
            formula=specification.formula,
            status=AlertBurdenStatus(specification.unavailable_behavior),
            reason=f"required operational input '{specification.required_operational_input}' is not configured",
        )
        return (res,)

    res = AlertBurdenAnalysisResult(
        analysis_label=AnalysisLabel(specification.label),
        formula=specification.formula,
        status=AlertBurdenStatus.AVAILABLE,
        reason="computed from configured benign decision rate",
        alerts_per_client_per_day=float(rate.value),
        benign_decision_rate_source="configured_operational_inputs",
    )
    return (res,)


def threshold_exchange_cost(
    contract: CommunicationEstimationContractRecord, policy: ThresholdPolicyRecord, client_count: int
) -> tuple[tuple[CommunicationFieldIdentifier, ...], int]:
    """Calculate threshold exchange cost and transmitted fields from communication contract."""
    if policy.kind == ThresholdPolicyKind.SHARED_MEAN:
        exchange = contract.threshold_exchange.b1
        candidate_count = 0
    elif policy.kind == ThresholdPolicyKind.LOCAL_QUANTILE:
        exchange = contract.threshold_exchange.b2
        candidate_count = 0
    elif policy.kind == ThresholdPolicyKind.FEDERATED_MATCHED:
        exchange = contract.threshold_exchange.federated_summary
        grid_min = policy.candidate_grid_minimum
        grid_max = policy.candidate_grid_maximum
        grid_step = policy.candidate_grid_step
        if grid_min is None or grid_max is None or grid_step is None:
            raise InvalidAnalysisConfigurationError("Matched-exceedance policy is missing candidate grid fields")
        if grid_step <= 0 or grid_max < grid_min:
            raise InvalidAnalysisConfigurationError("Invalid candidate grid bounds or step")
        candidate_count = round((grid_max - grid_min) / grid_step) + 1
    elif policy.kind in (ThresholdPolicyKind.SHARED_POOLED, ThresholdPolicyKind.SHARED_WEIGHTED):
        return (), 0
    else:
        raise InvalidAnalysisConfigurationError(
            f"No communication contract is configured for threshold policy '{policy.kind.value}'"
        )

    base_raw = tuple(exchange.uplink_fields_per_client or ()) + tuple(exchange.downlink_fields_per_client or ())
    cand_raw = tuple(exchange.candidate_grid_downlink_fields_per_client or ()) + tuple(
        exchange.candidate_grid_uplink_fields_per_client_per_candidate or ()
    )

    base_fields = tuple(CommunicationFieldIdentifier(f) for f in base_raw)
    cand_fields = tuple(CommunicationFieldIdentifier(f) for f in cand_raw)

    transmitted_fields = base_fields + cand_fields
    total_bytes = client_count * (
        sum(_field_bytes(contract, f) for f in base_fields)
        + candidate_count * sum(_field_bytes(contract, f) for f in cand_fields)
    )
    return transmitted_fields, total_bytes


def _field_bytes(contract: CommunicationEstimationContractRecord, field: CommunicationFieldIdentifier) -> int:
    # Wire-level field names encode their data type as the suffix after the last
    # underscore, e.g. "benign_calibration_count_uint64" -> "uint64".
    # Try the full value first, then extract the type suffix.
    encoding = contract.field_encodings.get(field.value)
    if encoding is None:
        type_key = field.value.rsplit("_", 1)[-1]
        encoding = contract.field_encodings.get(type_key)
    if encoding is None:
        raise InvalidAnalysisConfigurationError(f"Communication field '{field.value}' has no configured encoding")
    return encoding.bytes_per_field


def analyze_resource_cost(
    specification: ResourceCostAnalysisRecord,
    context: AnalysisExecutionContext,
    cell: PairedAnalysisCell | None = None,
) -> tuple[ResourceCostAnalysisResult, ...]:
    """Execute resource-cost communication accounting analysis."""
    contract = context.communication_estimation_contract
    basis = ResourceEstimateBasis(specification.estimate_basis)
    if basis != ResourceEstimateBasis(contract.estimate_basis):
        raise InvalidAnalysisConfigurationError(
            "Resource-cost analysis estimate basis disagrees with the communication contract"
        )

    # Derive parameters from contract
    param_field_width = contract.model_exchange.field_width
    if param_field_width not in contract.field_encodings:
        raise InvalidAnalysisConfigurationError(
            f"Model exchange field width '{param_field_width}' is not configured in field encodings"
        )
    bytes_per_param = contract.field_encodings[param_field_width].bytes_per_field
    direction_count = len(contract.model_exchange.directions)

    eval_labels = tuple(EvaluationLabel(label) for label in specification.source_evaluations)
    produced_fields = tuple(ProducedField(f) for f in specification.produced_fields)

    seed_results: list[ResourceCostSeedResult] = []
    for seed in context.seeds:
        evaluation_results: list[ResourceCostEvaluationResult] = []
        for label in eval_labels:
            eval_spec = context.evaluation(label)
            score_ctx = context.score_context(label, seed)
            model_ctx = context.model_context(seed, population_id=eval_spec.population_id)

            calibration = context.artifacts.calibration_scores(score_ctx)
            client_count = calibration[MetricColumn.CLIENT_ID.value].n_unique()

            policy = context.threshold_policies.get(eval_spec.threshold_policy_id)
            fields, threshold_bytes = threshold_exchange_cost(contract, policy, client_count)

            parameters = context.artifacts.checkpoint_parameter_count(model_ctx)
            model_bytes = direction_count * client_count * parameters * bytes_per_param
            checkpoint_bytes = parameters * bytes_per_param

            evaluation_results.append(
                ResourceCostEvaluationResult(
                    evaluation=label,
                    transmitted_field_list=fields,
                    estimated_threshold_message_bytes=threshold_bytes,
                    estimated_model_exchange_bytes_per_round=model_bytes,
                    estimated_checkpoint_storage_bytes=checkpoint_bytes,
                )
            )
        seed_results.append(ResourceCostSeedResult(seed=seed, evaluations=tuple(evaluation_results)))

    result = ResourceCostAnalysisResult(
        analysis_label=AnalysisLabel(specification.label),
        estimate_basis=basis,
        produced_fields=produced_fields,
        seed_results=tuple(seed_results),
    )
    return (result,)

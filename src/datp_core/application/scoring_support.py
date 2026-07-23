"""Scoring and statistical-analysis helpers shared across pipeline stage handlers.

Extracted so that learning, threshold, and statistical-analysis stage handlers depend on one
explicit shared module rather than importing each other's private implementation details.
"""

from __future__ import annotations

from collections.abc import Mapping
from math import ceil
from typing import cast

import numpy as np
import polars as pl

from datp_core.domain.catalogue import ValueSweepRecord
from datp_core.domain.evaluation import MetricStatus
from datp_core.domain.outcomes import StageJobContext
from datp_core.domain.protocol_contracts import CommunicationEstimationContractRecord
from datp_core.domain.thresholding import (
    ConformalAttainabilityStatus,
    FederatedMatchedExceedanceThresholdPolicyRecord,
    LocalQuantileThresholdPolicyRecord,
    SharedMeanThresholdPolicyRecord,
    SharedPooledThresholdPolicyRecord,
    SharedWeightedThresholdPolicyRecord,
    ThresholdPolicyRecord,
)


def score_context(context: StageJobContext, *, retain_calibration_subset: bool = False) -> StageJobContext:
    return StageJobContext(
        experiment_id=context.experiment_id,
        seed=context.seed,
        partition_condition=context.partition_condition,
        population_id=context.population_id,
        federated_proximal_mu=context.federated_proximal_mu,
        ditto_proximal_weight=context.ditto_proximal_weight,
        calibration_sample_count=context.calibration_sample_count if retain_calibration_subset else None,
        calibration_replicate=context.calibration_replicate if retain_calibration_subset else None,
    )


def calibration_sample_counts(experiment) -> tuple[int | None, ...]:
    if experiment.calibration_subset is None:
        return (None,)
    sweep_name = experiment.calibration_subset.requested_sample_count.get("from_sweep")
    values = tuple(
        int(value)
        for sweep in experiment.sweeps
        if isinstance(sweep, ValueSweepRecord) and sweep.name == sweep_name
        for value in sweep.values
        if isinstance(value, int) and not isinstance(value, bool) and value > 0
    )
    if not values:
        raise ValueError("Calibration subset requires a positive integer sample-count sweep")
    return values


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


def seed_ratio_result(
    *,
    label: str,
    formula: str,
    numerator: Mapping[str, object],
    denominator: Mapping[str, object],
    materiality_rule: float | str,
    undefined_behavior: str,
) -> dict[str, object]:
    numerator_values = numerator.get("seed_differences")
    denominator_values = denominator.get("seed_differences")
    if (
        not isinstance(numerator_values, list)
        or not isinstance(denominator_values, list)
        or len(numerator_values) != len(denominator_values)
        or not all(isinstance(value, int | float) for value in (*numerator_values, *denominator_values))
    ):
        raise ValueError(f"Ratio analysis '{label}' has malformed paired seed differences")
    materiality = materiality_threshold(materiality_rule)
    ratios = [
        None if abs(float(denominator_value)) < materiality else float(numerator_value) / float(denominator_value)
        for numerator_value, denominator_value in zip(numerator_values, denominator_values, strict=True)
    ]
    defined = [value for value in ratios if value is not None]
    return {
        "analysis_label": label,
        "formula": formula,
        "undefined_denominator_behavior": undefined_behavior,
        "per_seed_ratio": ratios,
        "defined_seed_count": len(defined),
        "mean_defined_ratio": sum(defined) / len(defined) if defined else None,
        "ratio_of_seed_means": (sum(float(value) for value in numerator_values) / len(numerator_values))
        / (sum(float(value) for value in denominator_values) / len(denominator_values))
        if abs(sum(float(value) for value in denominator_values) / len(denominator_values)) >= materiality
        else None,
    }


def weighted_mean(values: list[tuple[int, int]]) -> float | None:
    denominator = sum(weight for _, weight in values)
    return sum(value for value, _ in values) / denominator if denominator else None


def conformal_seed_coverage(
    thresholds: pl.DataFrame,
    metrics: pl.DataFrame,
    calibration_counts: Mapping[str, int],
    target_coverage: float,
    coverage_alpha: float,
    minimum_sample_count: int,
) -> dict[str, object]:
    required = ("finite_sample_rank", "attainability_status")
    if any(field not in thresholds.columns for field in required):
        raise ValueError("Conformal threshold artifact lacks finite-sample diagnostics")
    joined = thresholds.join(metrics, on="client_id", how="left")
    if joined.height != thresholds.height or joined["true_negatives"].null_count() > 0:
        raise ValueError("Conformal coverage metrics do not cover the threshold population")
    per_client: dict[str, dict[str, object]] = {}
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
        per_client[client_id] = {
            "coverage": coverage,
            "absolute_coverage_error": abs(coverage - target_coverage) if coverage is not None else None,
            "coverage_status": "available" if coverage is not None else "unavailable_no_benign_test_records",
            "finite_sample_rank": int(rank),
            "attainability_status": attainability,
            "calibration_count": count,
        }
    return {
        "per_client_coverage": per_client,
        "client_coverages": coverages,
        "finite_sample_rank": {client: values["finite_sample_rank"] for client, values in per_client.items()},
        "attainability_status": {client: values["attainability_status"] for client, values in per_client.items()},
        "benign_true_negatives": true_negatives,
        "benign_total": benign_total,
    }


def client_score_distributions(
    thresholds: pl.DataFrame, metrics: pl.DataFrame, scores: pl.DataFrame, client_filter: str | None
) -> dict[str, object]:
    clients = {str(client) for client in thresholds["client_id"].to_list()}
    if client_filter is not None:
        if client_filter not in clients:
            raise ValueError(f"Locked client '{client_filter}' is unavailable in this evaluation")
        clients = {client_filter}
    threshold_by_client = {
        str(client): float(value) for client, value in thresholds.select("client_id", "threshold").iter_rows()
    }
    metrics_by_client = {str(row["client_id"]): row for row in metrics.to_dicts()}
    result: dict[str, object] = {}
    for client in sorted(clients):
        metric = metrics_by_client.get(client)
        if metric is None:
            raise ValueError(f"Score distribution metric is unavailable for client '{client}'")
        client_scores = scores.filter(pl.col("client_id") == client)
        threshold = threshold_by_client[client]
        benign = sorted(float(value) for value in client_scores.filter(pl.col("label") == 0)["score"].to_list())
        attack = sorted(float(value) for value in client_scores.filter(pl.col("label") == 1)["score"].to_list())
        result[client] = {
            "per_client_benign_score_cdf": _empirical_cdf(benign),
            "per_client_attack_score_cdf": _empirical_cdf(attack),
            "per_client_threshold_position": {
                "threshold": threshold,
                "benign_cdf": _cdf_position(benign, threshold),
                "attack_cdf": _cdf_position(attack, threshold),
            },
            "threshold": threshold,
            "false_positive_rate": metric["false_positive_rate"],
            "false_positive_rate_status": metric["false_positive_rate_status"],
            "true_positive_rate": metric["true_positive_rate"],
            "true_positive_rate_status": metric["true_positive_rate_status"],
            "balanced_accuracy": metric["balanced_accuracy"],
            "balanced_accuracy_status": metric["balanced_accuracy_status"],
            "macro_f1": metric["macro_f1"],
            "macro_f1_status": metric["macro_f1_status"],
        }
    return result


def _empirical_cdf(values: list[float]) -> list[dict[str, float]]:
    return [{"score": value, "cumulative_probability": (index + 1) / len(values)} for index, value in enumerate(values)]


def _cdf_position(values: list[float], threshold: float) -> float | None:
    return sum(value <= threshold for value in values) / len(values) if values else None


def threshold_tradeoff(baseline: dict[str, object], shifted: dict[str, object]) -> dict[str, dict[str, float | None]]:
    if set(baseline) != set(shifted):
        raise ValueError("Threshold trade-off sources have incompatible client populations")
    baseline_values = cast(dict[str, dict[str, object]], baseline)
    shifted_values = cast(dict[str, dict[str, object]], shifted)
    return {
        client: {
            "threshold_shift": float(cast(float, shifted_values[client]["threshold"]))
            - float(cast(float, baseline_values[client]["threshold"])),
            "fpr_delta": _metric_delta(baseline_values[client], shifted_values[client], "false_positive_rate"),
            "tpr_delta": _metric_delta(baseline_values[client], shifted_values[client], "true_positive_rate"),
        }
        for client in sorted(baseline)
    }


def _metric_delta(baseline: object, shifted: object, metric: str) -> float | None:
    left = cast(dict[str, object], baseline).get(metric)
    right = cast(dict[str, object], shifted).get(metric)
    return float(right) - float(left) if isinstance(left, float) and isinstance(right, float) else None


def calibration_variance_terms(calibration: pl.DataFrame) -> dict[str, float | None]:
    values = np.asarray(calibration["score"].to_list(), dtype=np.float64)
    if values.size == 0:
        raise ValueError("Quantile-estimation analysis requires calibration scores")
    pooled_variance = float(np.var(values))
    means_and_variances = []
    for _, group in calibration.group_by("client_id", maintain_order=True):
        group_values = np.asarray(group["score"].to_list(), dtype=np.float64)
        means_and_variances.append((group_values.size, float(group_values.mean()), float(np.var(group_values))))
    total = sum(count for count, _, _ in means_and_variances)
    pooled_mean = float(values.mean())
    within = sum(count * variance for count, _, variance in means_and_variances) / total
    between = sum(count * (mean - pooled_mean) ** 2 for count, mean, _ in means_and_variances) / total
    return {
        "within_term": within,
        "between_term": between,
        "between_ratio": between / pooled_variance if pooled_variance else None,
    }


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

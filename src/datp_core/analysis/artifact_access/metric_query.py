"""Evaluation-record and threshold-policy lookups shared by every analysis capability."""

from __future__ import annotations

from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.experiments.models import EvaluationSpecRecord, ExperimentRecord


def experiment_evaluation(experiment: ExperimentRecord, label: str) -> EvaluationSpecRecord:
    return next(item for item in experiment.evaluations if item.label == label)


def evaluation_policy_id(experiment: ExperimentRecord, label: str) -> str:
    return experiment_evaluation(experiment, label).threshold_policy_id.value


def evaluation_threshold_quantile(
    config: ResolvedProjectConfiguration, evaluation: EvaluationSpecRecord
) -> float | None:
    policy = config.threshold_policies.get(evaluation.threshold_policy_id)
    quantile = getattr(policy, "quantile", None)
    return quantile if isinstance(quantile, float) else None


__all__ = ["evaluation_policy_id", "evaluation_threshold_quantile", "experiment_evaluation"]

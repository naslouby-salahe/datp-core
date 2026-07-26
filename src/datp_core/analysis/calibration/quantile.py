"""Quantile-estimator analysis."""

from __future__ import annotations

from datp_core.analysis.contracts import (
    PairedAnalysisCell,
    QuantileEstimationAnalysisResult,
    QuantileEstimationClientResult,
    QuantileEstimationEvaluationResult,
    QuantileEstimationSeedResult,
)
from datp_core.analysis.enums import ProducedField
from datp_core.analysis.errors import ScientificContractViolationError
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.analysis.runtime.runner import run_analysis
from datp_core.artifacts.schemas.columns import ScoreColumn, ThresholdColumn
from datp_core.core.identifiers import AnalysisLabel, ClientId, EvaluationLabel
from datp_core.evaluation.distributions import calibration_variance_terms
from datp_core.experiments import QuantileEstimationAnalysisRecord


@run_analysis.register
def analyze_quantile_estimation(
    specification: QuantileEstimationAnalysisRecord,
    context: AnalysisExecutionContext,
    cell: PairedAnalysisCell | None = None,
) -> tuple[QuantileEstimationAnalysisResult, ...]:
    """Execute quantile-estimation analysis across experiment seeds."""
    oracle_label = EvaluationLabel(specification.oracle_reference)
    eval_labels = tuple(EvaluationLabel(label) for label in specification.source_evaluations)
    produced_fields = tuple(ProducedField(field) for field in specification.produced_fields)

    seed_results: list[QuantileEstimationSeedResult] = []
    for seed in context.seeds:
        oracle_ctx = context.evaluation_context(oracle_label, seed)
        oracle_thresholds = context.artifacts.thresholds(oracle_ctx)
        oracle_values = {
            ClientId(str(client)): float(value)
            for client, value in oracle_thresholds.select(
                ThresholdColumn.CLIENT_ID.value, ThresholdColumn.THRESHOLD.value
            ).iter_rows()
        }
        if len(set(oracle_values.values())) != 1:
            raise ScientificContractViolationError(
                "Quantile-estimation oracle must provide one shared threshold"
            )
        oracle_threshold = next(iter(oracle_values.values()))

        evaluation_results: list[QuantileEstimationEvaluationResult] = []
        for label in eval_labels:
            eval_ctx = context.evaluation_context(label, seed)
            score_ctx = context.score_context(label, seed)
            thresholds = context.artifacts.thresholds(eval_ctx)
            calibration = context.artifacts.calibration_scores(score_ctx)

            # Group calibration scores by client for efficient exceedance calculation
            scores_by_client = {
                ClientId(str(client_id[0])): [float(v) for v in rows[ScoreColumn.SCORE.value].to_list()]
                for client_id, rows in calibration.group_by(ScoreColumn.CLIENT_ID.value, maintain_order=True)
            }

            client_results: list[QuantileEstimationClientResult] = []
            for client, threshold, target in thresholds.select(
                ThresholdColumn.CLIENT_ID.value,
                ThresholdColumn.THRESHOLD.value,
                ScoreColumn.TARGET_QUANTILE.value,
            ).iter_rows():
                client_id = ClientId(str(client))
                t_val = float(threshold)
                target_val = float(target)
                values = scores_by_client.get(client_id, [])
                exceedance = (
                    sum(val > t_val for val in values) / len(values) if values else None
                )
                client_results.append(
                    QuantileEstimationClientResult(
                        client_id=client_id,
                        absolute_threshold_error=abs(t_val - oracle_threshold),
                        relative_threshold_error=(
                            abs(t_val - oracle_threshold) / abs(oracle_threshold)
                            if oracle_threshold
                            else None
                        ),
                        achieved_exceedance=exceedance,
                        signed_attainment_error=(
                            exceedance - (1.0 - target_val) if exceedance is not None else None
                        ),
                        absolute_attainment_error=(
                            abs(exceedance - (1.0 - target_val))
                            if exceedance is not None
                            else None
                        ),
                    )
                )
            variance_terms = calibration_variance_terms(calibration)
            evaluation_results.append(
                QuantileEstimationEvaluationResult(
                    evaluation_label=label,
                    per_client=tuple(client_results),
                    within_term=variance_terms.within_term,
                    between_term=variance_terms.between_term,
                    between_ratio=variance_terms.between_ratio,
                )
            )
        seed_results.append(
            QuantileEstimationSeedResult(
                seed=seed,
                oracle_threshold=oracle_threshold,
                evaluations=tuple(evaluation_results),
            )
        )
    result = QuantileEstimationAnalysisResult(
        analysis_label=AnalysisLabel(specification.label),
        produced_fields=produced_fields,
        seed_results=tuple(seed_results),
    )
    return (result,)

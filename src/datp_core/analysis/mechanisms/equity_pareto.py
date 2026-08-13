from dataclasses import dataclass

from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
from datp_core.analysis.inference.bootstrap.estimation import seed_level_bca_interval
from datp_core.analysis.inference.contracts import PairedInferenceProtocol
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.models import MetricStatus, PopulationMetricResult, metric_by_id
from datp_core.analysis.metrics.operating_point import HeldOutOperatingPointSummary
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import FederatedThresholdMethod, MetricId, PopulationId
from datp_core.core.numeric import MetricValue, Seed, ShrinkageWeight
from datp_core.experiments.common.seeds import CONFIRMATORY_ANALYSIS_SEED
from datp_core.experiments.confirmatory.spec import CONFIRMATORY_INFERENCE_PROTOCOL


class EquityParetoPoint(StrictModel):
    threshold_method: FederatedThresholdMethod
    shrinkage_weight: ShrinkageWeight | None = None
    seed_values_x: tuple[MetricValue, ...]
    seed_values_y: tuple[MetricValue, ...]
    mean_x: MetricValue
    mean_y: MetricValue
    x_interval: BootstrapInterval
    y_interval: BootstrapInterval
    nondominated: bool


class EquityTargetAttainmentRow(StrictModel):
    """Held-out operating-target diagnostics accompanying one Pareto method."""

    threshold_method: FederatedThresholdMethod
    shrinkage_weight: ShrinkageWeight | None = None
    seed_mean_absolute_target_errors: tuple[MetricValue, ...]
    seed_worst_absolute_target_errors: tuple[MetricValue, ...]
    seed_mean_absolute_calibration_generalization_gaps: tuple[MetricValue, ...]
    mean_absolute_target_error: MetricValue
    worst_absolute_target_error: MetricValue
    mean_absolute_calibration_generalization_gap: MetricValue


class EquityUtilityParetoView(StrictModel):
    utility_metric: MetricId
    points: tuple[EquityParetoPoint, ...]
    target_attainment: tuple[EquityTargetAttainmentRow, ...]


@dataclass(frozen=True, slots=True)
class _ParetoSeedEvidence:
    threshold_method: FederatedThresholdMethod
    shrinkage_weight: ShrinkageWeight | None
    seed: Seed
    population: PopulationMetricResult
    target_attainment: HeldOutOperatingPointSummary | None


type _PolicyKey = tuple[FederatedThresholdMethod, ShrinkageWeight | None]
type _ParetoCoordinates = tuple[
    FederatedThresholdMethod,
    ShrinkageWeight | None,
    tuple[MetricValue, ...],
    tuple[MetricValue, ...],
]


def equity_utility_pareto(
    documents: tuple[FederatedEvaluationDocument, ...],
    *,
    utility_metric: MetricId,
    fixed_shrinkage_documents: tuple[FederatedEvaluationDocument, ...] = (),
    inference_protocol: PairedInferenceProtocol = CONFIRMATORY_INFERENCE_PROTOCOL,
    analysis_seed: Seed = CONFIRMATORY_ANALYSIS_SEED,
) -> EquityUtilityParetoView:
    evidence = _pareto_evidence(documents, fixed_shrinkage_documents)
    by_method: dict[_PolicyKey, list[_ParetoSeedEvidence]] = {}
    for item in evidence:
        by_method.setdefault((item.threshold_method, item.shrinkage_weight), []).append(item)
    preliminary: list[_ParetoCoordinates] = []
    for (method, shrinkage_weight), records in sorted(by_method.items()):
        if len({record.seed for record in records}) != len(records):
            raise ScientificContractError(ErrorMessage("equity Pareto inputs cannot repeat a method seed"))
        ordered = tuple(sorted(records, key=lambda item: item.seed))
        x = tuple(_metric(item.population, MetricId.FPR_COEFFICIENT_OF_VARIATION) for item in ordered)
        y = tuple(_metric(item.population, utility_metric) for item in ordered)
        preliminary.append((method, shrinkage_weight, x, y))
    seed_cohorts = {
        tuple(record.seed for record in sorted(records, key=lambda item: item.seed)) for records in by_method.values()
    }
    if len(seed_cohorts) != 1:
        raise ScientificContractError(ErrorMessage("equity Pareto methods must use one common seed cohort"))
    points = tuple(
        EquityParetoPoint(
            threshold_method=method,
            shrinkage_weight=shrinkage_weight,
            seed_values_x=x,
            seed_values_y=y,
            mean_x=_mean(x),
            mean_y=_mean(y),
            x_interval=seed_level_bca_interval(
                x,
                protocol=inference_protocol,
                analysis_seed=analysis_seed,
            ),
            y_interval=seed_level_bca_interval(
                y,
                protocol=inference_protocol,
                analysis_seed=analysis_seed,
            ),
            nondominated=not any(
                _dominates(other_x, other_y, x, y)
                for other_method, other_weight, other_x, other_y in preliminary
                if (other_method, other_weight) != (method, shrinkage_weight)
            ),
        )
        for method, shrinkage_weight, x, y in preliminary
    )
    target_attainment = tuple(
        _target_attainment_row(method, shrinkage_weight, records)
        for (method, shrinkage_weight), records in sorted(by_method.items())
    )
    return EquityUtilityParetoView(
        utility_metric=utility_metric,
        points=points,
        target_attainment=target_attainment,
    )


def _pareto_evidence(
    documents: tuple[FederatedEvaluationDocument, ...],
    fixed_shrinkage_documents: tuple[FederatedEvaluationDocument, ...],
) -> tuple[_ParetoSeedEvidence, ...]:
    evidence: list[_ParetoSeedEvidence] = []
    for document in documents:
        if document.score_coordinate.population is not PopulationId.NBAIOT_NATURAL_DEVICES:
            raise ScientificContractError(ErrorMessage("equity Pareto analysis is N-BaIoT natural-device only"))
        evidence.append(
            _ParetoSeedEvidence(
                threshold_method=document.threshold_method,
                shrinkage_weight=None,
                seed=document.score_coordinate.training_seed,
                population=document.population,
                target_attainment=document.diagnostics.held_out_operating_point_summary,
            )
        )
    for document in fixed_shrinkage_documents:
        if document.threshold_method is not FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE:
            raise ScientificContractError(
                ErrorMessage("fixed shrinkage Pareto evidence requires fixed shrinkage documents")
            )
        for evaluation in document.diagnostics.shrinkage_curve:
            evidence.append(
                _ParetoSeedEvidence(
                    threshold_method=document.threshold_method,
                    shrinkage_weight=evaluation.lambda_weight,
                    seed=document.score_coordinate.training_seed,
                    population=evaluation.population,
                    target_attainment=evaluation.held_out_operating_point_summary,
                )
            )
    return tuple(evidence)


def _metric(population: PopulationMetricResult, metric: MetricId) -> MetricValue:
    result = metric_by_id(population.metrics, metric)
    if result.status is not MetricStatus.AVAILABLE or result.value is None:
        raise ScientificContractError(ErrorMessage(f"equity Pareto requires available {metric.value}"))
    return result.value


def _target_attainment_row(
    method: FederatedThresholdMethod,
    shrinkage_weight: ShrinkageWeight | None,
    records: list[_ParetoSeedEvidence],
) -> EquityTargetAttainmentRow:
    ordered = tuple(sorted(records, key=lambda item: item.seed))
    summaries = tuple(item.target_attainment for item in ordered)
    if any(summary is None for summary in summaries):
        raise ScientificContractError(
            ErrorMessage("equity Pareto target-attainment rows require held-out operating-point summaries")
        )
    available_summaries = tuple(summary for summary in summaries if summary is not None)
    target_errors = tuple(summary.mean_absolute_target_error for summary in available_summaries)
    worst_target_errors = tuple(summary.worst_absolute_target_error for summary in available_summaries)
    generalization_gaps = tuple(summary.mean_absolute_calibration_generalization_gap for summary in available_summaries)
    return EquityTargetAttainmentRow(
        threshold_method=method,
        shrinkage_weight=shrinkage_weight,
        seed_mean_absolute_target_errors=target_errors,
        seed_worst_absolute_target_errors=worst_target_errors,
        seed_mean_absolute_calibration_generalization_gaps=generalization_gaps,
        mean_absolute_target_error=_mean(target_errors),
        worst_absolute_target_error=_mean(worst_target_errors),
        mean_absolute_calibration_generalization_gap=_mean(generalization_gaps),
    )


def _mean(values: tuple[MetricValue, ...]) -> MetricValue:
    return MetricValue(sum(value.value for value in values) / len(values))


def _dominates(
    left_x: tuple[MetricValue, ...],
    left_y: tuple[MetricValue, ...],
    right_x: tuple[MetricValue, ...],
    right_y: tuple[MetricValue, ...],
) -> bool:
    lx = _mean(left_x).value
    ly = _mean(left_y).value
    rx = _mean(right_x).value
    ry = _mean(right_y).value
    return lx <= rx and ly >= ry and (lx < rx or ly > ry)

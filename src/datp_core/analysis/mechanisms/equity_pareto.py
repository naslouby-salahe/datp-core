from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.models import MetricStatus, metric_by_id
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import FederatedThresholdMethod, MetricId, PopulationId
from datp_core.core.numeric import MetricValue


class EquityParetoPoint(StrictModel):
    threshold_method: FederatedThresholdMethod
    seed_values_x: tuple[MetricValue, ...]
    seed_values_y: tuple[MetricValue, ...]
    mean_x: MetricValue
    mean_y: MetricValue
    nondominated: bool


class EquityUtilityParetoView(StrictModel):
    utility_metric: MetricId
    points: tuple[EquityParetoPoint, ...]


def equity_utility_pareto(
    documents: tuple[FederatedEvaluationDocument, ...], *, utility_metric: MetricId
) -> EquityUtilityParetoView:
    by_method: dict[FederatedThresholdMethod, list[FederatedEvaluationDocument]] = {}
    for document in documents:
        if document.score_coordinate.population is not PopulationId.NBAIOT_NATURAL_DEVICES:
            raise ScientificContractError(ErrorMessage("equity Pareto analysis is N-BaIoT natural-device only"))
        by_method.setdefault(document.threshold_method, []).append(document)
    preliminary: list[tuple[FederatedThresholdMethod, tuple[MetricValue, ...], tuple[MetricValue, ...]]] = []
    for method, records in sorted(by_method.items()):
        if len({record.score_coordinate.training_seed for record in records}) != len(records):
            raise ScientificContractError(ErrorMessage("equity Pareto inputs cannot repeat a method seed"))
        ordered = tuple(sorted(records, key=lambda item: item.score_coordinate.training_seed))
        x = tuple(_metric(item, MetricId.FPR_COEFFICIENT_OF_VARIATION) for item in ordered)
        y = tuple(_metric(item, utility_metric) for item in ordered)
        preliminary.append((method, x, y))
    points = tuple(
        EquityParetoPoint(
            threshold_method=method,
            seed_values_x=x,
            seed_values_y=y,
            mean_x=MetricValue(sum(value.value for value in x) / len(x)),
            mean_y=MetricValue(sum(value.value for value in y) / len(y)),
            nondominated=not any(
                _dominates(other_x, other_y, x, y)
                for other_method, other_x, other_y in preliminary
                if other_method is not method
            ),
        )
        for method, x, y in preliminary
    )
    return EquityUtilityParetoView(utility_metric=utility_metric, points=points)


def _metric(document: FederatedEvaluationDocument, metric: MetricId) -> MetricValue:
    result = metric_by_id(document.population.metrics, metric)
    if result.status is not MetricStatus.AVAILABLE or result.value is None:
        raise ScientificContractError(ErrorMessage(f"equity Pareto requires available {metric.value}"))
    return result.value


def _dominates(
    left_x: tuple[MetricValue, ...],
    left_y: tuple[MetricValue, ...],
    right_x: tuple[MetricValue, ...],
    right_y: tuple[MetricValue, ...],
) -> bool:
    lx = sum(value.value for value in left_x) / len(left_x)
    ly = sum(value.value for value in left_y) / len(left_y)
    rx = sum(value.value for value in right_x) / len(right_x)
    ry = sum(value.value for value in right_y) / len(right_y)
    return lx <= rx and ly >= ry and (lx < rx or ly > ry)

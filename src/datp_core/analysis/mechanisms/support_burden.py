from enum import StrEnum

from datp_core.analysis.mechanisms.movement import ThresholdMovementCohort
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.models import MetricStatus, metric_by_id
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import AnalysisReasonText, MetricId
from datp_core.core.numeric import MetricValue, RowCount, Seed
from datp_core.data.populations.contracts import ClientIdentity


class SupportAssociationAvailability(StrEnum):
    AVAILABLE = "available"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNDEFINED_CONSTANT_INPUT = "undefined_constant_input"


class CalibrationSupportBurdenClient(StrictModel):
    client: ClientIdentity
    source_benign_calibration_count: RowCount
    shared_false_positive_rate: MetricValue
    personalization_relief: MetricValue


class CalibrationSupportBurdenSeedEvidence(StrictModel):
    seed: Seed
    clients: tuple[CalibrationSupportBurdenClient, ...]
    support_fpr_spearman: MetricValue | None
    support_relief_spearman: MetricValue | None
    availability: SupportAssociationAvailability
    reason: AnalysisReasonText | None


def calibration_support_burden_evidence(
    shared: FederatedEvaluationDocument,
    local: FederatedEvaluationDocument,
    movement: ThresholdMovementCohort,
) -> CalibrationSupportBurdenSeedEvidence:
    if shared.score_coordinate.training_seed != local.score_coordinate.training_seed:
        raise ValueError("calibration-support burden evidence requires paired policy seeds")
    if not movement.movements:
        return _unavailable(
            shared.score_coordinate.training_seed, (), SupportAssociationAvailability.INSUFFICIENT_EVIDENCE
        )
    supports = {item.client: item.source_benign_calibration_count for item in shared.diagnostics.calibration_support}
    movements = {item.client: item for item in movement.movements}
    fprs: dict[ClientIdentity, MetricValue] = {}
    for result in shared.clients:
        metric = metric_by_id(result.metrics, MetricId.FALSE_POSITIVE_RATE)
        if metric.status is MetricStatus.AVAILABLE and metric.value is not None:
            fprs[result.client] = metric.value
    clients = tuple(
        CalibrationSupportBurdenClient(
            client=client,
            source_benign_calibration_count=supports[client],
            shared_false_positive_rate=fprs[client],
            personalization_relief=MetricValue(-movements[client].delta_fpr.value),
        )
        for client in sorted(set(supports) & set(movements) & set(fprs))
    )
    if len(clients) < 5:
        return _unavailable(
            shared.score_coordinate.training_seed, clients, SupportAssociationAvailability.INSUFFICIENT_EVIDENCE
        )
    support = tuple(float(item.source_benign_calibration_count.value) for item in clients)
    fpr = tuple(item.shared_false_positive_rate.value for item in clients)
    relief = tuple(item.personalization_relief.value for item in clients)
    support_fpr = _spearman(support, fpr)
    support_relief = _spearman(support, relief)
    if support_fpr is None or support_relief is None:
        return _unavailable(
            shared.score_coordinate.training_seed, clients, SupportAssociationAvailability.UNDEFINED_CONSTANT_INPUT
        )
    return CalibrationSupportBurdenSeedEvidence(
        seed=shared.score_coordinate.training_seed,
        clients=clients,
        support_fpr_spearman=MetricValue(support_fpr),
        support_relief_spearman=MetricValue(support_relief),
        availability=SupportAssociationAvailability.AVAILABLE,
        reason=None,
    )


def _unavailable(
    seed: Seed,
    clients: tuple[CalibrationSupportBurdenClient, ...],
    availability: SupportAssociationAvailability,
) -> CalibrationSupportBurdenSeedEvidence:
    return CalibrationSupportBurdenSeedEvidence(
        seed=seed,
        clients=clients,
        support_fpr_spearman=None,
        support_relief_spearman=None,
        availability=availability,
        reason=AnalysisReasonText(availability.value),
    )


def _spearman(left: tuple[float, ...], right: tuple[float, ...]) -> float | None:
    left_ranks = _average_ranks(left)
    right_ranks = _average_ranks(right)
    left_mean = sum(left_ranks) / len(left_ranks)
    right_mean = sum(right_ranks) / len(right_ranks)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left_ranks, right_ranks, strict=True))
    left_sum = sum((x - left_mean) ** 2 for x in left_ranks)
    right_sum = sum((y - right_mean) ** 2 for y in right_ranks)
    return None if left_sum == 0.0 or right_sum == 0.0 else numerator / (left_sum * right_sum) ** 0.5


def _average_ranks(values: tuple[float, ...]) -> tuple[float, ...]:
    ranks = [0.0] * len(values)
    sorted_indices = tuple(sorted(range(len(values)), key=values.__getitem__))
    start = 0
    while start < len(sorted_indices):
        end = start + 1
        while end < len(sorted_indices) and values[sorted_indices[end]] == values[sorted_indices[start]]:
            end += 1
        rank = (start + 1 + end) / 2.0
        for index in sorted_indices[start:end]:
            ranks[index] = rank
        start = end
    return tuple(ranks)

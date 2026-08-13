from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from datp_core.analysis.mechanisms.movement import ThresholdMovementCohort
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.models import MetricStatus, metric_by_id
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import AnalysisReasonText, MetricId
from datp_core.core.numeric import MetricValue, PairedObservationCount, RowCount, Seed, SeedObservationCount
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.thresholds.protocols import CANONICAL_QUANTILE


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

    @model_validator(mode="after")
    def validate_availability(self) -> CalibrationSupportBurdenSeedEvidence:
        clients = tuple(item.client for item in self.clients)
        if len(clients) != len(frozenset(clients)):
            raise ValueError("calibration-support burden clients must be unique within a seed")
        available = self.availability is SupportAssociationAvailability.AVAILABLE
        if available != (self.support_fpr_spearman is not None and self.support_relief_spearman is not None):
            raise ValueError("available support evidence requires both Spearman statistics")
        if available != (self.reason is None):
            raise ValueError("support evidence availability and reason must agree")
        return self


class SupportCorrelationDirectionSummary(StrictModel):
    valid_seed_count: SeedObservationCount
    unavailable_seed_count: SeedObservationCount
    median: MetricValue | None
    minimum: MetricValue | None
    maximum: MetricValue | None
    negative_count: PairedObservationCount
    zero_count: PairedObservationCount
    positive_count: PairedObservationCount


class CalibrationSupportBurdenCampaignSummary(StrictModel):
    seed_evidence: tuple[CalibrationSupportBurdenSeedEvidence, ...]
    support_fpr: SupportCorrelationDirectionSummary
    support_relief: SupportCorrelationDirectionSummary

    @model_validator(mode="after")
    def validate_seed_evidence(self) -> CalibrationSupportBurdenCampaignSummary:
        seeds = tuple(item.seed for item in self.seed_evidence)
        if not seeds or len(seeds) != len(frozenset(seeds)):
            raise ValueError("calibration-support campaign requires unique non-empty seed evidence")
        return self


class CalibrationSupportBurdenDeviceSummary(StrictModel):
    client: ClientIdentity
    median_source_benign_calibration_count: MetricValue
    mean_shared_false_positive_rate: MetricValue
    median_shared_false_positive_rate: MetricValue
    mean_shared_target_burden: MetricValue
    median_shared_target_burden: MetricValue
    mean_personalization_relief: MetricValue
    median_personalization_relief: MetricValue


class CalibrationSupportBurdenDeviceReport(StrictModel):
    devices: tuple[CalibrationSupportBurdenDeviceSummary, ...]

    @model_validator(mode="after")
    def validate_devices(self) -> CalibrationSupportBurdenDeviceReport:
        clients = tuple(item.client for item in self.devices)
        if len(clients) != len(frozenset(clients)):
            raise ValueError("calibration-support device report must not duplicate clients")
        return self


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


def summarize_calibration_support_burden(
    evidence: tuple[CalibrationSupportBurdenSeedEvidence, ...],
) -> CalibrationSupportBurdenCampaignSummary:
    if not evidence:
        raise ValueError("calibration-support burden summary requires seed evidence")
    seeds = tuple(item.seed for item in evidence)
    if len(seeds) != len(frozenset(seeds)):
        raise ValueError("calibration-support burden seed evidence must be unique")
    return CalibrationSupportBurdenCampaignSummary(
        seed_evidence=evidence,
        support_fpr=_summarize_correlation(tuple(item.support_fpr_spearman for item in evidence)),
        support_relief=_summarize_correlation(tuple(item.support_relief_spearman for item in evidence)),
    )


def summarize_calibration_support_burden_devices(
    evidence: tuple[CalibrationSupportBurdenSeedEvidence, ...],
) -> CalibrationSupportBurdenDeviceReport:
    clients: dict[ClientIdentity, list[CalibrationSupportBurdenClient]] = {}
    for seed in evidence:
        for client in seed.clients:
            clients.setdefault(client.client, []).append(client)
    return CalibrationSupportBurdenDeviceReport(
        devices=tuple(_device_summary(client, values) for client, values in sorted(clients.items()))
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


def _summarize_correlation(values: tuple[MetricValue | None, ...]) -> SupportCorrelationDirectionSummary:
    available = tuple(item.value for item in values if item is not None)
    unavailable = len(values) - len(available)
    if not available:
        return SupportCorrelationDirectionSummary(
            valid_seed_count=SeedObservationCount(0),
            unavailable_seed_count=SeedObservationCount(unavailable),
            median=None,
            minimum=None,
            maximum=None,
            negative_count=PairedObservationCount(0),
            zero_count=PairedObservationCount(0),
            positive_count=PairedObservationCount(0),
        )
    ordered = tuple(sorted(available))
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2.0
    return SupportCorrelationDirectionSummary(
        valid_seed_count=SeedObservationCount(len(available)),
        unavailable_seed_count=SeedObservationCount(unavailable),
        median=MetricValue(median),
        minimum=MetricValue(ordered[0]),
        maximum=MetricValue(ordered[-1]),
        negative_count=PairedObservationCount(sum(value < 0.0 for value in available)),
        zero_count=PairedObservationCount(sum(value == 0.0 for value in available)),
        positive_count=PairedObservationCount(sum(value > 0.0 for value in available)),
    )


def _device_summary(
    client: ClientIdentity, values: list[CalibrationSupportBurdenClient]
) -> CalibrationSupportBurdenDeviceSummary:
    support = tuple(float(item.source_benign_calibration_count.value) for item in values)
    fpr = tuple(item.shared_false_positive_rate.value for item in values)
    relief = tuple(item.personalization_relief.value for item in values)
    target = 1.0 - CANONICAL_QUANTILE.value
    burden = tuple(value - target for value in fpr)
    return CalibrationSupportBurdenDeviceSummary(
        client=client,
        median_source_benign_calibration_count=MetricValue(_median(support)),
        mean_shared_false_positive_rate=MetricValue(sum(fpr) / len(fpr)),
        median_shared_false_positive_rate=MetricValue(_median(fpr)),
        mean_shared_target_burden=MetricValue(sum(burden) / len(burden)),
        median_shared_target_burden=MetricValue(_median(burden)),
        mean_personalization_relief=MetricValue(sum(relief) / len(relief)),
        median_personalization_relief=MetricValue(_median(relief)),
    )


def _median(values: tuple[float, ...]) -> float:
    ordered = tuple(sorted(values))
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2.0

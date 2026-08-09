"""Operational diagnostics derived from validated evaluation evidence."""

from dataclasses import dataclass
from enum import StrEnum

from datp_core.analysis.metrics.models import MetricAvailability, MetricReason, MetricStatus, WarningCode
from datp_core.analysis.metrics.semantics import available, metric_value, unavailable
from datp_core.analysis.operational.traffic_rates import ValidatedTrafficRateEvidence, validate_traffic_rate_evidence
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import MetricId
from datp_core.core.numeric import Ratio, Seed
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedTrainingCoordinate


class AlertBurdenSuppressionReason(StrEnum):
    NO_APPLICABLE_TRAFFIC_RATE_EVIDENCE = "no_applicable_traffic_rate_evidence"
    POPULATION_MISMATCH = "traffic_rate_population_mismatch"
    NOT_PER_CLIENT_APPLICABLE = "traffic_rate_not_per_client_applicable"


@dataclass(frozen=True, slots=True)
class AlertBurdenDiagnostic:
    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    training_seed: Seed
    false_positive_rate: Ratio
    metric: MetricAvailability
    suppression_reason: AlertBurdenSuppressionReason | None
    warning: WarningCode | None

    def __post_init__(self) -> None:
        if (
            self.coordinate.population is not self.client.population
            or self.coordinate.training_seed != self.training_seed
        ):
            raise ScientificContractError(ErrorMessage("alert-burden coordinate must match client and training seed"))
        if self.metric.metric is not MetricId.ALERTS_PER_DAY:
            raise ScientificContractError(ErrorMessage("alert-burden diagnostics require the alerts-per-day metric"))
        is_available = self.metric.status is MetricStatus.AVAILABLE
        if is_available == (self.suppression_reason is not None):
            raise ScientificContractError(
                ErrorMessage("alert burden must carry exactly one of a value or suppression reason")
            )
        if is_available != (self.warning is None):
            raise ScientificContractError(ErrorMessage("suppressed alert burden requires an explicit warning"))

    @property
    def alerts_per_client_per_day(self) -> float | None:
        return metric_value(self.metric)


def calculate_alert_burden(
    *,
    client: ClientIdentity,
    coordinate: FederatedTrainingCoordinate,
    training_seed: Seed,
    false_positive_rate: Ratio,
    evidence: ValidatedTrafficRateEvidence | None,
) -> AlertBurdenDiagnostic:
    if evidence is None:
        return _suppressed(
            client,
            coordinate,
            training_seed,
            false_positive_rate,
            AlertBurdenSuppressionReason.NO_APPLICABLE_TRAFFIC_RATE_EVIDENCE,
        )
    validated = validate_traffic_rate_evidence(evidence)
    if validated.population is not client.population:
        return _suppressed(
            client,
            coordinate,
            training_seed,
            false_positive_rate,
            AlertBurdenSuppressionReason.POPULATION_MISMATCH,
        )
    if not validated.applicable_to_each_client:
        return _suppressed(
            client,
            coordinate,
            training_seed,
            false_positive_rate,
            AlertBurdenSuppressionReason.NOT_PER_CLIENT_APPLICABLE,
        )
    return AlertBurdenDiagnostic(
        client=client,
        coordinate=coordinate,
        training_seed=training_seed,
        false_positive_rate=false_positive_rate,
        metric=available(MetricId.ALERTS_PER_DAY, false_positive_rate.value * validated.rate_per_day.value),
        suppression_reason=None,
        warning=None,
    )


def _suppressed(
    client: ClientIdentity,
    coordinate: FederatedTrainingCoordinate,
    training_seed: Seed,
    false_positive_rate: Ratio,
    reason: AlertBurdenSuppressionReason,
) -> AlertBurdenDiagnostic:
    return AlertBurdenDiagnostic(
        client=client,
        coordinate=coordinate,
        training_seed=training_seed,
        false_positive_rate=false_positive_rate,
        metric=unavailable(
            MetricId.ALERTS_PER_DAY,
            MetricStatus.SUPPRESSED,
            MetricReason.MISSING_CAPABILITY,
        ),
        suppression_reason=reason,
        warning=WarningCode.MISSING_TRAFFIC_RATE_EVIDENCE,
    )

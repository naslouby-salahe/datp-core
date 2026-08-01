"""Evidence-gated operational alert-burden diagnostics."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

from datp_core.domain.enums import MetricId, WarningCode
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Seed
from datp_core.evaluation.metric_semantics import available, unavailable
from datp_core.evaluation.models import AlertBurdenResult, MetricReason, MetricStatus
from datp_core.evaluation.traffic_rates import ValidatedTrafficRateEvidence, validate_traffic_rate_evidence
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity


class AlertBurdenSuppressionReason(StrEnum):
    NO_APPLICABLE_TRAFFIC_RATE_EVIDENCE = "no_applicable_traffic_rate_evidence"
    POPULATION_MISMATCH = "traffic_rate_population_mismatch"
    NOT_PER_CLIENT_APPLICABLE = "traffic_rate_not_per_client_applicable"


@dataclass(frozen=True, slots=True)
class AlertBurdenDiagnostic:
    """Per-client alert burden, or an explicit protocol-mandated suppression."""

    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    training_seed: Seed
    false_positive_rate: float
    alerts_per_client_per_day: float | None
    suppression_reason: AlertBurdenSuppressionReason | None
    warning: WarningCode | None
    result: AlertBurdenResult

    def __post_init__(self) -> None:
        if (
            self.coordinate.population is not self.client.population
            or self.coordinate.training_seed != self.training_seed
        ):
            raise ScientificContractError("alert-burden coordinate must match client and training seed")
        if not isfinite(self.false_positive_rate) or not 0 <= self.false_positive_rate <= 1:
            raise ScientificContractError("alert burden requires a finite false-positive rate in [0, 1]")
        is_available = self.result.alerts_per_client_per_day.status is MetricStatus.AVAILABLE
        if is_available != (self.alerts_per_client_per_day is not None):
            raise ScientificContractError("alert-burden availability must match its numeric value")
        if is_available == (self.suppression_reason is not None):
            raise ScientificContractError("alert burden must carry exactly one of a value or suppression reason")


def calculate_alert_burden(
    *,
    client: ClientIdentity,
    coordinate: FederatedTrainingCoordinate,
    training_seed: Seed,
    false_positive_rate: float,
    evidence: ValidatedTrafficRateEvidence | None,
) -> AlertBurdenDiagnostic:
    """Calculate FPR × benign decisions/client/day only for applicable valid evidence."""
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
        alerts_per_client_per_day=false_positive_rate * validated.rate_per_day.value,
        suppression_reason=None,
        warning=None,
        result=AlertBurdenResult(
            alerts_per_client_per_day=available(
                MetricId.ALERTS_PER_DAY,
                false_positive_rate * validated.rate_per_day.value,
            )
        ),
    )


def _suppressed(
    client: ClientIdentity,
    coordinate: FederatedTrainingCoordinate,
    training_seed: Seed,
    false_positive_rate: float,
    reason: AlertBurdenSuppressionReason,
) -> AlertBurdenDiagnostic:
    return AlertBurdenDiagnostic(
        client=client,
        coordinate=coordinate,
        training_seed=training_seed,
        false_positive_rate=false_positive_rate,
        alerts_per_client_per_day=None,
        suppression_reason=reason,
        warning=WarningCode.MISSING_TRAFFIC_RATE_EVIDENCE,
        result=AlertBurdenResult(
            alerts_per_client_per_day=unavailable(
                MetricId.ALERTS_PER_DAY,
                MetricStatus.SUPPRESSED,
                MetricReason.MISSING_CAPABILITY,
            )
        ),
    )

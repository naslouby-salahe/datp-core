"""Operational diagnostics and typed evaluation publication lifecycles."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.centralized_reference.evaluation import (
    CentralizedEvaluationResult,
    evaluate_centralized_reference,
    evaluation_result_checksum,
    write_evaluation_document,
)
from datp_core.centralized_reference.scoring import PooledScoreArtifact
from datp_core.centralized_reference.thresholding import PooledThresholdResult
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import MetricId, WarningCode
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Ratio, Seed
from datp_core.evaluation.metric_semantics import available, metric_value, unavailable
from datp_core.evaluation.models import MetricAvailability, MetricReason, MetricStatus
from datp_core.evaluation.traffic_rates import ValidatedTrafficRateEvidence, validate_traffic_rate_evidence
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity


class AlertBurdenSuppressionReason(StrEnum):
    NO_APPLICABLE_TRAFFIC_RATE_EVIDENCE = "no_applicable_traffic_rate_evidence"
    POPULATION_MISMATCH = "traffic_rate_population_mismatch"
    NOT_PER_CLIENT_APPLICABLE = "traffic_rate_not_per_client_applicable"


class CentralizedEvaluationPublicationAsset(StrEnum):
    EVALUATION = "centralized_evaluation.json"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True)
class AlertBurdenDiagnostic:
    """Per-client alert burden, or an explicit protocol-mandated suppression."""

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
            raise ScientificContractError("alert-burden coordinate must match client and training seed")
        if self.metric.metric is not MetricId.ALERTS_PER_DAY:
            raise ScientificContractError("alert-burden diagnostics require the alerts-per-day metric")
        is_available = self.metric.status is MetricStatus.AVAILABLE
        if is_available == (self.suppression_reason is not None):
            raise ScientificContractError("alert burden must carry exactly one of a value or suppression reason")
        if is_available != (self.warning is None):
            raise ScientificContractError("suppressed alert burden requires an explicit warning")

    @property
    def alerts_per_client_per_day(self) -> float | None:
        return metric_value(self.metric)


@dataclass(frozen=True, slots=True)
class CentralizedEvaluationPublicationRequest:
    coordinate: CentralizedTrainingCoordinate
    evaluation_scores: PooledScoreArtifact
    threshold: PooledThresholdResult


def write_centralized_evaluation(
    request: CentralizedEvaluationPublicationRequest,
    directory: Path,
) -> CentralizedEvaluationResult:
    evaluation = evaluate_centralized_publication(request)
    write_evaluation_document(evaluation, directory)
    (directory / CentralizedEvaluationPublicationAsset.COMPLETE).write_text(
        evaluation_result_checksum(evaluation).value,
        encoding="utf-8",
    )
    return evaluation


def centralized_evaluation_is_reusable(
    request: CentralizedEvaluationPublicationRequest,
    directory: Path,
) -> bool:
    complete = directory / CentralizedEvaluationPublicationAsset.COMPLETE
    document = directory / CentralizedEvaluationPublicationAsset.EVALUATION
    if not complete.is_file() or not document.is_file():
        return False
    expected = evaluation_result_checksum(evaluate_centralized_publication(request))
    try:
        return complete.read_text(encoding="utf-8").strip() == expected.value
    except OSError:
        return False


def load_reused_centralized_evaluation(
    request: CentralizedEvaluationPublicationRequest,
    directory: Path,
) -> CentralizedEvaluationResult:
    del directory
    return evaluate_centralized_publication(request)


def rebase_centralized_evaluation(
    result: CentralizedEvaluationResult,
    directory: Path,
) -> CentralizedEvaluationResult:
    del directory
    return result


def evaluate_centralized_publication(
    request: CentralizedEvaluationPublicationRequest,
) -> CentralizedEvaluationResult:
    return evaluate_centralized_reference(
        coordinate=request.coordinate,
        evaluation_scores=request.evaluation_scores,
        threshold_result=request.threshold,
    )


def calculate_alert_burden(
    *,
    client: ClientIdentity,
    coordinate: FederatedTrainingCoordinate,
    training_seed: Seed,
    false_positive_rate: float,
    evidence: ValidatedTrafficRateEvidence | None,
) -> AlertBurdenDiagnostic:
    """Calculate FPR × benign decisions/client/day only for applicable valid evidence."""
    fpr = Ratio(false_positive_rate)
    if evidence is None:
        return _suppressed(
            client,
            coordinate,
            training_seed,
            fpr,
            AlertBurdenSuppressionReason.NO_APPLICABLE_TRAFFIC_RATE_EVIDENCE,
        )
    validated = validate_traffic_rate_evidence(evidence)
    if validated.population is not client.population:
        return _suppressed(
            client,
            coordinate,
            training_seed,
            fpr,
            AlertBurdenSuppressionReason.POPULATION_MISMATCH,
        )
    if not validated.applicable_to_each_client:
        return _suppressed(
            client,
            coordinate,
            training_seed,
            fpr,
            AlertBurdenSuppressionReason.NOT_PER_CLIENT_APPLICABLE,
        )
    return AlertBurdenDiagnostic(
        client=client,
        coordinate=coordinate,
        training_seed=training_seed,
        false_positive_rate=fpr,
        metric=available(
            MetricId.ALERTS_PER_DAY,
            fpr.value * validated.rate_per_day.value,
        ),
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

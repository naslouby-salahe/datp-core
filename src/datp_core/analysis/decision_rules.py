"""Narrow scientific decisions that keep confirmatory evidence separate from diagnostics."""

from dataclasses import dataclass

from datp_core.analysis.inference import BootstrapInterval
from datp_core.analysis.temporal import TemporalRecoveryResult
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole, ScientificDecision
from datp_core.domain.values import MetricValue


@dataclass(frozen=True, slots=True)
class ScientificDecisionResult:
    evidence_role: EvidenceRole
    decision: ScientificDecision
    point_estimate: MetricValue | None
    interval: BootstrapInterval | None
    availability: AvailabilityStatus
    rationale: str


def decide_confirmatory(interval: BootstrapInterval) -> ScientificDecisionResult:
    if (
        interval.availability is not AvailabilityStatus.AVAILABLE
        or interval.point_estimate is None
        or interval.lower_bound is None
        or interval.upper_bound is None
    ):
        return ScientificDecisionResult(
            EvidenceRole.CONFIRMATORY,
            ScientificDecision.BLOCKED,
            interval.point_estimate,
            interval,
            AvailabilityStatus.UNAVAILABLE,
            "confirmatory BCa interval is unavailable or degenerate",
        )
    if interval.lower_bound.value > 0:
        decision = ScientificDecision.SUPPORTED
        rationale = "the paired BCa interval supports lower CV(FPR) under local thresholds"
    elif interval.upper_bound.value < 0:
        decision = ScientificDecision.OPPOSITE_DIRECTION
        rationale = "the paired BCa interval supports the opposite direction"
    elif interval.point_estimate.value > 0:
        decision = ScientificDecision.DIRECTIONAL_INCONCLUSIVE
        rationale = "the point estimate is directional but the paired BCa interval crosses zero"
    else:
        decision = ScientificDecision.NO_OBSERVED_ADVANTAGE
        rationale = "the paired BCa interval crosses zero without a positive point estimate"
    return ScientificDecisionResult(
        EvidenceRole.CONFIRMATORY, decision, interval.point_estimate, interval, AvailabilityStatus.AVAILABLE, rationale
    )


def decide_model_absorption(
    delta_fedavg: MetricValue | None, delta_ditto: MetricValue | None
) -> ScientificDecisionResult:
    if delta_fedavg is None or delta_ditto is None or delta_fedavg.value <= 0:
        return ScientificDecisionResult(
            EvidenceRole.SUPPORTIVE,
            ScientificDecision.BLOCKED,
            delta_ditto,
            None,
            AvailabilityStatus.UNAVAILABLE,
            "model absorption requires a valid positive FedAvg reference effect",
        )
    ratio = delta_ditto.value / delta_fedavg.value
    if ratio >= 0.75:
        decision, rationale = ScientificDecision.SUPPORTED, "the Ditto effect is retained"
    elif ratio >= 0.25:
        decision, rationale = ScientificDecision.PARTIAL_ABSORPTION, "the Ditto effect is partially absorbed"
    else:
        decision, rationale = ScientificDecision.FULL_ABSORPTION, "the Ditto effect is largely absorbed"
    return ScientificDecisionResult(
        EvidenceRole.SUPPORTIVE, decision, delta_ditto, None, AvailabilityStatus.AVAILABLE, rationale
    )


def decide_temporal(result: TemporalRecoveryResult) -> ScientificDecisionResult:
    if result.availability is not AvailabilityStatus.AVAILABLE or result.recovery_ratio is None:
        return ScientificDecisionResult(
            EvidenceRole.TEMPORAL_BOUNDARY,
            ScientificDecision.BLOCKED,
            None,
            None,
            AvailabilityStatus.UNAVAILABLE,
            result.reason,
        )
    if result.recovered_amount.value > 0:
        return ScientificDecisionResult(
            EvidenceRole.TEMPORAL_BOUNDARY,
            ScientificDecision.SUPPORTED,
            result.recovery_ratio,
            None,
            AvailabilityStatus.AVAILABLE,
            "temporal degradation has positive one-shot recalibration recovery",
        )
    return ScientificDecisionResult(
        EvidenceRole.TEMPORAL_BOUNDARY,
        ScientificDecision.BOUNDARY_RESULT,
        result.recovery_ratio,
        None,
        AvailabilityStatus.AVAILABLE,
        "temporal degradation has no positive one-shot recalibration recovery",
    )

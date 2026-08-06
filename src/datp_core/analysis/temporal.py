"""Typed temporal recovery quantities and campaign-level scientific interpretation."""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import model_validator

from datp_core.analysis.scientific_decision import ScientificDecision, ScientificDecisionResult
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
)
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import MetricValue
from datp_core.protocols.metrics import TEMPORAL_CV_MATERIALITY_CUTOFF


class TemporalInterpretation(StrEnum):
    TEMPORAL_DEGRADATION_WITH_RECOVERY = "temporal_degradation_with_recovery"
    TEMPORAL_DEGRADATION_WITHOUT_RECOVERY = "temporal_degradation_without_recovery"
    NO_DETECTABLE_TEMPORAL_DEGRADATION = "no_detectable_temporal_degradation"
    OPPOSITE_TEMPORAL_MOVEMENT = "opposite_temporal_movement"


class TemporalRecoveryResult(StrictModel):
    seed: Seed
    experiment: ExperimentId
    threshold_method: FederatedThresholdMethod
    static_reference_cv: MetricValue
    frozen_future_cv: MetricValue
    recalibrated_future_cv: MetricValue

    @property
    def evidence_role(self) -> EvidenceRole:
        return EvidenceRole.TEMPORAL_BOUNDARY

    @property
    def drift_excess(self) -> MetricValue:
        return MetricValue(self.frozen_future_cv.value - self.static_reference_cv.value)

    @property
    def recovered_amount(self) -> MetricValue:
        return MetricValue(self.frozen_future_cv.value - self.recalibrated_future_cv.value)

    @property
    def materiality_cutoff(self) -> MetricValue:
        return TEMPORAL_CV_MATERIALITY_CUTOFF

    @property
    def recovery_ratio(self) -> MetricValue | None:
        if self.drift_excess.value <= self.materiality_cutoff.value:
            return None
        return MetricValue(self.recovered_amount.value / self.drift_excess.value)

    @property
    def availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.UNDEFINED if self.recovery_ratio is None else AvailabilityStatus.AVAILABLE

    @property
    def interpretation(self) -> TemporalInterpretation:
        if self.recovery_ratio is None:
            if self.drift_excess.value < 0.0:
                return TemporalInterpretation.OPPOSITE_TEMPORAL_MOVEMENT
            return TemporalInterpretation.NO_DETECTABLE_TEMPORAL_DEGRADATION
        if self.recovered_amount.value > 0.0:
            return TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_RECOVERY
        return TemporalInterpretation.TEMPORAL_DEGRADATION_WITHOUT_RECOVERY

    @property
    def reason(self) -> str | None:
        return (
            None
            if self.recovery_ratio is not None
            else "drift excess does not satisfy the declared positive-materiality rule"
        )


class TemporalAnalysisRecord(StrictModel):
    """Per-seed temporal quantities. Never carries a publication-level SUPPORTED decision."""

    recovery: TemporalRecoveryResult
    interpretation: TemporalInterpretation

    @model_validator(mode="after")
    def validate_record(self) -> "TemporalAnalysisRecord":
        if self.interpretation is not self.recovery.interpretation:
            raise ValueError("temporal interpretation must be derived from the recovery quantities")
        return self


def temporal_recovery(
    *,
    seed: Seed,
    experiment: ExperimentId,
    threshold_method: FederatedThresholdMethod,
    static_reference_cv: MetricValue,
    frozen_future_cv: MetricValue,
    recalibrated_future_cv: MetricValue,
) -> TemporalRecoveryResult:
    return TemporalRecoveryResult(
        seed=seed,
        experiment=experiment,
        threshold_method=threshold_method,
        static_reference_cv=static_reference_cv,
        frozen_future_cv=frozen_future_cv,
        recalibrated_future_cv=recalibrated_future_cv,
    )


def temporal_analysis_record(result: TemporalRecoveryResult) -> TemporalAnalysisRecord:
    return TemporalAnalysisRecord(
        recovery=result,
        interpretation=result.interpretation,
    )


def decide_temporal_campaign(
    records: tuple[TemporalRecoveryResult, ...],
) -> ScientificDecisionResult:
    """One campaign-level decision over the complete declared temporal seed cohort."""
    blocked = _blocked_temporal_campaign(records)
    if blocked is not None:
        return blocked
    counts = _temporal_interpretation_counts(records)
    ratios = tuple(record.recovery_ratio for record in records if record.recovery_ratio is not None)
    point = MetricValue(sum(ratio.value for ratio in ratios) / len(ratios)) if ratios else None
    decision, rationale = _campaign_decision_from_counts(counts, total=len(records))
    return ScientificDecisionResult(
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        decision=decision,
        point_estimate=point,
        interval=None,
        rationale=rationale,
    )


@dataclass(frozen=True, slots=True)
class _TemporalInterpretationCounts:
    with_recovery: int
    without_recovery: int
    opposite: int
    no_degradation: int


def _temporal_interpretation_counts(
    records: tuple[TemporalRecoveryResult, ...],
) -> _TemporalInterpretationCounts:
    return _TemporalInterpretationCounts(
        with_recovery=sum(
            record.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_RECOVERY for record in records
        ),
        without_recovery=sum(
            record.interpretation is TemporalInterpretation.TEMPORAL_DEGRADATION_WITHOUT_RECOVERY for record in records
        ),
        opposite=sum(record.interpretation is TemporalInterpretation.OPPOSITE_TEMPORAL_MOVEMENT for record in records),
        no_degradation=sum(
            record.interpretation is TemporalInterpretation.NO_DETECTABLE_TEMPORAL_DEGRADATION for record in records
        ),
    )


def _campaign_decision_from_counts(
    counts: _TemporalInterpretationCounts,
    *,
    total: int,
) -> tuple[ScientificDecision, str]:
    if counts.with_recovery == total:
        return (
            ScientificDecision.SUPPORTED,
            "campaign-level temporal evidence shows material degradation with positive "
            "one-shot recalibration recovery on every seed",
        )
    if counts.opposite == total:
        return (
            ScientificDecision.OPPOSITE_DIRECTION,
            "campaign-level temporal evidence moved opposite to the declared degradation direction",
        )
    if counts.no_degradation == total:
        return (
            ScientificDecision.BOUNDARY_RESULT,
            "campaign-level temporal evidence shows no material degradation across the seed cohort",
        )
    if counts.without_recovery == total:
        return (
            ScientificDecision.BOUNDARY_RESULT,
            "campaign-level temporal evidence shows degradation without positive recovery",
        )
    return (
        ScientificDecision.BOUNDARY_RESULT,
        (
            "campaign-level temporal evidence is mixed across seeds "
            f"(recovery={counts.with_recovery}, without={counts.without_recovery}, "
            f"no_degradation={counts.no_degradation}, opposite={counts.opposite})"
        ),
    )


def _blocked_temporal_campaign(
    records: tuple[TemporalRecoveryResult, ...],
) -> ScientificDecisionResult | None:
    if not records:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="temporal campaign decision requires at least one seed recovery record",
        )
    if len({record.experiment for record in records}) != 1 or len({record.threshold_method for record in records}) != 1:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="temporal campaign records must share one experiment and threshold method",
        )
    seeds = tuple(record.seed for record in records)
    if len(seeds) != len(frozenset(seeds)):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="temporal campaign records must be unique by seed",
        )
    return None

"""Typed temporal recovery quantities and scientific interpretation."""

from enum import StrEnum

from pydantic import model_validator

from datp_core.analysis.decisions import ScientificDecisionResult
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole, ScientificDecision
from datp_core.domain.values import MetricValue, Seed
from datp_core.protocols.metrics import TEMPORAL_CV_MATERIALITY_CUTOFF


class TemporalInterpretation(StrEnum):
    TEMPORAL_DEGRADATION_WITH_RECOVERY = "temporal_degradation_with_recovery"
    TEMPORAL_DEGRADATION_WITHOUT_RECOVERY = "temporal_degradation_without_recovery"
    NO_DETECTABLE_TEMPORAL_DEGRADATION = "no_detectable_temporal_degradation"
    OPPOSITE_TEMPORAL_MOVEMENT = "opposite_temporal_movement"


class TemporalRecoveryResult(StrictModel):
    seed: Seed
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
    recovery: TemporalRecoveryResult
    interpretation: TemporalInterpretation
    decision: ScientificDecisionResult

    @model_validator(mode="after")
    def validate_record(self) -> "TemporalAnalysisRecord":
        if self.interpretation is not self.recovery.interpretation:
            raise ValueError("temporal interpretation must be derived from the recovery quantities")
        if self.decision.evidence_role is not EvidenceRole.TEMPORAL_BOUNDARY:
            raise ValueError("temporal decisions must remain temporal-boundary evidence")
        if self.decision.point_estimate != self.recovery.recovery_ratio:
            raise ValueError("temporal decision estimate must equal the recovery ratio")
        return self


def temporal_recovery(
    *,
    seed: Seed,
    static_reference_cv: MetricValue,
    frozen_future_cv: MetricValue,
    recalibrated_future_cv: MetricValue,
) -> TemporalRecoveryResult:
    return TemporalRecoveryResult(
        seed=seed,
        static_reference_cv=static_reference_cv,
        frozen_future_cv=frozen_future_cv,
        recalibrated_future_cv=recalibrated_future_cv,
    )


def decide_temporal(result: TemporalRecoveryResult) -> ScientificDecisionResult:
    match result.interpretation:
        case TemporalInterpretation.TEMPORAL_DEGRADATION_WITH_RECOVERY:
            decision = ScientificDecision.SUPPORTED
            rationale = "temporal degradation has positive one-shot recalibration recovery"
        case TemporalInterpretation.TEMPORAL_DEGRADATION_WITHOUT_RECOVERY:
            decision = ScientificDecision.BOUNDARY_RESULT
            rationale = "temporal degradation has no positive one-shot recalibration recovery"
        case TemporalInterpretation.NO_DETECTABLE_TEMPORAL_DEGRADATION:
            decision = ScientificDecision.BOUNDARY_RESULT
            rationale = "no materially positive temporal degradation was detected"
        case TemporalInterpretation.OPPOSITE_TEMPORAL_MOVEMENT:
            decision = ScientificDecision.OPPOSITE_DIRECTION
            rationale = "future CV(FPR) moved opposite to the declared degradation direction"
    return ScientificDecisionResult(
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        decision=decision,
        point_estimate=result.recovery_ratio,
        interval=None,
        rationale=rationale,
    )


def temporal_analysis_record(result: TemporalRecoveryResult) -> TemporalAnalysisRecord:
    return TemporalAnalysisRecord(
        recovery=result,
        interpretation=result.interpretation,
        decision=decide_temporal(result),
    )

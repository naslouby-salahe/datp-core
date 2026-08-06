"""Typed temporal recovery quantities and campaign-level scientific interpretation."""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import model_validator

from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
from datp_core.analysis.inference.bootstrap.estimation import seed_level_bca_interval
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
from datp_core.protocols.seeds import BOUNDED_EVIDENCE_SEED_COHORT, CONFIRMATORY_ANALYSIS_SEED, SeedCohort
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL, PairedInferenceProtocol


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
    mean_fpr_static: MetricValue | None = None
    mean_fpr_frozen: MetricValue | None = None
    mean_fpr_recalibrated: MetricValue | None = None

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
    mean_fpr_static: MetricValue | None = None,
    mean_fpr_frozen: MetricValue | None = None,
    mean_fpr_recalibrated: MetricValue | None = None,
) -> TemporalRecoveryResult:
    return TemporalRecoveryResult(
        seed=seed,
        experiment=experiment,
        threshold_method=threshold_method,
        static_reference_cv=static_reference_cv,
        frozen_future_cv=frozen_future_cv,
        recalibrated_future_cv=recalibrated_future_cv,
        mean_fpr_static=mean_fpr_static,
        mean_fpr_frozen=mean_fpr_frozen,
        mean_fpr_recalibrated=mean_fpr_recalibrated,
    )


def temporal_analysis_record(result: TemporalRecoveryResult) -> TemporalAnalysisRecord:
    return TemporalAnalysisRecord(
        recovery=result,
        interpretation=result.interpretation,
    )


def decide_temporal_campaign(
    records: tuple[TemporalRecoveryResult, ...],
    *,
    required_seed_cohort: SeedCohort = BOUNDED_EVIDENCE_SEED_COHORT,
    analysis_seed: Seed = CONFIRMATORY_ANALYSIS_SEED,
    inference_protocol: PairedInferenceProtocol | None = None,
) -> ScientificDecisionResult:
    """One campaign-level decision over the complete declared temporal seed cohort."""
    blocked = _blocked_temporal_campaign(records, required_seed_cohort)
    if blocked is not None:
        return blocked
    protocol = inference_protocol or _temporal_inference_protocol(required_seed_cohort)
    defined_ratios = tuple(record.recovery_ratio for record in records if record.recovery_ratio is not None)
    # Recovery-ratio BCa is defined only when every seed has a defined ratio (full cohort).
    recovery_interval = (
        seed_level_bca_interval(
            defined_ratios,
            protocol=protocol,
            analysis_seed=analysis_seed,
            require_full_cohort=True,
        )
        if len(defined_ratios) == len(records)
        else None
    )
    counts = _temporal_interpretation_counts(records)
    point = recovery_interval.point_estimate if recovery_interval is not None else None
    decision, rationale = _campaign_decision_from_counts(
        counts,
        total=len(records),
        defined_recovery_count=len(defined_ratios),
        cohort_size=required_seed_cohort.member_count.value,
    )
    return ScientificDecisionResult(
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        decision=decision,
        point_estimate=point,
        interval=recovery_interval,
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
    defined_recovery_count: int,
    cohort_size: int,
) -> tuple[ScientificDecision, str]:
    if total < cohort_size or total < 2:
        return (
            ScientificDecision.BLOCKED,
            "publication-level temporal SUPPORTED requires the complete multi-seed declared cohort",
        )
    if counts.with_recovery == total:
        return (
            ScientificDecision.SUPPORTED,
            "campaign-level temporal evidence shows material degradation with positive "
            f"one-shot recalibration recovery on every seed of the declared cohort "
            f"(defined_recovery_ratio_count={defined_recovery_count})",
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
            f"no_degradation={counts.no_degradation}, opposite={counts.opposite}, "
            f"defined_recovery_ratio_count={defined_recovery_count})"
        ),
    )


def _blocked_temporal_campaign(
    records: tuple[TemporalRecoveryResult, ...],
    required_seed_cohort: SeedCohort,
) -> ScientificDecisionResult | None:
    if not records:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="temporal campaign decision requires the complete declared seed cohort",
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
    if frozenset(seeds) != frozenset(required_seed_cohort.values):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="temporal campaign records must equal the complete declared seed cohort",
        )
    if required_seed_cohort.member_count.value < 2:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="publication-level temporal decisions require a multi-seed declared cohort",
        )
    return None


def _temporal_inference_protocol(seed_cohort: SeedCohort) -> PairedInferenceProtocol:
    base = CONFIRMATORY_INFERENCE_PROTOCOL
    return PairedInferenceProtocol(
        confidence_level=base.confidence_level,
        seed_cohort=seed_cohort,
        interval_method=base.interval_method,
        bootstrap_replicates=base.bootstrap_replicates,
        statistical_test=base.statistical_test,
        wilcoxon_alternative=base.wilcoxon_alternative,
        wilcoxon_zero_method=base.wilcoxon_zero_method,
        wilcoxon_computation_preference=base.wilcoxon_computation_preference,
        effect_size=base.effect_size,
        multiplicity_correction=base.multiplicity_correction,
        descriptive_lower_quantile=base.descriptive_lower_quantile,
        descriptive_upper_quantile=base.descriptive_upper_quantile,
    )


def temporal_seed_series_intervals(
    records: tuple[TemporalRecoveryResult, ...],
    *,
    required_seed_cohort: SeedCohort = BOUNDED_EVIDENCE_SEED_COHORT,
    analysis_seed: Seed = CONFIRMATORY_ANALYSIS_SEED,
) -> tuple[BootstrapInterval, BootstrapInterval | None, BootstrapInterval | None]:
    """BCa over seed-level drift excess, recovery amount, and recovery ratio when defined."""
    protocol = _temporal_inference_protocol(required_seed_cohort)
    drift = seed_level_bca_interval(
        tuple(record.drift_excess for record in records),
        protocol=protocol,
        analysis_seed=analysis_seed,
    )
    recovered = seed_level_bca_interval(
        tuple(record.recovered_amount for record in records),
        protocol=protocol,
        analysis_seed=analysis_seed,
    )
    ratios = tuple(record.recovery_ratio for record in records if record.recovery_ratio is not None)
    recovery_ratio = (
        seed_level_bca_interval(ratios, protocol=protocol, analysis_seed=analysis_seed, require_full_cohort=True)
        if len(ratios) == len(records)
        else None
    )
    return drift, recovered, recovery_ratio

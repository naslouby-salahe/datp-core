"""Shared immutable contracts for statistical analysis."""

from enum import StrEnum
from math import isfinite

from pydantic import field_validator, model_validator

from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    AvailabilityStatus,
    EffectSizeId,
    EvidenceRole,
    FederatedThresholdMethod,
    IntervalMethod,
    MetricId,
    MultiplicityCorrectionId,
    PopulationId,
    ScientificDecision,
    StatisticalTestId,
)
from datp_core.domain.values import (
    BootstrapReplicateCount,
    ConfidenceLevel,
    MetricValue,
    PairedObservationCount,
    RankSum,
    Seed,
)
from datp_core.learning.federated.models import FederatedTrainingCoordinate

type MetricSeries = tuple[MetricValue, ...]


class BcaOutcome(StrEnum):
    AVAILABLE = "available"
    BLOCKED = "blocked"
    DEGENERATE = "degenerate"

    @property
    def availability(self) -> AvailabilityStatus:
        match self:
            case BcaOutcome.AVAILABLE:
                return AvailabilityStatus.AVAILABLE
            case BcaOutcome.BLOCKED:
                return AvailabilityStatus.UNAVAILABLE
            case BcaOutcome.DEGENERATE:
                return AvailabilityStatus.UNDEFINED


class BcaReason(StrEnum):
    NONE = ""
    CANONICAL_PROTOCOL_MISMATCH = "canonical_protocol_mismatch"
    BOOTSTRAP_REPLICATE_COUNT_MISMATCH = "bootstrap_replicate_count_mismatch"
    DUPLICATE_SEED = "duplicate_seed"
    SEED_COHORT_MISMATCH = "seed_cohort_mismatch"
    CONFIRMATORY_ENDPOINT_MISMATCH = "confirmatory_endpoint_mismatch"
    FIXED_COORDINATE_MISMATCH = "fixed_coordinate_mismatch"
    IDENTICAL_PAIRED_DELTAS = "identical_paired_deltas"
    DEGENERATE_BOOTSTRAP_DISTRIBUTION = "degenerate_bootstrap_distribution"
    INFINITE_BIAS_CORRECTION = "infinite_bias_correction"
    UNDEFINED_ACCELERATION = "undefined_acceleration"
    INVALID_ADJUSTED_QUANTILES = "invalid_adjusted_quantiles"
    EXTERNAL_ANALYSIS_PLAN_MISMATCH = "external_analysis_plan_mismatch"
    EXTERNAL_SEED_COHORT_MISMATCH = "external_seed_cohort_mismatch"


class WilcoxonAlternative(StrEnum):
    TWO_SIDED = "two-sided"


class WilcoxonZeroMethod(StrEnum):
    PRATT = "pratt"


class WilcoxonComputationMethod(StrEnum):
    SCIPY_ASYMPTOTIC = "scipy_asymptotic"


class PValue(StrictModel):
    value: float

    @field_validator("value")
    @classmethod
    def _validate(cls, v: float) -> float:
        if not isfinite(v) or not 0.0 <= v <= 1.0:
            raise ValueError("p-value must be finite and lie in [0, 1]")
        return v


class PairedDifferenceCounts(StrictModel):
    positive: int
    zero: int
    negative: int

    @field_validator("positive", "zero", "negative")
    @classmethod
    def _validate_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("paired-difference counts must be non-negative")
        return v

    @property
    def total(self) -> int:
        return self.positive + self.zero + self.negative

    @property
    def positive_proportion(self) -> float | None:
        return self.positive / self.total if self.total else None


class PairedContrast(StrictModel):
    coordinate: FederatedTrainingCoordinate
    evidence_role: EvidenceRole
    metric: MetricId
    left_method: FederatedThresholdMethod
    right_method: FederatedThresholdMethod
    left_value: MetricValue
    right_value: MetricValue

    @model_validator(mode="after")
    def _validate_distinct_methods(self) -> "PairedContrast":
        if self.left_method is self.right_method:
            raise ValueError("paired contrast requires two distinct threshold methods")
        return self

    @property
    def seed(self) -> Seed:
        return self.coordinate.training_seed

    @property
    def delta(self) -> MetricValue:
        return MetricValue(self.left_value.value - self.right_value.value)


type PairedContrasts = tuple[PairedContrast, ...]


class ExternalPairedAnalysisPlan(StrictModel):
    population: PopulationId
    evidence_role: EvidenceRole
    metric: MetricId
    left_method: FederatedThresholdMethod
    right_method: FederatedThresholdMethod
    seed_cohort: tuple[Seed, ...]
    confidence_level: ConfidenceLevel

    @model_validator(mode="after")
    def _validate(self) -> "ExternalPairedAnalysisPlan":
        if self.evidence_role not in {
            EvidenceRole.EXTERNAL_VALIDATION,
            EvidenceRole.APPLICABILITY_BOUNDARY,
            EvidenceRole.TEMPORAL_BOUNDARY,
        }:
            raise ValueError("supplementary paired analysis requires non-confirmatory evidence")
        if not self.seed_cohort or len(set(self.seed_cohort)) != len(self.seed_cohort):
            raise ValueError("external paired analysis requires a unique non-empty seed cohort")
        if self.left_method is self.right_method:
            raise ValueError("external paired analysis requires two distinct threshold methods")
        return self


class BcaAdjustment(StrictModel):
    bias_correction: MetricValue
    acceleration: MetricValue


class BootstrapInterval(StrictModel):
    method: IntervalMethod
    confidence_level: ConfidenceLevel
    replicate_count: BootstrapReplicateCount
    analysis_seed: Seed
    point_estimate: MetricValue | None
    lower_bound: MetricValue | None
    upper_bound: MetricValue | None
    adjustment: BcaAdjustment | None
    outcome: BcaOutcome
    reason: BcaReason

    @model_validator(mode="after")
    def _validate(self) -> "BootstrapInterval":
        bounds_present = self.lower_bound is not None and self.upper_bound is not None
        if (self.lower_bound is None) != (self.upper_bound is None):
            raise ValueError("bootstrap interval bounds must occur together")
        if (
            bounds_present
            and self.lower_bound is not None
            and self.upper_bound is not None
            and self.lower_bound.value > self.upper_bound.value
        ):
            raise ValueError("bootstrap interval lower bound cannot exceed upper bound")

        match self.outcome:
            case BcaOutcome.AVAILABLE:
                if (
                    self.point_estimate is None
                    or not bounds_present
                    or self.adjustment is None
                    or self.reason is not BcaReason.NONE
                ):
                    raise ValueError("available BCa interval requires estimate, bounds, adjustment, and no reason")
            case BcaOutcome.BLOCKED:
                if bounds_present or self.adjustment is not None or self.reason is BcaReason.NONE:
                    raise ValueError("blocked BCa interval requires a typed reason and no interval values")
            case BcaOutcome.DEGENERATE:
                if (
                    self.point_estimate is None
                    or bounds_present
                    or self.adjustment is not None
                    or self.reason is BcaReason.NONE
                ):
                    raise ValueError("degenerate BCa interval requires an estimate and typed reason")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        return self.outcome.availability

    @classmethod
    def available(
        cls,
        *,
        method: IntervalMethod,
        confidence_level: ConfidenceLevel,
        replicate_count: BootstrapReplicateCount,
        analysis_seed: Seed,
        point_estimate: MetricValue,
        lower_bound: MetricValue,
        upper_bound: MetricValue,
        adjustment: BcaAdjustment,
    ) -> "BootstrapInterval":
        return cls(
            method=method,
            confidence_level=confidence_level,
            replicate_count=replicate_count,
            analysis_seed=analysis_seed,
            point_estimate=point_estimate,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            adjustment=adjustment,
            outcome=BcaOutcome.AVAILABLE,
            reason=BcaReason.NONE,
        )

    @classmethod
    def blocked(
        cls,
        *,
        method: IntervalMethod,
        confidence_level: ConfidenceLevel,
        replicate_count: BootstrapReplicateCount,
        analysis_seed: Seed,
        point_estimate: MetricValue | None,
        reason: BcaReason,
    ) -> "BootstrapInterval":
        return cls(
            method=method,
            confidence_level=confidence_level,
            replicate_count=replicate_count,
            analysis_seed=analysis_seed,
            point_estimate=point_estimate,
            lower_bound=None,
            upper_bound=None,
            adjustment=None,
            outcome=BcaOutcome.BLOCKED,
            reason=reason,
        )

    @classmethod
    def degenerate(
        cls,
        *,
        method: IntervalMethod,
        confidence_level: ConfidenceLevel,
        replicate_count: BootstrapReplicateCount,
        analysis_seed: Seed,
        point_estimate: MetricValue,
        reason: BcaReason,
    ) -> "BootstrapInterval":
        return cls(
            method=method,
            confidence_level=confidence_level,
            replicate_count=replicate_count,
            analysis_seed=analysis_seed,
            point_estimate=point_estimate,
            lower_bound=None,
            upper_bound=None,
            adjustment=None,
            outcome=BcaOutcome.DEGENERATE,
            reason=reason,
        )


class ScientificDecisionResult(StrictModel):
    evidence_role: EvidenceRole
    decision: ScientificDecision
    point_estimate: MetricValue | None
    interval: BootstrapInterval | None
    rationale: str

    @model_validator(mode="after")
    def _validate(self) -> "ScientificDecisionResult":
        if not self.rationale:
            raise ValueError("scientific decisions require a rationale")
        if self.interval is not None and self.point_estimate != self.interval.point_estimate:
            raise ValueError("decision estimate must match its interval estimate")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        if self.decision is ScientificDecision.BLOCKED:
            return AvailabilityStatus.UNAVAILABLE
        return AvailabilityStatus.AVAILABLE


class WilcoxonResult(StrictModel):
    statistic: RankSum | None
    p_value: PValue | None
    nonzero_pair_count: PairedObservationCount
    computation_method: WilcoxonComputationMethod | None
    availability: AvailabilityStatus
    reason: str

    @model_validator(mode="after")
    def _validate(self) -> "WilcoxonResult":
        available = self.availability is AvailabilityStatus.AVAILABLE
        if available:
            if (
                self.statistic is None
                or self.p_value is None
                or self.computation_method is None
                or self.reason
            ):
                raise ValueError("available Wilcoxon result requires finite values and no reason")
        elif self.statistic is not None or self.p_value is not None or not self.reason:
            raise ValueError("unavailable Wilcoxon result requires no values and an explicit reason")
        return self

    @property
    def test(self) -> StatisticalTestId:
        return StatisticalTestId.WILCOXON_SIGNED_RANK

    @property
    def alternative(self) -> WilcoxonAlternative:
        return WilcoxonAlternative.TWO_SIDED

    @property
    def zero_method(self) -> WilcoxonZeroMethod:
        return WilcoxonZeroMethod.PRATT


class RankBiserialResult(StrictModel):
    value: MetricValue | None
    positive_rank_sum: RankSum | None
    negative_rank_sum: RankSum | None
    nonzero_pair_count: PairedObservationCount
    availability: AvailabilityStatus
    reason: str

    @model_validator(mode="after")
    def _validate(self) -> "RankBiserialResult":
        available = self.availability is AvailabilityStatus.AVAILABLE
        values = (
            self.value,
            self.positive_rank_sum,
            self.negative_rank_sum,
        )
        if available:
            if any(value is None for value in values) or self.reason:
                raise ValueError("available rank-biserial result requires finite values and no reason")
            if self.value is not None and not -1.0 <= self.value <= 1.0:
                raise ValueError("rank-biserial correlation must lie in [-1, 1]")
        elif any(value is not None for value in values) or not self.reason:
            raise ValueError("unavailable rank-biserial result requires no values and an explicit reason")
        return self

    @property
    def effect_size(self) -> EffectSizeId:
        return EffectSizeId.MATCHED_PAIRS_RANK_BISERIAL


class MultiplicityDecision(StrictModel):
    raw_p_value: PValue
    adjusted_p_value: PValue
    rejected: bool


class MultiplicityResult(StrictModel):
    correction: MultiplicityCorrectionId
    family_name: str
    decisions: tuple[MultiplicityDecision, ...]

    @model_validator(mode="after")
    def _validate(self) -> "MultiplicityResult":
        if not self.family_name.strip() or not self.decisions:
            raise ValueError("multiplicity requires a named non-empty test family")
        return self

    @property
    def raw_p_values(self) -> tuple[PValue, ...]:
        return tuple(decision.raw_p_value for decision in self.decisions)

    @property
    def adjusted_p_values(self) -> tuple[PValue, ...]:
        return tuple(decision.adjusted_p_value for decision in self.decisions)

    @property
    def rejected(self) -> tuple[bool, ...]:
        return tuple(decision.rejected for decision in self.decisions)


def _extract_named_attributes(
    result: object,
    names: tuple[str, ...],
) -> tuple[float, ...] | None:
    """Extract finite float attributes from a scipy result object."""
    values: list[float] = []
    for name in names:
        try:
            raw = getattr(result, name)
        except AttributeError:
            return None
        if isinstance(raw, bool) or not isinstance(raw, int | float):
            return None
        value = float(raw)
        if not isfinite(value):
            return None
        values.append(value)
    return tuple(values)

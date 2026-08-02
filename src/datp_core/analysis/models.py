"""Shared immutable contracts for statistical analysis."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

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


@dataclass(frozen=True, slots=True)
class PValue:
    value: float

    def __post_init__(self) -> None:
        if not isfinite(self.value) or not 0.0 <= self.value <= 1.0:
            raise ValueError("p-value must be finite and lie in [0, 1]")

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type: object, _handler: object) -> object:
        from pydantic_core import core_schema as _cs

        def _validate(v: object) -> "PValue":
            if isinstance(v, cls):
                return v
            if isinstance(v, int | float) and not isinstance(v, bool):
                return cls(float(v))
            raise ValueError(f"cannot construct PValue from {type(v).__qualname__}")

        return _cs.no_info_plain_validator_function(
            _validate,
            serialization=_cs.plain_serializer_function_ser_schema(lambda instance: instance.value),
        )


@dataclass(frozen=True, slots=True)
class PairedDifferenceCounts:
    positive: int
    zero: int
    negative: int

    def __post_init__(self) -> None:
        if min(self.positive, self.zero, self.negative) < 0:
            raise ValueError("paired-difference counts must be non-negative")

    @property
    def total(self) -> int:
        return self.positive + self.zero + self.negative

    @property
    def positive_proportion(self) -> float | None:
        return self.positive / self.total if self.total else None


@dataclass(frozen=True, slots=True)
class PairedContrast:
    coordinate: FederatedTrainingCoordinate
    evidence_role: EvidenceRole
    metric: MetricId
    left_method: FederatedThresholdMethod
    right_method: FederatedThresholdMethod
    left_value: MetricValue
    right_value: MetricValue

    def __post_init__(self) -> None:
        if self.left_method is self.right_method:
            raise ValueError("paired contrast requires two distinct threshold methods")

    @property
    def seed(self) -> Seed:
        return self.coordinate.training_seed

    @property
    def delta(self) -> MetricValue:
        return MetricValue(self.left_value.value - self.right_value.value)


type PairedContrasts = tuple[PairedContrast, ...]


@dataclass(frozen=True, slots=True)
class ExternalPairedAnalysisPlan:
    """Predeclared supplementary interval plan kept separate from the endpoint."""

    population: PopulationId
    evidence_role: EvidenceRole
    metric: MetricId
    left_method: FederatedThresholdMethod
    right_method: FederatedThresholdMethod
    seed_cohort: tuple[Seed, ...]
    confidence_level: ConfidenceLevel

    def __post_init__(self) -> None:
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


@dataclass(frozen=True, slots=True)
class BcaAdjustment:
    bias_correction: float
    acceleration: float

    def __post_init__(self) -> None:
        if not isfinite(self.bias_correction) or not isfinite(self.acceleration):
            raise ValueError("BCa adjustment values must be finite")


@dataclass(frozen=True, slots=True)
class BootstrapInterval:
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

    def __post_init__(self) -> None:
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


@dataclass(frozen=True, slots=True)
class ScientificDecisionResult:
    evidence_role: EvidenceRole
    decision: ScientificDecision
    point_estimate: MetricValue | None
    interval: BootstrapInterval | None
    rationale: str

    def __post_init__(self) -> None:
        if not self.rationale:
            raise ValueError("scientific decisions require a rationale")
        if self.interval is not None and self.point_estimate != self.interval.point_estimate:
            raise ValueError("decision estimate must match its interval estimate")

    @property
    def availability(self) -> AvailabilityStatus:
        if self.decision is ScientificDecision.BLOCKED:
            return AvailabilityStatus.UNAVAILABLE
        return AvailabilityStatus.AVAILABLE


@dataclass(frozen=True, slots=True)
class WilcoxonResult:
    statistic: float | None
    p_value: PValue | None
    nonzero_pair_count: int
    computation_method: WilcoxonComputationMethod | None
    availability: AvailabilityStatus
    reason: str

    def __post_init__(self) -> None:
        if self.nonzero_pair_count < 0:
            raise ValueError("nonzero pair count must be non-negative")

        available = self.availability is AvailabilityStatus.AVAILABLE
        if available:
            if (
                self.statistic is None
                or not isfinite(self.statistic)
                or self.p_value is None
                or self.computation_method is None
                or self.reason
            ):
                raise ValueError("available Wilcoxon result requires finite values and no reason")
        elif self.statistic is not None or self.p_value is not None or not self.reason:
            raise ValueError("unavailable Wilcoxon result requires no values and an explicit reason")

    @property
    def test(self) -> StatisticalTestId:
        return StatisticalTestId.WILCOXON_SIGNED_RANK

    @property
    def alternative(self) -> WilcoxonAlternative:
        return WilcoxonAlternative.TWO_SIDED

    @property
    def zero_method(self) -> WilcoxonZeroMethod:
        return WilcoxonZeroMethod.PRATT


@dataclass(frozen=True, slots=True)
class RankBiserialResult:
    value: float | None
    positive_rank_sum: float | None
    negative_rank_sum: float | None
    nonzero_pair_count: int
    availability: AvailabilityStatus
    reason: str

    def __post_init__(self) -> None:
        if self.nonzero_pair_count < 0:
            raise ValueError("nonzero pair count must be non-negative")

        available = self.availability is AvailabilityStatus.AVAILABLE
        values = (
            self.value,
            self.positive_rank_sum,
            self.negative_rank_sum,
        )
        if available:
            if any(value is None or not isfinite(value) for value in values) or self.reason:
                raise ValueError("available rank-biserial result requires finite values and no reason")
            if self.value is not None and not -1.0 <= self.value <= 1.0:
                raise ValueError("rank-biserial correlation must lie in [-1, 1]")
        elif any(value is not None for value in values) or not self.reason:
            raise ValueError("unavailable rank-biserial result requires no values and an explicit reason")

    @property
    def effect_size(self) -> EffectSizeId:
        return EffectSizeId.MATCHED_PAIRS_RANK_BISERIAL


@dataclass(frozen=True, slots=True)
class MultiplicityDecision:
    raw_p_value: PValue
    adjusted_p_value: PValue
    rejected: bool


@dataclass(frozen=True, slots=True)
class MultiplicityResult:
    correction: MultiplicityCorrectionId
    family_name: str
    decisions: tuple[MultiplicityDecision, ...]

    def __post_init__(self) -> None:
        if not self.family_name.strip() or not self.decisions:
            raise ValueError("multiplicity requires a named non-empty test family")

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

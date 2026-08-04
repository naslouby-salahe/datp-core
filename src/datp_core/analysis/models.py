"""Shared immutable contracts for statistical analysis."""

from enum import StrEnum
from math import isfinite
from typing import ClassVar

from pydantic import model_validator

from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    FederatedThresholdMethod,
    IntervalMethod,
    MetricId,
    MultiplicityCorrectionId,
    PopulationId,
    PreprocessingProtocolId,
    ScientificDecision,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.values import (
    BootstrapReplicateCount,
    ClosedUnitIntervalValue,
    ConfidenceLevel,
    DittoRegularization,
    MetricValue,
    PairedObservationCount,
    ProximalCoefficient,
    RankSum,
    Ratio,
    Seed,
)
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.models import SeedCohort
from datp_core.protocols.statistics import PairedInferenceProtocol, WilcoxonComputationMethod

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
    CANONICAL_PROTOCOL_MISMATCH = "canonical_protocol_mismatch"
    DUPLICATE_SEED = "duplicate_seed"
    SEED_COHORT_MISMATCH = "seed_cohort_mismatch"
    CONFIRMATORY_ENDPOINT_MISMATCH = "confirmatory_endpoint_mismatch"
    FIXED_COORDINATE_MISMATCH = "fixed_coordinate_mismatch"
    IDENTICAL_PAIRED_DELTAS = "identical_paired_deltas"
    DEGENERATE_BOOTSTRAP_DISTRIBUTION = "degenerate_bootstrap_distribution"
    INFINITE_BIAS_CORRECTION = "infinite_bias_correction"
    UNDEFINED_ACCELERATION = "undefined_acceleration"
    INVALID_ADJUSTED_QUANTILES = "invalid_adjusted_quantiles"
    SUPPLEMENTARY_ANALYSIS_PLAN_MISMATCH = "supplementary_analysis_plan_mismatch"
    SUPPLEMENTARY_SEED_COHORT_MISMATCH = "supplementary_seed_cohort_mismatch"


class PValue(ClosedUnitIntervalValue):
    validation_name: ClassVar[str] = "p-value"


class CorrelationCoefficient(MetricValue):
    validation_name: ClassVar[str] = "correlation coefficient"

    def __post_init__(self) -> None:
        super().__post_init__()
        if not -1.0 <= self.value <= 1.0:
            raise ValueError("correlation coefficient must lie in [-1, 1]")


class PairedDifferenceCounts(StrictModel):
    positive: PairedObservationCount
    zero: PairedObservationCount
    negative: PairedObservationCount

    @property
    def total(self) -> PairedObservationCount:
        return PairedObservationCount(self.positive.value + self.zero.value + self.negative.value)

    @property
    def positive_proportion(self) -> Ratio | None:
        return Ratio(self.positive.value / self.total.value) if self.total.value else None


class FederatedDesignIdentity(StrictModel):
    """Seed-independent detector design fixed across paired contrasts."""

    population: PopulationId
    split_protocol: SplitProtocolId
    preprocessing_identity: PreprocessingProtocolId
    model: TrainingModelId
    model_coefficient: ProximalCoefficient | DittoRegularization | None

    @classmethod
    def from_coordinate(cls, coordinate: FederatedTrainingCoordinate) -> "FederatedDesignIdentity":
        return cls(
            population=coordinate.population,
            split_protocol=coordinate.split_protocol,
            preprocessing_identity=coordinate.preprocessing_identity,
            model=coordinate.model,
            model_coefficient=coordinate.model_coefficient,
        )


class PairedContrast(StrictModel):
    coordinate: FederatedTrainingCoordinate
    evidence_role: EvidenceRole
    metric: MetricId
    left_method: FederatedThresholdMethod
    right_method: FederatedThresholdMethod
    left_value: MetricValue
    right_value: MetricValue

    @model_validator(mode="after")
    def validate_distinct_methods(self) -> "PairedContrast":
        if self.left_method is self.right_method:
            raise ValueError("paired contrast requires two distinct threshold methods")
        return self

    @property
    def seed(self) -> Seed:
        return self.coordinate.training_seed

    @property
    def design(self) -> FederatedDesignIdentity:
        return FederatedDesignIdentity.from_coordinate(self.coordinate)

    @property
    def delta(self) -> MetricValue:
        return MetricValue(self.left_value.value - self.right_value.value)


type PairedContrasts = tuple[PairedContrast, ...]


class SupplementaryPairedAnalysisPlan(StrictModel):
    population: PopulationId
    evidence_role: EvidenceRole
    metric: MetricId
    left_method: FederatedThresholdMethod
    right_method: FederatedThresholdMethod
    seed_cohort: SeedCohort
    inference_protocol: PairedInferenceProtocol

    @model_validator(mode="after")
    def validate_plan(self) -> "SupplementaryPairedAnalysisPlan":
        if self.evidence_role not in {
            EvidenceRole.EXTERNAL_VALIDATION,
            EvidenceRole.APPLICABILITY_BOUNDARY,
            EvidenceRole.TEMPORAL_BOUNDARY,
        }:
            raise ValueError("supplementary paired analysis requires non-confirmatory evidence")
        if self.left_method is self.right_method:
            raise ValueError("supplementary paired analysis requires two distinct threshold methods")
        if self.seed_cohort != self.inference_protocol.seed_cohort:
            raise ValueError("supplementary plan and inference protocol must share one seed cohort")
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
    reason: BcaReason | None

    @model_validator(mode="after")
    def validate_interval(self) -> "BootstrapInterval":
        bounds_present = self.lower_bound is not None and self.upper_bound is not None
        if (self.lower_bound is None) != (self.upper_bound is None):
            raise ValueError("bootstrap interval bounds must occur together")
        if bounds_present and self.lower_bound is not None and self.upper_bound is not None:
            if self.lower_bound.value > self.upper_bound.value:
                raise ValueError("bootstrap interval lower bound cannot exceed upper bound")
        match self.outcome:
            case BcaOutcome.AVAILABLE:
                valid = (
                    self.point_estimate is not None
                    and bounds_present
                    and self.adjustment is not None
                    and self.reason is None
                )
            case BcaOutcome.BLOCKED:
                valid = not bounds_present and self.adjustment is None and self.reason is not None
            case BcaOutcome.DEGENERATE:
                valid = (
                    self.point_estimate is not None
                    and not bounds_present
                    and self.adjustment is None
                    and self.reason is not None
                )
        if not valid:
            raise ValueError(f"invalid {self.outcome.value} BCa interval state")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        return self.outcome.availability

    @classmethod
    def available(
        cls,
        *,
        protocol: PairedInferenceProtocol,
        analysis_seed: Seed,
        point_estimate: MetricValue,
        lower_bound: MetricValue,
        upper_bound: MetricValue,
        adjustment: BcaAdjustment,
    ) -> "BootstrapInterval":
        return cls(
            method=protocol.interval_method,
            confidence_level=protocol.confidence_level,
            replicate_count=protocol.bootstrap_replicates,
            analysis_seed=analysis_seed,
            point_estimate=point_estimate,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            adjustment=adjustment,
            outcome=BcaOutcome.AVAILABLE,
            reason=None,
        )

    @classmethod
    def blocked(
        cls,
        *,
        protocol: PairedInferenceProtocol,
        analysis_seed: Seed,
        point_estimate: MetricValue | None,
        reason: BcaReason,
    ) -> "BootstrapInterval":
        return cls(
            method=protocol.interval_method,
            confidence_level=protocol.confidence_level,
            replicate_count=protocol.bootstrap_replicates,
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
        protocol: PairedInferenceProtocol,
        analysis_seed: Seed,
        point_estimate: MetricValue,
        reason: BcaReason,
    ) -> "BootstrapInterval":
        return cls(
            method=protocol.interval_method,
            confidence_level=protocol.confidence_level,
            replicate_count=protocol.bootstrap_replicates,
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
    def validate_decision(self) -> "ScientificDecisionResult":
        if not self.rationale.strip():
            raise ValueError("scientific decisions require a rationale")
        if self.interval is not None and self.point_estimate != self.interval.point_estimate:
            raise ValueError("decision estimate must match its interval estimate")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        return (
            AvailabilityStatus.UNAVAILABLE
            if self.decision is ScientificDecision.BLOCKED
            else AvailabilityStatus.AVAILABLE
        )


class WilcoxonResult(StrictModel):
    statistic: RankSum | None
    p_value: PValue | None
    nonzero_pair_count: PairedObservationCount
    computation_method: WilcoxonComputationMethod | None
    availability: AvailabilityStatus
    reason: str | None

    @model_validator(mode="after")
    def validate_result(self) -> "WilcoxonResult":
        available = self.availability is AvailabilityStatus.AVAILABLE
        if available:
            valid = (
                self.statistic is not None
                and self.p_value is not None
                and self.computation_method is not None
                and self.reason is None
            )
        else:
            valid = self.statistic is None and self.p_value is None and self.reason is not None
        if not valid:
            raise ValueError("Wilcoxon availability and values are inconsistent")
        return self


class RankBiserialResult(StrictModel):
    value: CorrelationCoefficient | None
    positive_rank_sum: RankSum | None
    negative_rank_sum: RankSum | None
    nonzero_pair_count: PairedObservationCount
    availability: AvailabilityStatus
    reason: str | None

    @model_validator(mode="after")
    def validate_result(self) -> "RankBiserialResult":
        values = (self.value, self.positive_rank_sum, self.negative_rank_sum)
        available = self.availability is AvailabilityStatus.AVAILABLE
        valid = (
            all(item is not None for item in values) and self.reason is None
            if available
            else all(item is None for item in values) and self.reason is not None
        )
        if not valid:
            raise ValueError("rank-biserial availability and values are inconsistent")
        return self


class MultiplicityPlan(StrictModel):
    family_name: str
    raw_p_values: tuple[PValue, ...]
    alpha: Ratio

    @model_validator(mode="after")
    def validate_plan(self) -> "MultiplicityPlan":
        if not self.family_name.strip() or not self.raw_p_values:
            raise ValueError("multiplicity requires a named non-empty test family")
        return self


class MultiplicityDecision(StrictModel):
    raw_p_value: PValue
    adjusted_p_value: PValue
    rejected: bool


class MultiplicityResult(StrictModel):
    correction: MultiplicityCorrectionId
    family_name: str
    decisions: tuple[MultiplicityDecision, ...]

    @model_validator(mode="after")
    def validate_result(self) -> "MultiplicityResult":
        if not self.family_name.strip() or not self.decisions:
            raise ValueError("multiplicity result requires a named non-empty family")
        return self

    @property
    def raw_p_values(self) -> tuple[PValue, ...]:
        return tuple(item.raw_p_value for item in self.decisions)

    @property
    def adjusted_p_values(self) -> tuple[PValue, ...]:
        return tuple(item.adjusted_p_value for item in self.decisions)

    @property
    def rejected(self) -> tuple[bool, ...]:
        return tuple(item.rejected for item in self.decisions)


def extract_named_numeric_attributes(result: object, names: tuple[str, ...]) -> tuple[float, ...] | None:
    """Extract finite numeric attributes from a SciPy result object."""
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

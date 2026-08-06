"""Typed BCa interval outcomes and persisted adjustment contracts."""

from enum import StrEnum

from pydantic import model_validator

from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import AvailabilityStatus, IntervalMethod
from datp_core.domain.values.counts import BootstrapReplicateCount, Seed
from datp_core.domain.values.ratios import ConfidenceLevel, MetricValue
from datp_core.protocols.statistics import PairedInferenceProtocol


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

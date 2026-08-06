"""Metric-specific full-precision anchor comparison strategies and their typed records."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import Field, field_validator, model_validator

from datp_core.anchor.models import _require_non_empty_detail
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    CheckpointStatus,
    ContractSubject,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    TrainingModelId,
)
from datp_core.domain.errors import require_contract
from datp_core.domain.values.base import floats_absolutely_close, floats_exactly_equal, is_numeric_zero
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import ClientCount, Seed
from datp_core.domain.values.ratios import MetricDelta, MetricValue

if TYPE_CHECKING:
    from datp_core.anchor.reproduction import AnchorDependencyBlocker


class AnchorComparisonStrategy(StrEnum):
    EXACT_EQUALITY = "exact_equality"
    ABSOLUTE_TOLERANCE = "absolute_tolerance"
    RELATIVE_TOLERANCE = "relative_tolerance"
    INTERVAL_OVERLAP = "interval_overlap"
    EXACT_COUNT = "exact_count"
    SOURCE_DEFINED = "source_defined"


class AnchorComparisonDecision(StrEnum):
    EQUIVALENT = "equivalent"
    ACCEPTABLE_DECLARED_DEVIATION = "acceptable_declared_deviation"
    MATERIAL_DISCREPANCY = "material_discrepancy"
    UNAVAILABLE = "unavailable"
    BLOCKED_INVALID_INPUT = "blocked_invalid_input"


class AnchorObservationSourceKind(StrEnum):
    HISTORICAL_ARTIFACT = "historical_artifact"
    INDEPENDENT_REPRODUCTION = "independent_reproduction"


class AnchorDiscrepancyReason(StrEnum):
    EXACT_MISMATCH = "exact_mismatch"
    ABSOLUTE_TOLERANCE_EXCEEDED = "absolute_tolerance_exceeded"
    RELATIVE_TOLERANCE_EXCEEDED = "relative_tolerance_exceeded"
    RELATIVE_COMPARISON_UNDEFINED_FOR_ZERO_REFERENCE = "relative_comparison_undefined_for_zero_reference"
    INTERVAL_NO_OVERLAP = "interval_no_overlap"
    COUNT_MISMATCH = "count_mismatch"
    MISSING_MANDATORY_OBSERVATION = "missing_mandatory_observation"
    WRONG_SEED_SUBSET = "wrong_seed_subset"
    CONFIRMATORY_TEN_SEED_COHORT_REJECTED = "confirmatory_ten_seed_cohort_rejected"
    DUPLICATE_SEED = "duplicate_seed"
    WRONG_POPULATION = "wrong_population"
    WRONG_TRAINING_MODEL = "wrong_training_model"
    WRONG_THRESHOLD_METHOD = "wrong_threshold_method"
    WRONG_METRIC = "wrong_metric"
    WRONG_CHECKPOINT_SEMANTICS = "wrong_checkpoint_semantics"
    STALE_OR_MISMATCHED_ARTIFACT = "stale_or_mismatched_artifact"
    UNSUPPORTED_GLOBAL_TOLERANCE = "unsupported_global_tolerance"
    MISSING_TOLERANCE_RULE = "missing_tolerance_rule"
    DEPENDENCY_BLOCKER = "dependency_blocker"
    ROUNDED_EQUALITY_CANNOT_OVERRIDE_FULL_PRECISION_FAILURE = "rounded_equality_cannot_override_full_precision_failure"


# ---------------------------------------------------------------------------
# Tolerance rule models
# ---------------------------------------------------------------------------


class ExactEqualityRule(StrictModel):
    strategy: Literal[AnchorComparisonStrategy.EXACT_EQUALITY] = AnchorComparisonStrategy.EXACT_EQUALITY


class AbsoluteToleranceRule(StrictModel):
    absolute_tolerance: MetricValue
    strategy: Literal[AnchorComparisonStrategy.ABSOLUTE_TOLERANCE] = AnchorComparisonStrategy.ABSOLUTE_TOLERANCE

    @model_validator(mode="after")
    def validate_tolerance(self) -> "AbsoluteToleranceRule":
        if self.absolute_tolerance.value < 0:
            raise ValueError("absolute tolerance must be non-negative")
        return self


class RelativeToleranceRule(StrictModel):
    relative_tolerance: MetricValue
    strategy: Literal[AnchorComparisonStrategy.RELATIVE_TOLERANCE] = AnchorComparisonStrategy.RELATIVE_TOLERANCE

    @model_validator(mode="after")
    def validate_tolerance(self) -> "RelativeToleranceRule":
        if self.relative_tolerance.value <= 0:
            raise ValueError("relative tolerance must be positive")
        return self


class IntervalOverlapRule(StrictModel):
    strategy: Literal[AnchorComparisonStrategy.INTERVAL_OVERLAP] = AnchorComparisonStrategy.INTERVAL_OVERLAP


class ExactCountRule(StrictModel):
    strategy: Literal[AnchorComparisonStrategy.EXACT_COUNT] = AnchorComparisonStrategy.EXACT_COUNT


class SourceDefinedRule(StrictModel):
    description: str
    strategy: Literal[AnchorComparisonStrategy.SOURCE_DEFINED] = AnchorComparisonStrategy.SOURCE_DEFINED

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        if not v:
            raise ValueError("source-defined rule requires a non-empty description")
        return v


AnchorToleranceRule = Annotated[
    ExactEqualityRule
    | AbsoluteToleranceRule
    | RelativeToleranceRule
    | IntervalOverlapRule
    | ExactCountRule
    | SourceDefinedRule,
    Field(discriminator="strategy"),
]


# ---------------------------------------------------------------------------
# Scientific identity models
# ---------------------------------------------------------------------------


class MetricInterval(StrictModel):
    lower: MetricValue
    upper: MetricValue

    @model_validator(mode="after")
    def validate_bounds(self) -> "MetricInterval":
        if self.lower > self.upper:
            raise ValueError("metric interval lower bound cannot exceed upper bound")
        return self


@dataclass(frozen=True, slots=True)
class AnchorScientificCoordinates:
    population: PopulationId
    training_model: TrainingModelId
    threshold_method: FederatedThresholdMethod
    metric: MetricId
    checkpoint_status: CheckpointStatus


def _require_anchor_coordinates(coordinates: AnchorScientificCoordinates) -> None:
    require_contract(
        coordinates.population is PopulationId.NBAIOT_NATURAL_DEVICES,
        "historical anchor coordinates require N-BaIoT natural devices",
        ContractSubject.COORDINATE,
    )
    require_contract(
        coordinates.training_model is TrainingModelId.FEDAVG_AUTOENCODER,
        "historical anchor coordinates require FedAvg autoencoder",
        ContractSubject.COORDINATE,
    )
    require_contract(
        coordinates.threshold_method
        in {
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
        },
        "historical anchor coordinates support only shared and local thresholds",
        ContractSubject.COORDINATE,
    )
    require_contract(
        coordinates.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION,
        "historical anchor coordinates require CV(FPR)",
        ContractSubject.COORDINATE,
    )
    require_contract(
        coordinates.checkpoint_status is CheckpointStatus.HISTORICAL_ENDPOINT,
        "historical anchor coordinates require historical endpoint checkpoint semantics",
        ContractSubject.COORDINATE,
    )


class AnchorMetricReference(StrictModel):
    seed: Seed
    population: PopulationId
    training_model: TrainingModelId
    threshold_method: FederatedThresholdMethod
    metric: MetricId
    value: MetricValue
    tolerance_rule: AnchorToleranceRule
    checkpoint_status: CheckpointStatus
    interval: MetricInterval | None = None
    count: ClientCount | None = None

    @model_validator(mode="after")
    def validate_coordinates(self) -> "AnchorMetricReference":
        _require_anchor_coordinates(
            AnchorScientificCoordinates(
                population=self.population,
                training_model=self.training_model,
                threshold_method=self.threshold_method,
                metric=self.metric,
                checkpoint_status=self.checkpoint_status,
            )
        )
        return self


class AnchorObservedMetric(StrictModel):
    """Observed metric candidate.

    Coordinates are not pre-forced to the historical identity so mismatched
    population, model, threshold, metric, or checkpoint semantics can be recorded
    as explicit comparison failures rather than construction-time silence.
    """

    seed: Seed
    population: PopulationId
    training_model: TrainingModelId
    threshold_method: FederatedThresholdMethod
    metric: MetricId
    value: MetricValue
    checkpoint_status: CheckpointStatus
    source_kind: AnchorObservationSourceKind
    artifact_path: Path
    artifact_checksum: Checksum
    model_checkpoint_identity: Checksum
    evidence_role: EvidenceRole
    interval: MetricInterval | None = None
    count: ClientCount | None = None

    @field_validator("evidence_role")
    @classmethod
    def validate_evidence_role(cls, v: EvidenceRole) -> EvidenceRole:
        if v is not EvidenceRole.ANCHOR_REPRODUCTION:
            raise ValueError("anchor observations must use the anchor_reproduction evidence role")
        return v


class AnchorMetricComparison(StrictModel):
    reference: AnchorMetricReference
    observation: AnchorObservedMetric | None
    decision: AnchorComparisonDecision
    signed_difference: MetricDelta | None
    relative_difference: MetricDelta | None
    tolerance_rule: AnchorToleranceRule
    reason: AnchorDiscrepancyReason | None

    @property
    def detail(self) -> str:
        expected = self.reference.value.value
        observed = None if self.observation is None else self.observation.value.value
        return (
            f"seed={self.reference.seed.value} "
            f"method={self.reference.threshold_method.value} "
            f"metric={self.reference.metric.value} "
            f"expected={expected!r} observed={observed!r} "
            f"decision={self.decision.value} "
            f"reason={None if self.reason is None else self.reason.value}"
        )


class AnchorSeedSubsetComparison(StrictModel):
    expected_seeds: tuple[Seed, ...]
    observed_seeds: tuple[Seed, ...]
    decision: AnchorComparisonDecision
    reason: AnchorDiscrepancyReason | None


class AnchorDiscrepancy(StrictModel):
    reason: AnchorDiscrepancyReason
    seed: Seed | None = None
    threshold_method: FederatedThresholdMethod | None = None
    metric: MetricId | None = None
    expected_value: MetricValue | None = None
    observed_value: MetricValue | None = None
    signed_difference: MetricDelta | None = None
    relative_difference: MetricDelta | None = None
    tolerance_rule: AnchorToleranceRule | None = None
    artifact_path: Path | None = None
    artifact_checksum: Checksum | None = None
    detail: str

    @field_validator("detail")
    @classmethod
    def validate_detail(cls, v: str) -> str:
        return _require_non_empty_detail(v)

    @classmethod
    def from_seed_subset(cls, seed_subset: AnchorSeedSubsetComparison) -> "AnchorDiscrepancy":
        return cls(
            reason=seed_subset.reason or AnchorDiscrepancyReason.WRONG_SEED_SUBSET,
            detail=(
                f"expected seeds {[seed.value for seed in seed_subset.expected_seeds]}; "
                f"observed seeds {[seed.value for seed in seed_subset.observed_seeds]}"
            ),
        )

    @classmethod
    def from_comparison(cls, comparison: AnchorMetricComparison) -> "AnchorDiscrepancy":
        observation = comparison.observation
        return cls(
            reason=comparison.reason or AnchorDiscrepancyReason.EXACT_MISMATCH,
            seed=comparison.reference.seed,
            threshold_method=comparison.reference.threshold_method,
            metric=comparison.reference.metric,
            expected_value=comparison.reference.value,
            observed_value=None if observation is None else observation.value,
            signed_difference=comparison.signed_difference,
            relative_difference=comparison.relative_difference,
            tolerance_rule=comparison.tolerance_rule,
            artifact_path=None if observation is None else observation.artifact_path,
            artifact_checksum=None if observation is None else observation.artifact_checksum,
            detail=comparison.detail,
        )

    @classmethod
    def from_dependency_blocker(cls, blocker: "AnchorDependencyBlocker") -> "AnchorDiscrepancy":
        return cls(
            reason=AnchorDiscrepancyReason.DEPENDENCY_BLOCKER,
            detail=blocker.detail,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class _NumericDelta:
    expected: float
    observed: float

    @property
    def signed(self) -> float:
        return self.observed - self.expected

    @property
    def relative(self) -> float | None:
        if is_numeric_zero(self.expected):
            return None
        return self.signed / abs(self.expected)


def compare_anchor_metric(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric | None,
) -> AnchorMetricComparison:
    """Compare one mandatory reference against an optional observation at full precision."""
    rule = reference.tolerance_rule
    if observation is None:
        return _build(
            reference,
            None,
            rule,
            decision=AnchorComparisonDecision.BLOCKED_INVALID_INPUT,
            reason=AnchorDiscrepancyReason.MISSING_MANDATORY_OBSERVATION,
        )

    coordinate_failure = _coordinate_mismatch_reason(reference, observation)
    delta = _NumericDelta(expected=reference.value.value, observed=observation.value.value)
    if coordinate_failure is not None:
        return _build(
            reference,
            observation,
            rule,
            decision=AnchorComparisonDecision.BLOCKED_INVALID_INPUT,
            reason=coordinate_failure,
            signed=delta.signed,
            relative=delta.relative,
        )
    return _compare_with_rule(reference, observation, rule, delta)


def reject_global_floating_point_tolerance() -> None:
    """Explicit rejection of an undifferentiated global floating-point tolerance."""
    raise ValueError("global floating-point tolerance is unsupported; declare a metric-specific rule")


def full_precision_failure_stands_despite_rounded_equality(
    *,
    full_precision_decision: AnchorComparisonDecision,
    presentation_decimals: int,
    expected: float,
    observed: float,
) -> bool:
    """Return True when rounded presentation equality must not rescue a full-precision failure."""
    if presentation_decimals < 0:
        raise ValueError("presentation decimals must be non-negative")
    if full_precision_decision is AnchorComparisonDecision.EQUIVALENT:
        return False
    return floats_exactly_equal(round(expected, presentation_decimals), round(observed, presentation_decimals))


def _compare_with_rule(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric,
    rule: AnchorToleranceRule,
    delta: _NumericDelta,
) -> AnchorMetricComparison:
    match rule:
        case ExactEqualityRule() | SourceDefinedRule():
            return _equality_result(reference, observation, rule, delta)
        case AbsoluteToleranceRule(absolute_tolerance=tolerance):
            if floats_absolutely_close(delta.expected, delta.observed, tolerance.value):
                return _pass(reference, observation, rule, delta)
            return _fail(
                reference,
                observation,
                rule,
                delta,
                AnchorDiscrepancyReason.ABSOLUTE_TOLERANCE_EXCEEDED,
            )
        case RelativeToleranceRule():
            return _relative_result(reference, observation, rule, delta)
        case IntervalOverlapRule():
            return _interval_result(reference, observation, rule, delta)
        case ExactCountRule():
            return _count_result(reference, observation, rule, delta)
        case _:
            raise ValueError(f"unsupported tolerance rule strategy {rule.strategy}")


def _equality_result(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric,
    rule: AnchorToleranceRule,
    delta: _NumericDelta,
) -> AnchorMetricComparison:
    if floats_exactly_equal(delta.expected, delta.observed):
        return _pass(reference, observation, rule, delta)
    return _fail(reference, observation, rule, delta, AnchorDiscrepancyReason.EXACT_MISMATCH)


def _relative_result(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric,
    rule: RelativeToleranceRule,
    delta: _NumericDelta,
) -> AnchorMetricComparison:
    if is_numeric_zero(delta.expected):
        return _build(
            reference,
            observation,
            rule,
            decision=AnchorComparisonDecision.UNAVAILABLE,
            reason=AnchorDiscrepancyReason.RELATIVE_COMPARISON_UNDEFINED_FOR_ZERO_REFERENCE,
            signed=delta.signed,
        )
    if delta.relative is not None and abs(delta.relative) <= rule.relative_tolerance.value:
        return _pass(reference, observation, rule, delta)
    return _fail(reference, observation, rule, delta, AnchorDiscrepancyReason.RELATIVE_TOLERANCE_EXCEEDED)


def _interval_result(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric,
    rule: IntervalOverlapRule,
    delta: _NumericDelta,
) -> AnchorMetricComparison:
    if reference.interval is None or observation.interval is None:
        return _build(
            reference,
            observation,
            rule,
            decision=AnchorComparisonDecision.UNAVAILABLE,
            reason=AnchorDiscrepancyReason.MISSING_MANDATORY_OBSERVATION,
            signed=delta.signed,
            relative=delta.relative,
        )
    left = reference.interval
    right = observation.interval
    lower_bound = max(left.lower.value, right.lower.value)
    upper_bound = min(left.upper.value, right.upper.value)
    overlaps = lower_bound < upper_bound or floats_exactly_equal(lower_bound, upper_bound)
    if overlaps:
        return _pass(reference, observation, rule, delta)
    return _fail(reference, observation, rule, delta, AnchorDiscrepancyReason.INTERVAL_NO_OVERLAP)


def _count_result(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric,
    rule: ExactCountRule,
    delta: _NumericDelta,
) -> AnchorMetricComparison:
    if reference.count is None or observation.count is None:
        return _build(
            reference,
            observation,
            rule,
            decision=AnchorComparisonDecision.UNAVAILABLE,
            reason=AnchorDiscrepancyReason.MISSING_MANDATORY_OBSERVATION,
            signed=delta.signed,
            relative=delta.relative,
        )
    if reference.count == observation.count:
        return _pass(reference, observation, rule, delta)
    return _build(
        reference,
        observation,
        rule,
        decision=AnchorComparisonDecision.MATERIAL_DISCREPANCY,
        reason=AnchorDiscrepancyReason.COUNT_MISMATCH,
        signed=float(observation.count.value - reference.count.value),
        relative=delta.relative,
    )


def _coordinate_mismatch_reason(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric,
) -> AnchorDiscrepancyReason | None:
    if observation.seed != reference.seed:
        return AnchorDiscrepancyReason.WRONG_SEED_SUBSET
    if observation.population is not reference.population:
        return AnchorDiscrepancyReason.WRONG_POPULATION
    if observation.training_model is not reference.training_model:
        return AnchorDiscrepancyReason.WRONG_TRAINING_MODEL
    if observation.threshold_method is not reference.threshold_method:
        return AnchorDiscrepancyReason.WRONG_THRESHOLD_METHOD
    if observation.metric is not reference.metric:
        return AnchorDiscrepancyReason.WRONG_METRIC
    if observation.checkpoint_status is not reference.checkpoint_status:
        return AnchorDiscrepancyReason.WRONG_CHECKPOINT_SEMANTICS
    return None


def _pass(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric,
    rule: AnchorToleranceRule,
    delta: _NumericDelta,
) -> AnchorMetricComparison:
    return _build(
        reference,
        observation,
        rule,
        decision=AnchorComparisonDecision.EQUIVALENT,
        signed=delta.signed,
        relative=delta.relative,
    )


def _fail(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric,
    rule: AnchorToleranceRule,
    delta: _NumericDelta,
    reason: AnchorDiscrepancyReason,
) -> AnchorMetricComparison:
    return _build(
        reference,
        observation,
        rule,
        decision=AnchorComparisonDecision.MATERIAL_DISCREPANCY,
        reason=reason,
        signed=delta.signed,
        relative=delta.relative,
    )


def _build(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric | None,
    rule: AnchorToleranceRule,
    *,
    decision: AnchorComparisonDecision,
    reason: AnchorDiscrepancyReason | None = None,
    signed: float | None = None,
    relative: float | None = None,
) -> AnchorMetricComparison:
    return AnchorMetricComparison(
        reference=reference,
        observation=observation,
        decision=decision,
        signed_difference=None if signed is None else MetricDelta(signed),
        relative_difference=None if relative is None else MetricDelta(relative),
        tolerance_rule=rule,
        reason=reason,
    )

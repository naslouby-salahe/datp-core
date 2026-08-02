"""Typed historical-anchor records, comparison identities, and gate decisions."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from pathlib import Path
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    CheckpointStatus,
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    TrainingModelId,
)
from datp_core.domain.values import Checksum, ClientCount, MetricValue, Seed, SeedCount
from datp_core.protocols.anchor import HISTORICAL_ANCHOR_SEED_COHORT
from datp_core.protocols.models import SeedCohort
from datp_core.protocols.populations import NBAIOT_NATURAL_DEVICES
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT


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


class AnchorGateStatus(StrEnum):
    PASS = "pass"
    PASS_WITH_DECLARED_DISCREPANCY = "pass_with_declared_discrepancy"
    BLOCKED = "blocked"


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


class AnchorDependencyKind(StrEnum):
    FEDERATED_TRAINING_CHECKPOINTING_AND_SCORING = "federated_training_checkpointing_and_scoring"
    HISTORICAL_ARTIFACT_ROOT = "historical_artifact_root"


def _str_enum_schema(cls, _source_type, _handler):
    """Pydantic v2 schema: validates raw str → cls, passes through existing members."""
    from pydantic_core import core_schema as _cs

    def _validate(v):
        if isinstance(v, cls):
            return v
        if not isinstance(v, str):
            raise TypeError(f"expected {cls.__name__} or str")
        return cls(v)

    return _cs.no_info_plain_validator_function(_validate)


class HistoricalThresholdScopeToken(StrEnum):
    """Semantic threshold-scope tokens stored in historical metrics artifacts."""

    ELIGIBLE_CLIENT_ARITHMETIC_MEAN = "eligible_client_arithmetic_mean"
    PER_CLIENT_PERCENTILE = "per_client_percentile"

    __get_pydantic_core_schema__ = classmethod(_str_enum_schema)


class HistoricalDatasetToken(StrEnum):
    NBAIOT = "nbaiot"

    __get_pydantic_core_schema__ = classmethod(_str_enum_schema)


class HistoricalRegimeToken(StrEnum):
    PHYSICAL_DEVICE_ANCHOR = "a"

    __get_pydantic_core_schema__ = classmethod(_str_enum_schema)


class AnchorArtifactFileName(StrEnum):
    """On-disk artifact file names used by historical load and stage diagnostics."""

    METRICS = "metrics.json"
    GATE_DECISION = "anchor_gate_decision.json"
    DISCREPANCIES = "anchor_discrepancies.json"


class AnchorSeedDirectoryPrefix(StrEnum):
    SEED = "seed_"


class HistoricalBoundaryModel(StrictModel):
    """External historical-artifact boundary. Extra legacy fields are ignored, never trusted."""

    model_config = ConfigDict(frozen=True, extra="ignore", strict=True)


class HistoricalArtifactProvenanceDocument(HistoricalBoundaryModel):
    model_checkpoint_identity: Checksum
    score_artifact_identity: Checksum
    split_manifest_identity: Checksum
    config_identity: Checksum
    metric_code_version: Checksum
    threshold_code_version: Checksum
    package_version: Checksum
    generated_at_utc: str


class HistoricalMetricsDocument(HistoricalBoundaryModel):
    """Boundary model for historical seed-level metrics artifacts."""

    seed: Seed
    dataset: HistoricalDatasetToken
    regime: HistoricalRegimeToken
    threshold_scope: HistoricalThresholdScopeToken
    cv_fpr: MetricValue
    client_count: ClientCount
    eligible_count: ClientCount
    provenance: HistoricalArtifactProvenanceDocument


ANCHOR_EXPERIMENT: ExperimentId = ExperimentId.HISTORICAL_DATP_REPRODUCTION
ANCHOR_POPULATION: PopulationId = PopulationId.NBAIOT_NATURAL_DEVICES
ANCHOR_TRAINING_MODEL: TrainingModelId = TrainingModelId.FEDAVG_AUTOENCODER
ANCHOR_METRIC: MetricId = MetricId.FPR_COEFFICIENT_OF_VARIATION
ANCHOR_CHECKPOINT_STATUS: CheckpointStatus = CheckpointStatus.HISTORICAL_ENDPOINT
ANCHOR_EVIDENCE_ROLE: EvidenceRole = EvidenceRole.ANCHOR_REPRODUCTION
ANCHOR_HISTORICAL_SEED_COUNT: SeedCount = HISTORICAL_ANCHOR_SEED_COHORT.member_count
CONFIRMATORY_PAIRED_SEED_COUNT: SeedCount = CONFIRMATORY_SEED_COHORT.member_count
HISTORICAL_ELIGIBLE_CLIENT_COUNT: ClientCount = NBAIOT_NATURAL_DEVICES.client_count

# No non-blocking discrepancy reasons are currently declared in the scientific source.
DECLARED_NON_BLOCKING_DISCREPANCY_REASONS: frozenset[AnchorDiscrepancyReason] = frozenset()


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
        if self.absolute_tolerance < 0:
            raise ValueError("absolute tolerance must be non-negative")
        return self


class RelativeToleranceRule(StrictModel):
    relative_tolerance: MetricValue
    strategy: Literal[AnchorComparisonStrategy.RELATIVE_TOLERANCE] = AnchorComparisonStrategy.RELATIVE_TOLERANCE

    @model_validator(mode="after")
    def validate_tolerance(self) -> "RelativeToleranceRule":
        if self.relative_tolerance <= 0:
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
    signed_difference: float | None
    relative_difference: float | None
    tolerance_rule: AnchorToleranceRule
    reason: AnchorDiscrepancyReason | None

    @model_validator(mode="after")
    def validate_finite(self) -> "AnchorMetricComparison":
        if self.signed_difference is not None and not isfinite(self.signed_difference):
            raise ValueError("signed difference must be finite when present")
        if self.relative_difference is not None and not isfinite(self.relative_difference):
            raise ValueError("relative difference must be finite when present")
        return self

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
    signed_difference: float | None = None
    relative_difference: float | None = None
    tolerance_rule: AnchorToleranceRule | None = None
    artifact_path: Path | None = None
    artifact_checksum: Checksum | None = None
    detail: str

    @field_validator("detail")
    @classmethod
    def validate_detail(cls, v: str) -> str:
        if not v:
            raise ValueError("discrepancy detail must be non-empty")
        return v

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


class AnchorDependencyBlocker(StrictModel):
    kind: AnchorDependencyKind
    detail: str

    @field_validator("detail")
    @classmethod
    def validate_detail(cls, v: str) -> str:
        if not v:
            raise ValueError("dependency blocker detail must be non-empty")
        return v


class AnchorReproductionResult(StrictModel):
    experiment: ExperimentId
    evidence_role: EvidenceRole
    seed_cohort: SeedCohort
    references: tuple[AnchorMetricReference, ...]
    observations: tuple[AnchorObservedMetric, ...]
    seed_subset_comparison: AnchorSeedSubsetComparison
    metric_comparisons: tuple[AnchorMetricComparison, ...]
    discrepancies: tuple[AnchorDiscrepancy, ...]
    dependency_blocker: AnchorDependencyBlocker | None = None

    @model_validator(mode="after")
    def validate_identity(self) -> "AnchorReproductionResult":
        if self.experiment is not ExperimentId.HISTORICAL_DATP_REPRODUCTION:
            raise ValueError("anchor reproduction requires the historical DATP reproduction experiment")
        if self.evidence_role is not EvidenceRole.ANCHOR_REPRODUCTION:
            raise ValueError("anchor reproduction requires the anchor_reproduction evidence role")
        return self


class AnchorGateDecision(StrictModel):
    status: AnchorGateStatus
    dependent_readiness: ExperimentReadiness
    reproduction: AnchorReproductionResult
    blocking_discrepancies: tuple[AnchorDiscrepancy, ...]
    declared_discrepancies: tuple[AnchorDiscrepancy, ...]

    @model_validator(mode="after")
    def validate_gate_integrity(self) -> "AnchorGateDecision":
        match self.status:
            case AnchorGateStatus.PASS:
                _require_clean_pass(self)
            case AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY:
                _require_declared_discrepancy_pass(self)
            case AnchorGateStatus.BLOCKED:
                _require_blocked_gate(self)
        return self


class HistoricalMetricArtifactSource(StrictModel):
    path: Path
    seed: Seed
    threshold_method: FederatedThresholdMethod

    @model_validator(mode="after")
    def validate_threshold_method(self) -> "HistoricalMetricArtifactSource":
        if self.threshold_method not in {
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
        }:
            raise ValueError("historical anchor artifacts support only shared and local thresholds")
        return self


# ---------------------------------------------------------------------------
# Gate integrity validators (package-private)
# ---------------------------------------------------------------------------


def _require_clean_pass(decision: AnchorGateDecision) -> None:
    if decision.blocking_discrepancies or decision.declared_discrepancies:
        raise ValueError("PASS forbids discrepancies")
    if decision.dependent_readiness is not ExperimentReadiness.DECLARED:
        raise ValueError("PASS permits only declared dependent readiness handoff")


def _require_declared_discrepancy_pass(decision: AnchorGateDecision) -> None:
    if decision.blocking_discrepancies or not decision.declared_discrepancies:
        raise ValueError("PASS_WITH_DECLARED_DISCREPANCY requires only declared discrepancies")
    if decision.dependent_readiness is not ExperimentReadiness.DECLARED:
        raise ValueError("declared-discrepancy pass still only unlocks declared dependent readiness")


def _require_blocked_gate(decision: AnchorGateDecision) -> None:
    if not decision.blocking_discrepancies and decision.reproduction.dependency_blocker is None:
        raise ValueError("BLOCKED requires blocking discrepancies or a dependency blocker")
    if decision.dependent_readiness is not ExperimentReadiness.BLOCKED:
        raise ValueError("blocked anchor gate must block dependent readiness")


def _require_anchor_coordinates(coordinates: AnchorScientificCoordinates) -> None:
    checks: tuple[tuple[bool, str], ...] = (
        (
            coordinates.population is not PopulationId.NBAIOT_NATURAL_DEVICES,
            "historical anchor coordinates require N-BaIoT natural devices",
        ),
        (
            coordinates.training_model is not TrainingModelId.FEDAVG_AUTOENCODER,
            "historical anchor coordinates require FedAvg autoencoder",
        ),
        (
            coordinates.threshold_method
            not in {
                FederatedThresholdMethod.SHARED_THRESHOLD,
                FederatedThresholdMethod.LOCAL_THRESHOLD,
            },
            "historical anchor coordinates support only shared and local thresholds",
        ),
        (
            coordinates.metric is not MetricId.FPR_COEFFICIENT_OF_VARIATION,
            "historical anchor coordinates require CV(FPR)",
        ),
        (
            coordinates.checkpoint_status is not CheckpointStatus.HISTORICAL_ENDPOINT,
            "historical anchor coordinates require historical endpoint checkpoint semantics",
        ),
    )
    for failed, message in checks:
        if failed:
            raise ValueError(message)

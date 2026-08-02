"""Typed historical-anchor records, comparison identities, and gate decisions."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from pathlib import Path

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


class HistoricalThresholdScopeToken(StrEnum):
    """Semantic threshold-scope tokens stored in historical metrics artifacts."""

    ELIGIBLE_CLIENT_ARITHMETIC_MEAN = "eligible_client_arithmetic_mean"
    PER_CLIENT_PERCENTILE = "per_client_percentile"


class HistoricalDatasetToken(StrEnum):
    NBAIOT = "nbaiot"


class HistoricalRegimeToken(StrEnum):
    PHYSICAL_DEVICE_ANCHOR = "a"


class AnchorArtifactFileName(StrEnum):
    """On-disk artifact file names used by historical load and stage diagnostics."""

    METRICS = "metrics.json"
    GATE_DECISION = "anchor_gate_decision.json"
    DISCREPANCIES = "anchor_discrepancies.json"


class AnchorSeedDirectoryPrefix(StrEnum):
    SEED = "seed_"


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


@dataclass(frozen=True, slots=True)
class ExactEqualityRule:
    strategy: AnchorComparisonStrategy = AnchorComparisonStrategy.EXACT_EQUALITY

    def __post_init__(self) -> None:
        if self.strategy is not AnchorComparisonStrategy.EXACT_EQUALITY:
            raise ValueError("exact equality rule requires exact_equality strategy")


@dataclass(frozen=True, slots=True)
class AbsoluteToleranceRule:
    absolute_tolerance: MetricValue
    strategy: AnchorComparisonStrategy = AnchorComparisonStrategy.ABSOLUTE_TOLERANCE

    def __post_init__(self) -> None:
        if self.strategy is not AnchorComparisonStrategy.ABSOLUTE_TOLERANCE:
            raise ValueError("absolute tolerance rule requires absolute_tolerance strategy")
        if self.absolute_tolerance < 0:
            raise ValueError("absolute tolerance must be non-negative")


@dataclass(frozen=True, slots=True)
class RelativeToleranceRule:
    relative_tolerance: MetricValue
    strategy: AnchorComparisonStrategy = AnchorComparisonStrategy.RELATIVE_TOLERANCE

    def __post_init__(self) -> None:
        if self.strategy is not AnchorComparisonStrategy.RELATIVE_TOLERANCE:
            raise ValueError("relative tolerance rule requires relative_tolerance strategy")
        if self.relative_tolerance <= 0:
            raise ValueError("relative tolerance must be positive")


@dataclass(frozen=True, slots=True)
class IntervalOverlapRule:
    strategy: AnchorComparisonStrategy = AnchorComparisonStrategy.INTERVAL_OVERLAP

    def __post_init__(self) -> None:
        if self.strategy is not AnchorComparisonStrategy.INTERVAL_OVERLAP:
            raise ValueError("interval overlap rule requires interval_overlap strategy")


@dataclass(frozen=True, slots=True)
class ExactCountRule:
    strategy: AnchorComparisonStrategy = AnchorComparisonStrategy.EXACT_COUNT

    def __post_init__(self) -> None:
        if self.strategy is not AnchorComparisonStrategy.EXACT_COUNT:
            raise ValueError("exact count rule requires exact_count strategy")


@dataclass(frozen=True, slots=True)
class SourceDefinedRule:
    description: str
    strategy: AnchorComparisonStrategy = AnchorComparisonStrategy.SOURCE_DEFINED

    def __post_init__(self) -> None:
        if self.strategy is not AnchorComparisonStrategy.SOURCE_DEFINED:
            raise ValueError("source-defined rule requires source_defined strategy")
        if not isinstance(self.description, str) or not self.description:
            raise ValueError("source-defined rule requires a non-empty description")


type AnchorToleranceRule = (
    ExactEqualityRule
    | AbsoluteToleranceRule
    | RelativeToleranceRule
    | IntervalOverlapRule
    | ExactCountRule
    | SourceDefinedRule
)


@dataclass(frozen=True, slots=True)
class MetricInterval:
    lower: MetricValue
    upper: MetricValue

    def __post_init__(self) -> None:
        if self.lower > self.upper:
            raise ValueError("metric interval lower bound cannot exceed upper bound")


@dataclass(frozen=True, slots=True)
class AnchorScientificCoordinates:
    population: PopulationId
    training_model: TrainingModelId
    threshold_method: FederatedThresholdMethod
    metric: MetricId
    checkpoint_status: CheckpointStatus


@dataclass(frozen=True, slots=True)
class AnchorMetricReference:
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

    def __post_init__(self) -> None:
        _require_anchor_coordinates(
            AnchorScientificCoordinates(
                population=self.population,
                training_model=self.training_model,
                threshold_method=self.threshold_method,
                metric=self.metric,
                checkpoint_status=self.checkpoint_status,
            )
        )


@dataclass(frozen=True, slots=True)
class AnchorObservedMetric:
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

    def __post_init__(self) -> None:
        if self.evidence_role is not EvidenceRole.ANCHOR_REPRODUCTION:
            raise ValueError("anchor observations must use the anchor_reproduction evidence role")
        if not isinstance(self.artifact_path, Path):
            raise TypeError("artifact path must be a Path")


@dataclass(frozen=True, slots=True)
class AnchorMetricComparison:
    reference: AnchorMetricReference
    observation: AnchorObservedMetric | None
    decision: AnchorComparisonDecision
    signed_difference: float | None
    relative_difference: float | None
    tolerance_rule: AnchorToleranceRule
    reason: AnchorDiscrepancyReason | None

    def __post_init__(self) -> None:
        if self.signed_difference is not None and not isfinite(self.signed_difference):
            raise ValueError("signed difference must be finite when present")
        if self.relative_difference is not None and not isfinite(self.relative_difference):
            raise ValueError("relative difference must be finite when present")


@dataclass(frozen=True, slots=True)
class AnchorSeedSubsetComparison:
    expected_seeds: tuple[Seed, ...]
    observed_seeds: tuple[Seed, ...]
    decision: AnchorComparisonDecision
    reason: AnchorDiscrepancyReason | None

    def __post_init__(self) -> None:
        if not isinstance(self.expected_seeds, tuple) or not isinstance(self.observed_seeds, tuple):
            raise TypeError("seed subsets must be immutable tuples")


@dataclass(frozen=True, slots=True)
class AnchorDiscrepancy:
    reason: AnchorDiscrepancyReason
    seed: Seed | None
    threshold_method: FederatedThresholdMethod | None
    metric: MetricId | None
    expected_value: MetricValue | None
    observed_value: MetricValue | None
    signed_difference: float | None
    relative_difference: float | None
    tolerance_rule: AnchorToleranceRule | None
    artifact_path: Path | None
    artifact_checksum: Checksum | None
    detail: str

    def __post_init__(self) -> None:
        if not isinstance(self.detail, str) or not self.detail:
            raise ValueError("discrepancy detail must be non-empty")


@dataclass(frozen=True, slots=True)
class AnchorDependencyBlocker:
    kind: AnchorDependencyKind
    detail: str

    def __post_init__(self) -> None:
        if not isinstance(self.detail, str) or not self.detail:
            raise ValueError("dependency blocker detail must be non-empty")


@dataclass(frozen=True, slots=True)
class AnchorReproductionResult:
    experiment: ExperimentId
    evidence_role: EvidenceRole
    seed_cohort: SeedCohort
    references: tuple[AnchorMetricReference, ...]
    observations: tuple[AnchorObservedMetric, ...]
    seed_subset_comparison: AnchorSeedSubsetComparison
    metric_comparisons: tuple[AnchorMetricComparison, ...]
    discrepancies: tuple[AnchorDiscrepancy, ...]
    dependency_blocker: AnchorDependencyBlocker | None

    def __post_init__(self) -> None:
        if self.experiment is not ExperimentId.HISTORICAL_DATP_REPRODUCTION:
            raise ValueError("anchor reproduction requires the historical DATP reproduction experiment")
        if self.evidence_role is not EvidenceRole.ANCHOR_REPRODUCTION:
            raise ValueError("anchor reproduction requires the anchor_reproduction evidence role")
        if not isinstance(self.references, tuple) or not isinstance(self.observations, tuple):
            raise TypeError("references and observations must be immutable tuples")
        if not isinstance(self.metric_comparisons, tuple) or not isinstance(self.discrepancies, tuple):
            raise TypeError("comparisons and discrepancies must be immutable tuples")


@dataclass(frozen=True, slots=True)
class AnchorGateDecision:
    status: AnchorGateStatus
    dependent_readiness: ExperimentReadiness
    reproduction: AnchorReproductionResult
    blocking_discrepancies: tuple[AnchorDiscrepancy, ...]
    declared_discrepancies: tuple[AnchorDiscrepancy, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.blocking_discrepancies, tuple) or not isinstance(self.declared_discrepancies, tuple):
            raise TypeError("gate discrepancy collections must be immutable tuples")
        match self.status:
            case AnchorGateStatus.PASS:
                _require_clean_pass(self)
            case AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY:
                _require_declared_discrepancy_pass(self)
            case AnchorGateStatus.BLOCKED:
                _require_blocked_gate(self)


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


@dataclass(frozen=True, slots=True)
class HistoricalMetricArtifactSource:
    path: Path
    seed: Seed
    threshold_method: FederatedThresholdMethod

    def __post_init__(self) -> None:
        if self.threshold_method not in {
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
        }:
            raise ValueError("historical anchor artifacts support only shared and local thresholds")
        if not isinstance(self.path, Path):
            raise TypeError("historical artifact path must be a Path")


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

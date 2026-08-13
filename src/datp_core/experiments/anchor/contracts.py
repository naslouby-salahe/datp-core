from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
from datp_core.core.contracts import StrictModel, str_enum_schema
from datp_core.core.errors import (
    ErrorMessage,
    require_contract,
)
from datp_core.core.identifiers import (
    ArtifactDirectoryPathText,
    ContractSubject,
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    MetricId,
    NonEmptyString,
    PopulationId,
    PreprocessingProtocolId,
    Sha256Digest,
    SourceRuleDescription,
    SplitProtocolId,
    TrainingModelId,
    UtcInstantText,
)
from datp_core.core.numeric import ClientCount, MetricDelta, MetricValue, Seed
from datp_core.experiments.common.seeds import SeedCohort


class AnchorDetail(NonEmptyString):
    pass


class AnchorComparisonStrategy(StrEnum):
    EXACT_EQUALITY = "exact_equality"
    ABSOLUTE_TOLERANCE = "absolute_tolerance"
    RELATIVE_TOLERANCE = "relative_tolerance"
    INTERVAL_OVERLAP = "interval_overlap"
    EXACT_COUNT = "exact_count"
    SOURCE_DEFINED = "source_defined"
    DIAGNOSTIC = "diagnostic"


class AnchorComparisonDecision(StrEnum):
    EQUIVALENT = "equivalent"
    ACCEPTABLE_DECLARED_DEVIATION = "acceptable_declared_deviation"
    MATERIAL_DISCREPANCY = "material_discrepancy"
    UNAVAILABLE = "unavailable"
    BLOCKED_INVALID_INPUT = "blocked_invalid_input"
    DIAGNOSTIC_REPORTED = "diagnostic_reported"


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
    STALE_OR_MISMATCHED_ARTIFACT = "stale_or_mismatched_artifact"
    UNSUPPORTED_GLOBAL_TOLERANCE = "unsupported_global_tolerance"
    MISSING_TOLERANCE_RULE = "missing_tolerance_rule"
    DEPENDENCY_BLOCKER = "dependency_blocker"
    ROUNDED_EQUALITY_CANNOT_OVERRIDE_FULL_PRECISION_FAILURE = "rounded_equality_cannot_override_full_precision_failure"
    BCA_INTERVAL_UNAVAILABLE = "bca_interval_unavailable"
    BCA_INTERVAL_NOT_ENTIRELY_POSITIVE = "bca_interval_not_entirely_positive"
    BCA_INTERVAL_DOES_NOT_OVERLAP_REFERENCE = "bca_interval_does_not_overlap_reference"
    BCA_INTERVAL_WIDTH_EXCEEDS_MAXIMUM = "bca_interval_width_exceeds_maximum"


class ExactEqualityRule(StrictModel):
    strategy: Literal[AnchorComparisonStrategy.EXACT_EQUALITY] = AnchorComparisonStrategy.EXACT_EQUALITY


class AbsoluteToleranceRule(StrictModel):
    absolute_tolerance: MetricValue
    strategy: Literal[AnchorComparisonStrategy.ABSOLUTE_TOLERANCE] = AnchorComparisonStrategy.ABSOLUTE_TOLERANCE

    @model_validator(mode="after")
    def validate_tolerance(self) -> AbsoluteToleranceRule:
        if self.absolute_tolerance.value < 0:
            raise ValueError("absolute tolerance must be non-negative")
        return self


class RelativeToleranceRule(StrictModel):
    relative_tolerance: MetricValue
    strategy: Literal[AnchorComparisonStrategy.RELATIVE_TOLERANCE] = AnchorComparisonStrategy.RELATIVE_TOLERANCE

    @model_validator(mode="after")
    def validate_tolerance(self) -> RelativeToleranceRule:
        if self.relative_tolerance.value <= 0:
            raise ValueError("relative tolerance must be positive")
        return self


class IntervalOverlapRule(StrictModel):
    strategy: Literal[AnchorComparisonStrategy.INTERVAL_OVERLAP] = AnchorComparisonStrategy.INTERVAL_OVERLAP


class ExactCountRule(StrictModel):
    strategy: Literal[AnchorComparisonStrategy.EXACT_COUNT] = AnchorComparisonStrategy.EXACT_COUNT


class SourceDefinedRule(StrictModel):
    description: SourceRuleDescription
    strategy: Literal[AnchorComparisonStrategy.SOURCE_DEFINED] = AnchorComparisonStrategy.SOURCE_DEFINED


class DiagnosticRule(StrictModel):
    strategy: Literal[AnchorComparisonStrategy.DIAGNOSTIC] = AnchorComparisonStrategy.DIAGNOSTIC


AnchorToleranceRule = Annotated[
    ExactEqualityRule
    | AbsoluteToleranceRule
    | RelativeToleranceRule
    | IntervalOverlapRule
    | ExactCountRule
    | SourceDefinedRule
    | DiagnosticRule,
    Field(discriminator="strategy"),
]


class MetricInterval(StrictModel):
    lower: MetricValue
    upper: MetricValue

    @model_validator(mode="after")
    def validate_bounds(self) -> MetricInterval:
        if self.lower > self.upper:
            raise ValueError("metric interval lower bound cannot exceed upper bound")
        return self


@dataclass(frozen=True, slots=True)
class AnchorScientificCoordinates:
    population: PopulationId
    training_model: TrainingModelId
    threshold_method: FederatedThresholdMethod
    metric: MetricId


_HISTORICAL_THRESHOLDS = frozenset(
    {
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    }
)


def _require_anchor_coordinates(coordinates: AnchorScientificCoordinates) -> None:
    require_contract(
        coordinates.population is PopulationId.NBAIOT_NATURAL_DEVICES,
        ErrorMessage("historical anchor coordinates require N-BaIoT natural devices"),
        ContractSubject.COORDINATE,
    )
    require_contract(
        coordinates.training_model is TrainingModelId.FEDAVG_AUTOENCODER,
        ErrorMessage("historical anchor coordinates require FedAvg autoencoder"),
        ContractSubject.COORDINATE,
    )
    require_contract(
        coordinates.threshold_method in _HISTORICAL_THRESHOLDS,
        ErrorMessage("historical anchor coordinates support only shared and local thresholds"),
        ContractSubject.COORDINATE,
    )
    require_contract(
        coordinates.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION,
        ErrorMessage("historical anchor coordinates require CV(FPR)"),
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
    interval: MetricInterval | None = None
    count: ClientCount | None = None

    @model_validator(mode="after")
    def validate_coordinates(self) -> AnchorMetricReference:
        _require_anchor_coordinates(
            AnchorScientificCoordinates(
                population=self.population,
                training_model=self.training_model,
                threshold_method=self.threshold_method,
                metric=self.metric,
            )
        )
        return self


class AnchorObservedMetric(StrictModel):
    seed: Seed
    population: PopulationId
    training_model: TrainingModelId
    threshold_method: FederatedThresholdMethod
    metric: MetricId
    value: MetricValue
    source_kind: AnchorObservationSourceKind
    artifact_path: Path
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
    def detail(self) -> AnchorDetail:
        reference = self.reference
        observation = self.observation
        observed = None if observation is None else observation.value.value
        reason = None if self.reason is None else self.reason.value

        return AnchorDetail(
            f"seed={reference.seed.value} "
            f"method={reference.threshold_method.value} "
            f"metric={reference.metric.value} "
            f"expected={reference.value.value!r} observed={observed!r} "
            f"decision={self.decision.value} "
            f"reason={reason}"
        )


class AnchorSeedSubsetComparison(StrictModel):
    expected_seeds: tuple[Seed, ...]
    observed_seeds: tuple[Seed, ...]
    decision: AnchorComparisonDecision
    reason: AnchorDiscrepancyReason | None


class AnchorBcaComparison(StrictModel):
    interval: BootstrapInterval
    reference_interval: MetricInterval
    maximum_operative_width: MetricValue
    decision: AnchorComparisonDecision
    reason: AnchorDiscrepancyReason | None

    @model_validator(mode="after")
    def validate_decision(self) -> AnchorBcaComparison:
        if (self.decision is AnchorComparisonDecision.EQUIVALENT) != (self.reason is None):
            raise ValueError("an equivalent BCa comparison must carry no discrepancy reason")
        return self


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
    detail: AnchorDetail

    @classmethod
    def from_seed_subset(cls, seed_subset: AnchorSeedSubsetComparison) -> AnchorDiscrepancy:
        return cls(
            reason=seed_subset.reason or AnchorDiscrepancyReason.WRONG_SEED_SUBSET,
            detail=AnchorDetail(
                f"expected seeds {[seed.value for seed in seed_subset.expected_seeds]}; "
                f"observed seeds {[seed.value for seed in seed_subset.observed_seeds]}"
            ),
        )

    @classmethod
    def from_comparison(cls, comparison: AnchorMetricComparison) -> AnchorDiscrepancy:
        observation = comparison.observation
        reference = comparison.reference
        return cls(
            reason=comparison.reason or AnchorDiscrepancyReason.EXACT_MISMATCH,
            seed=reference.seed,
            threshold_method=reference.threshold_method,
            metric=reference.metric,
            expected_value=reference.value,
            observed_value=None if observation is None else observation.value,
            signed_difference=comparison.signed_difference,
            relative_difference=comparison.relative_difference,
            tolerance_rule=comparison.tolerance_rule,
            artifact_path=None if observation is None else observation.artifact_path,
            detail=comparison.detail,
        )

    @classmethod
    def from_dependency_blocker(cls, blocker: AnchorDependencyBlocker) -> AnchorDiscrepancy:
        return cls(
            reason=AnchorDiscrepancyReason.DEPENDENCY_BLOCKER,
            detail=blocker.detail,
        )

    @classmethod
    def from_bca_comparison(cls, comparison: AnchorBcaComparison) -> AnchorDiscrepancy:
        interval = comparison.interval
        lower = None if interval.lower_bound is None else interval.lower_bound.value
        upper = None if interval.upper_bound is None else interval.upper_bound.value
        reference = comparison.reference_interval
        return cls(
            reason=comparison.reason or AnchorDiscrepancyReason.BCA_INTERVAL_UNAVAILABLE,
            detail=AnchorDetail(
                f"reproduced BCa interval outcome={interval.outcome.value} lower={lower!r} upper={upper!r}; "
                f"reference=[{reference.lower.value},{reference.upper.value}] "
                f"maximum_operative_width={comparison.maximum_operative_width.value!r}"
            ),
        )


class AnchorGateStatus(StrEnum):
    PASS = "pass"
    PASS_WITH_DECLARED_DISCREPANCY = "pass_with_declared_discrepancy"
    ANCHOR_REPRODUCTION_FAILED = "anchor_reproduction_failed"


_PERMITTING_GATE_STATUSES = frozenset(
    {
        AnchorGateStatus.PASS,
        AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY,
    }
)


class AnchorGateDecision(StrictModel):
    status: AnchorGateStatus
    dependent_readiness: ExperimentReadiness
    reproduction: AnchorReproductionResult
    blocking_discrepancies: tuple[AnchorDiscrepancy, ...]
    declared_discrepancies: tuple[AnchorDiscrepancy, ...]

    @model_validator(mode="after")
    def validate_gate_integrity(self) -> AnchorGateDecision:
        match self.status:
            case AnchorGateStatus.PASS:
                _require_clean_pass(self)
            case AnchorGateStatus.PASS_WITH_DECLARED_DISCREPANCY:
                _require_declared_discrepancy_pass(self)
            case AnchorGateStatus.ANCHOR_REPRODUCTION_FAILED:
                _require_blocked_gate(self)
        return self


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


class VerifiedAnchorGateArtifact(StrictModel):
    decision: AnchorGateDecision
    diagnostics_directory: ArtifactDirectoryPathText

    @model_validator(mode="after")
    def validate_passed_gate(self) -> VerifiedAnchorGateArtifact:
        if self.decision.status is AnchorGateStatus.ANCHOR_REPRODUCTION_FAILED:
            raise ValueError("verified anchor-gate artifact cannot be blocked")
        return self

    @property
    def permits_confirmatory_claims(self) -> bool:
        return self.decision.status in _PERMITTING_GATE_STATUSES


class AnchorConfirmatoryHandoff(StrictModel):
    anchor_experiment: ExperimentId
    anchor_seed_cohort: SeedCohort
    dependent_confirmatory_experiment: ExperimentId
    dependent_population: PopulationId
    dependent_model: TrainingModelId
    dependent_seed_cohort: SeedCohort
    split_protocol_identity: SplitProtocolId
    preprocessing_protocol_identity: PreprocessingProtocolId
    threshold_protocol_identities: tuple[FederatedThresholdMethod, ...]
    verified_gate_status: AnchorGateStatus
    diagnostics_directory: ArtifactDirectoryPathText
    gate_decision_sha256: Sha256Digest

    @model_validator(mode="after")
    def validate_handoff_integrity(self) -> AnchorConfirmatoryHandoff:
        if self.anchor_experiment is not ExperimentId.HISTORICAL_DATP_REPRODUCTION:
            raise ValueError("handoff anchor experiment must be historical DATP reproduction")
        if self.dependent_confirmatory_experiment is not ExperimentId.SHARED_VS_LOCAL_CONFIRMATION:
            raise ValueError("handoff dependent experiment must be shared-vs-local confirmation")
        if self.verified_gate_status is AnchorGateStatus.ANCHOR_REPRODUCTION_FAILED:
            raise ValueError("confirmatory handoff cannot bind a blocked gate")
        if self.verified_gate_status not in _PERMITTING_GATE_STATUSES:
            raise ValueError("confirmatory handoff requires a permitting gate status")
        if not self.threshold_protocol_identities:
            raise ValueError("handoff requires at least one threshold protocol identity")
        return self


class AnchorDependencyKind(StrEnum):
    FEDERATED_TRAINING_AND_SCORING = "federated_training_and_scoring"
    HISTORICAL_ARTIFACT_ROOT = "historical_artifact_root"


class HistoricalThresholdScopeToken(StrEnum):
    ELIGIBLE_CLIENT_ARITHMETIC_MEAN = "eligible_client_arithmetic_mean"
    PER_CLIENT_PERCENTILE = "per_client_percentile"

    __get_pydantic_core_schema__ = classmethod(str_enum_schema)

    def to_threshold_method(self) -> FederatedThresholdMethod:
        if self is HistoricalThresholdScopeToken.ELIGIBLE_CLIENT_ARITHMETIC_MEAN:
            return FederatedThresholdMethod.SHARED_THRESHOLD
        return FederatedThresholdMethod.LOCAL_THRESHOLD


class HistoricalDatasetToken(StrEnum):
    NBAIOT = "nbaiot"

    __get_pydantic_core_schema__ = classmethod(str_enum_schema)


class HistoricalRegimeToken(StrEnum):
    PHYSICAL_DEVICE_ANCHOR = "a"

    __get_pydantic_core_schema__ = classmethod(str_enum_schema)


class AnchorArtifactFileName(StrEnum):
    METRICS = "metrics.json"
    GATE_DECISION = "anchor_gate_decision.json"
    DISCREPANCIES = "anchor_discrepancies.json"
    CONFIRMATORY_HANDOFF = "anchor_confirmatory_handoff.json"


class AnchorSeedDirectoryPrefix(StrEnum):
    SEED = "seed_"


class HistoricalBoundaryModel(StrictModel):
    model_config = ConfigDict(frozen=True, extra="ignore", strict=True)


class HistoricalArtifactProvenanceDocument(HistoricalBoundaryModel):
    generated_at_utc: UtcInstantText


class HistoricalMetricsDocument(HistoricalBoundaryModel):
    seed: Seed
    dataset: HistoricalDatasetToken
    regime: HistoricalRegimeToken
    threshold_scope: HistoricalThresholdScopeToken
    cv_fpr: MetricValue
    client_count: ClientCount
    eligible_count: ClientCount
    provenance: HistoricalArtifactProvenanceDocument


class AnchorDependencyBlocker(StrictModel):
    kind: AnchorDependencyKind
    detail: AnchorDetail


class AnchorReproductionResult(StrictModel):
    experiment: ExperimentId
    evidence_role: EvidenceRole
    seed_cohort: SeedCohort
    references: tuple[AnchorMetricReference, ...]
    observations: tuple[AnchorObservedMetric, ...]
    seed_subset_comparison: AnchorSeedSubsetComparison
    metric_comparisons: tuple[AnchorMetricComparison, ...]
    bca_comparison: AnchorBcaComparison
    discrepancies: tuple[AnchorDiscrepancy, ...]
    dependency_blocker: AnchorDependencyBlocker | None = None

    @model_validator(mode="after")
    def validate_identity(self) -> AnchorReproductionResult:
        if self.experiment is not ExperimentId.HISTORICAL_DATP_REPRODUCTION:
            raise ValueError("anchor reproduction requires the historical DATP reproduction experiment")
        if self.evidence_role is not EvidenceRole.ANCHOR_REPRODUCTION:
            raise ValueError("anchor reproduction requires the anchor_reproduction evidence role")
        return self


class HistoricalMetricArtifactSource(StrictModel):
    path: Path
    seed: Seed
    threshold_method: FederatedThresholdMethod

    @model_validator(mode="after")
    def validate_threshold_method(self) -> HistoricalMetricArtifactSource:
        if self.threshold_method not in _HISTORICAL_THRESHOLDS:
            raise ValueError("historical anchor artifacts support only shared and local thresholds")
        return self

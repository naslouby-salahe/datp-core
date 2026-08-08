"""Typed anchor-domain models: comparison records, gate decision records, and historical reproduction records."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from datp_core.artifacts.provenance import Checksum, checksum_text
from datp_core.artifacts.serializers.json import canonical_checksum, canonical_json_text
from datp_core.core.contracts import StrictModel, str_enum_schema
from datp_core.core.identifiers import (
    CheckpointStatus,
    ContractSubject,
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.core.errors import require_contract
from datp_core.core.identifiers import NonEmptyString
from datp_core.core.numeric import ClientCount, MetricDelta, MetricValue, Seed
from datp_core.experiments.common.seeds import SeedCohort


class AnchorDetail(NonEmptyString):
    def __new__(cls, value: str) -> AnchorDetail:
        return super().__new__(cls, value)


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
    checkpoint_status: CheckpointStatus


_HISTORICAL_THRESHOLDS = frozenset(
    {
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    }
)


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
        coordinates.threshold_method in _HISTORICAL_THRESHOLDS,
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
    def validate_coordinates(self) -> AnchorMetricReference:
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
            artifact_checksum=None if observation is None else observation.artifact_checksum,
            detail=comparison.detail,
        )

    @classmethod
    def from_dependency_blocker(cls, blocker: AnchorDependencyBlocker) -> AnchorDiscrepancy:
        return cls(
            reason=AnchorDiscrepancyReason.DEPENDENCY_BLOCKER,
            detail=blocker.detail,
        )


class AnchorGateStatus(StrEnum):
    PASS = "pass"
    PASS_WITH_DECLARED_DISCREPANCY = "pass_with_declared_discrepancy"
    BLOCKED = "blocked"


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
            case AnchorGateStatus.BLOCKED:
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


class AnchorGateCompletionMarker(StrictModel):
    artifact_checksum: Checksum
    status: AnchorGateStatus


class VerifiedAnchorGateArtifact(StrictModel):
    """Checksum-verified anchor-gate artifact that claim export must consume."""

    decision: AnchorGateDecision
    artifact_checksum: Checksum
    diagnostics_directory: str

    @model_validator(mode="after")
    def validate_passed_gate(self) -> VerifiedAnchorGateArtifact:
        if self.decision.status is AnchorGateStatus.BLOCKED:
            raise ValueError("verified anchor-gate artifact cannot be blocked")
        recomputed = checksum_text(canonical_json_text(self.decision))
        if recomputed != self.artifact_checksum:
            raise ValueError("anchor-gate artifact checksum does not match the decision payload")
        return self

    @property
    def permits_confirmatory_claims(self) -> bool:
        return self.decision.status in _PERMITTING_GATE_STATUSES


class AnchorConfirmatoryHandoff(StrictModel):
    """Typed anchor→confirmatory binding artifact that locks programme identity."""

    creation_identity: Checksum
    anchor_experiment: ExperimentId
    anchor_seed_cohort: SeedCohort
    anchor_protocol_checksum: Checksum
    anchor_references_observations_checksum: Checksum
    anchor_gate_decision_checksum: Checksum
    dependent_confirmatory_experiment: ExperimentId
    dependent_population: PopulationId
    dependent_model: TrainingModelId
    dependent_seed_cohort: SeedCohort
    split_protocol_identity: SplitProtocolId
    preprocessing_protocol_identity: PreprocessingProtocolId
    checkpoint_protocol_identity: Checksum
    scoring_protocol_identity: Checksum
    threshold_protocol_identities: tuple[FederatedThresholdMethod, ...]
    evaluation_protocol_identity: Checksum
    confirmatory_inference_protocol_identity: Checksum
    complete_artifact_inventory_checksum: Checksum
    verified_gate_status: AnchorGateStatus
    verified_gate_artifact_checksum: Checksum
    diagnostics_directory: str

    @model_validator(mode="after")
    def validate_handoff_integrity(self) -> AnchorConfirmatoryHandoff:
        if self.anchor_experiment is not ExperimentId.HISTORICAL_DATP_REPRODUCTION:
            raise ValueError("handoff anchor experiment must be historical DATP reproduction")
        if self.dependent_confirmatory_experiment is not ExperimentId.SHARED_VS_LOCAL_CONFIRMATION:
            raise ValueError("handoff dependent experiment must be shared-vs-local confirmation")
        if self.verified_gate_status is AnchorGateStatus.BLOCKED:
            raise ValueError("confirmatory handoff cannot bind a blocked gate")
        if self.verified_gate_status not in _PERMITTING_GATE_STATUSES:
            raise ValueError("confirmatory handoff requires a permitting gate status")
        if self.anchor_gate_decision_checksum != self.verified_gate_artifact_checksum:
            raise ValueError("handoff gate decision checksum must match verified gate artifact checksum")
        if not self.threshold_protocol_identities:
            raise ValueError("handoff requires at least one threshold protocol identity")
        if not self.diagnostics_directory.strip():
            raise ValueError("handoff diagnostics directory must be non-empty")
        recomputed = _handoff_creation_identity(self)
        if recomputed != self.creation_identity:
            raise ValueError("handoff creation identity does not match the binding payload")
        return self


_HANDOFF_PAYLOAD_FIELDS = tuple(name for name in AnchorConfirmatoryHandoff.model_fields if name != "creation_identity")


def _handoff_creation_identity(handoff: AnchorConfirmatoryHandoff) -> Checksum:
    payload = {name: getattr(handoff, name) for name in _HANDOFF_PAYLOAD_FIELDS}
    return canonical_checksum(payload)


class AnchorDependencyKind(StrEnum):
    FEDERATED_TRAINING_CHECKPOINTING_AND_SCORING = "federated_training_checkpointing_and_scoring"
    HISTORICAL_ARTIFACT_ROOT = "historical_artifact_root"


class HistoricalThresholdScopeToken(StrEnum):
    """Semantic threshold-scope tokens stored in historical metrics artifacts."""

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
    """On-disk artifact file names used by historical load and stage diagnostics."""

    METRICS = "metrics.json"
    GATE_DECISION = "anchor_gate_decision.json"
    DISCREPANCIES = "anchor_discrepancies.json"
    GATE_COMPLETION = "anchor_gate_complete.json"
    CONFIRMATORY_HANDOFF = "anchor_confirmatory_handoff.json"


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

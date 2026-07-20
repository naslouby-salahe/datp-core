"""Pure resolved experiment catalogue records."""

from __future__ import annotations

from enum import Enum

from attrs import define, field

from datp_core.domain.fingerprints import Fingerprint
from datp_core.domain.identifiers import (
    CheckpointProfileId,
    DatasetId,
    DatasetSetupId,
    EligibilityPolicyId,
    ExperimentId,
    MetricBundleId,
    PopulationId,
    SeedCohortId,
    StatisticalProfileId,
    ThresholdPolicyId,
    TrainingProfileId,
)
from datp_core.domain.values import PositiveInt, Probability, Seed, TypedDomainRegistry


class EvidenceRole(Enum):
    ANCHOR = "anchor"
    CONFIRMATORY = "confirmatory"
    SENSITIVITY = "sensitivity"
    EXPLORATORY = "exploratory"
    STRESS_TEST = "stress_test"
    COMPARATOR = "comparator"
    MECHANISM = "mechanism"
    SUPPORTIVE = "supportive"
    BOUNDARY = "boundary"
    EXTERNAL_VALIDATION = "external_validation"


class RunRequirement(Enum):
    MANDATORY = "mandatory"
    CONDITIONAL = "conditional"
    EXPLORATORY = "exploratory"
    OPTIONAL = "optional"


@define(frozen=True, slots=True, kw_only=True)
class TrainingProfileRecord:
    identifier: TrainingProfileId
    kind: str
    model_architecture_id: str
    optimizer_id: str
    batching_profile_id: str
    local_epochs: PositiveInt | None
    participation: str | None
    checkpoint_authorization: str
    personalization: str | None
    federation: FederationProfileRecord | None


@define(frozen=True, slots=True, kw_only=True)
class FederationProfileRecord:
    """Pure resolved Flower participation contract."""

    fraction_fit: float
    fraction_evaluate: float
    minimum_fit_clients: PositiveInt
    minimum_evaluate_clients: PositiveInt
    minimum_available_clients: PositiveInt


@define(frozen=True, slots=True, kw_only=True)
class CheckpointProfileRecord:
    identifier: CheckpointProfileId
    total_rounds: PositiveInt | None
    selected_rounds: tuple[PositiveInt, ...]
    early_stopping: str
    selection_rule: str


@define(frozen=True, slots=True, kw_only=True)
class SeedCohortRecord:
    identifier: SeedCohortId
    paired_seed_count: PositiveInt
    training_seeds: tuple[Seed, ...]
    bootstrap_analysis_seed: Seed
    analysis_seed_model: str


@define(frozen=True, slots=True, kw_only=True)
class StatisticalProfileRecord:
    """Resolved, executable statistical analysis contract."""

    identifier: StatisticalProfileId
    method: str | None
    confidence_level: Probability | None
    resample_count: PositiveInt | None
    minimum_units: PositiveInt | None


@define(frozen=True, slots=True, kw_only=True)
class CapabilityRequirementRecord:
    capability: str
    when_unavailable: str


@define(frozen=True, slots=True, kw_only=True)
class EvaluationSpecRecord:
    label: str
    threshold_policy_id: ThresholdPolicyId
    run_requirement: RunRequirement


@define(frozen=True, slots=True, kw_only=True)
class AnalysisSpecRecord:
    label: str
    kind: str
    result_type: str
    primary_metric: str | None
    statistical_profile: str | None


@define(frozen=True, slots=True, kw_only=True)
class SweepRecord:
    name: str
    values: tuple[str | int | float, ...]


@define(frozen=True, slots=True, kw_only=True)
class PopulationRecord:
    identifier: PopulationId
    dataset_id: DatasetId
    setup_id: DatasetSetupId
    metric_bundle_id: MetricBundleId


@define(frozen=True, slots=True, kw_only=True)
class ExperimentRecord:
    identifier: ExperimentId
    display_name: str
    evidence_role: EvidenceRole
    run_requirement: RunRequirement
    population_ids: tuple[PopulationId, ...]
    training_profile_id: TrainingProfileId
    checkpoint_profile_id: CheckpointProfileId
    seed_cohort_id: SeedCohortId
    eligibility_policy_id: EligibilityPolicyId
    prerequisite_ids: tuple[ExperimentId, ...]
    capability_requirements: tuple[CapabilityRequirementRecord, ...]
    evaluations: tuple[EvaluationSpecRecord, ...]
    analyses: tuple[AnalysisSpecRecord, ...]
    report_ids: tuple[str, ...]
    sweeps: tuple[SweepRecord, ...] = field(factory=tuple)


@define(frozen=True, slots=True, kw_only=True)
class ResolvedCatalogue:
    schema_version: PositiveInt
    populations: TypedDomainRegistry[PopulationId, PopulationRecord]
    experiments: TypedDomainRegistry[ExperimentId, ExperimentRecord]
    training_profiles: TypedDomainRegistry[TrainingProfileId, TrainingProfileRecord]
    checkpoint_profiles: TypedDomainRegistry[CheckpointProfileId, CheckpointProfileRecord]
    seed_cohorts: TypedDomainRegistry[SeedCohortId, SeedCohortRecord]
    fingerprint: Fingerprint

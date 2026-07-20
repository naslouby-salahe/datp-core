"""Resolved domain catalogue models representing scientific definitions without generic mappings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

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
    ThresholdPolicyId,
    TrainingProfileId,
)
from datp_core.domain.values import PositiveFloat, PositiveInt, Seed, TypedDomainRegistry


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


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainingProfileRecord:
    identifier: TrainingProfileId
    training_loss: str
    optimizer_type: str
    learning_rate: PositiveFloat
    max_rounds: PositiveInt
    local_epochs: PositiveInt


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointProfileRecord:
    identifier: CheckpointProfileId
    strategy: str
    selection_metric: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SeedCohortRecord:
    identifier: SeedCohortId
    paired_seed_count: PositiveInt
    seeds: tuple[Seed, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluationSpecRecord:
    label: str
    threshold_policy_id: ThresholdPolicyId


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisSpecRecord:
    label: str
    kind: str
    result_type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PopulationRecord:
    identifier: PopulationId
    dataset_id: DatasetId
    setup_id: DatasetSetupId
    metric_bundle_id: MetricBundleId


@dataclass(frozen=True, slots=True, kw_only=True)
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
    evaluations: tuple[EvaluationSpecRecord, ...]
    analyses: tuple[AnalysisSpecRecord, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedCatalogue:
    schema_version: PositiveInt
    populations: TypedDomainRegistry[PopulationId, PopulationRecord]
    experiments: TypedDomainRegistry[ExperimentId, ExperimentRecord]
    training_profiles: TypedDomainRegistry[TrainingProfileId, TrainingProfileRecord]
    checkpoint_profiles: TypedDomainRegistry[CheckpointProfileId, CheckpointProfileRecord]
    seed_cohorts: TypedDomainRegistry[SeedCohortId, SeedCohortRecord]
    fingerprint: Fingerprint

"""Top-level resolved project configuration, validation report, and configuration drift report types."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datp_core.config.domain_models import (
    AnalysisConventions,
    NormalizationFitScopes,
    PopulationReadinessRule,
)
from datp_core.config.operational_contracts import (
    CommunicationEstimationContractRecord,
    OperationalInputsRecord,
)
from datp_core.config.report_profiles import ReportDefaultsRecord, ReportProfileRecord
from datp_core.config.resolution.protocols.training import ProtocolDeterminismRecord
from datp_core.config.resolution.runtime import ResolvedProjectPaths, ResolvedRuntimeConfiguration
from datp_core.config.statistical_profiles import NestedReplicatePolicyRecord, StatisticalProfileRecord
from datp_core.core.hashing import CanonicalProjection, Fingerprint
from datp_core.core.identifiers import (
    CheckpointProfileId,
    DatasetId,
    EligibilityPolicyId,
    ExperimentId,
    MetricBundleId,
    NormalizationStrategyId,
    PopulationId,
    SeedCohortId,
    StatisticalProfileId,
    ThresholdPolicyId,
    TrainingProfileId,
)
from datp_core.core.registry import TypedDomainRegistry
from datp_core.data.contracts.dataset import ResolvedDataset
from datp_core.data.contracts.eligibility import EligibilityPolicy
from datp_core.data.contracts.materialization import NormalizationConfig
from datp_core.evaluation.specs import (
    EvaluationResultContract,
    MetricBundleSpec,
    MetricDefinitions,
)
from datp_core.experiments import (
    EligibilityGateRecord,
    EvidenceRole,
    ExperimentRecord,
    PopulationRecord,
    ResultTypeRecord,
)
from datp_core.learning.contracts.checkpoints import CheckpointProfile
from datp_core.learning.contracts.model import (
    AdamOptimizerProfile,
    BatchingProfile,
    DenseAutoencoderProfile,
    LearningDataSchema,
)
from datp_core.learning.contracts.training import SeedCohortProfile, TrainingProfile
from datp_core.learning.model.runtime import SeedDerivationProfile, TorchRuntimeProfile
from datp_core.thresholding.policies import ThresholdPolicyRecord


class ResolvedProjectConfiguration(BaseModel):
    """Single resolved project configuration authority loaded once during composition root
    initialization."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    datasets: TypedDomainRegistry[DatasetId, ResolvedDataset]
    populations: TypedDomainRegistry[PopulationId, PopulationRecord]
    experiments: TypedDomainRegistry[ExperimentId, ExperimentRecord]
    capabilities: tuple[str, ...]
    suppression_behaviors: tuple[str, ...]
    population_readiness_rule: PopulationReadinessRule
    eligibility_gates: TypedDomainRegistry[str, EligibilityGateRecord]
    analysis_conventions: AnalysisConventions
    training_profiles: TypedDomainRegistry[TrainingProfileId, TrainingProfile]
    checkpoint_profiles: TypedDomainRegistry[CheckpointProfileId, CheckpointProfile]
    seed_cohorts: TypedDomainRegistry[SeedCohortId, SeedCohortProfile]
    statistical_profiles: TypedDomainRegistry[StatisticalProfileId, StatisticalProfileRecord]
    threshold_policies: TypedDomainRegistry[ThresholdPolicyId, ThresholdPolicyRecord]
    model_architectures: TypedDomainRegistry[str, DenseAutoencoderProfile]
    optimizers: TypedDomainRegistry[str, AdamOptimizerProfile]
    batching_profiles: TypedDomainRegistry[str, BatchingProfile]
    learning_data_schemas: TypedDomainRegistry[str, LearningDataSchema]
    runtime_profile: TorchRuntimeProfile
    seed_derivation: SeedDerivationProfile
    eligibility_policies: TypedDomainRegistry[EligibilityPolicyId, EligibilityPolicy]
    normalization_strategies: TypedDomainRegistry[NormalizationStrategyId, NormalizationConfig]
    metric_bundles: TypedDomainRegistry[MetricBundleId, MetricBundleSpec]
    metric_definitions: MetricDefinitions
    communication_estimation_contract: CommunicationEstimationContractRecord
    operational_inputs: OperationalInputsRecord
    report_profiles: TypedDomainRegistry[str, ReportProfileRecord]
    communication_estimation: dict[str, object] | None
    protocol_determinism: ProtocolDeterminismRecord
    normalization_fit_scopes: NormalizationFitScopes
    normalization_leakage_rule: str
    nested_replicate_policy: NestedReplicatePolicyRecord
    result_types: TypedDomainRegistry[str, ResultTypeRecord]
    evaluation_result_contract: EvaluationResultContract
    report_defaults: ReportDefaultsRecord
    runtime: ResolvedRuntimeConfiguration
    paths: ResolvedProjectPaths
    scientific_fingerprint: Fingerprint
    execution_fingerprint: Fingerprint
    scientific_projection: CanonicalProjection
    execution_projection: CanonicalProjection

    def primary_federated_checkpoint_experiment(self) -> ExperimentRecord:
        """Return the sole confirmatory FedAvg experiment authorized to choose the shared round."""
        from datp_core.learning.contracts.checkpoints import AuthorizedLookupSelection

        candidates = tuple(
            experiment
            for experiment in self.experiments.values()
            if experiment.evidence_role is EvidenceRole.CONFIRMATORY
            and self.training_profiles.contains(experiment.training_profile_id)
            and self.checkpoint_profiles.contains(experiment.checkpoint_profile_id)
            and isinstance(
                self.checkpoint_profiles.get(experiment.checkpoint_profile_id).selection,
                AuthorizedLookupSelection,
            )
        )
        if len(candidates) != 1:
            raise ValueError("Configuration must define exactly one confirmatory primary FedAvg checkpoint selector")
        return candidates[0]

    def primary_ditto_selection_experiment(self) -> ExperimentRecord:
        """Return the sole natural-regime Ditto experiment allowed to select its proximal weight."""
        from datp_core.learning.contracts.training import DittoTrainingProfile

        candidates = tuple(
            experiment
            for experiment in self.experiments.values()
            if self.training_profiles.contains(experiment.training_profile_id)
            and isinstance(self.training_profiles.get(experiment.training_profile_id), DittoTrainingProfile)
            and experiment.personalization_parameter_selection_source is None
        )
        if len(candidates) != 1:
            raise ValueError("Configuration must define exactly one natural-regime Ditto parameter selector")
        return candidates[0]


class ValidationReport(BaseModel):
    """Typed validation result report."""

    model_config = ConfigDict(frozen=True)
    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    datasets_checked: int
    experiments_checked: int
    threshold_policies_checked: int

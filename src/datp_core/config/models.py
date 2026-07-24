"""Top-level resolved project configuration, validation report, and configuration drift report types."""

from __future__ import annotations

from collections.abc import Mapping

from attrs import define

from datp_core.analysis.statistics.models import NestedReplicatePolicyRecord, StatisticalProfileRecord
from datp_core.artifacts.manifest import ArtifactIdentityRecord
from datp_core.config.resolution.protocols.training import ProtocolDeterminismRecord
from datp_core.config.resolution.runtime import ResolvedProjectPaths, ResolvedRuntimeConfiguration
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
from datp_core.data.contracts import EligibilityPolicyRecord, NormalizationStrategyRecord, ResolvedDataset
from datp_core.evaluation import (
    EvaluationResultContractRecord,
    MetricBundleRecord,
    MetricDefinitionsRecord,
)
from datp_core.analysis.operations.models import (
    CommunicationEstimationContractRecord,
    OperationalInputsRecord,
)
from datp_core.experiments import (
    EligibilityGateRecord,
    EvidenceRole,
    ExperimentRecord,
    PopulationRecord,
    ResultTypeRecord,
)
from datp_core.learning.models import (
    BatchingRecord,
    CheckpointAuthorization,
    CheckpointProfileRecord,
    ModelArchitectureRecord,
    OptimizerRecord,
    PersonalizationStrategy,
    SeedCohortRecord,
    TrainingProfileRecord,
)
from datp_core.reporting.models import ReportDefaultsRecord, ReportProfileRecord
from datp_core.thresholding.models import QuantileEstimatorRecord, ThresholdPolicyDefaultsRecord, ThresholdPolicyRecord


@define(frozen=True, slots=True, kw_only=True)
class ResolvedProjectConfiguration:
    """Single resolved project configuration authority loaded once during composition root
    initialization."""

    datasets: TypedDomainRegistry[DatasetId, ResolvedDataset]
    populations: TypedDomainRegistry[PopulationId, PopulationRecord]
    experiments: TypedDomainRegistry[ExperimentId, ExperimentRecord]
    capabilities: tuple[str, ...]
    suppression_behaviors: tuple[str, ...]
    population_readiness_rule: Mapping[str, str | bool]
    eligibility_gates: TypedDomainRegistry[str, EligibilityGateRecord]
    analysis_conventions: Mapping[str, str]
    training_profiles: TypedDomainRegistry[TrainingProfileId, TrainingProfileRecord]
    checkpoint_profiles: TypedDomainRegistry[CheckpointProfileId, CheckpointProfileRecord]
    seed_cohorts: TypedDomainRegistry[SeedCohortId, SeedCohortRecord]
    statistical_profiles: TypedDomainRegistry[StatisticalProfileId, StatisticalProfileRecord]
    threshold_policies: TypedDomainRegistry[ThresholdPolicyId, ThresholdPolicyRecord]
    model_architectures: TypedDomainRegistry[str, ModelArchitectureRecord]
    optimizers: TypedDomainRegistry[str, OptimizerRecord]
    batching_profiles: TypedDomainRegistry[str, BatchingRecord]
    eligibility_policies: TypedDomainRegistry[EligibilityPolicyId, EligibilityPolicyRecord]
    normalization_strategies: TypedDomainRegistry[NormalizationStrategyId, NormalizationStrategyRecord]
    quantile_estimators: TypedDomainRegistry[str, QuantileEstimatorRecord]
    metric_bundles: TypedDomainRegistry[MetricBundleId, MetricBundleRecord]
    metric_definitions: MetricDefinitionsRecord
    artifact_identity: ArtifactIdentityRecord
    communication_estimation_contract: CommunicationEstimationContractRecord
    operational_inputs: OperationalInputsRecord
    report_profiles: TypedDomainRegistry[str, ReportProfileRecord]
    communication_estimation: Mapping[str, object] | None
    protocol_determinism: ProtocolDeterminismRecord
    normalization_fit_scopes: Mapping[str, str]
    normalization_leakage_rule: str
    threshold_policy_defaults: ThresholdPolicyDefaultsRecord
    nested_replicate_policy: NestedReplicatePolicyRecord
    result_types: TypedDomainRegistry[str, ResultTypeRecord]
    evaluation_result_contract: EvaluationResultContractRecord
    report_defaults: ReportDefaultsRecord
    runtime: ResolvedRuntimeConfiguration
    paths: ResolvedProjectPaths
    scientific_fingerprint: Fingerprint
    execution_fingerprint: Fingerprint
    scientific_projection: CanonicalProjection
    execution_projection: CanonicalProjection

    def primary_federated_checkpoint_experiment(self) -> ExperimentRecord:
        """Return the sole confirmatory FedAvg experiment authorized to choose the shared round."""
        candidates = tuple(
            experiment
            for experiment in self.experiments.values()
            if experiment.evidence_role is EvidenceRole.CONFIRMATORY
            and self.training_profiles.contains(experiment.training_profile_id)
            and self.training_profiles.get(experiment.training_profile_id).checkpoint_authorization
            == CheckpointAuthorization.PRIMARY_SELECTION_COMPUTED_ONCE
        )
        if len(candidates) != 1:
            raise ValueError(
                "Configuration must define exactly one confirmatory primary FedAvg checkpoint selector"
            )
        return candidates[0]

    def primary_ditto_selection_experiment(self) -> ExperimentRecord:
        """Return the sole natural-regime Ditto experiment allowed to select its proximal weight."""
        candidates = tuple(
            experiment
            for experiment in self.experiments.values()
            if self.training_profiles.contains(experiment.training_profile_id)
            and self.training_profiles.get(experiment.training_profile_id).personalization
            == PersonalizationStrategy.DITTO
            and experiment.personalization_parameter_selection_source is None
        )
        if len(candidates) != 1:
            raise ValueError(
                "Configuration must define exactly one natural-regime Ditto parameter selector"
            )
        return candidates[0]


@define(frozen=True, slots=True, kw_only=True)
class ValidationReport:
    """Typed validation result report."""

    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    datasets_checked: int
    experiments_checked: int
    threshold_policies_checked: int

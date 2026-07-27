"""Immutable analysis execution context — sole authority for evaluation lookups,
context construction, and typed domain operations.

Capability modules must use this context instead of constructing
evaluation/model/selection contexts manually, calling ``getattr(policy, …)``, or
performing ``next(item for item in …)`` searches.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datp_core.analysis.contracts import QuantileThresholdPolicy
from datp_core.analysis.errors import InvalidAnalysisConfigurationError
from datp_core.analysis.runtime.artifacts import AnalysisArtifactRepository
from datp_core.analysis.statistics.inference import StatisticalAnalysisUseCase
from datp_core.config.operational_contracts import CommunicationEstimationContractRecord, OperationalInputsRecord
from datp_core.core.identifiers import EvaluationLabel, PartitionConditionId, PopulationId, ThresholdPolicyId
from datp_core.core.registry import TypedDomainRegistry
from datp_core.core.seeding import Seed
from datp_core.evaluation.definitions.metrics import MetricDefinitionsRecord
from datp_core.experiments import EvaluationSpecRecord, ExperimentRecord
from datp_core.learning.contracts.seeds import SeedCohortRecord
from datp_core.pipeline.stages.context import DataContext, EvaluationContext, TrainingContext
from datp_core.thresholding.policies import ThresholdPolicyRecord


class AnalysisExecutionContext(BaseModel):
    """Immutable context holding resolved configuration and artifact access for one analysis run."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    threshold_policies: TypedDomainRegistry[ThresholdPolicyId, ThresholdPolicyRecord]
    seed_cohort: SeedCohortRecord
    metric_definitions: MetricDefinitionsRecord
    operational_inputs: OperationalInputsRecord
    communication_estimation_contract: CommunicationEstimationContractRecord
    artifacts: AnalysisArtifactRepository
    experiment: ExperimentRecord
    seeds: tuple[Seed, ...]
    statistical_analysis: StatisticalAnalysisUseCase

    def evaluation(self, label: EvaluationLabel) -> EvaluationSpecRecord:
        """Return the evaluation spec for *label*."""
        for item in self.experiment.evaluations:
            if item.label == label.value:
                return item
        raise InvalidAnalysisConfigurationError(
            f"Experiment '{self.experiment.display_name}' has no evaluation labelled '{label.value}'"
        )

    def threshold_policy_id(self, evaluation_label: EvaluationLabel) -> ThresholdPolicyId:
        """Return the typed threshold-policy identifier for an evaluation."""
        return self.evaluation(evaluation_label).threshold_policy_id

    def quantile_for_evaluation(self, evaluation_label: EvaluationLabel) -> float:
        """Return the quantile of the threshold policy bound to *evaluation_label*."""
        policy = self.threshold_policies.get(self.threshold_policy_id(evaluation_label))
        if not isinstance(policy, QuantileThresholdPolicy):
            raise InvalidAnalysisConfigurationError(
                f"Evaluation '{evaluation_label.value}' does not bind a quantile threshold policy"
            )
        return float(policy.quantile)

    def evaluation_context(
        self,
        label: EvaluationLabel,
        seed: Seed,
        *,
        partition_condition: PartitionConditionId | None = None,
        proximal_mu: float | None = None,
        ditto_weight: float | None = None,
        threshold_quantile: float | None = None,
        shrinkage_weight: float | None = None,
        calibration_sample_count: int | None = None,
        calibration_replicate: int | None = None,
        fingerprint_features: tuple[str, ...] | None = None,
    ) -> EvaluationContext:
        """Construct an ``EvaluationContext`` with complete evaluation metadata."""
        eval_spec = self.evaluation(label)
        return EvaluationContext(
            experiment_id=self.experiment.identifier,
            seed=seed.value,
            evaluation_label=label.value,
            population_id=eval_spec.population_id,
            recalibration_mode=eval_spec.recalibration_mode,
            partition_condition=partition_condition.value if partition_condition is not None else None,
            federated_proximal_mu=proximal_mu,
            ditto_proximal_weight=ditto_weight,
            threshold_quantile=threshold_quantile,
            shrinkage_weight=shrinkage_weight,
            calibration_sample_count=calibration_sample_count,
            calibration_replicate=calibration_replicate,
            fingerprint_features=fingerprint_features,
        )

    def score_context(
        self,
        label: EvaluationLabel,
        seed: Seed,
        *,
        partition_condition: PartitionConditionId | None = None,
        proximal_mu: float | None = None,
        ditto_weight: float | None = None,
        calibration_sample_count: int | None = None,
        calibration_replicate: int | None = None,
        fingerprint_features: tuple[str, ...] | None = None,
    ) -> EvaluationContext:
        """Construct an ``EvaluationContext`` for score generation artifacts."""
        eval_spec = self.evaluation(label)
        return EvaluationContext(
            experiment_id=self.experiment.identifier,
            seed=seed.value,
            evaluation_label=label.value,
            population_id=eval_spec.population_id,
            recalibration_mode=eval_spec.recalibration_mode,
            partition_condition=partition_condition.value if partition_condition is not None else None,
            federated_proximal_mu=proximal_mu,
            ditto_proximal_weight=ditto_weight,
            calibration_sample_count=calibration_sample_count,
            calibration_replicate=calibration_replicate,
            fingerprint_features=fingerprint_features,
        )

    def model_context(
        self,
        seed: Seed,
        *,
        population_id: PopulationId | None = None,
    ) -> TrainingContext:
        """Construct a ``TrainingContext`` for model training / checkpoint artifacts."""
        pop_id = (
            population_id
            if population_id is not None
            else (self.experiment.population_ids[0] if self.experiment.population_ids else None)
        )
        return TrainingContext(
            experiment_id=self.experiment.identifier,
            seed=seed.value,
            population_id=pop_id,
        )

    def selection_context(
        self,
        seed: Seed,
    ) -> DataContext:
        """Construct a ``DataContext`` for checkpoint selection artifacts."""
        return DataContext(
            experiment_id=self.experiment.identifier,
            seed=seed.value,
        )
